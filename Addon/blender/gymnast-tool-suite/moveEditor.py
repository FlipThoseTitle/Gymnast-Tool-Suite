# #################### #
# Move Editor
# #################### #
#
#  Edits Vector's moves.xml: Moves, Event Groups, Reaction Groups and Sounds,
#  each in its own tab, and previews Moves on the timeline.
#
#  Works together with Animation Tools (animationPanel.py):



import codecs
import json
import math
import os
import re
import sys
import time
import types
import xml.etree.ElementTree as ET
from html import unescape

import bpy
from bpy.props import (BoolProperty, CollectionProperty, EnumProperty, FloatProperty,
                       IntProperty, PointerProperty, StringProperty)





# ============================================================================ #
#  Constants
# ============================================================================ #

CATEGORY = "Gymnast Tool Suite"

XML_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_.\-]*$")
ATTR_PAIR = re.compile(r'([A-Za-z_][A-Za-z0-9_.\-]*)\s*=\s*"([^"]*)"')
COMMENT_SEP = "\x1f"

# Physics direction: game Y points down, Blender Z points up
GAME_Y_TO_BLENDER_Z = -1.0

TABS = [
    ('MOVES', "Moves", "Edit the moves and their intervals, events and reactions", 'ARMATURE_DATA', 0),
    ('EVENT_GROUPS', "Event Groups", "Reusable sets of events, used by intervals", 'GROUP', 1),
    ('REACTION_GROUPS', "Reaction Groups", "Reusable lists of reactions, used by events", 'LINKED', 2),
    ('SOUNDS', "Sounds", "The sounds moves are allowed to play", 'SPEAKER', 3),
]

MOVE_TYPES = [
    ('1', "Normal", "Regular move that does not use physics"),
    ('2', "Physics", "Moves along a physics path (Binding, Velocity, Gravity)"),
    ('3', "Trick", "A trick. Needs an ID and an ItemName"),
    ('4', "Gadget", "Gadget move (unused in the base game)"),
    ('5', "Catch", "Hunter catch move. Needs the Arrest attribute in the level's model properties"),
]

SUB_TYPES = [
    ('NONE', "Nothing", "Not counted in the statistics"),
    ('1', "Jump", "Counts as a jump in the statistics"),
    ('2', "Slide", "Counts as a slide in the statistics"),
]

PIVOTS = [
    ('NPivot', "NPivot", "Objects and cutscenes"),
    ('COM', "COM", "Center of mass. Common for physics moves"),
    ('DetectorH', "DetectorH", "Moves that start on the ground or when landing"),
    ('DetectorV', "DetectorV", "Moves that start on a wall or when climbing"),
    ('CUSTOM', "Custom...", "Type any node name"),
]
PIVOT_IDS = {p[0] for p in PIVOTS if p[0] != 'CUSTOM'}

KEYS = [('Up', "Up", ""), ('Down', "Down", ""), ('Left', "Left", ""), ('Right', "Right", ""), ('C', "C", "")]

DETECTOR_STATES = [
    ('1', "Touches a collision", "The detector touches a collision"),
    ('2', "Leaves / touches nothing", "The detector leaves a collision, or touches nothing"),
]

COLLISION_TYPES = [
    ('1', "Regular collision", "Walls, floors and other regular collisions"),
    ('2', "Physics model", "Physics models such as stools or ladders"),
    ('3', "Regular model", "Regular models such as barrel_tower"),
]

SLOPES = [('NONE', "Any", "No requirement"), ('0', "Flat", "Not a slope"),
          ('1', "Downhill", "A downhill slope"), ('2', "Uphill", "An uphill slope")]

SIDES = [('NONE', "Any", "No requirement"), ('0', "Top (floor)", "Usual for DetectorH"),
         ('1', "Right", ""), ('2', "Bottom", ""), ('3', "Left (wall)", "Usual for DetectorV")]

CONDITION_KINDS = [
    ('Width', "Width", "Width of the touched collision"),
    ('Height', "Height", "Height of the touched collision"),
    ('DeltaX', "Distance X", "Horizontal distance of the node from a corner of the collision"),
    ('DeltaY', "Distance Y", "Vertical distance of the node from a corner of the collision"),
    ('VelosityX', "Speed X", "Horizontal speed of the node (always positive)"),
    ('VelosityY', "Speed Y", "Vertical speed of the node (always positive)"),
]
CONDITION_TAGS = {c[0] for c in CONDITION_KINDS}

CONDITION_NODES = [('H', "Ground detector (H)", "DetectorH"), ('V', "Wall detector (V)", "DetectorV"),
                   ('C', "Any collidable node (C)", "Any collidable node")]

CORNERS = [('0', "Top Left", ""), ('1', "Top Right", ""), ('2', "Bottom Right", ""), ('3', "Bottom Left", "")]

EVENT_TYPES = [
    ('Keys', "Key Press", "The player presses a key"),
    ('DetectorH', "Ground Detector", "DetectorH (below the feet) touches or leaves a collision"),
    ('DetectorV', "Wall Detector", "DetectorV (in front of the body) touches or leaves a collision"),
    ('OnCollision', "Collision", "Any node of the character touches something"),
    ('OnTrigger', "Trigger Area", "The player is inside a trigger area (OnTrigger)"),
    ('OnArea', "Area", "The player is inside an area (OnArea)"),
    ('OnEnd', "Interval End", "The interval reaches its last frame"),
    ('OnFrame', "On Frame", "A specific frame is reached"),
]
EVENT_TAGS = {e[0] for e in EVENT_TYPES}
EVENT_LABEL = {e[0]: e[1] for e in EVENT_TYPES}
SEQUENTIAL_EVENTS = {'OnEnd', 'OnFrame'}

# Reactions that are not moves. Their FirstFrame and Priority are fixed.
SPECIAL_REACTIONS = {
    "Death": "The player dies. Always Start Frame 1 and Priority 1",
}


def is_special(name):
    return name in SPECIAL_REACTIONS
DETECTOR_EVENTS = {'DetectorH', 'DetectorV'}

# <root> section tag -> tag of its entries
SECTIONS = (("Sounds", "Sound"), ("EventGroups", "EventGroup"), ("ReactionGroups", "ReactionGroup"), ("Moves", None))





# ============================================================================ #
#  Attribute tables
# ============================================================================ #
#
#  XML attribute -> (property, kind, default)
#  Attributes not listed here are kept in "Other Attributes" and saved unchanged.
#
#  kinds: int, float, bool, str, enum, opt (enum with a 'NONE' item meaning "leave out"),
#         pivot (enum + custom text), optfloat (checkbox + value)

MOVE_FIELDS = {
    "ID": ("move_id", "int", 0),
    "ItemName": ("item_name", "str", ""),
    "Type": ("move_type", "enum", '1'),
    "SubType": ("sub_type", "opt", 'NONE'),
    "Loop": ("loop", "bool", False),
    "Mirror": ("mirror", "bool", False),
    "FileName": ("file_name", "str", ""),
    "MidFrames": ("mid_frames", "int", 0),
    "FirstFrame": ("first_frame", "int", 0),
    "EndFrame": ("end_frame", "int", 0),
    "PivotNode": ("pivot", "pivot", 'NPivot'),
    "Priority": ("priority", "int", 0),
    "VelocityX": ("velocity_x", "float", 0.0),
    "VelocityY": ("velocity_y", "float", 0.0),
    "Binding": ("binding", "bool", False),
    "Gravity": ("gravity", "float", 0.0),
    "DeltaDetectorH": ("delta_detector_h", "float", 0.0),
    "DeltaDetectorV": ("delta_detector_v", "float", 0.0),
    "LandingPositionDetectorH": ("landing_detector_h", "float", 0.0),
    "LandingPositionDetectorV": ("landing_detector_v", "float", 0.0),
    "AutoPositionDetectorH": ("auto_detector_h", "float", 0.0),
    "AutoPositionDetectorV": ("auto_detector_v", "float", 0.0),
    "PlatformAnticipationFrames": ("platform_anticipation", "float", 0.0),
}

INTERVAL_FIELDS = {
    "Start": ("start", "int", 0),
    "End": ("end", "int", 0),
    "Lock": ("lock", "bool", False),
    "Safe": ("safe", "bool", False),
    "SafeH": ("safe_h", "bool", False),
    "SafeV": ("safe_v", "bool", False),
    "ConditionlessPlatformBoundH": ("bound_h", "bool", False),
    "ConditionlessPlatformBoundV": ("bound_v", "bool", False),
    "ConditionlessPlatformBoundC": ("bound_c", "bool", False),
    "NoPlatformBoundX": ("unbound_x", "bool", False),
    "NoPlatformBoundY": ("unbound_y", "bool", False),
    "Groups": ("groups", "str", ""),
    "Action": ("action", "str", ""),
    "LT": ("lt", "str", ""),
    "RB": ("rb", "str", ""),
}

REACTION_FIELDS = {
    "FirstFrame": ("first_frame", "int", 0),
    "Priority": ("priority", "int", 0),
    "TriggerName": ("trigger_name", "str", ""),
    "OnEndTrigger": ("on_end_trigger", "bool", False),
    "Sides": ("sides", "opt", 'NONE'),
    "CornerCling": ("corner_cling", "bool", False),
    "InsideH": ("inside_h", "bool", False),
    "InsideV": ("inside_v", "bool", False),
    "SlopeH": ("slope_h", "opt", 'NONE'),
    "SlopeV": ("slope_v", "opt", 'NONE'),
    "SafeH": ("safe_h", "bool", False),
    "SafeV": ("safe_v", "bool", False),
    "NodesWI": ("nodes_wi", "str", ""),
    "Reverse": ("reverse", "bool", False),
}

CONDITION_FIELDS = {
    "Min": (("use_min", "min"), "optfloat", 0.0),
    "Max": (("use_max", "max"), "optfloat", 0.0),
    "Type": ("node", "enum", 'V'),
    "Corner": ("corner", "enum", '0'),
}

SOUND_FIELDS = {
    "Name": ("name", "str", ""),
    "Type": ("sound_type", "int", 0),
}

NAME_FIELDS = {"Name": ("name", "str", "")}


def event_fields(event):
    fields = {"Groups": ("groups", "str", "")}
    kind = event.event_type
    if kind == 'Keys':
        fields["Key"] = ("key", "enum", 'Up')
    elif kind == 'OnFrame':
        fields["Frame"] = ("frame", "int", 0)
    elif kind in DETECTOR_EVENTS:
        fields[event.type_key or "Type"] = ("detector_state", "enum", '1')
    elif kind == 'OnCollision':
        fields[event.type_key or "Types"] = ("collision_type", "enum", '1')
    return fields





# ============================================================================ #
#  Helpers
# ============================================================================ #

class MoveEditorError(Exception):
    """A problem shown in Blender's status bar."""


_LOADING = 0            # > 0 while the editor sets many values (skips update callbacks)


def get_settings(context):
    return context.scene.gymnast_move_editor


def is_loaded(settings):
    return bool(settings.template)


def _wrap(text, width=42):
    lines, line = [], ""
    for word in text.split():
        if line and len(line) + len(word) + 1 > width:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}" if line else word
    if line:
        lines.append(line)
    return lines


def draw_wrapped(layout, text, icon='NONE', width=42):
    col = layout.column(align=True)
    for i, line in enumerate(_wrap(text, width)):
        col.label(text=line, icon=icon if i == 0 else ('BLANK1' if icon != 'NONE' else 'NONE'))


def section(layout, idname, title, icon='NONE', closed=True, toggle=None):
    """A collapsible group of settings. Returns the layout to draw into, or None when closed.
    toggle: (data, property) of a checkbox drawn in the header, for sections it switches on."""
    if hasattr(layout, "panel"):
        header, body = layout.panel(idname, default_closed=closed)
        header.use_property_split = False
        if toggle:
            header.prop(toggle[0], toggle[1], text="")
            header.label(text=title)
        else:
            header.label(text=title, icon=icon)
        if body is not None:
            body.use_property_split = True
            body.use_property_decorate = False
            if toggle:
                body.active = bool(getattr(toggle[0], toggle[1]))
        return body
    box = layout.box()
    if toggle:
        box.prop(toggle[0], toggle[1], text=title)
    else:
        box.label(text=title, icon=icon)
    return box


def raw_attrs(item):
    try:
        return json.loads(item.raw) if item.raw else []
    except ValueError:
        return []


def has_attr(item, key):
    return any(k == key for k, _ in raw_attrs(item))


def format_attrs(pairs):
    return " ".join(f'{k}="{_escape(v)}"' for k, v in pairs)


def parse_attrs(text):
    return [(k, unescape(v)) for k, v in ATTR_PAIR.findall(text or "")]


def _escape(value):
    return (value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
            .replace("\n", "&#10;").replace("\r", "&#13;").replace("\t", "&#9;"))


def _strict_int(text):
    return int(text) if re.fullmatch(r"\s*-?\d+\s*", text) else None


def _fmt_float(value):
    text = f"{value:.6g}"
    return "0" if text == "-0" else text


def pivot_name(move):
    return move.pivot_custom.strip() if move.pivot == 'CUSTOM' else move.pivot


def set_name_silent(item, name):
    """Renames a Move / group / sound without renaming the references to the old name."""
    global _LOADING
    _LOADING += 1
    try:
        item.name = name
        item.prev_name = name
    finally:
        _LOADING -= 1


def unique_name(collection, base):
    names = {item.name for item in collection}
    if base not in names:
        return base
    n = 2
    while f"{base}{n}" in names:
        n += 1
    return f"{base}{n}"


def copy_group(src, dst):
    """Copies every property (and nested collection) of one PropertyGroup to another."""
    for prop in src.bl_rna.properties:
        ident = prop.identifier
        if ident == "rna_type":
            continue
        if prop.type == 'COLLECTION':
            target = getattr(dst, ident)
            target.clear()
            for item in getattr(src, ident):
                copy_group(item, target.add())
        elif not prop.is_readonly:
            try:
                setattr(dst, ident, getattr(src, ident))
            except (AttributeError, TypeError):
                pass


def pick(collection, index):
    return collection[index] if 0 <= index < len(collection) else None


def split_names(text):
    return [p for p in text.split("|") if p]


def replace_name(text, old, new):
    parts = text.split("|")
    return "|".join(new if p == old else p for p in parts) if old in parts else text




# ---------------------------------------------------------------------------- #
#  Selection
# ---------------------------------------------------------------------------- #

def active(settings):
    """(move, interval, event, reaction) selected in the Moves tab. Missing levels are None."""
    move = pick(settings.moves, settings.active_move_index)
    interval = pick(move.intervals, move.active_interval_index) if move else None
    event = pick(interval.events, interval.active_event_index) if interval else None
    reaction = pick(event.reactions, event.active_reaction_index) if event else None
    return move, interval, event, reaction


def event_owner(settings):
    """What the Events editor is editing: the selected Interval (Moves tab) or Event Group."""
    if settings.tab == 'MOVES':
        return active(settings)[1]
    if settings.tab == 'EVENT_GROUPS':
        return pick(settings.event_groups, settings.active_event_group_index)
    return None


def current_event(settings):
    owner = event_owner(settings)
    return pick(owner.events, owner.active_event_index) if owner else None


def reaction_owner(settings):
    """What the Reactions editor is editing: the selected Event or Reaction Group."""
    if settings.tab == 'REACTION_GROUPS':
        return pick(settings.reaction_groups, settings.active_reaction_group_index)
    return current_event(settings)


def current_reaction(settings):
    owner = reaction_owner(settings)
    return pick(owner.reactions, owner.active_reaction_index) if owner else None





# ---------------------------------------------------------------------------- #
#  References between sections
# ---------------------------------------------------------------------------- #

def iter_events(settings):
    for move in settings.moves:
        for interval in move.intervals:
            yield from interval.events
    for group in settings.event_groups:
        yield from group.events


def iter_reactions(settings):
    for event in iter_events(settings):
        yield from event.reactions
    for group in settings.reaction_groups:
        yield from group.reactions


def iter_sound_uses(settings):
    for move in settings.moves:
        for interval in move.intervals:
            yield from interval.sounds
    for event in iter_events(settings):
        yield from event.sounds


def rename_references(settings, kind, old, new):
    """Points every reference to `old` at `new`. Returns how many were changed."""
    count = 0
    if kind == 'MOVE':
        for reaction in iter_reactions(settings):
            if reaction.name == old:
                reaction.name = new
                count += 1
    elif kind == 'EVENT_GROUP':
        for move in settings.moves:
            for interval in move.intervals:
                if old in split_names(interval.groups):
                    interval.groups = replace_name(interval.groups, old, new)
                    count += 1
    elif kind == 'REACTION_GROUP':
        for event in iter_events(settings):
            if old in split_names(event.groups):
                event.groups = replace_name(event.groups, old, new)
                count += 1
    elif kind == 'SOUND':
        for sound in iter_sound_uses(settings):
            if old in split_names(sound.name):
                sound.name = replace_name(sound.name, old, new)
                count += 1
    return count


def count_uses(settings, kind, name):
    if kind == 'EVENT_GROUP':
        return sum(name in split_names(i.groups) for m in settings.moves for i in m.intervals)
    if kind == 'REACTION_GROUP':
        return sum(name in split_names(e.groups) for e in iter_events(settings))
    if kind == 'SOUND':
        return sum(name in split_names(s.name) for s in iter_sound_uses(settings))
    if kind == 'MOVE':
        return sum(r.name == name for r in iter_reactions(settings))
    return 0





# ---------------------------------------------------------------------------- #
#  Animation Tools link
# ---------------------------------------------------------------------------- #

_NODE_ORDER = {"key": None, "nodes": None}

VECTOR_NODE_COUNT = 46          # Vector's usual character. Other counts only get a warning
SHADOW_FIGHT_NODE_COUNT = 67    # Shadow Fight 2's character: not supported
SHADOW_FIGHT_MESSAGE = "Shadow Fight 2 is not supported"


def _anim_api(namespace):
    """import_bin / get_node_order / AnimationError from a module's globals, or None."""
    import_bin = namespace.get("import_bin")
    get_order = namespace.get("get_node_order")
    error = namespace.get("AnimationError")
    if callable(import_bin) and callable(get_order) and isinstance(error, type) and issubclass(error, BaseException):
        return types.SimpleNamespace(import_bin=import_bin, get_node_order=get_order, AnimationError=error)
    return None


def _subclasses(cls):
    for sub in cls.__subclasses__():
        yield sub
        yield from _subclasses(sub)


def anim_module():
    """Animation Tools' functions, found through its registered Import Animation operator.
    Works whether animationPanel is part of an add-on or run as a Text block."""
    for cls in _subclasses(bpy.types.Operator):
        if getattr(cls, "bl_idname", "") == "import.bin" and getattr(cls, "is_registered", True):
            run = getattr(cls, "run", None) or getattr(cls, "execute", None)
            api = _anim_api(getattr(run, "__globals__", {}))
            if api:
                return api
    for module in list(sys.modules.values()):
        if isinstance(module, types.ModuleType) and not module.__name__.startswith("bpy"):
            api = _anim_api(vars(module))
            if api:
                return api
    return None


def anim_settings(scene):
    return getattr(scene, "gymnast_tool_props", None)


def node_order(scene):
    """Node order from Animation Tools' Dependencies XML + Model XML (cached until the files change)."""
    anim, aset = anim_module(), anim_settings(scene)
    if anim is None or aset is None:
        raise MoveEditorError("Animation Tools is not available. Enable it to preview moves.")

    paths = [bpy.path.abspath(p) if p else "" for p in (aset.dependencies_xml, aset.model_xml)]
    stamps = []
    for path in paths:
        try:
            stamps.append(os.path.getmtime(path) if path else 0)
        except OSError:
            stamps.append(-1)
    key = (tuple(paths), tuple(stamps))
    if _NODE_ORDER["key"] != key:
        try:
            nodes = anim.get_node_order(aset)
        except anim.AnimationError as err:
            raise MoveEditorError(f"Animation Tools: {err}")
        _NODE_ORDER.update(key=key, nodes=nodes)
    return _NODE_ORDER["nodes"]


def frame_step(scene):
    """Timeline frames per animation frame. Same formula as Animation Tools' import."""
    aset = anim_settings(scene)
    speed = aset.animation_speed if aset else 1.0
    return (scene.render.fps / 20.0) / (speed or 1.0)


def character_status(scene):
    """(message, level): level is 'OK', 'WARNING' (unusual node count, still works) or 'ERROR'."""
    try:
        nodes = node_order(scene)
    except MoveEditorError as err:
        return str(err), 'ERROR'
    count = len(nodes)
    if count == SHADOW_FIGHT_NODE_COUNT:
        return f"{SHADOW_FIGHT_MESSAGE} ({count} nodes)", 'ERROR'
    if count != VECTOR_NODE_COUNT:
        return f"{count} nodes, Vector usually has {VECTOR_NODE_COUNT}", 'WARNING'
    return f"Character: {count} nodes (from Animation Tools)", 'OK'





# ---------------------------------------------------------------------------- #
#  Animation files
# ---------------------------------------------------------------------------- #

_BINS = {"key": None, "files": [], "lower": {}}
_BIN_FRAMES = {}


def bin_folder(settings):
    return bpy.path.abspath(settings.bin_folder) if settings.bin_folder else ""


def list_bins(settings):
    folder = bin_folder(settings)
    try:
        stamp = os.stat(folder).st_mtime_ns if folder and os.path.isdir(folder) else None
    except OSError:
        stamp = None
    if stamp is None:
        return [], {}
    if _BINS["key"] != (folder, stamp):
        try:
            files = sorted((f for f in os.listdir(folder) if f.lower().endswith((".bin", ".bytes"))), key=str.lower)
        except OSError:
            files = []
        _BINS.update(key=(folder, stamp), files=files, lower={f.lower(): f for f in files})
    return _BINS["files"], _BINS["lower"]


def bin_path(settings, file_name):
    """Full path of an animation file, matching the name without caring about capitals. '' when missing."""
    if not file_name:
        return ""
    folder = bin_folder(settings)
    path = os.path.join(folder, file_name)
    if os.path.isfile(path):
        return path
    real = list_bins(settings)[1].get(file_name.lower())
    return os.path.join(folder, real) if real else ""


def bin_frame_count(path):
    try:
        st = os.stat(path)
    except OSError:
        return None
    key = (st.st_mtime_ns, st.st_size)
    cached = _BIN_FRAMES.get(path)
    if cached and cached[0] == key:
        return cached[1]
    count = None
    try:
        with open(path, "rb") as f:
            head = f.read(4)
        if len(head) == 4:
            count = int.from_bytes(head, "little", signed=True)
    except OSError:
        pass
    _BIN_FRAMES[path] = (key, count)
    return count







# ============================================================================ #
#  XML: reading
# ============================================================================ #
#
#  A comment is attached to the item that follows it (comment_before), so it is written
#  back in the same place. Anything the editor does not understand goes into extra_xml.

def _parse_text(text):
    parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
    parser.feed(text)
    return parser.close()


def read_xml_file(path):
    """(root, encoding, newline). Keeps comments."""
    with open(path, "rb") as f:
        raw = f.read()
    newline = "\r\n" if b"\r\n" in raw else "\n"
    encoding = "utf-8"
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    else:
        m = re.match(rb'\s*<\?xml[^>]*encoding\s*=\s*["\']([A-Za-z0-9._\-]+)["\']', raw)
        if m:
            encoding = m.group(1).decode("ascii")
    try:
        codecs.lookup(encoding)
    except LookupError:
        raise MoveEditorError(f"Unknown text encoding '{encoding}'.")
    text = re.sub(r"^\s*<\?xml[^>]*\?>", "", raw.decode(encoding, errors="replace"), count=1)
    try:
        return _parse_text(text), encoding, newline
    except ET.ParseError as err:
        raise MoveEditorError(f"Could not read '{os.path.basename(path)}': {err}")


def _element_text(el):
    """One child element (or comment) as a compact XML string."""
    if el.tag is ET.Comment:
        return f"<!--{el.text or ''}-->"
    el.tail = None
    return ET.tostring(el, encoding="unicode")


def _comment_xml(comments):
    return "".join(f"<!--{c}-->" for c in comments)


def _set_field(item, spec, value):
    """Puts an XML value into a property. False when the value doesn't fit (it is kept as-is instead)."""
    prop, kind, default = spec
    rna = item.bl_rna.properties if hasattr(item, "bl_rna") else None
    if kind == "int":
        number = _strict_int(value)
        if number is None:
            return False
        if rna is not None and not rna[prop].hard_min <= number <= rna[prop].hard_max:
            return False            # out of range: kept unchanged instead of being clamped
        setattr(item, prop, number)
    elif kind in ("float", "optfloat"):
        try:
            number = float(value)
        except ValueError:
            return False
        if kind == "optfloat":
            setattr(item, prop[0], True)
            setattr(item, prop[1], number)
        else:
            setattr(item, prop, number)
    elif kind == "bool":
        if value not in ("0", "1"):
            return False
        setattr(item, prop, value == "1")
    elif kind in ("enum", "opt"):
        if rna is not None and value not in {i.identifier for i in rna[prop].enum_items}:
            return False
        setattr(item, prop, value)
    elif kind == "pivot":
        if value in PIVOT_IDS:
            item.pivot = value
        else:
            item.pivot = 'CUSTOM'
            item.pivot_custom = value
    else:
        setattr(item, prop, value)
    return True


def _apply_attrs(item, attrs, fields):
    item.raw = json.dumps(attrs)
    extras = [(k, v) for k, v in attrs if not (k in fields and _set_field(item, fields[k], v))]
    item.extra_attrs = format_attrs(extras)


def _read_condition(cond, el):
    cond.kind = el.tag
    _apply_attrs(cond, list(el.attrib.items()), CONDITION_FIELDS)
    cond.extra_xml = "".join(_element_text(c) for c in el)


def _read_reaction(reaction, el):
    reaction.name = el.tag
    _apply_attrs(reaction, list(el.attrib.items()), REACTION_FIELDS)
    extra = []
    for child in el:
        if isinstance(child.tag, str) and child.tag in CONDITION_TAGS:
            _read_condition(reaction.conditions.add(), child)
        else:
            extra.append(_element_text(child))
    reaction.extra_xml = "".join(extra)


def _read_reaction_list(owner, children):
    """Reactions with their comments. Returns comments left over at the end."""
    comments = []
    for child in children:
        if child.tag is ET.Comment:
            comments.append(child.text or "")
        elif isinstance(child.tag, str):
            reaction = owner.reactions.add()
            reaction.comment_before = COMMENT_SEP.join(comments)
            comments = []
            _read_reaction(reaction, child)
    return comments


def _read_sound(sound, el):
    _apply_attrs(sound, list(el.attrib.items()), SOUND_FIELDS)


def _read_event(event, el):
    event.event_type = el.tag
    attrs = list(el.attrib.items())
    keys = {k for k, _ in attrs}
    if el.tag in DETECTOR_EVENTS or el.tag == 'OnCollision':
        default = "Type" if el.tag in DETECTOR_EVENTS else "Types"
        event.type_key = "Types" if "Types" in keys and "Type" not in keys else ("Type" if "Type" in keys else default)
    _apply_attrs(event, attrs, event_fields(event))

    extra, comments = [], []
    event.wrapped = False
    for child in el:
        if child.tag is ET.Comment:
            comments.append(child.text or "")
        elif child.tag == "Sound":
            extra.append(_comment_xml(comments))
            comments = []
            _read_sound(event.sounds.add(), child)
        elif child.tag == "Reactions" and not event.wrapped:
            event.wrapped = True
            event.reactions_comment = COMMENT_SEP.join(comments)
            comments = []
            event.reaction_comments = _comment_xml(_read_reaction_list(event, child))
        else:
            extra.append(_comment_xml(comments) + _element_text(child))
            comments = []
    extra.append(_comment_xml(comments))
    event.extra_xml = "".join(extra)


def _read_events(owner, children, sounds=False):
    """Events (and, for intervals, Sounds) of an Interval or Event Group. Returns extra_xml."""
    extra, comments = [], []
    for child in children:
        if child.tag is ET.Comment:
            comments.append(child.text or "")
        elif sounds and child.tag == "Sound":
            extra.append(_comment_xml(comments))
            comments = []
            _read_sound(owner.sounds.add(), child)
        elif isinstance(child.tag, str) and child.tag in EVENT_TAGS:
            event = owner.events.add()
            event.comment_before = COMMENT_SEP.join(comments)
            comments = []
            _read_event(event, child)
        else:
            extra.append(_comment_xml(comments) + _element_text(child))
            comments = []
    extra.append(_comment_xml(comments))
    return "".join(extra)


def _read_interval(interval, el):
    _apply_attrs(interval, list(el.attrib.items()), INTERVAL_FIELDS)
    interval.extra_xml = _read_events(interval, el, sounds=True)


def _read_move(move, el):
    set_name_silent(move, el.tag)
    _apply_attrs(move, list(el.attrib.items()), MOVE_FIELDS)
    extra, comments = [], []
    for child in el:
        if child.tag is ET.Comment:
            comments.append(child.text or "")
        elif child.tag == "Interval":
            interval = move.intervals.add()
            interval.comment_before = COMMENT_SEP.join(comments)
            comments = []
            _read_interval(interval, child)
        else:
            extra.append(_comment_xml(comments) + _element_text(child))
            comments = []
    extra.append(_comment_xml(comments))
    move.extra_xml = "".join(extra)


def _read_named(item, el):
    _apply_attrs(item, list(el.attrib.items()), NAME_FIELDS)
    item.prev_name = item.name


def _read_event_group(group, el):
    _read_named(group, el)
    group.extra_xml = _read_events(group, el)


def _read_reaction_group(group, el):
    _read_named(group, el)
    group.extra_xml = _comment_xml(_read_reaction_list(group, el))


def _read_section(root, tag, entry_tag, collection, reader):
    """Fills a collection from one <root> section and empties that section in the tree.
    Returns the XML kept for the end of the section (unknown entries, last comments)."""
    sec = root.find(tag)
    if sec is None:
        return ""
    extra, comments = [], []
    for child in list(sec):
        if child.tag is ET.Comment:
            comments.append(child.text or "")
        elif isinstance(child.tag, str) and (entry_tag is None or child.tag == entry_tag):
            item = collection.add()
            item.comment_before = COMMENT_SEP.join(comments)
            comments = []
            reader(item, child)
        else:
            extra.append(_comment_xml(comments) + _element_text(child))
            comments = []
    extra.append(_comment_xml(comments))
    for child in list(sec):
        sec.remove(child)
    return "".join(extra)


def load_file(settings, path):
    global _LOADING
    if not path or not os.path.isfile(path):
        raise MoveEditorError(f"Could not find '{path or 'moves.xml'}'.")
    root, encoding, newline = read_xml_file(path)
    if root.find("Moves") is None:
        raise MoveEditorError("This file has no <Moves> section.")
    if settings.condition_view:
        clear_condition_view()
        set_condition_view(settings, False)

    _LOADING += 1
    try:
        settings.moves.clear()
        settings.event_groups.clear()
        settings.reaction_groups.clear()
        settings.sounds.clear()
        tails = {
            "Sounds": _read_section(root, "Sounds", "Sound", settings.sounds, _read_named),
            "EventGroups": _read_section(root, "EventGroups", "EventGroup", settings.event_groups, _read_event_group),
            "ReactionGroups": _read_section(root, "ReactionGroups", "ReactionGroup", settings.reaction_groups, _read_reaction_group),
            "Moves": _read_section(root, "Moves", None, settings.moves, _read_move),
        }
        settings.tails = json.dumps(tails)
        settings.template = serialize(root)
        settings.encoding = encoding
        settings.newline = newline
        for prop, collection in (("active_move_index", settings.moves), ("active_event_group_index", settings.event_groups),
                                 ("active_reaction_group_index", settings.reaction_groups), ("active_sound_index", settings.sounds)):
            setattr(settings, prop, 0 if len(collection) else -1)
    finally:
        _LOADING -= 1
    return len(settings.moves)






# ============================================================================ #
#  XML: writing
# ============================================================================ #

def _field_string(item, key, spec, raw):
    """Text to write for one attribute, or None to leave it out.
    An attribute that was in the file and was not changed keeps its exact original text."""
    prop, kind, default = spec
    present = key in raw
    if kind == "int":
        value = getattr(item, prop)
        if not present and value == default:
            return None
        return raw[key] if present and _strict_int(raw[key]) == value else str(value)
    if kind in ("float", "optfloat"):
        if kind == "optfloat":
            if not getattr(item, prop[0]):
                return None
            value = getattr(item, prop[1])
        else:
            value = getattr(item, prop)
            if not present and abs(value - default) < 1e-9:
                return None
        if present:
            try:
                if abs(float(raw[key]) - value) <= 1e-5 * max(1.0, abs(value)):
                    return raw[key]
            except ValueError:
                pass
        return _fmt_float(value)
    if kind == "bool":
        value = getattr(item, prop)
        if not present and not value:
            return None
        return "1" if value else "0"
    if kind == "str":
        value = getattr(item, prop)
        return None if not present and value == "" else value
    if kind == "enum":
        value = getattr(item, prop)
        return None if not present and value == default else value
    if kind == "opt":
        value = getattr(item, prop)
        return None if value == 'NONE' else value
    if kind == "pivot":
        value = pivot_name(item)
        return None if not present and (not value or value == default) else value
    return None


def _attributes(item, fields):
    """Attribute list in the original order, then new ones, then 'Other Attributes'."""
    raw_pairs = raw_attrs(item)
    raw = dict(raw_pairs)
    extras = parse_attrs(item.extra_attrs)
    extra_keys = {k for k, _ in extras}

    values = {}
    for key, spec in fields.items():
        if key in extra_keys:
            continue
        text = _field_string(item, key, spec, raw)
        if text is not None:
            values[key] = text
    values.update(extras)

    ordered = [k for k, _ in raw_pairs if k in values]
    ordered += [k for k in fields if k in values and k not in ordered]
    ordered += [k for k, _ in extras if k not in ordered]
    return [(k, values[k]) for k in ordered]


def _fragment(text):
    if not text:
        return []
    return list(_parse_text(f"<x>{text}</x>"))


def _element(tag, item, fields):
    if not XML_NAME.match(tag or ""):
        raise MoveEditorError(f"'{tag}' is not a valid name (names start with a letter and use letters, digits, '_', '-', '.').")
    el = ET.Element(tag)
    for k, v in _attributes(item, fields):
        if not XML_NAME.match(k):
            raise MoveEditorError(f"'{k}' in Other Attributes of '{tag}' is not a valid attribute name.")
        el.set(k, v)
    return el


def _comments(parent, text):
    if text:
        for c in text.split(COMMENT_SEP):
            parent.append(ET.Comment(c))


def build_reaction(reaction):
    el = _element(reaction.name, reaction, REACTION_FIELDS)
    for cond in reaction.conditions:
        c = _element(cond.kind, cond, CONDITION_FIELDS)
        c.extend(_fragment(cond.extra_xml))
        el.append(c)
    el.extend(_fragment(reaction.extra_xml))
    return el


def _append_reactions(parent, owner):
    for reaction in owner.reactions:
        _comments(parent, reaction.comment_before)
        parent.append(build_reaction(reaction))


def build_event(event):
    el = _element(event.event_type, event, event_fields(event))
    for sound in event.sounds:
        el.append(_element("Sound", sound, SOUND_FIELDS))
    if event.wrapped or len(event.reactions):
        _comments(el, event.reactions_comment)
        block = ET.SubElement(el, "Reactions")
        _append_reactions(block, event)
        block.extend(_fragment(event.reaction_comments))
    el.extend(_fragment(event.extra_xml))
    return el


def _append_events(parent, owner):
    for event in owner.events:
        _comments(parent, event.comment_before)
        parent.append(build_event(event))


def build_move(move):
    el = _element(move.name, move, MOVE_FIELDS)
    for interval in move.intervals:
        _comments(el, interval.comment_before)
        iel = _element("Interval", interval, INTERVAL_FIELDS)
        for sound in interval.sounds:
            iel.append(_element("Sound", sound, SOUND_FIELDS))
        _append_events(iel, interval)
        iel.extend(_fragment(interval.extra_xml))
        el.append(iel)
    el.extend(_fragment(move.extra_xml))
    return el


def build_event_group(group):
    el = _element("EventGroup", group, NAME_FIELDS)
    _append_events(el, group)
    el.extend(_fragment(group.extra_xml))
    return el


def build_reaction_group(group):
    el = _element("ReactionGroup", group, NAME_FIELDS)
    _append_reactions(el, group)
    el.extend(_fragment(group.extra_xml))
    return el


def build_sound(sound):
    return _element("Sound", sound, NAME_FIELDS)


def serialize(el, depth=0, lines=None):
    """Tab-indented XML in the same style as the game's files."""
    top = lines is None
    lines = [] if top else lines
    indent = "\t" * depth
    if el.tag is ET.Comment:
        lines.append(f"{indent}<!--{(el.text or '').replace('--', '- -')}-->")
    else:
        attrs = "".join(f' {k}="{_escape(v)}"' for k, v in el.attrib.items())
        kids = list(el)
        text = el.text.strip() if el.text and el.text.strip() else ""
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        if kids:
            lines.append(f"{indent}<{el.tag}{attrs}>")
            if text:
                lines.append(f"{indent}\t{text}")
            for kid in kids:
                serialize(kid, depth + 1, lines)
            lines.append(f"{indent}</{el.tag}>")
        elif text:
            lines.append(f"{indent}<{el.tag}{attrs}>{text}</{el.tag}>")
        else:
            lines.append(f"{indent}<{el.tag}{attrs}/>")
    return "\n".join(lines) if top else None


def save_file(settings, path):
    if not is_loaded(settings):
        raise MoveEditorError("Load a moves.xml first.")
    root = _parse_text(settings.template)
    try:
        tails = json.loads(settings.tails) if settings.tails else {}
    except ValueError:
        tails = {}

    content = {
        "Sounds": (settings.sounds, build_sound),
        "EventGroups": (settings.event_groups, build_event_group),
        "ReactionGroups": (settings.reaction_groups, build_reaction_group),
        "Moves": (settings.moves, build_move),
    }
    for tag, _ in SECTIONS:
        items, builder = content[tag]
        tail = tails.get(tag, "")
        sec = root.find(tag)
        if sec is None:
            if not len(items) and not tail:
                continue
            sec = ET.Element(tag)
            moves_el = root.find("Moves")
            position = list(root).index(moves_el) if moves_el is not None else len(root)
            root.insert(position, sec)
        for item in items:
            _comments(sec, item.comment_before)
            sec.append(builder(item))
        sec.extend(_fragment(tail))
    body = serialize(root)          # built first, so a failure never leaves half a file

    encoding = settings.encoding or "windows-1251"
    try:
        codecs.lookup(encoding)
    except LookupError:
        encoding = "utf-8"

    newline = settings.newline if settings.newline in ("\n", "\r\n") else "\n"
    with open(path, "w", encoding=encoding, errors="xmlcharrefreplace", newline=newline) as f:
        f.write(f'<?xml version="1.0" encoding="{encoding}"?>\n{body}\n')







# ============================================================================ #
#  Timeline preview
# ============================================================================ #
#
#  A preview is a list of segments. Each segment is one Move imported with Animation
#  Tools, starting at a timeline frame. The second segment of a sequential reaction
#  (OnEnd / OnFrame) cuts the first one and continues from where its PivotNode is.

class Segment:
    def __init__(self, move, first, length, start, pivot=None, reverse=False):
        self.reverse = reverse      # played in the opposite direction (reaction Reverse="1")
        self.move = move            # GTS_ME_Move
        self.first = first          # animation frame to start from
        self.length = length        # animation frames to play after the first one
        self.start = start          # timeline frame of the first frame
        self.pivot = pivot          # node to line up with the previous segment


def fcurves_of(obj):
    ad = obj.animation_data
    action = ad.action if ad else None
    if action is None:
        return []
    curves = getattr(action, "fcurves", None)
    if curves is not None:
        return list(curves)
    try:                            # Blender 5: layered actions only
        from bpy_extras import anim_utils
        bag = anim_utils.action_get_channelbag_for_slot(action, ad.action_slot)
        return list(bag.fcurves) if bag else []
    except Exception:
        return []


def clear_animation(objects):
    for obj in objects:
        ad = obj.animation_data
        if not ad:
            continue
        action = ad.action
        obj.animation_data_clear()
        if action and action.users == 0:
            bpy.data.actions.remove(action)


def trim_keys(objects, keep):
    for obj in objects:
        for fc in fcurves_of(obj):
            points = fc.keyframe_points
            removed = False
            for i in range(len(points) - 1, -1, -1):
                if not keep(points[i].co.x):
                    points.remove(points[i], fast=True)
                    removed = True
            if removed:
                fc.update()


def keyed_from(obj, frame):
    for fc in fcurves_of(obj):
        if fc.data_path == "location" and len(fc.keyframe_points) and fc.keyframe_points[-1].co.x >= frame - 1e-3:
            return True
    return False


def physics_offset(move, steps):
    """(x, game y) the Pivot Node has moved after `steps` frames of Velocity + Gravity.
    Velocity Y grows by Gravity every frame: vy, vy+g, vy+2g... so y = vy*n + g*n(n-1)/2."""
    return move.velocity_x * steps, move.velocity_y * steps + move.gravity * steps * (steps - 1) / 2.0


def mirror_segment(objects, pivot, start, end):
    """Reverse: mirrors the X of every key between start and end around the pivot's X at `start`,
    so the move faces and travels the other way while staying where it began."""
    centre = None
    if pivot is not None:
        for fc in fcurves_of(pivot):
            if fc.data_path == "location" and fc.array_index == 0:
                centre = fc.evaluate(start)
        if centre is None:
            centre = pivot.location.x
    for obj in objects:
        for fc in fcurves_of(obj):
            if fc.data_path != "location" or fc.array_index != 0:
                continue
            c = centre if centre is not None else fc.evaluate(start)
            for kp in fc.keyframe_points:
                if start - 1e-3 <= kp.co.x <= end + 1e-3:
                    kp.co.y = 2 * c - kp.co.y
                    kp.handle_left.y = 2 * c - kp.handle_left.y
                    kp.handle_right.y = 2 * c - kp.handle_right.y
            fc.update()


def shift_segment(objects, segment, step, align, continues=False):
    """Adds the alignment offset and the Binding physics path to every frame of a segment.
    continues: the segment follows another move. Its first frame is the frame after the previous
    move's last one, so it has already moved one step (60 -> 90, not 60 -> 60)."""
    move = segment.move
    physics = move.binding and (move.velocity_x or move.velocity_y or move.gravity)
    frames = [segment.start + k * step for k in range(segment.length + 1)]
    first_step = 1 if continues else 0

    offsets = []
    for k in range(len(frames)):
        dx, dy, dz = align
        if physics:
            px, py = physics_offset(move, k + first_step)
            dx += -px if segment.reverse else px
            dz += GAME_Y_TO_BLENDER_Z * py
        offsets.append((dx, dy, dz))

    for obj in objects:
        curves = {fc.array_index: fc for fc in fcurves_of(obj) if fc.data_path == "location"}
        for axis in range(3):
            if all(abs(o[axis]) < 1e-9 for o in offsets):
                continue
            if axis not in curves:
                obj.keyframe_insert(data_path="location", index=axis, frame=segment.start)
                curves = {fc.array_index: fc for fc in fcurves_of(obj) if fc.data_path == "location"}
            fc = curves.get(axis)
            if fc is None:
                continue
            base = [fc.evaluate(f) for f in frames]       # read everything before writing anything
            points = fc.keyframe_points
            for f, value, offset in zip(frames, base, offsets):
                points.insert(f, value + offset[axis], options={'FAST'})
            fc.update()


def _misc_collection(scene):
    col = bpy.data.collections.get("Misc")
    if col is None:
        col = bpy.data.collections.new("Misc")
        scene.collection.children.link(col)
    return col


def detector_box(scene, name, target_name):
    target = bpy.data.objects.get(target_name)
    if target is None:
        return None
    obj = bpy.data.objects.get(name)
    if obj is None:
        mesh = bpy.data.meshes.new(name)
        verts = [(x, y, z) for x in (-0.5, 0.5) for y in (-0.5, 0.5) for z in (-0.5, 0.5)]
        faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
        mesh.from_pydata(verts, [], faces)
        obj = bpy.data.objects.new(name, mesh)
        _misc_collection(scene).objects.link(obj)
        obj.display_type = 'WIRE'
        obj.show_in_front = True
        obj.hide_select = True
        c = obj.constraints.new(type='COPY_LOCATION')
        c.target = target
    detector_center(scene, name + "Center", target)
    return obj


CENTER_SIZE = 0.05          # metres, diameter of the dot in the middle of a detector range
CENTER_COLOR = (1.0, 0.55, 0.0, 1.0)


def _center_material():
    mat = bpy.data.materials.get("DeltaDetectorCenter")
    if mat is None:
        mat = bpy.data.materials.new("DeltaDetectorCenter")
        mat.diffuse_color = CENTER_COLOR        # the colour shown in Solid view
        if hasattr(mat, "use_nodes"):
            mat.use_nodes = True
            bsdf = mat.node_tree.nodes.get("Principled BSDF")
            if bsdf:
                bsdf.inputs["Base Color"].default_value = CENTER_COLOR
                if "Emission Color" in bsdf.inputs:
                    bsdf.inputs["Emission Color"].default_value = CENTER_COLOR
                    bsdf.inputs["Emission Strength"].default_value = 1.0
    return mat


def detector_center(scene, name, target):
    """A small highlighted sphere that marks the middle of a detector range (follows the detector)."""
    size = CENTER_SIZE / (scene.unit_settings.scale_length or 1.0)
    obj = bpy.data.objects.get(name)
    if obj is not None:
        obj.scale = (size, size, size)              # keeps existing dots in sync with CENTER_SIZE
        return obj
    import bmesh
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=8, radius=0.5)
    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = True
    mesh.materials.append(_center_material())
    obj = bpy.data.objects.new(name, mesh)
    _misc_collection(scene).objects.link(obj)
    obj.scale = (size, size, size)                  # radius 0.5 -> 0.03 m across on every axis
    obj.show_in_front = True
    obj.hide_select = True
    obj.color = CENTER_COLOR
    c = obj.constraints.new(type='COPY_LOCATION')
    c.target = target
    return obj


def key_detector_boxes(scene, boxes, move, frame):
    """DeltaDetectorH/V shown as boxes around the detectors (they extend both ways)."""
    thick = 0.015 / (scene.unit_settings.scale_length or 1.0)
    h, v = boxes
    if h:
        h.scale = (max(0.001, 2 * move.delta_detector_h), thick, thick)
        h.keyframe_insert(data_path="scale", frame=frame)
    if v:
        v.scale = (thick, thick, max(0.001, 2 * move.delta_detector_v))
        v.keyframe_insert(data_path="scale", frame=frame)
    for box in boxes:
        if box:
            for fc in fcurves_of(box):
                for kp in fc.keyframe_points:
                    kp.interpolation = 'CONSTANT'


TRAJECTORY_NAME = "COMTrajectory"
TRAJECTORY_NODE = "COM"


def _sample_positions(obj, scene, frames):
    """World positions of an object on the given timeline frames."""
    curves = {fc.array_index: fc for fc in fcurves_of(obj) if fc.data_path == "location"}
    if obj.parent is None and not len(obj.constraints) and curves:
        # fast path: read the curves directly instead of updating the whole scene every frame
        base = obj.location
        return [tuple(curves[i].evaluate(f) if i in curves else base[i] for i in range(3)) for f in frames]
    out = []
    for f in frames:
        scene.frame_set(int(f))
        out.append(tuple(obj.matrix_world.translation))
    return out


def remove_trajectory():
    obj = bpy.data.objects.get(TRAJECTORY_NAME)
    if obj is not None:
        data = obj.data
        bpy.data.objects.remove(obj)
        if data is not None and data.users == 0:
            bpy.data.curves.remove(data)


def update_trajectory(scene, settings):
    """Draws the path of the COM over the previewed frames as a thin curve in the Misc collection."""
    if not settings.show_trajectory:
        remove_trajectory()
        return
    com = bpy.data.objects.get(TRAJECTORY_NODE)
    if com is None or scene.frame_end <= scene.frame_start:
        remove_trajectory()
        return

    frame_before = scene.frame_current
    points = _sample_positions(com, scene, range(scene.frame_start, scene.frame_end + 1))
    if scene.frame_current != frame_before:
        scene.frame_set(frame_before)

    obj = bpy.data.objects.get(TRAJECTORY_NAME)
    if obj is None or obj.type != 'CURVE':
        remove_trajectory()
        curve = bpy.data.curves.new(TRAJECTORY_NAME, 'CURVE')
        curve.dimensions = '3D'
        obj = bpy.data.objects.new(TRAJECTORY_NAME, curve)
        _misc_collection(scene).objects.link(obj)
        obj.hide_select = True
        obj.show_in_front = True
    curve = obj.data
    curve.bevel_depth = 0.008 / (scene.unit_settings.scale_length or 1.0)
    curve.splines.clear()
    spline = curve.splines.new('POLY')
    spline.points.add(len(points) - 1)
    for point, co in zip(spline.points, points):
        point.co = (co[0], co[1], co[2], 1.0)


def run_preview(context, segments, keep_frame=False):
    scene = context.scene
    frame_before = scene.frame_current
    settings = get_settings(context)
    anim, aset = anim_module(), anim_settings(scene)
    order = node_order(scene)
    if len(order) == SHADOW_FIGHT_NODE_COUNT:
        raise MoveEditorError(SHADOW_FIGHT_MESSAGE + ".")
    nodes = [o for o in (bpy.data.objects.get(n) for n in order) if o]
    armature = aset.armature_object if aset.use_armature and aset.armature_object else None
    animated = nodes + ([armature] if armature else [])

    files = []
    for seg in segments:
        path = bin_path(settings, seg.move.file_name)
        if not path:
            raise MoveEditorError(f"'{seg.move.file_name or seg.move.name}' was not found in the Animations Folder.")
        files.append(path)

    boxes = (None, None)
    if settings.show_detectors:
        boxes = (detector_box(scene, "DeltaDetectorH", "DetectorH"), detector_box(scene, "DeltaDetectorV", "DetectorV"))

    clear_animation(animated + [b for b in boxes if b])
    step = frame_step(scene)
    saved = {k: getattr(aset, k) for k in ("use_spline", "stay_in_place", "pivot_node", "start_frame")}
    end = segments[0].start

    try:
        for i, (seg, path) in enumerate(zip(segments, files)):
            start = seg.start
            target = None
            pivot = bpy.data.objects.get(seg.pivot) if seg.pivot else None

            if i > 0:
                # the previous move stops where this one starts
                trim_keys(animated, lambda x: x < start - 1e-3)
                if pivot:
                    scene.frame_set(int(round(start)))
                    target = pivot.matrix_world.translation.copy()

            # Binding: the character keeps still around its PivotNode, the physics path is added below
            aset.use_spline = False
            aset.stay_in_place = seg.move.binding
            if seg.move.binding:
                aset.pivot_node = pivot_name(seg.move) or "NPivot"
            aset.start_frame = max(0, seg.first)
            scene.frame_start = int(round(start))
            try:
                anim.import_bin(path, order)
            except anim.AnimationError as err:
                raise MoveEditorError(f"Animation Tools: {err}")

            seg_end = start + seg.length * step
            trim_keys(animated, lambda x: x <= seg_end + 1e-3)

            if seg.reverse:
                pivot_obj = bpy.data.objects.get(pivot_name(seg.move) or "NPivot")
                mirror_segment([o for o in nodes if keyed_from(o, start)], pivot_obj, start, seg_end)

            align = (0.0, 0.0, 0.0)
            if target is not None:
                scene.frame_set(int(round(start)))
                here = pivot.matrix_world.translation
                align = (target.x - here.x, target.y - here.y, target.z - here.z)

            moving = seg.move.binding and (seg.move.velocity_x or seg.move.velocity_y or seg.move.gravity)
            if moving or any(abs(a) > 1e-6 for a in align):
                shifted = [o for o in nodes if keyed_from(o, start)] + ([armature] if armature else [])
                shift_segment(shifted, seg, step, align, continues=target is not None)

            if any(boxes):
                key_detector_boxes(scene, boxes, seg.move, start)
            end = max(end, seg_end)
    finally:
        for key, value in saved.items():
            setattr(aset, key, value)

    scene.frame_start = int(round(segments[0].start))
    scene.frame_end = max(scene.frame_start, int(math.ceil(end - 1e-6)))
    try:
        update_trajectory(scene, settings)
    except Exception as err:            # the path is a helper, never break the preview
        print(f"[Move Editor] Could not draw the COM path: {err}")
    if keep_frame:
        scene.frame_set(min(max(frame_before, scene.frame_start), scene.frame_end))
    else:
        scene.frame_set(scene.frame_start)


def move_segments(move):
    return [Segment(move, move.first_frame, max(0, move.end_frame - move.first_frame), move.first_frame)]


def reaction_start_frame(reaction, target):
    """FirstFrame of the Reaction when it has one, otherwise the target Move's FirstFrame."""
    return reaction.first_frame if has_attr(reaction, "FirstFrame") or reaction.first_frame else target.first_frame


def transition_frame(interval, event):
    """Animation frame where a sequential reaction starts (the frame after the trigger)."""
    return (interval.end if event.event_type == 'OnEnd' else event.frame) + 1


def standalone_segments(settings, reaction):
    if is_special(reaction.name):
        raise MoveEditorError(f"{reaction.name} has no animation: {SPECIAL_REACTIONS[reaction.name].split('.')[0].lower()}.")
    target = settings.moves.get(reaction.name)
    if target is None:
        raise MoveEditorError(f"There is no Move named '{reaction.name}'.")
    first = reaction_start_frame(reaction, target)
    return [Segment(target, first, max(0, target.end_frame - first), first, reverse=reaction.reverse)]


def reaction_segments(settings, scene, move, interval, event, reaction):
    if is_special(reaction.name) and event.event_type in SEQUENTIAL_EVENTS:
        # Death after Interval End / On Frame: play the move up to the frame it happens on
        last = max(transition_frame(interval, event) - 1, move.first_frame)
        return [Segment(move, move.first_frame, last - move.first_frame, move.first_frame)]
    standalone = standalone_segments(settings, reaction)
    if event.event_type not in SEQUENTIAL_EVENTS:
        return standalone
    target = standalone[0]
    switch = max(transition_frame(interval, event), move.first_frame + 1)
    main_length = max(move.end_frame, switch - 1) - move.first_frame
    start = move.first_frame + (switch - move.first_frame) * frame_step(scene)
    return [Segment(move, move.first_frame, max(0, main_length), move.first_frame),
            Segment(target.move, target.first, target.length, start, pivot_name(target.move) or "NPivot",
                    reverse=target.reverse)]


def play_timeline(context):
    screen = getattr(context, "screen", None)
    if screen is not None:
        if not screen.is_animation_playing:
            bpy.ops.screen.animation_play()
        return
    wm = bpy.context.window_manager
    for window in wm.windows:
        with bpy.context.temp_override(window=window, screen=window.screen):
            if not window.screen.is_animation_playing:
                bpy.ops.screen.animation_play()
        return


def selection_key(settings, kind):
    """What a preview was made from. A live update only redoes a preview while this still matches."""
    if kind == 'MOVE':
        return ('MOVE', settings.active_move_index)
    owner = reaction_owner(settings)
    path = [settings.tab, settings.active_move_index, settings.active_event_group_index,
            settings.active_reaction_group_index]
    if settings.tab == 'MOVES':
        move, interval, _, _ = active(settings)
        path += [move.active_interval_index if move else -1, interval.active_event_index if interval else -1]
    elif settings.tab == 'EVENT_GROUPS':
        group = pick(settings.event_groups, settings.active_event_group_index)
        path.append(group.active_event_index if group else -1)
    path.append(owner.active_reaction_index if owner else -1)
    return ('REACTION', tuple(path))


# The last preview: its kind, selection and segments (move name, timeline start)
_LAST = {"kind": None, "key": None, "segments": [], "timing": []}


def animation_frame_at(scene, move=None):
    """Animation frame shown at the timeline's current frame, for `move` (or whatever is under the
    playhead when move is None). Uses where the last preview placed the move; without a preview
    the timeline frame is used as it is."""
    current = scene.frame_current
    timing = [t for t in _LAST["timing"] if move is None or t[0] == move.name]
    if timing:
        before = [t for t in timing if t[1] <= current + 1e-6]
        name, start, first = before[-1] if before else timing[0]
        return max(0, first + int(round((current - start) / (frame_step(scene) or 1.0))))
    return max(0, current)


def preview(context, kind, live=False):
    """kind: 'MOVE' or 'REACTION'. Sets a status line in the panel and returns (ok, message).
    Reactions in groups have no move to follow, so they always play on their own.
    live: a refresh after an edit. Keeps the current frame and doesn't start playback."""
    settings = get_settings(context)
    try:
        if kind == 'REACTION':
            reaction = current_reaction(settings)
            if reaction is None:
                raise MoveEditorError("Select a Reaction first.")
            if settings.tab == 'MOVES':
                move, interval, event, _ = active(settings)
                segments = reaction_segments(settings, context.scene, move, interval, event, reaction)
            else:
                segments = standalone_segments(settings, reaction)
        else:
            move = active(settings)[0]
            if move is None:
                raise MoveEditorError("Select a Move first.")
            segments = move_segments(move)
        run_preview(context, segments, keep_frame=live)
        _LAST.update(kind=kind, key=selection_key(settings, kind),
                     segments=[(s.move.name, s.start) for s in segments],
                     timing=[(s.move.name, s.start, s.first) for s in segments])
        settings.preview_status = "Previewing " + " → ".join(s.move.name for s in segments)
        refresh_condition_view(context, settings)
        if settings.play_after_preview and not live:
            play_timeline(context)
        return True, settings.preview_status
    except MoveEditorError as err:
        settings.preview_status = str(err)
        return False, str(err)





# ---------------------------------------------------------------------------- #
#  Auto preview (runs from a timer, outside the UI drawing code)
# ---------------------------------------------------------------------------- #

LIVE_DELAY = 0.4        # seconds without changes before a live update re-imports

_AUTO = {"kind": None, "live": False, "due": 0.0}


def _auto_preview():
    """Timer. Waits until nothing changed for a moment, so dragging a slider re-imports only once."""
    wait = _AUTO["due"] - time.monotonic()
    if wait > 0.01:
        return wait
    kind, live = _AUTO["kind"], _AUTO["live"]
    _AUTO.update(kind=None, live=False)
    if kind:
        try:
            context = bpy.context
            if live and _LAST["key"] != selection_key(get_settings(context), kind):
                return None             # the selection changed since that preview
            preview(context, kind, live=live)
        except Exception as err:            # never let a timer raise
            print(f"[Move Editor] Preview failed: {err}")
    return None


def _start_timer(kind, live, delay):
    _AUTO.update(kind=kind, live=live, due=time.monotonic() + delay)
    if not bpy.app.timers.is_registered(_auto_preview):
        bpy.app.timers.register(_auto_preview, first_interval=delay)


def schedule_preview(settings, kind):
    """Preview on selection (Auto Preview)."""
    if _LOADING or not settings.auto_preview:
        return
    _start_timer(kind, False, 0.15)


def schedule_live_update(settings):
    """Redo the last preview after an edit (Live Update)."""
    if _LOADING or not settings.live_preview or not _LAST["kind"]:
        return
    if _AUTO["kind"] and not _AUTO["live"]:
        return                          # a selection preview is already on its way
    _start_timer(_LAST["kind"], True, LIVE_DELAY)


def refresh_detector_boxes(scene, move):
    """DeltaDetector edits only resize the boxes: no re-import, so it can follow a slider live."""
    boxes = (bpy.data.objects.get("DeltaDetectorH"), bpy.data.objects.get("DeltaDetectorV"))
    if not any(boxes):
        return
    for name, start in _LAST["segments"]:
        if name == move.name:
            key_detector_boxes(scene, boxes, move, start)







# ============================================================================ #
#  Condition View
# ============================================================================ #
#
#  Shows the selected reaction's Width / Height / Distance X / Distance Y conditions next to the
#  character, on top of the normal reaction preview. A box (Box Offset X, Box Size X / Y) stands in for
#  the collision; each condition is a line showing the range it allows, Min (green) to Max (orange).
#
#  Positions are in game units. Animation Tools imports them 1:1, so one game unit is one Blender unit
#  (with Unit Scale 0.01, 140 shows as 140 cm). Game Y points down, so a negative Height goes up.
#
#      side view (X right, Z up)          Min line: green     Max line: orange
#
#        DistanceX  o----------o
#        Width      o-------o
#                   +-------------+
#      |  |         |             |
#      |  |  Height |   box       |      box origin: bottom left, middle of its depth
#      o  o         +-------------+  <- (Box Offset X, 0, 0)
#      DistY

VIEW_COLLECTION = "ConditionView"
VIEW_OFFSET_X = 140.0                # default Box Offset X, game units
VIEW_DEFAULT_SIZE = 200.0            # default Box Size X / Y, game units
VIEW_OPEN_LENGTH = 60.0              # how far a line runs past a Min that has no Max ("at least")
VIEW_DEPTH = 60.0                    # box thickness, towards and away from the camera
VIEW_GAP = 12.0                      # distance between the box and its lines, and between lines
VIEW_DOT_SIZE = 0.05                 # metres, the dots at both ends of every line
VIEW_LINE_SIZE = 0.008               # metres, line thickness
MIN_COLOR = (0.1, 0.85, 0.2, 1.0)    # green
MAX_COLOR = (1.0, 0.5, 0.0, 1.0)     # orange
RANGE_COLOR = (0.9, 0.9, 0.9, 1.0)   # the line between them: the allowed range
BOX_COLOR = (0.55, 0.65, 0.8, 0.25)

SHOWN_CONDITIONS = ('Width', 'Height', 'DeltaX', 'DeltaY')


def _view_material(name, color):
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = color[:3] + (1.0,)
            if "Emission Color" in bsdf.inputs:
                bsdf.inputs["Emission Color"].default_value = color[:3] + (1.0,)
                bsdf.inputs["Emission Strength"].default_value = 1.0
    mat.diffuse_color = color           # Solid view colour (alpha makes the box see-through)
    return mat


def _view_collection(scene):
    col = bpy.data.collections.get(VIEW_COLLECTION)
    if col is None:
        col = bpy.data.collections.new(VIEW_COLLECTION)
        scene.collection.children.link(col)
    return col


def _view_object(scene, name, data):
    obj = bpy.data.objects.new(name, data)
    _view_collection(scene).objects.link(obj)
    obj.hide_select = True
    return obj


def _dot_mesh(which, mat):
    """One sphere mesh per colour, shared by every dot of that colour (built once, not per dot)."""
    name = f"ConditionDot{which}"
    mesh = bpy.data.meshes.get(name)
    if mesh is None:
        import bmesh
        mesh = bpy.data.meshes.new(name)
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=8, radius=0.5)
        bm.to_mesh(mesh)
        bm.free()
        for poly in mesh.polygons:
            poly.use_smooth = True
        mesh.materials.append(mat)
    return mesh


def _view_dot(scene, name, location, which, mat):
    obj = _view_object(scene, name, _dot_mesh(which, mat))
    size = VIEW_DOT_SIZE / (scene.unit_settings.scale_length or 1.0)
    obj.scale = (size, size, size)
    obj.location = location
    obj.show_in_front = True
    return obj


def _view_line(scene, name, start, end, start_dot, end_dot, mats):
    """A range line. start_dot / end_dot: 'Min', 'Max' or None (an open end, no dot)."""
    curve = bpy.data.curves.new(name, 'CURVE')
    curve.dimensions = '3D'
    curve.bevel_depth = VIEW_LINE_SIZE / (scene.unit_settings.scale_length or 1.0)
    spline = curve.splines.new('POLY')
    spline.points.add(1)
    curve.materials.append(mats["Range"])
    obj = _view_object(scene, name, curve)
    obj.show_in_front = True
    for suffix, which, location in (("Start", start_dot, start), ("End", end_dot, end)):
        if which:
            _view_dot(scene, name + suffix, location, which, mats[which])
    _move_line(obj, start, end)


def _move_line(obj, start, end):
    points = obj.data.splines[0].points
    points[0].co = (*start, 1.0)
    points[1].co = (*end, 1.0)
    obj.data.update_tag()
    for suffix, location in (("Start", start), ("End", end)):
        dot = bpy.data.objects.get(obj.name + suffix)
        if dot is not None:
            dot.location = location


def _box_verts(left, right, bottom, top):
    half = VIEW_DEPTH / 2.0
    return [(x - left, y, z - bottom) for x in (left, right) for y in (-half, half) for z in (bottom, top)]


def _view_box(scene, left, right, bottom, top):
    """The stand-in collision. Its origin is the bottom left corner, in the middle of its depth."""
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    mesh = bpy.data.meshes.new("ConditionBox")
    mesh.from_pydata(_box_verts(left, right, bottom, top), [], faces)
    mesh.materials.append(_view_material("ConditionBox", BOX_COLOR))
    obj = _view_object(scene, "ConditionBox", mesh)
    obj.location = (left, 0.0, bottom)
    obj.show_wire = True


def _move_box(obj, left, right, bottom, top):
    for vert, co in zip(obj.data.vertices, _box_verts(left, right, bottom, top)):
        vert.co = co
    obj.data.update()
    obj.location = (left, 0.0, bottom)


def clear_condition_view():
    _VIEW["signature"] = None
    col = bpy.data.collections.get(VIEW_COLLECTION)
    if col is None:
        return
    for obj in list(col.objects):
        data = obj.data
        bpy.data.objects.remove(obj)
        if data is not None and data.users == 0:
            (bpy.data.curves if isinstance(data, bpy.types.Curve) else bpy.data.meshes).remove(data)
    bpy.data.collections.remove(col)


def _condition_ranges(reaction):
    """{kind: condition} for the conditions the view can show (the first of each kind)."""
    found = {}
    for cond in reaction.conditions:
        if cond.kind in SHOWN_CONDITIONS and cond.kind not in found and (cond.use_min or cond.use_max):
            found[cond.kind] = cond
    return found


_VIEW = {"key": None, "pending": False, "signature": None}


def condition_view_key(settings):
    return selection_key(settings, 'REACTION')


def condition_view_shapes(reaction, offset_x=VIEW_OFFSET_X, size_x=VIEW_DEFAULT_SIZE, size_y=VIEW_DEFAULT_SIZE):
    """What to draw: ((left, right, bottom, top) of the box, [(name, start, end, start_dot, end_dot), ...]).

    The box is set by Box Offset X and Box Size only. Each condition is one line showing the range it
    allows: Min (green dot) to Max (orange dot). Only a Max: from 0 to the Max. Only a Min: from the Min,
    running on past it with an open end."""
    conds = _condition_ranges(reaction)
    oy = 0.0
    up = GAME_Y_TO_BLENDER_Z              # game Y down -> Blender Z up
    left, right = sorted((offset_x, offset_x + size_x))
    bottom, top = sorted((0.0, size_y))
    corners = {'0': (left, top), '1': (right, top), '2': (right, bottom), '3': (left, bottom)}

    def value_range(cond):
        """(start value, end value, start dot, end dot) of a condition, in game units."""
        if cond.use_min and cond.use_max:
            return cond.min, cond.max, "Min", "Max"
        if cond.use_max:
            return 0.0, cond.max, None, "Max"
        away = 1.0 if cond.min >= 0 else -1.0           # further from 0 = "more than the Min"
        return cond.min, cond.min + away * VIEW_OPEN_LENGTH, "Min", None

    lines = []

    def add(cond, label, point):
        a, b, dot_a, dot_b = value_range(cond)
        lines.append((f"Condition{label}", point(a), point(b), dot_a, dot_b))

    if 'Height' in conds:           # left side of the box, measured up from its bottom left
        x = left - VIEW_GAP
        add(conds['Height'], "Height", lambda v: (x, oy, bottom + up * v))
    if 'Width' in conds:            # on top of the box, measured from its left side
        z = top + VIEW_GAP
        add(conds['Width'], "Width", lambda v: (left + v, oy, z))
    if 'DeltaY' in conds:           # further left, from the chosen corner
        cx, cz = corners[conds['DeltaY'].corner]
        x = left - 2 * VIEW_GAP
        add(conds['DeltaY'], "DistanceY", lambda v: (x, oy, cz + up * v))
    if 'DeltaX' in conds:           # further up, from the chosen corner
        cx, cz = corners[conds['DeltaX'].corner]
        z = top + 2 * VIEW_GAP
        add(conds['DeltaX'], "DistanceX", lambda v: (cx + v, oy, z))
    return (left, right, bottom, top), lines


def build_condition_view(scene, settings):
    """Draws the box and the condition lines for the selected reaction.
    When the same lines already exist (a value is being dragged) they are only moved, which is fast;
    the objects are only re-created when lines or dots appear or disappear."""
    _VIEW["key"] = condition_view_key(settings)
    reaction = current_reaction(settings)
    if reaction is None:
        clear_condition_view()
        return
    box, lines = condition_view_shapes(reaction, settings.condition_offset_x,
                                       settings.condition_size_x, settings.condition_size_y)
    signature = tuple((name, dot_a, dot_b) for name, _, _, dot_a, dot_b in lines)

    box_obj = bpy.data.objects.get("ConditionBox")
    line_objs = [bpy.data.objects.get(line[0]) for line in lines]
    if _VIEW["signature"] == signature and box_obj is not None and all(line_objs):
        _move_box(box_obj, *box)
        for obj, (_, start, end, _, _) in zip(line_objs, lines):
            _move_line(obj, start, end)
        return

    clear_condition_view()
    _view_box(scene, *box)
    mats = {"Min": _view_material("ConditionMin", MIN_COLOR), "Max": _view_material("ConditionMax", MAX_COLOR),
            "Range": _view_material("ConditionRange", RANGE_COLOR)}
    for name, start, end, dot_a, dot_b in lines:
        _view_line(scene, name, start, end, dot_a, dot_b, mats)
    _VIEW["signature"] = signature


def enter_condition_view(context):
    """Previews the selected reaction as usual (unless it already is) and adds the box."""
    settings = get_settings(context)
    if _LAST["kind"] != 'REACTION' or _LAST["key"] != selection_key(settings, 'REACTION'):
        preview(context, 'REACTION')
    build_condition_view(context.scene, settings)


def exit_condition_view(context):
    """Removes the box, the lines and the dots. The preview itself stays on the timeline."""
    clear_condition_view()


def set_condition_view(settings, on):
    """Turns the Condition View switch on or off without running its callback."""
    global _LOADING
    _LOADING += 1
    try:
        settings.condition_view = on
    finally:
        _LOADING -= 1


def _refresh_from_timer():
    _VIEW["pending"] = False
    try:
        context = bpy.context
        refresh_condition_view(context, get_settings(context))
    except Exception as err:
        print(f"[Move Editor] Could not draw the conditions: {err}")
    return None


def condition_view_follow_selection(settings):
    """Called while drawing: redraws the view (from a timer) when another reaction got selected."""
    if settings.condition_view and not _VIEW["pending"] and _VIEW["key"] != condition_view_key(settings):
        _VIEW["pending"] = True
        bpy.app.timers.register(_refresh_from_timer, first_interval=0.01)


def refresh_condition_view(context, settings):
    """After an edit or a new selection while Condition View is on."""
    if not settings.condition_view:
        return
    try:
        build_condition_view(getattr(context, "scene", None) or bpy.context.scene, settings)
    except Exception as err:
        print(f"[Move Editor] Could not draw the conditions: {err}")







# ============================================================================ #
#  Find References
# ============================================================================ #
#
#  A result's path says where it lives:
#    ['MOVES', move, interval(, event(, reaction))]
#    ['EVENT_GROUPS', group, event(, reaction)]
#    ['REACTION_GROUPS', group, reaction]

REF_KINDS = [('MOVE', "Move", ""), ('EVENT_GROUP', "Event Group", ""),
             ('REACTION_GROUP', "Reaction Group", ""), ('SOUND', "Sound", "")]
TAB_KIND = {'MOVES': 'MOVE', 'EVENT_GROUPS': 'EVENT_GROUP', 'REACTION_GROUPS': 'REACTION_GROUP', 'SOUNDS': 'SOUND'}
TAB_ICON = {t[0]: t[3] for t in TABS}


def _plays(sounds, name):
    return any(name in split_names(s.name) for s in sounds)


def _event_refs(out, kind, name, event, label, path):
    if kind == 'MOVE':
        for ri, reaction in enumerate(event.reactions):
            if reaction.name == name:
                out.append((label, path + [ri]))
    elif kind == 'REACTION_GROUP' and name in split_names(event.groups):
        out.append((label, path))
    elif kind == 'SOUND' and _plays(event.sounds, name):
        out.append((label + "  (sound)", path))


def find_references(settings, kind, name):
    """[(label, path)] of everything that refers to a Move / group / sound."""
    out = []
    for mi, move in enumerate(settings.moves):
        for ii, interval in enumerate(move.intervals):
            where = f"{move.name} › {interval.start}–{interval.end}"
            if kind == 'EVENT_GROUP' and name in split_names(interval.groups):
                out.append((where, ['MOVES', mi, ii]))
            elif kind == 'SOUND' and _plays(interval.sounds, name):
                out.append((where + "  (interval sound)", ['MOVES', mi, ii]))
            for ei, event in enumerate(interval.events):
                _event_refs(out, kind, name, event, f"{where} › {event_trigger_text(event)}", ['MOVES', mi, ii, ei])
    for gi, group in enumerate(settings.event_groups):
        for ei, event in enumerate(group.events):
            _event_refs(out, kind, name, event, f"{group.name} › {event_trigger_text(event)}", ['EVENT_GROUPS', gi, ei])
    if kind == 'MOVE':
        for gi, group in enumerate(settings.reaction_groups):
            for ri, reaction in enumerate(group.reactions):
                if reaction.name == name:
                    out.append((f"{group.name} › #{ri + 1}", ['REACTION_GROUPS', gi, ri]))
    return out


def go_to(settings, path):
    """Opens the tab and selects every level of a reference. False when the lists changed since the search."""
    global _LOADING
    tab, idx = path[0], path[1:]
    if tab == 'MOVES':
        chain = [(settings, "active_move_index", settings.moves), ("intervals", "active_interval_index"),
                 ("events", "active_event_index"), ("reactions", "active_reaction_index")]
    elif tab == 'EVENT_GROUPS':
        chain = [(settings, "active_event_group_index", settings.event_groups), ("events", "active_event_index"),
                 ("reactions", "active_reaction_index")]
    else:
        chain = [(settings, "active_reaction_group_index", settings.reaction_groups),
                 ("reactions", "active_reaction_index")]

    # check the whole path first, so a stale result changes nothing
    owner, prop, items = chain[0]
    steps = []
    for level, i in enumerate(idx):
        if level > 0:
            coll_name, prop = chain[level]
            owner, items = item, getattr(item, coll_name)
        if not 0 <= i < len(items):
            return False
        item = items[i]
        steps.append((owner, prop, i))

    _LOADING += 1           # no auto preview / live update while jumping
    try:
        settings.tab = tab
        if tab == 'MOVES' and settings.search:
            move = settings.moves[idx[0]]
            query = settings.search.strip().lower()
            if query not in move.name.lower() and query not in move.file_name.lower():
                settings.search = ""            # the move would be hidden by the filter
        for owner, prop, i in steps:
            setattr(owner, prop, i)
    finally:
        _LOADING -= 1
    return True







# ============================================================================ #
#  Property callbacks
# ============================================================================ #

def _renamed(item, context, kind):
    """Renaming a Move / group / sound also renames everything that refers to it."""
    if _LOADING:
        return
    old, new = item.prev_name, item.name
    item.prev_name = new
    if old and old != new:
        owner = getattr(item, "id_data", None)          # the Scene that holds the settings
        settings = getattr(owner, "gymnast_move_editor", None) or get_settings(context)
        rename_references(settings, kind, old, new)


def _on_move_renamed(self, context):
    _renamed(self, context, 'MOVE')


def _on_event_group_renamed(self, context):
    _renamed(self, context, 'EVENT_GROUP')


def _on_reaction_group_renamed(self, context):
    _renamed(self, context, 'REACTION_GROUP')


def _on_sound_renamed(self, context):
    _renamed(self, context, 'SOUND')


def _on_trajectory_toggled(self, context):
    """Shows or hides the COM path at once, from the animation already on the timeline."""
    if _LOADING:
        return
    try:
        if self.show_trajectory and not _LAST["kind"]:
            return                      # nothing previewed yet: drawn with the next preview
        update_trajectory(getattr(context, "scene", None) or bpy.context.scene, self)
    except Exception as err:
        print(f"[Move Editor] Could not draw the COM path: {err}")


def _on_condition_changed(self, context):
    if not _LOADING:
        refresh_condition_view(context, _settings_of(self, context))


def _on_condition_offset_changed(self, context):
    if not _LOADING:
        refresh_condition_view(context, self)


def _on_condition_view_toggled(self, context):
    """Runs from a timer: it imports an animation and starts playback."""
    if _LOADING:
        return
    settings, on = self, self.condition_view

    def run():
        context = bpy.context
        try:
            if on:
                enter_condition_view(context)
            else:
                exit_condition_view(context)
        except MoveEditorError as err:
            settings.preview_status = str(err)
            clear_condition_view()
            set_condition_view(settings, False)
        except Exception as err:
            print(f"[Move Editor] Condition View failed: {err}")
            clear_condition_view()
            set_condition_view(settings, False)
        return None

    bpy.app.timers.register(run, first_interval=0.01)


def _on_move_selected(self, context):
    schedule_preview(self, 'MOVE')


def _on_reaction_selected(self, context):
    if not _LOADING:
        schedule_preview(_settings_of(self, context), 'REACTION')


# ---- Live Update: edits redo the last preview -----------------------------------

def _settings_of(item, context):
    owner = getattr(item, "id_data", None)
    return getattr(owner, "gymnast_move_editor", None) or get_settings(context)


def _in_last_preview(move_name):
    return any(name == move_name for name, _ in _LAST["segments"])


def format_item_name(text):
    """Trick item names are always TRICK_<NAME> in capitals, without spaces.
    'my cool awesome trick' -> TRICK_MYCOOLAWESOMETRICK, 'TRICK_hello' -> TRICK_HELLO, 'trick_' -> TRICK_."""
    text = text.strip()
    if not text:
        return ""
    upper = text.upper()
    rest = upper[len("TRICK_"):] if upper.startswith("TRICK_") else upper
    return "TRICK_" + re.sub(r"[^A-Z0-9_]", "", rest)


def _on_item_name_changed(self, context):
    if _LOADING:
        return                          # names in the file are kept exactly as they are
    formatted = format_item_name(self.item_name)
    if formatted != self.item_name:
        self.item_name = formatted


def _on_move_changed(self, context):
    """Animation, frames, pivot, Binding, Velocity, Gravity: re-import once the value settles."""
    if not _LOADING and _in_last_preview(self.name):
        schedule_live_update(_settings_of(self, context))


def _on_detector_range_changed(self, context):
    """DeltaDetectorH/V: only the boxes change, updated right away while dragging."""
    if _LOADING or not _in_last_preview(self.name) or not _settings_of(self, context).live_preview:
        return
    try:
        refresh_detector_boxes(getattr(context, "scene", None) or bpy.context.scene, self)
    except Exception as err:
        print(f"[Move Editor] Could not update the detector boxes: {err}")


def _on_reaction_changed(self, context):
    """Target move / Start Frame of the previewed reaction. Special reactions (Death) keep their fixed values."""
    if _LOADING:
        return
    if is_special(self.name):
        if self.first_frame != 1:
            self.first_frame = 1
        if self.priority != 1:
            self.priority = 1
    if _LAST["kind"] != 'REACTION':
        return
    settings = _settings_of(self, context)
    if self == current_reaction(settings):
        schedule_live_update(settings)


def _on_timing_changed(self, context):
    """Interval End, event type and On Frame frame: they move the switch to a sequential reaction."""
    if _LOADING or _LAST["kind"] != 'REACTION':
        return
    settings = _settings_of(self, context)
    if settings.tab == 'MOVES' and (self == active(settings)[1] or self == current_event(settings)):
        schedule_live_update(settings)







# ============================================================================ #
#  Data
# ============================================================================ #
#
#  Every item keeps `raw` (the attributes exactly as loaded, to keep their order and text),
#  `extra_attrs` (attributes without a field), `extra_xml` (child elements without a field)
#  and `comment_before` (comments written right before it).

class GTS_ME_Sound(bpy.types.PropertyGroup):
    """A sound played by an interval or event."""
    name: StringProperty(name="Sound", description="Sound to play. Several can be separated with '|' (from the Sounds tab)")
    sound_type: IntProperty(name="Type", min=0, max=1, description="0 is used for voice sounds (m_jump, m_hit) and 1 for effects in the original file")
    raw: StringProperty()
    extra_attrs: StringProperty(name="Other Attributes")


class GTS_ME_Condition(bpy.types.PropertyGroup):
    kind: EnumProperty(name="Measure", items=CONDITION_KINDS, update=_on_condition_changed)
    node: EnumProperty(name="Node", items=CONDITION_NODES, default='V', update=_on_condition_changed)
    corner: EnumProperty(name="From Corner", items=CORNERS, description="Corner of the collision the distance is measured from", update=_on_condition_changed)
    use_min: BoolProperty(name="Min", description="Value must be at least this much", update=_on_condition_changed)
    min: FloatProperty(name="Min", precision=2, update=_on_condition_changed)
    use_max: BoolProperty(name="Max", description="Value must be at most this much", update=_on_condition_changed)
    max: FloatProperty(name="Max", precision=2, update=_on_condition_changed)
    raw: StringProperty()
    extra_attrs: StringProperty(name="Other Attributes")
    extra_xml: StringProperty()


class GTS_ME_Reaction(bpy.types.PropertyGroup):
    name: StringProperty(name="Move", description="The Move this reaction switches to", update=_on_reaction_changed)
    first_frame: IntProperty(name="Start Frame", min=0, description="Frame of the new Move to start from (FirstFrame)", update=_on_reaction_changed)
    priority: IntProperty(name="Priority", description="When several reactions are possible, the highest Priority wins", update=_on_reaction_changed)
    trigger_name: StringProperty(name="Trigger Name", description="Only reacts inside the trigger area with this name (TriggerName)")
    on_end_trigger: BoolProperty(name="When Leaving the Area", description="React when the player leaves the trigger area instead (OnEndTrigger). Tricks use this")
    sides: EnumProperty(name="Side", items=SIDES, description="Side of the collision the detector must touch (Sides). A wrong side can teleport the character")
    corner_cling: BoolProperty(name="Snap to Corner", description="Snaps DetectorV to the top left corner of the collision, used for climbing (CornerCling)")
    inside_h: BoolProperty(name="Ground Detector Inside", description="DetectorH must overlap a collision (InsideH)")
    inside_v: BoolProperty(name="Wall Detector Inside", description="DetectorV must overlap a collision (InsideV)")
    slope_h: EnumProperty(name="Ground Slope", items=SLOPES, description="Slope DetectorH must touch (SlopeH)")
    slope_v: EnumProperty(name="Wall Slope", items=SLOPES, description="Slope DetectorV must touch (SlopeV)")
    safe_h: BoolProperty(name="Ignore Ground Collisions", description="Disables DetectorH collision events (SafeH)")
    safe_v: BoolProperty(name="Ignore Wall Collisions", description="Disables DetectorV collision events (SafeV)")
    reverse: BoolProperty(name="Reverse Direction", update=_on_reaction_changed,
                          description="The new move plays facing and travelling the opposite way (Reverse)")
    nodes_wi: StringProperty(name="NodesWI", description="Mostly used by landings, usually DetectorV. Its exact behaviour is undocumented")
    conditions: CollectionProperty(type=GTS_ME_Condition)
    comment_before: StringProperty()
    raw: StringProperty()
    extra_attrs: StringProperty(name="Other Attributes", description='Attributes without a field, written as Name="Value"')
    extra_xml: StringProperty()


class GTS_ME_Event(bpy.types.PropertyGroup):
    event_type: EnumProperty(name="When", items=EVENT_TYPES, update=_on_timing_changed)
    key: EnumProperty(name="Key", items=KEYS)
    frame: IntProperty(name="Frame", min=0, description="Frame that fires the event. The reaction starts on the next frame", update=_on_timing_changed)
    detector_state: EnumProperty(name="Detector", items=DETECTOR_STATES)
    collision_type: EnumProperty(name="Collides With", items=COLLISION_TYPES)
    type_key: StringProperty()          # "Type" or "Types", as the file wrote it
    groups: StringProperty(name="Reaction Groups", description="Reaction Groups added to this event, separated by '|'")
    sounds: CollectionProperty(type=GTS_ME_Sound)
    reactions: CollectionProperty(type=GTS_ME_Reaction)
    active_reaction_index: IntProperty(default=-1, update=_on_reaction_selected)
    wrapped: BoolProperty(default=True)
    reactions_comment: StringProperty()     # comments right before <Reactions>
    reaction_comments: StringProperty()     # comments at the end of <Reactions>
    comment_before: StringProperty()
    raw: StringProperty()
    extra_attrs: StringProperty(name="Other Attributes", description='Attributes without a field, written as Name="Value"')
    extra_xml: StringProperty()


class GTS_ME_Interval(bpy.types.PropertyGroup):
    start: IntProperty(name="From", min=0, description="First frame of the interval")
    end: IntProperty(name="To", min=0, description="Last frame of the interval", update=_on_timing_changed)
    safe: BoolProperty(name="Invincible", description="No collision can kill the character (Safe)")
    safe_h: BoolProperty(name="Ignore Ground Collisions", description="Disables DetectorH collision events (SafeH)")
    safe_v: BoolProperty(name="Ignore Wall Collisions", description="Disables DetectorV collision events (SafeV)")
    lock: BoolProperty(name="Taser Lock", description="Controls whether the Hunter can tase the player during this interval (Lock)")
    bound_h: BoolProperty(name="Ground", description="DetectorH can bind to any platform, e.g. running onto a moving platform (ConditionlessPlatformBoundH)")
    bound_v: BoolProperty(name="Wall", description="DetectorV can bind to any platform (ConditionlessPlatformBoundV)")
    bound_c: BoolProperty(name="Node", description="A collidable node can bind to any platform (ConditionlessPlatformBoundC)")
    unbound_x: BoolProperty(name="X", description="Stop following the platform horizontally after leaving it (NoPlatformBoundX)")
    unbound_y: BoolProperty(name="Y", description="Stop following the platform vertically after leaving it (NoPlatformBoundY)")
    groups: StringProperty(name="Event Groups", description="Event Groups used during this interval, separated by '|'")
    action: StringProperty(name="Tutorial Button", description="Shows a tutorial button while the interval runs (Action). Any value works, \"1\" is enough")
    lt: StringProperty(name="LT", description="Left Top, written as x|y. Undocumented")
    rb: StringProperty(name="RB", description="Right Bottom, written as x|y. Undocumented")
    sounds: CollectionProperty(type=GTS_ME_Sound)
    events: CollectionProperty(type=GTS_ME_Event)
    active_event_index: IntProperty(default=-1)
    comment_before: StringProperty()
    raw: StringProperty()
    extra_attrs: StringProperty(name="Other Attributes", description='Attributes without a field, written as Name="Value"')
    extra_xml: StringProperty()


class GTS_ME_Move(bpy.types.PropertyGroup):
    name: StringProperty(name="Name", description="Move name. Renaming also updates the reactions that use it", update=_on_move_renamed)
    prev_name: StringProperty()
    move_id: IntProperty(name="ID", min=0, description="0 for normal moves. Tricks use their own ID")
    item_name: StringProperty(name="Item Name", update=_on_item_name_changed,
                              description="Trick item name, used by Trick moves. Always written as TRICK_NAME: "
                                          "\"my cool trick\" becomes TRICK_MYCOOLTRICK")
    move_type: EnumProperty(name="Type", items=MOVE_TYPES)
    sub_type: EnumProperty(name="Counts As", items=SUB_TYPES, description="Statistic this move counts towards (SubType)")
    loop: BoolProperty(name="Loop", description="Kept for the game. Does not change the preview")
    mirror: BoolProperty(name="Mirror", description="Kept for the game. Does not change the preview")
    file_name: StringProperty(name="Animation", description="The .bin / .bytes file of this move (FileName)", update=_on_move_changed)
    mid_frames: IntProperty(name="Mid Frames", min=0, max=2, description="Frames the game blends in between original frames (2 for 20 FPS animations). Information only")
    first_frame: IntProperty(name="First Frame", min=0, description="Frame of the animation the move starts from", update=_on_move_changed)
    end_frame: IntProperty(name="End Frame", min=0, description="Last frame of the move. Can be past the end of the file: the last pose is held", update=_on_move_changed)
    pivot: EnumProperty(name="Pivot Node", items=PIVOTS, description="Node the character is bound to, and lined up with when switching into this move", update=_on_move_changed)
    pivot_custom: StringProperty(name="Node", description="Name of the custom pivot node", update=_on_move_changed)
    priority: IntProperty(name="Priority", description="When several moves are possible, the highest Priority wins")
    velocity_x: FloatProperty(name="Velocity X", description="Horizontal movement per frame (Run = 30, Fast Run = 60)", update=_on_move_changed)
    velocity_y: FloatProperty(name="Velocity Y", description="Vertical movement per frame. Negative goes up", update=_on_move_changed)
    binding: BoolProperty(name="Binding", description="The whole character is bound to the Pivot Node, and the Pivot Node follows Velocity and Gravity", update=_on_move_changed)
    gravity: FloatProperty(name="Gravity", description="Added to Velocity Y every frame. The game's gravity is 2.5", update=_on_move_changed)
    delta_detector_h: FloatProperty(name="Ground Range", description="Extends DetectorH's check left and right (DeltaDetectorH)", update=_on_detector_range_changed)
    delta_detector_v: FloatProperty(name="Wall Range", description="Extends DetectorV's check up and down (DeltaDetectorV)", update=_on_detector_range_changed)
    landing_detector_h: FloatProperty(name="Landing H", description="Horizontal offset of the landing check (LandingPositionDetectorH)")
    landing_detector_v: FloatProperty(name="Landing V", description="Vertical offset of the landing check (LandingPositionDetectorV)")
    auto_detector_h: FloatProperty(name="AutoPosition H", description="AutoPositionDetectorH. Kept for compatibility")
    auto_detector_v: FloatProperty(name="AutoPosition V", description="AutoPositionDetectorV. Kept for compatibility")
    platform_anticipation: FloatProperty(name="Platform Anticipation", description="PlatformAnticipationFrames. Kept for compatibility")
    intervals: CollectionProperty(type=GTS_ME_Interval)
    active_interval_index: IntProperty(default=-1)
    comment_before: StringProperty()
    raw: StringProperty()
    extra_attrs: StringProperty(name="Other Attributes", description='Attributes without a field, written as Name="Value"')
    extra_xml: StringProperty()


class GTS_ME_EventGroup(bpy.types.PropertyGroup):
    name: StringProperty(name="Name", description="Group name. Renaming also updates the intervals that use it", update=_on_event_group_renamed)
    prev_name: StringProperty()
    events: CollectionProperty(type=GTS_ME_Event)
    active_event_index: IntProperty(default=-1)
    comment_before: StringProperty()
    raw: StringProperty()
    extra_attrs: StringProperty(name="Other Attributes", description='Attributes without a field, written as Name="Value"')
    extra_xml: StringProperty()


class GTS_ME_ReactionGroup(bpy.types.PropertyGroup):
    name: StringProperty(name="Name", description="Group name. Renaming also updates the events that use it", update=_on_reaction_group_renamed)
    prev_name: StringProperty()
    reactions: CollectionProperty(type=GTS_ME_Reaction)
    active_reaction_index: IntProperty(default=-1, update=_on_reaction_selected)
    comment_before: StringProperty()
    raw: StringProperty()
    extra_attrs: StringProperty(name="Other Attributes", description='Attributes without a field, written as Name="Value"')
    extra_xml: StringProperty()


class GTS_ME_SoundEntry(bpy.types.PropertyGroup):
    """An entry of the <Sounds> list."""
    name: StringProperty(name="Name", description="Sound name, the .wav lives in sound.dz or the sounds folder. "
                                                  "Renaming also updates the moves that play it", update=_on_sound_renamed)
    prev_name: StringProperty()
    comment_before: StringProperty()
    raw: StringProperty()
    extra_attrs: StringProperty(name="Other Attributes", description='Attributes without a field, written as Name="Value"')


class GTS_ME_Ref(bpy.types.PropertyGroup):
    """One Find References result."""
    label: StringProperty()
    path: StringProperty()      # JSON, see go_to()


class GTS_ME_Settings(bpy.types.PropertyGroup):
    moves_xml: StringProperty(name="Moves XML", subtype='FILE_PATH', description="The moves.xml to edit")
    bin_folder: StringProperty(name="Animations", subtype='DIR_PATH', description="Folder with the .bin / .bytes animation files")
    tab: EnumProperty(name="Tab", items=TABS)

    moves: CollectionProperty(type=GTS_ME_Move)
    active_move_index: IntProperty(default=-1, update=_on_move_selected)
    search: StringProperty(name="Search", description="Filter moves by name or animation file", options={'TEXTEDIT_UPDATE'})

    event_groups: CollectionProperty(type=GTS_ME_EventGroup)
    active_event_group_index: IntProperty(default=-1)
    reaction_groups: CollectionProperty(type=GTS_ME_ReactionGroup)
    active_reaction_group_index: IntProperty(default=-1)
    sounds: CollectionProperty(type=GTS_ME_SoundEntry)
    active_sound_index: IntProperty(default=-1)
    sound_search: StringProperty(name="Search", description="Filter sounds by name", options={'TEXTEDIT_UPDATE'})

    refs: CollectionProperty(type=GTS_ME_Ref)
    active_ref_index: IntProperty(default=-1)
    refs_title: StringProperty()

    auto_preview: BoolProperty(name="Auto Preview", description="Preview a move or reaction as soon as it is selected", default=True)
    condition_view: BoolProperty(name="Condition View", default=False, update=_on_condition_view_toggled,
                                 description="Show the reaction's Width / Height / Distance conditions as a box next to "
                                             "the reaction preview. Switch off to remove the box")
    condition_offset_x: FloatProperty(name="Box Offset X", default=VIEW_OFFSET_X, update=_on_condition_offset_changed,
                                      description="Where the box starts along X (its bottom left corner), "
                                                  "to line it up with the animation")
    condition_size_x: FloatProperty(name="Box Size X", default=VIEW_DEFAULT_SIZE, update=_on_condition_offset_changed,
                                    description="Width of the box, to the right of Box Offset X")
    condition_size_y: FloatProperty(name="Box Size Y", default=VIEW_DEFAULT_SIZE, update=_on_condition_offset_changed,
                                    description="Height of the box, up from the ground")
    show_trajectory: BoolProperty(name="Show COM Path", default=True, update=_on_trajectory_toggled,
                                  description="Draw the path the COM travels during the preview (COMTrajectory in the Misc collection)")
    live_preview: BoolProperty(name="Live Update", default=True,
                               description="Edits to the previewed move or reaction update the timeline. Detector ranges update "
                                           "while dragging, everything else once the value stops changing")
    play_after_preview: BoolProperty(name="Play", description="Start playback after a preview", default=True)
    show_detectors: BoolProperty(name="Show Detector Ranges", description="Show DeltaDetectorH/V as boxes around DetectorH and DetectorV", default=True)
    preview_status: StringProperty()

    template: StringProperty()           # the file with its four edited sections emptied
    tails: StringProperty()              # JSON: section -> XML kept for the end of the section
    encoding: StringProperty(default="windows-1251")
    newline: StringProperty(default="\r\n")







# ============================================================================ #
#  Operators
# ============================================================================ #

class MoveEditorOperator(bpy.types.Operator):
    """Subclasses implement run(); a MoveEditorError becomes a normal Blender error message."""
    bl_options = {'REGISTER', 'UNDO'}

    def run(self, context):
        raise NotImplementedError

    def execute(self, context):
        try:
            return self.run(context) or {'FINISHED'}
        except MoveEditorError as err:
            self.report({'ERROR'}, str(err))
            return {'CANCELLED'}
        except OSError as err:
            self.report({'ERROR'}, f"Could not read or write the file: {err}")
            return {'CANCELLED'}


def confirm(operator, context, event, message):
    try:
        return context.window_manager.invoke_confirm(operator, event, message=message)
    except TypeError:            # Blender before 4.1
        return context.window_manager.invoke_confirm(operator, event)


def moves_path(settings):
    path = bpy.path.abspath(settings.moves_xml) if settings.moves_xml else ""
    return os.path.join(path, "moves.xml") if path and os.path.isdir(path) else path


def _set_index(owner, prop, value):
    """Changes a selection without starting an auto preview."""
    global _LOADING
    _LOADING += 1
    try:
        setattr(owner, prop, value)
    finally:
        _LOADING -= 1


class GTS_OT_me_load(MoveEditorOperator):
    bl_idname = "gts_moveedit.load"
    bl_label = "Load"
    bl_description = "Load the moves, groups and sounds from the Moves XML"
    bl_options = {'REGISTER'}

    def invoke(self, context, event):
        if is_loaded(get_settings(context)):
            return confirm(self, context, event, "Reload and lose unsaved changes?")
        return self.execute(context)

    def run(self, context):
        settings = get_settings(context)
        count = load_file(settings, moves_path(settings))
        self.report({'INFO'}, f"Loaded {count} moves, {len(settings.event_groups)} event groups, "
                              f"{len(settings.reaction_groups)} reaction groups, {len(settings.sounds)} sounds")


class GTS_OT_me_save(MoveEditorOperator):
    bl_idname = "gts_moveedit.save"
    bl_label = "Save"
    bl_description = "Write everything back into the Moves XML."
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return is_loaded(get_settings(context))

    def invoke(self, context, event):
        return confirm(self, context, event, f"Overwrite {os.path.basename(moves_path(get_settings(context)))}?")

    def run(self, context):
        settings = get_settings(context)
        path = moves_path(settings)
        if not path:
            raise MoveEditorError("Set the Moves XML path first.")
        save_file(settings, path)
        self.report({'INFO'}, f"Saved {os.path.basename(path)}")


class GTS_OT_me_save_as(MoveEditorOperator):
    bl_idname = "gts_moveedit.save_as"
    bl_label = "Save As"
    bl_description = "Save to a new file. From then on, Moves XML points to that file"
    bl_options = {'REGISTER'}

    filepath: StringProperty(subtype='FILE_PATH')
    filename_ext = ".xml"
    filter_glob: StringProperty(default="*.xml", options={'HIDDEN'})
    check_existing: BoolProperty(default=True, options={'HIDDEN'})

    @classmethod
    def poll(cls, context):
        return is_loaded(get_settings(context))

    def invoke(self, context, event):
        current = moves_path(get_settings(context))
        self.filepath = current or "moves.xml"
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def run(self, context):
        path = bpy.path.abspath(self.filepath)
        if not path or os.path.isdir(path):
            raise MoveEditorError("Choose a file name to save to.")
        if not path.lower().endswith(".xml"):
            path += ".xml"
        settings = get_settings(context)
        save_file(settings, path)
        settings.moves_xml = path           # like Save As anywhere else: the new file is now the one being edited
        self.report({'INFO'}, f"Saved as {path}")


# ---------------------------------------------------------------------------- #
#  Lists: remove / duplicate / reorder
# ---------------------------------------------------------------------------- #

LEVELS = [('MOVE', "move", ""), ('INTERVAL', "interval", ""), ('EVENT', "event", ""), ('REACTION', "reaction", ""),
          ('EVENT_GROUP', "event group", ""), ('REACTION_GROUP', "reaction group", ""), ('SOUND', "sound", "")]
LEVEL_LABEL = {l[0]: l[1] for l in LEVELS}
NAMED_LEVELS = {'MOVE', 'EVENT_GROUP', 'REACTION_GROUP', 'SOUND'}


def level_list(settings, level):
    """(collection, owner, index property) of a level, or None when its parent isn't selected."""
    if level == 'MOVE':
        return settings.moves, settings, "active_move_index"
    if level == 'EVENT_GROUP':
        return settings.event_groups, settings, "active_event_group_index"
    if level == 'REACTION_GROUP':
        return settings.reaction_groups, settings, "active_reaction_group_index"
    if level == 'SOUND':
        return settings.sounds, settings, "active_sound_index"
    if level == 'INTERVAL':
        move = active(settings)[0]
        return (move.intervals, move, "active_interval_index") if move else None
    if level == 'EVENT':
        owner = event_owner(settings)
        return (owner.events, owner, "active_event_index") if owner else None
    if level == 'REACTION':
        owner = reaction_owner(settings)
        return (owner.reactions, owner, "active_reaction_index") if owner else None
    return None


class GTS_OT_me_list(MoveEditorOperator):
    bl_idname = "gts_moveedit.list"
    bl_label = "Edit List"

    level: EnumProperty(items=LEVELS, options={'HIDDEN'})
    action: EnumProperty(items=[('REMOVE', "Remove", ""), ('DUPLICATE', "Duplicate", ""),
                                ('UP', "Move Up", ""), ('DOWN', "Move Down", "")], options={'HIDDEN'})

    @classmethod
    def description(cls, context, properties):
        what = LEVEL_LABEL[properties.level]
        return {'REMOVE': f"Remove the selected {what}", 'DUPLICATE': f"Duplicate the selected {what}",
                'UP': f"Move the selected {what} up", 'DOWN': f"Move the selected {what} down"}[properties.action]

    def run(self, context):
        global _LOADING
        settings = get_settings(context)
        found = level_list(settings, self.level)
        if not found:
            return {'CANCELLED'}
        items, owner, prop = found
        i = getattr(owner, prop)
        if not 0 <= i < len(items):
            return {'CANCELLED'}

        if self.action == 'REMOVE':
            items.remove(i)
            _set_index(owner, prop, min(i, len(items) - 1))
        elif self.action == 'DUPLICATE':
            _LOADING += 1
            try:
                new = items.add()
                copy_group(items[i], new)
                new.comment_before = ""
                if self.level in NAMED_LEVELS:
                    set_name_silent(new, unique_name(items, f"{items[i].name}Copy"))
            finally:
                _LOADING -= 1
            items.move(len(items) - 1, i + 1)
            _set_index(owner, prop, i + 1)
        else:
            j = i - 1 if self.action == 'UP' else i + 1
            if 0 <= j < len(items):
                items.move(i, j)
                _set_index(owner, prop, j)


# ---------------------------------------------------------------------------- #
#  Adding
# ---------------------------------------------------------------------------- #

def _insert_after_active(items, owner, prop):
    """Moves the last item of a list to just below the selected one and selects it."""
    current = getattr(owner, prop)
    pos = current + 1 if 0 <= current < len(items) - 1 else len(items) - 1
    items.move(len(items) - 1, pos)
    _set_index(owner, prop, pos)
    return items[pos]


class GTS_OT_me_move_add(MoveEditorOperator):
    bl_idname = "gts_moveedit.move_add"
    bl_label = "Add Move"
    bl_description = "Add a new move below the selected one"

    def run(self, context):
        settings = get_settings(context)
        move = settings.moves.add()
        set_name_silent(move, unique_name(settings.moves, "NewMove"))
        move.raw = json.dumps([["ID", "0"], ["Type", "1"], ["FileName", ""], ["MidFrames", "2"],
                               ["FirstFrame", "0"], ["EndFrame", "0"], ["PivotNode", "DetectorH"], ["Priority", "2"]])
        move.mid_frames, move.pivot, move.priority = 2, 'DetectorH', 2
        interval = move.intervals.add()
        interval.raw = json.dumps([["Start", "0"], ["End", "0"]])
        move.active_interval_index = 0
        _insert_after_active(settings.moves, settings, "active_move_index")


class GTS_OT_me_entry_add(MoveEditorOperator):
    bl_idname = "gts_moveedit.entry_add"
    bl_label = "Add"

    level: EnumProperty(items=LEVELS, options={'HIDDEN'})

    @classmethod
    def description(cls, context, properties):
        return f"Add a new {LEVEL_LABEL[properties.level]} below the selected one"

    def run(self, context):
        settings = get_settings(context)
        items, owner, prop = level_list(settings, self.level)
        base = {'EVENT_GROUP': "NewEventGroup", 'REACTION_GROUP': "NewReactionGroup", 'SOUND': "new_sound"}[self.level]
        item = items.add()
        set_name_silent(item, unique_name(items, base))
        item.raw = json.dumps([["Name", item.name]])
        _insert_after_active(items, owner, prop)


class GTS_OT_me_interval_add(MoveEditorOperator):
    bl_idname = "gts_moveedit.interval_add"
    bl_label = "Add Interval"
    bl_description = "Add an interval covering the whole move"

    def run(self, context):
        move = active(get_settings(context))[0]
        if move is None:
            return {'CANCELLED'}
        interval = move.intervals.add()
        interval.start, interval.end = move.first_frame, move.end_frame
        interval.raw = json.dumps([["Start", str(interval.start)], ["End", str(interval.end)]])
        move.active_interval_index = len(move.intervals) - 1


class GTS_OT_me_event_add(MoveEditorOperator):
    bl_idname = "gts_moveedit.event_add"
    bl_label = "Add Event"
    bl_description = "Add something to react to"

    event_type: EnumProperty(name="When", items=EVENT_TYPES)

    def run(self, context):
        owner = event_owner(get_settings(context))
        if owner is None:
            return {'CANCELLED'}
        event = owner.events.add()
        event.event_type = self.event_type
        raw = []
        if self.event_type == 'Keys':
            raw = [["Key", "Up"]]
        elif self.event_type == 'OnFrame':
            event.frame = getattr(owner, "end", 0)
            raw = [["Frame", str(event.frame)]]
        elif self.event_type in DETECTOR_EVENTS:
            event.type_key, raw = "Type", [["Type", "1"]]
        elif self.event_type == 'OnCollision':
            event.type_key, raw = "Types", [["Types", "1"]]
        event.raw = json.dumps(raw)
        _set_index(owner, "active_event_index", len(owner.events) - 1)


_MOVE_ITEMS = []


def _move_items(self, context):
    global _MOVE_ITEMS
    names = list(SPECIAL_REACTIONS) + sorted({m.name for m in get_settings(context).moves} - set(SPECIAL_REACTIONS), key=str.lower)
    _MOVE_ITEMS = [(n, n, SPECIAL_REACTIONS.get(n, "")) for n in names]
    return _MOVE_ITEMS


class GTS_OT_me_reaction_add(MoveEditorOperator):
    bl_idname = "gts_moveedit.reaction_add"
    bl_label = "Add Reaction"
    bl_description = "Choose the move to switch to"
    bl_property = "target"

    target: EnumProperty(name="Move", items=_move_items)

    def invoke(self, context, event):
        context.window_manager.invoke_search_popup(self)
        return {'RUNNING_MODAL'}

    def run(self, context):
        owner = reaction_owner(get_settings(context))
        if owner is None or self.target == "__NONE__":
            return {'CANCELLED'}
        reaction = owner.reactions.add()
        reaction.name = self.target
        reaction.first_frame, reaction.priority = 1, 1
        reaction.raw = json.dumps([["FirstFrame", "1"], ["Priority", "1"]])
        _set_index(owner, "active_reaction_index", len(owner.reactions) - 1)


class GTS_OT_me_condition_add(MoveEditorOperator):
    bl_idname = "gts_moveedit.condition_add"
    bl_label = "Add Condition"
    bl_description = "Only react when the touched collision or the node's speed matches"

    kind: EnumProperty(name="Measure", items=CONDITION_KINDS)

    def run(self, context):
        reaction = current_reaction(get_settings(context))
        if reaction is None:
            return {'CANCELLED'}
        cond = reaction.conditions.add()
        cond.kind = self.kind
        cond.node = 'H' if self.kind.startswith("Velosity") else 'V'
        cond.use_min = True
        cond.raw = json.dumps([["Min", "0"], ["Type", cond.node], ["Corner", "0"]])
        refresh_condition_view(context, get_settings(context))


class GTS_OT_me_condition_remove(MoveEditorOperator):
    bl_idname = "gts_moveedit.condition_remove"
    bl_label = "Remove Condition"
    bl_description = "Remove this condition"

    index: IntProperty(options={'HIDDEN'})

    def run(self, context):
        reaction = current_reaction(get_settings(context))
        if reaction and 0 <= self.index < len(reaction.conditions):
            reaction.conditions.remove(self.index)
            refresh_condition_view(context, get_settings(context))


SOUND_SCOPES = [('EVENT', "Event", ""), ('INTERVAL', "Interval", "")]


def _sound_owner(settings, scope):
    return active(settings)[1] if scope == 'INTERVAL' else current_event(settings)


class GTS_OT_me_sound_add(MoveEditorOperator):
    bl_idname = "gts_moveedit.sound_add"
    bl_label = "Add Sound"
    bl_description = "Play a sound"

    scope: EnumProperty(items=SOUND_SCOPES, options={'HIDDEN'})

    def run(self, context):
        settings = get_settings(context)
        owner = _sound_owner(settings, self.scope)
        if owner is None:
            return {'CANCELLED'}
        sound = owner.sounds.add()
        sound.name = settings.sounds[0].name if len(settings.sounds) else "step1"
        sound.sound_type = 1
        sound.raw = json.dumps([["Name", sound.name], ["Type", "1"]])


class GTS_OT_me_sound_remove(MoveEditorOperator):
    bl_idname = "gts_moveedit.sound_remove"
    bl_label = "Remove Sound"
    bl_description = "Remove this sound"

    scope: EnumProperty(items=SOUND_SCOPES, options={'HIDDEN'})
    index: IntProperty(options={'HIDDEN'})

    def run(self, context):
        owner = _sound_owner(get_settings(context), self.scope)
        if owner and 0 <= self.index < len(owner.sounds):
            owner.sounds.remove(self.index)




# ---------------------------------------------------------------------------- #
#  Pickers
# ---------------------------------------------------------------------------- #

PICK_TARGETS = [
    ('FILE', "Animation", "Pick an animation file from the Animations folder"),
    ('REACTION', "Move", "Pick the move this reaction starts"),
    ('INTERVAL_GROUPS', "Event Group", "Add an Event Group"),
    ('EVENT_GROUPS', "Reaction Group", "Add a Reaction Group"),
    ('EVENT_SOUND', "Sound", "Pick a sound from the Sounds tab"),
    ('INTERVAL_SOUND', "Sound", "Pick a sound from the Sounds tab"),
]

_PICK_ITEMS = []


def _pick_names(settings, target):
    if target == 'FILE':
        return list_bins(settings)[0]
    if target == 'REACTION':
        return list(SPECIAL_REACTIONS) + sorted({m.name for m in settings.moves} - set(SPECIAL_REACTIONS), key=str.lower)
    if target == 'INTERVAL_GROUPS':
        return [g.name for g in settings.event_groups]
    if target == 'EVENT_GROUPS':
        return [g.name for g in settings.reaction_groups]
    return [s.name for s in settings.sounds]


def _pick_items(self, context):
    global _PICK_ITEMS
    names = [n for n in _pick_names(get_settings(context), self.target) if n]
    _PICK_ITEMS = [(n, n, "") for n in dict.fromkeys(names)] or [("__NONE__", "Nothing to pick from", "")]
    return _PICK_ITEMS


class GTS_OT_me_pick(MoveEditorOperator):
    bl_idname = "gts_moveedit.pick"
    bl_label = "Pick"
    bl_property = "choice"

    target: EnumProperty(items=PICK_TARGETS, options={'HIDDEN'})
    index: IntProperty(options={'HIDDEN'})
    choice: EnumProperty(items=_pick_items)

    @classmethod
    def description(cls, context, properties):
        return next(t[2] for t in PICK_TARGETS if t[0] == properties.target)

    def invoke(self, context, event):
        context.window_manager.invoke_search_popup(self)
        return {'RUNNING_MODAL'}

    def run(self, context):
        if self.choice == "__NONE__":
            return {'CANCELLED'}
        settings = get_settings(context)
        move, interval, _, _ = active(settings)
        event, reaction = current_event(settings), current_reaction(settings)
        if self.target == 'FILE' and move:
            move.file_name = self.choice
        elif self.target == 'REACTION' and reaction:
            reaction.name = self.choice
        elif self.target in ('INTERVAL_GROUPS', 'EVENT_GROUPS'):
            owner = interval if self.target == 'INTERVAL_GROUPS' else event
            if owner:
                parts = split_names(owner.groups)
                if self.choice not in parts:
                    parts.append(self.choice)
                owner.groups = "|".join(parts)
        else:
            owner = event if self.target == 'EVENT_SOUND' else interval
            if owner and 0 <= self.index < len(owner.sounds):
                owner.sounds[self.index].name = self.choice





# ---------------------------------------------------------------------------- #
#  Preview
# ---------------------------------------------------------------------------- #

class GTS_OT_me_find_refs(MoveEditorOperator):
    bl_idname = "gts_moveedit.find_refs"
    bl_label = "Find References"
    bl_options = {'REGISTER'}

    kind: EnumProperty(items=REF_KINDS, options={'HIDDEN'})

    @classmethod
    def description(cls, context, properties):
        return {'MOVE': "List every reaction that switches to the selected move",
                'EVENT_GROUP': "List every interval that uses the selected event group",
                'REACTION_GROUP': "List every event that uses the selected reaction group",
                'SOUND': "List every interval and event that plays the selected sound"}[properties.kind]

    def run(self, context):
        settings = get_settings(context)
        found = level_list(settings, self.kind)
        item = pick(found[0], getattr(found[1], found[2])) if found else None
        if item is None:
            return {'CANCELLED'}
        settings.refs.clear()
        for label, path in find_references(settings, self.kind, item.name):
            ref = settings.refs.add()
            ref.label, ref.path = label, json.dumps(path)
        settings.active_ref_index = -1
        count = len(settings.refs)
        settings.refs_title = f"{item.name}: {count} reference{'s' if count != 1 else ''}"
        self.report({'INFO'}, settings.refs_title)


class GTS_OT_me_go_ref(MoveEditorOperator):
    bl_idname = "gts_moveedit.go_ref"
    bl_label = "Go to Reference"
    bl_description = "Show this in its tab"
    bl_options = {'REGISTER'}

    index: IntProperty(options={'HIDDEN'})

    def run(self, context):
        settings = get_settings(context)
        if not 0 <= self.index < len(settings.refs):
            return {'CANCELLED'}
        settings.active_ref_index = self.index
        if not go_to(settings, json.loads(settings.refs[self.index].path)):
            raise MoveEditorError("The lists changed since the search. Press Find References again.")


class GTS_OT_me_clear_refs(bpy.types.Operator):
    bl_idname = "gts_moveedit.clear_refs"
    bl_label = "Close References"
    bl_description = "Close the search results"
    bl_options = {'REGISTER'}

    def execute(self, context):
        settings = get_settings(context)
        settings.refs.clear()
        settings.refs_title = ""
        return {'FINISHED'}


class GTS_OT_me_set_frame(MoveEditorOperator):
    bl_idname = "gts_moveedit.set_frame"
    bl_label = "Use Current Frame"
    bl_description = "Set this to the frame shown at the timeline's current frame"

    which: EnumProperty(items=[('FIRST', "First Frame", ""), ('END', "End Frame", ""),
                               ('INTERVAL_START', "Interval Start", ""), ('INTERVAL_END', "Interval End", ""),
                               ('EVENT_FRAME', "Event Frame", "")], options={'HIDDEN'})

    def run(self, context):
        settings = get_settings(context)
        move, interval, _, _ = active(settings)
        if self.which in ('FIRST', 'END'):
            target, prop = move, "first_frame" if self.which == 'FIRST' else "end_frame"
        elif self.which in ('INTERVAL_START', 'INTERVAL_END'):
            target, prop = interval, "start" if self.which == 'INTERVAL_START' else "end"
        else:
            target, prop = current_event(settings), "frame"
            if settings.tab != 'MOVES':
                move = None             # an Event Group has no move: use what is under the playhead
        if target is None:
            return {'CANCELLED'}
        frame = animation_frame_at(context.scene, move)
        setattr(target, prop, frame)
        self.report({'INFO'}, f"Set to frame {frame}")


class GTS_OT_me_preview(bpy.types.Operator):
    bl_idname = "gts_moveedit.preview"
    bl_label = "Preview"
    bl_options = {'REGISTER'}

    kind: EnumProperty(items=[('MOVE', "Move", ""), ('REACTION', "Reaction", "")], options={'HIDDEN'})

    @classmethod
    def description(cls, context, properties):
        if properties.kind == 'MOVE':
            return "Load the selected move on the timeline with Animation Tools"
        return ("Load the reaction on the timeline. Interval End / On Frame reactions of a move play after it, "
                "everything else plays the reaction move on its own")

    def execute(self, context):
        ok, message = preview(context, self.kind)
        self.report({'INFO'} if ok else {'ERROR'}, message)
        return {'FINISHED'} if ok else {'CANCELLED'}






# ============================================================================ #
#  Interface
# ============================================================================ #
#
#  Layout follows Blender's own editors (Human Interface Guidelines):
#    - labels on the left, values on the right (use_property_split)
#    - related checkboxes grouped under one heading instead of long checkbox names
#    - a checkbox that switches a section on lives in that section's header (Binding)
#    - lists use Blender's side column: Add, Remove, Duplicate, Find References, Move Up / Down
#    - rarely used settings sit in collapsed sections, preview toggles in one popover
#    - every panel header shows what is selected in it, on the right

TYPE_ICONS = {'1': 'ARMATURE_DATA', '2': 'PHYSICS', '3': 'SHADERFX', '4': 'TOOL_SETTINGS', '5': 'HAND'}
TAB_LABEL = {t[0]: t[1] for t in TABS}


def event_trigger_text(event):
    kind = event.event_type
    if kind == 'Keys':
        return f"Key {event.key}"
    if kind in DETECTOR_EVENTS:
        place = "Ground" if kind == 'DetectorH' else "Wall"
        return f"{place} {'touched' if event.detector_state == '1' else 'left'}"
    if kind == 'OnCollision':
        return f"Hit {dict((c[0], c[1]) for c in COLLISION_TYPES)[event.collision_type].lower()}"
    if kind == 'OnFrame':
        return f"Frame {event.frame}"
    return EVENT_LABEL.get(kind, kind)


def event_targets(event):
    names = [r.name for r in event.reactions]
    if names:
        return ", ".join(names[:2]) + (f" +{len(names) - 2}" if len(names) > 2 else "")
    if event.groups:
        return f"[{event.groups}]"
    if len(event.sounds):
        return "sound"
    return "—"


def event_summary(event):
    return f"{event_trigger_text(event)}  →  {event_targets(event)}"


def plural(count, word):
    return f"{count} {word}{'' if count == 1 else 's'}"


# ---------------------------------------------------------------------------- #
#  Small layout helpers
# ---------------------------------------------------------------------------- #

def split_layout(layout):
    """Labels on the left, values on the right, no animation dots."""
    layout.use_property_split = True
    layout.use_property_decorate = False
    return layout


def split_row(layout, text):
    """A row that lines up with property-split fields: `text` on the left, returns the right side."""
    split = layout.split(factor=0.4, align=True)
    left = split.row()
    left.alignment = 'RIGHT'
    left.label(text=text)
    return split.row(align=True)


def dim_label(layout, text, icon='NONE'):
    sub = layout.row()
    sub.active = False
    sub.label(text=text, icon=icon)


def _picker(layout, target, index=0):
    op = layout.operator(GTS_OT_me_pick.bl_idname, text="", icon='VIEWZOOM')
    op.target, op.index = target, index


def list_with_buttons(layout, list_cls, data, prop, active_data, active_prop, level,
                      add_operator=None, add_menu=None, add_level=None, rows=5):
    """A list with Blender's side column: Add, Remove, Duplicate, Find References, Move Up / Down."""
    items = getattr(data, prop)
    row = layout.row()
    row.template_list(list_cls.__name__, "", data, prop, active_data, active_prop,
                      rows=rows if len(items) else 3)
    col = row.column(align=True)
    if add_menu:
        col.operator_menu_enum(add_menu[0], add_menu[1], text="", icon='ADD')
    elif add_level:
        col.operator(GTS_OT_me_entry_add.bl_idname, text="", icon='ADD').level = add_level
    else:
        col.operator(add_operator, text="", icon='ADD')
    sub = col.column(align=True)
    sub.enabled = len(items) > 0
    op = sub.operator(GTS_OT_me_list.bl_idname, text="", icon='REMOVE')
    op.level, op.action = level, 'REMOVE'
    op = sub.operator(GTS_OT_me_list.bl_idname, text="", icon='DUPLICATE')
    op.level, op.action = level, 'DUPLICATE'
    if level in NAMED_LEVELS:
        sub.separator()
        sub.operator(GTS_OT_me_find_refs.bl_idname, text="", icon='VIEWZOOM').kind = level
    if len(items) > 1:
        col.separator()
        for action, icon in (('UP', 'TRIA_UP'), ('DOWN', 'TRIA_DOWN')):
            op = col.operator(GTS_OT_me_list.bl_idname, text="", icon=icon)
            op.level, op.action = level, action


def used_by(layout, settings, kind, name, what):
    """'Used By   12 reactions  [search]' lined up with the fields above it."""
    count = count_uses(settings, kind, name)
    row = split_row(layout, "Used By")
    row.label(text=plural(count, what))
    row.operator(GTS_OT_me_find_refs.bl_idname, text="", icon='VIEWZOOM').kind = kind


def preview_button(layout, text, kind, enabled=True):
    """The big Preview button, with the preview options in a popover next to it."""
    row = layout.row(align=True)
    row.scale_y = 1.25
    sub = row.row(align=True)
    sub.enabled = enabled
    sub.operator(GTS_OT_me_preview.bl_idname, text=text, icon='PLAY').kind = kind
    row.popover(panel=GTS_PT_me_preview_options.bl_idname, text="", icon='PREFERENCES')


def preview_status(layout, settings):
    status = settings.preview_status
    if not status:
        return
    if status.startswith("Previewing"):
        return                          # only problems are shown
    else:
        row = layout.row()
        row.alert = True
        row.label(text=status, icon='ERROR')


def draw_sounds(layout, owner, scope):
    col = layout.column(align=True)
    col.use_property_split = False
    for i, sound in enumerate(owner.sounds):
        row = col.row(align=True)
        row.prop(sound, "name", text="", icon='SPEAKER')
        _picker(row, 'EVENT_SOUND' if scope == 'EVENT' else 'INTERVAL_SOUND', i)
        sub = row.row(align=True)
        sub.ui_units_x = 3.5
        sub.prop(sound, "sound_type", text="Type")
        op = row.operator(GTS_OT_me_sound_remove.bl_idname, text="", icon='X')
        op.scope, op.index = scope, i
    layout.operator(GTS_OT_me_sound_add.bl_idname, text="Add Sound", icon='ADD').scope = scope


def draw_advanced(layout, item, idname, fields=()):
    """Rarely used settings. Not drawn at all when the item has none.
    Attributes and child elements without a field are still kept and saved, just not shown."""
    if not fields:
        return
    body = section(layout, idname, "Advanced", icon='PREFERENCES')
    if body is None:
        return
    for prop, text in fields:
        body.prop(item, prop, text=text)


# ---------------------------------------------------------------------------- #
#  Lists
# ---------------------------------------------------------------------------- #

class _PlainList(bpy.types.UIList):
    def draw_filter(self, context, layout):
        pass


def _two_columns(layout, left, right, icon='NONE', factor=0.6):
    split = layout.split(factor=factor)
    split.label(text=left, icon=icon)
    sub = split.row()
    sub.active = False
    sub.label(text=right)


class GTS_UL_me_moves(_PlainList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index=0):
        _two_columns(layout, item.name, item.file_name, TYPE_ICONS.get(item.move_type, 'ACTION'))

    def filter_items(self, context, data, propname):
        query = data.search.strip().lower()
        moves = getattr(data, propname)
        bit = self.bitflag_filter_item
        if not query:
            return [bit] * len(moves), []
        return [bit if query in m.name.lower() or query in m.file_name.lower() else 0 for m in moves], []


class GTS_UL_me_intervals(_PlainList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index=0):
        flags = [n for n, on in (("Safe", item.safe), ("Lock", item.lock)) if on]
        if item.groups:
            flags.append(f"[{item.groups}]")
        right = plural(len(item.events), "event") + (f" · {' '.join(flags)}" if flags else "")
        _two_columns(layout, f"{item.start} – {item.end}", right, 'TIME', factor=0.35)


class GTS_UL_me_events(_PlainList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index=0):
        icon = 'NEXT_KEYFRAME' if item.event_type in SEQUENTIAL_EVENTS else 'PLAY'
        _two_columns(layout, event_trigger_text(item), f"→ {event_targets(item)}", icon, factor=0.5)


class GTS_UL_me_reactions(_PlainList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index=0):
        if is_special(item.name):
            _two_columns(layout, item.name, "special", 'GHOST_ENABLED')
            return
        split = layout.split(factor=0.6)
        name = split.row()
        name.alert = get_settings(context).moves.get(item.name) is None
        name.label(text=item.name or "(no move)", icon='FORWARD')
        sub = split.row()
        sub.active = False
        sub.label(text=f"frame {item.first_frame} · prio {item.priority}")


class GTS_UL_me_event_groups(_PlainList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index=0):
        split = layout.split(factor=0.65)
        split.prop(item, "name", text="", emboss=False, icon='GROUP')
        sub = split.row()
        sub.active = False
        sub.label(text=plural(len(item.events), "event"))


class GTS_UL_me_reaction_groups(_PlainList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index=0):
        split = layout.split(factor=0.65)
        split.prop(item, "name", text="", emboss=False, icon='LINKED')
        sub = split.row()
        sub.active = False
        sub.label(text=plural(len(item.reactions), "reaction"))


class GTS_UL_me_sounds(_PlainList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index=0):
        layout.prop(item, "name", text="", emboss=False, icon='SPEAKER')

    def filter_items(self, context, data, propname):
        query = data.sound_search.strip().lower()
        sounds = getattr(data, propname)
        bit = self.bitflag_filter_item
        return [bit if not query or query in s.name.lower() else 0 for s in sounds], []


class GTS_UL_me_refs(_PlainList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index=0):
        tab = item.path.split('"')[1] if '"' in item.path else 'MOVES'
        op = layout.operator(GTS_OT_me_go_ref.bl_idname, text=item.label, icon=TAB_ICON.get(tab, 'FORWARD'), emboss=False)
        op.index = index


# ---------------------------------------------------------------------------- #
#  Preview options (popover next to every Preview button)
# ---------------------------------------------------------------------------- #

class GTS_PT_me_preview_options(bpy.types.Panel):
    bl_label = "Preview Options"
    bl_idname = "VIEW3D_PT_gymnast_move_editor_preview_options"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'HEADER'

    def draw(self, context):
        layout = split_layout(self.layout)
        settings = get_settings(context)
        col = layout.column(heading="Preview")
        col.prop(settings, "auto_preview", text="On Selection")
        col.prop(settings, "live_preview", text="On Edit")
        col.prop(settings, "play_after_preview", text="Play Afterwards")
        col = layout.column(heading="Show")
        col.prop(settings, "show_detectors", text="Detector Ranges")
        col.prop(settings, "show_trajectory", text="COM Path")


# ---------------------------------------------------------------------------- #
#  Editors shared between tabs
# ---------------------------------------------------------------------------- #

def draw_events(layout, context):
    """Events of the selected Interval (Moves tab) or Event Group."""
    settings = get_settings(context)
    owner = event_owner(settings)
    list_with_buttons(layout, GTS_UL_me_events, owner, "events", owner, "active_event_index", 'EVENT',
                      add_menu=(GTS_OT_me_event_add.bl_idname, "event_type"), rows=4)

    event = current_event(settings)
    if event is None:
        return

    col = split_layout(layout.column())
    col.prop(event, "event_type")
    kind = event.event_type
    if kind == 'Keys':
        col.prop(event, "key")
    elif kind in DETECTOR_EVENTS:
        col.prop(event, "detector_state")
    elif kind == 'OnCollision':
        col.prop(event, "collision_type")
    elif kind == 'OnFrame':
        row = col.row(align=True)
        row.prop(event, "frame")
        row.operator(GTS_OT_me_set_frame.bl_idname, text="", icon='TIME').which = 'EVENT_FRAME'
    row = col.row(align=True)
    row.prop(event, "groups")
    _picker(row, 'EVENT_GROUPS')

    body = section(layout, "GTS_ME_event_sounds", f"Sounds ({len(event.sounds)})", icon='SPEAKER')
    if body:
        draw_sounds(body, event, 'EVENT')
    draw_advanced(layout, event, "GTS_ME_event_adv")


def draw_conditions(layout, reaction):
    for i, cond in enumerate(reaction.conditions):
        box = layout.box()
        row = box.row(align=True)
        row.use_property_split = False
        row.prop(cond, "kind", text="")
        row.prop(cond, "node", text="")
        row.operator(GTS_OT_me_condition_remove.bl_idname, text="", icon='X', emboss=False).index = i
        if not cond.kind.startswith("Velosity"):
            box.prop(cond, "corner", text="From")
        row = box.row(align=True)
        row.use_property_split = False
        for use, value in (("use_min", "min"), ("use_max", "max")):
            row.prop(cond, use, text="")
            sub = row.row(align=True)
            sub.active = getattr(cond, use)
            sub.prop(cond, value)
    layout.operator_menu_enum(GTS_OT_me_condition_add.bl_idname, "kind", text="Add Condition", icon='ADD')


def draw_reactions(layout, context):
    """Reactions of the selected Event (Moves / Event Groups tab) or Reaction Group."""
    settings = get_settings(context)
    owner = reaction_owner(settings)
    list_with_buttons(layout, GTS_UL_me_reactions, owner, "reactions", owner, "active_reaction_index", 'REACTION',
                      add_operator=GTS_OT_me_reaction_add.bl_idname, rows=4)

    reaction = current_reaction(settings)
    if reaction is None:
        return

    special = is_special(reaction.name)
    target = settings.moves.get(reaction.name)
    sequential = settings.tab == 'MOVES' and owner.event_type in SEQUENTIAL_EVENTS

    col = split_layout(layout.column())
    row = col.row(align=True)
    row.prop(reaction, "name")
    _picker(row, 'REACTION')
    if special:
        row = split_row(col, "")
        row.label(text=SPECIAL_REACTIONS[reaction.name], icon='GHOST_ENABLED')
    else:
        if target is None:
            row = split_row(col, "")
            row.alert = True
            row.label(text="No move with this name", icon='ERROR')
        sub = col.column(align=True)
        sub.prop(reaction, "first_frame")
        sub.prop(reaction, "priority")
        col.prop(reaction, "reverse")

    if not special or sequential:
        if special:
            label = f"Preview Move → {reaction.name}"
        else:
            label = "Preview Move → Reaction" if sequential else "Preview Reaction"
        layout.separator(factor=0.5)
        preview_button(layout, label, 'REACTION', enabled=special or target is not None)
        preview_status(layout, settings)

    condition_view_follow_selection(settings)
    body = section(layout, "GTS_ME_conditions", f"Conditions ({len(reaction.conditions)})", icon='FILTER')
    if body:
        row = body.row()
        row.scale_y = 1.2
        row.prop(settings, "condition_view", text="Condition View", toggle=True,
                 icon='HIDE_OFF' if settings.condition_view else 'HIDE_ON')
        if settings.condition_view:
            sub = body.column()
            sub.prop(settings, "condition_offset_x")
            row = split_row(sub, "Box Size")
            row.prop(settings, "condition_size_x", text="X")
            row.prop(settings, "condition_size_y", text="Y")
            if not _condition_ranges(reaction):
                dim_label(body, "No Width, Height or Distance with Min / Max to show", icon='INFO')
            elif any(c.kind.startswith("Velosity") for c in reaction.conditions):
                dim_label(body, "Speed conditions are not shown", icon='INFO')
        draw_conditions(body, reaction)

    body = section(layout, "GTS_ME_reaction_detectors", "Detector Requirements", icon='MESH_CUBE')
    if body:
        body.prop(reaction, "sides", text="Side")
        sub = body.column(align=True)
        sub.prop(reaction, "slope_h", text="Ground Slope")
        sub.prop(reaction, "slope_v", text="Wall Slope")
        sub = body.column(heading="Must Be Inside")
        sub.prop(reaction, "inside_h", text="Ground Detector")
        sub.prop(reaction, "inside_v", text="Wall Detector")
        sub = body.column(heading="Ignore Collisions")
        sub.prop(reaction, "safe_h", text="Ground")
        sub.prop(reaction, "safe_v", text="Wall")
        sub = body.column(heading="Climbing")
        sub.prop(reaction, "corner_cling", text="Snap to Corner")

    body = section(layout, "GTS_ME_reaction_trigger", "Trigger Area", icon='SELECT_SET')
    if body:
        body.prop(reaction, "trigger_name", text="Name")
        body.prop(reaction, "on_end_trigger", text="When Leaving")

    draw_advanced(layout, reaction, "GTS_ME_reaction_adv", (("nodes_wi", "NodesWI"),))


def draw_refs(layout, settings):
    """Find References results, kept in every tab so the next result is one click away."""
    if not settings.refs_title:
        return
    if hasattr(layout, "panel"):
        header, body = layout.panel("GTS_ME_refs", default_closed=False)
        header.label(text=settings.refs_title, icon='VIEWZOOM')
        header.operator(GTS_OT_me_clear_refs.bl_idname, text="", icon='X', emboss=False)
    else:
        body = layout.box()
        row = body.row()
        row.label(text=settings.refs_title, icon='VIEWZOOM')
        row.operator(GTS_OT_me_clear_refs.bl_idname, text="", icon='X', emboss=False)
    if body is None:
        return
    if len(settings.refs):
        body.template_list(GTS_UL_me_refs.__name__, "", settings, "refs", settings, "active_ref_index",
                           rows=min(6, max(2, len(settings.refs))))
    else:
        dim_label(body, "Nothing refers to it", icon='INFO')


# ---------------------------------------------------------------------------- #
#  Tab contents (main panel)
# ---------------------------------------------------------------------------- #

def draw_moves_tab(layout, context, settings):
    layout.prop(settings, "search", text="", icon='VIEWZOOM', placeholder="Search moves or files")
    list_with_buttons(layout, GTS_UL_me_moves, settings, "moves", settings, "active_move_index", 'MOVE',
                      add_operator=GTS_OT_me_move_add.bl_idname, rows=8)
    preview_button(layout, "Preview Move", 'MOVE', enabled=active(settings)[0] is not None)
    preview_status(layout, settings)


def _group_details(layout, settings, item, kind, what, adv_id):
    if item is None:
        return
    col = split_layout(layout.column())
    col.prop(item, "name")
    used_by(col, settings, kind, item.name, what)
    draw_advanced(layout, item, adv_id)


def draw_event_groups_tab(layout, context, settings):
    list_with_buttons(layout, GTS_UL_me_event_groups, settings, "event_groups", settings,
                      "active_event_group_index", 'EVENT_GROUP', add_level='EVENT_GROUP', rows=6)
    _group_details(layout, settings, pick(settings.event_groups, settings.active_event_group_index),
                   'EVENT_GROUP', "interval", "GTS_ME_event_group_adv")


def draw_reaction_groups_tab(layout, context, settings):
    list_with_buttons(layout, GTS_UL_me_reaction_groups, settings, "reaction_groups", settings,
                      "active_reaction_group_index", 'REACTION_GROUP', add_level='REACTION_GROUP', rows=6)
    _group_details(layout, settings, pick(settings.reaction_groups, settings.active_reaction_group_index),
                   'REACTION_GROUP', "event", "GTS_ME_reaction_group_adv")


def draw_sounds_tab(layout, context, settings):
    layout.prop(settings, "sound_search", text="", icon='VIEWZOOM', placeholder="Search sounds")
    list_with_buttons(layout, GTS_UL_me_sounds, settings, "sounds", settings, "active_sound_index", 'SOUND',
                      add_level='SOUND', rows=8)
    _group_details(layout, settings, pick(settings.sounds, settings.active_sound_index),
                   'SOUND', "use", "GTS_ME_sound_adv")


TAB_DRAW = {'MOVES': draw_moves_tab, 'EVENT_GROUPS': draw_event_groups_tab,
            'REACTION_GROUPS': draw_reaction_groups_tab, 'SOUNDS': draw_sounds_tab}


def draw_tabs(layout, context, settings):
    """Tab row. Shows icons only when the sidebar is too narrow for the names."""
    region = getattr(context, "region", None)
    scale = context.preferences.system.ui_scale if getattr(context, "preferences", None) else 1.0
    wide = region is None or region.width / (scale or 1.0) >= 400
    row = layout.row(align=True)
    row.scale_y = 1.2
    row.prop(settings, "tab", expand=True, icon_only=not wide)
    if not wide:
        dim_label(layout, TAB_LABEL[settings.tab], icon=TAB_ICON[settings.tab])






# ============================================================================ #
#  Panels
# ============================================================================ #

class _SubPanel:
    bl_options = {'DEFAULT_CLOSED'}
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = CATEGORY
    bl_parent_id = "VIEW3D_PT_gymnast_move_editor"
    header_icon = 'NONE'

    def draw_header(self, context):
        self.layout.label(icon=self.header_icon)

    def header_text(self, settings):
        return ""

    def draw_header_preset(self, context):
        """The selected item, on the right side of the panel header."""
        text = self.header_text(get_settings(context))
        if text:
            row = self.layout.row()
            row.active = False
            row.label(text=text)


class GTS_PT_move_editor(bpy.types.Panel):
    bl_label = "Move Editor"
    bl_idname = "VIEW3D_PT_gymnast_move_editor"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = CATEGORY
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        settings = get_settings(context)

        # files
        col = split_layout(layout.column(align=True))
        col.prop(settings, "moves_xml", text="Moves XML")
        col.prop(settings, "bin_folder", text="Animations")
        row = layout.row(align=True)
        row.scale_y = 1.25
        row.operator(GTS_OT_me_load.bl_idname, text="Load", icon='IMPORT')
        row.operator(GTS_OT_me_save.bl_idname, text="Save", icon='FILE_TICK')
        row.operator(GTS_OT_me_save_as.bl_idname, text="Save As", icon='EXPORT')

        # only shown when something is missing
        message, level = character_status(context.scene)
        if level != 'OK':
            row = layout.row()
            row.alert = level == 'ERROR'                # red for errors, normal text for warnings
            row.label(text=message, icon='CANCEL' if level == 'ERROR' else 'ERROR')

        if not is_loaded(settings):
            dim_label(layout, "Choose a moves.xml and press Load", icon='INFO')
            return

        layout.separator()
        draw_tabs(layout, context, settings)
        TAB_DRAW[settings.tab](layout, context, settings)
        draw_refs(layout, settings)


# ---- Moves tab ---------------------------------------------------------------

class GTS_PT_me_move(_SubPanel, bpy.types.Panel):
    bl_label = "Move"
    bl_idname = "VIEW3D_PT_gymnast_move_editor_move"
    header_icon = 'ARMATURE_DATA'

    @classmethod
    def poll(cls, context):
        settings = get_settings(context)
        return settings.tab == 'MOVES' and active(settings)[0] is not None

    def header_text(self, settings):
        return active(settings)[0].name

    def draw(self, context):
        layout = split_layout(self.layout)
        settings = get_settings(context)
        move = active(settings)[0]

        col = layout.column()
        col.prop(move, "name")
        col.prop(move, "move_type")
        col.prop(move, "sub_type")
        col.prop(move, "priority")
        if move.move_type == '3' or move.move_id or move.item_name:
            sub = col.column(align=True)
            sub.prop(move, "move_id", text="Trick ID")
            sub.prop(move, "item_name")
        col.prop(move, "pivot")
        if move.pivot == 'CUSTOM':
            col.prop(move, "pivot_custom", text="Custom Node")
        used_by(col, settings, 'MOVE', move.name, "reaction")

        body = section(layout, "GTS_ME_animation", "Animation", icon='ACTION')
        if body:
            row = body.row(align=True)
            row.prop(move, "file_name")
            _picker(row, 'FILE')
            path = bin_path(settings, move.file_name)
            frames = bin_frame_count(path) if path else None
            if move.file_name and not path:
                row = split_row(body, "")
                row.alert = True
                row.label(text="Not in the Animations folder", icon='ERROR')
            sub = body.column(align=True)
            for prop, text, which in (("first_frame", "Frame Start", 'FIRST'), ("end_frame", "End", 'END')):
                row = sub.row(align=True)
                row.prop(move, prop, text=text)
                row.operator(GTS_OT_me_set_frame.bl_idname, text="", icon='TIME').which = which
            if frames is not None:
                row = split_row(body, "Length")
                row.active = False
                note = f"{frames} frames (0 – {max(0, frames - 1)})"
                row.label(text=note + (", last pose held" if move.end_frame > frames - 1 else ""))
            body.prop(move, "mid_frames")
            sub = body.column(heading="Playback")
            sub.prop(move, "loop")
            sub.prop(move, "mirror")

        body = section(layout, "GTS_ME_movement", "Binding", toggle=(move, "binding"))
        if body:
            sub = body.column(align=True)
            sub.prop(move, "velocity_x")
            sub.prop(move, "velocity_y")
            body.prop(move, "gravity")
            row = split_row(body, "")
            row.active = False
            row.label(text="Per frame, negative Y goes up")

        body = section(layout, "GTS_ME_detectors", "Detectors", icon='MESH_CUBE')
        if body:
            sub = body.column(align=True)
            sub.prop(move, "delta_detector_h", text="Range Ground")
            sub.prop(move, "delta_detector_v", text="Wall")
            sub = body.column(align=True)
            sub.prop(move, "landing_detector_h", text="Landing H")
            sub.prop(move, "landing_detector_v", text="V")

        body = section(layout, "GTS_ME_compat", "Advanced", icon='PREFERENCES')
        if body:
            sub = body.column(align=True)
            sub.prop(move, "auto_detector_h", text="AutoPosition H")
            sub.prop(move, "auto_detector_v", text="V")
            body.prop(move, "platform_anticipation")
            row = split_row(body, "")
            row.active = False
            row.label(text="Kept for the game, not used by the preview")


class GTS_PT_me_intervals(_SubPanel, bpy.types.Panel):
    bl_label = "Intervals"
    bl_idname = "VIEW3D_PT_gymnast_move_editor_intervals"
    header_icon = 'TIME'

    @classmethod
    def poll(cls, context):
        settings = get_settings(context)
        return settings.tab == 'MOVES' and active(settings)[0] is not None

    def header_text(self, settings):
        interval = active(settings)[1]
        return f"{interval.start} – {interval.end}" if interval else ""

    def draw(self, context):
        layout = self.layout
        settings = get_settings(context)
        move, interval, _, _ = active(settings)

        list_with_buttons(layout, GTS_UL_me_intervals, move, "intervals", move, "active_interval_index", 'INTERVAL',
                          add_operator=GTS_OT_me_interval_add.bl_idname, rows=4)
        if interval is None:
            return

        col = split_layout(layout.column())
        sub = col.column(align=True)
        for prop, text, which in (("start", "Frame Start", 'INTERVAL_START'), ("end", "End", 'INTERVAL_END')):
            row = sub.row(align=True)
            row.prop(interval, prop, text=text)
            row.operator(GTS_OT_me_set_frame.bl_idname, text="", icon='TIME').which = which
        row = col.row(align=True)
        row.prop(interval, "groups")
        _picker(row, 'INTERVAL_GROUPS')

        body = section(layout, "GTS_ME_interval_rules", "Collisions & Platforms", icon='MOD_PHYSICS')
        if body:
            sub = body.column(heading="Protection")
            sub.prop(interval, "safe", text="Invincible")
            sub.prop(interval, "lock", text="Taser Lock")
            sub = body.column(heading="Ignore Collisions")
            sub.prop(interval, "safe_h", text="Ground")
            sub.prop(interval, "safe_v", text="Wall")
            sub = body.column(heading="Bind to Any Platform")
            sub.prop(interval, "bound_h", text="Ground")
            sub.prop(interval, "bound_v", text="Wall")
            sub.prop(interval, "bound_c", text="Node")
            sub = body.column(heading="Leave Platform")
            sub.prop(interval, "unbound_x", text="X")
            sub.prop(interval, "unbound_y", text="Y")

        body = section(layout, "GTS_ME_interval_sounds", f"Sounds ({len(interval.sounds)})", icon='SPEAKER')
        if body:
            draw_sounds(body, interval, 'INTERVAL')

        draw_advanced(layout, interval, "GTS_ME_interval_adv",
                      (("action", "Tutorial Button"), ("lt", "LT"), ("rb", "RB")))


class GTS_PT_me_events(_SubPanel, bpy.types.Panel):
    bl_label = "Events"
    bl_idname = "VIEW3D_PT_gymnast_move_editor_events"
    header_icon = 'KEYFRAME_HLT'

    @classmethod
    def poll(cls, context):
        settings = get_settings(context)
        return settings.tab == 'MOVES' and active(settings)[1] is not None

    def header_text(self, settings):
        event = current_event(settings)
        return event_trigger_text(event) if event else ""

    def draw(self, context):
        draw_events(self.layout, context)


class GTS_PT_me_reactions(_SubPanel, bpy.types.Panel):
    bl_label = "Reactions"
    bl_idname = "VIEW3D_PT_gymnast_move_editor_reactions"
    header_icon = 'FORWARD'

    @classmethod
    def poll(cls, context):
        settings = get_settings(context)
        return settings.tab == 'MOVES' and active(settings)[2] is not None

    def header_text(self, settings):
        reaction = current_reaction(settings)
        return reaction.name if reaction else ""

    def draw(self, context):
        draw_reactions(self.layout, context)


# ---- Event Groups tab ----------------------------------------------------------

class GTS_PT_me_group_events(_SubPanel, bpy.types.Panel):
    bl_label = "Events"
    bl_idname = "VIEW3D_PT_gymnast_move_editor_group_events"
    header_icon = 'KEYFRAME_HLT'

    @classmethod
    def poll(cls, context):
        settings = get_settings(context)
        return settings.tab == 'EVENT_GROUPS' and event_owner(settings) is not None

    def header_text(self, settings):
        return event_owner(settings).name

    def draw(self, context):
        draw_events(self.layout, context)


class GTS_PT_me_group_event_reactions(_SubPanel, bpy.types.Panel):
    bl_label = "Reactions"
    bl_idname = "VIEW3D_PT_gymnast_move_editor_group_event_reactions"
    header_icon = 'FORWARD'

    @classmethod
    def poll(cls, context):
        settings = get_settings(context)
        return settings.tab == 'EVENT_GROUPS' and current_event(settings) is not None

    def header_text(self, settings):
        return event_trigger_text(current_event(settings))

    def draw(self, context):
        draw_reactions(self.layout, context)


# ---- Reaction Groups tab -------------------------------------------------------

class GTS_PT_me_group_reactions(_SubPanel, bpy.types.Panel):
    bl_label = "Reactions"
    bl_idname = "VIEW3D_PT_gymnast_move_editor_group_reactions"
    header_icon = 'FORWARD'

    @classmethod
    def poll(cls, context):
        settings = get_settings(context)
        return settings.tab == 'REACTION_GROUPS' and reaction_owner(settings) is not None

    def header_text(self, settings):
        return reaction_owner(settings).name

    def draw(self, context):
        draw_reactions(self.layout, context)







# ============================================================================ #
#  Registration
# ============================================================================ #

classes = (
    GTS_ME_Sound,
    GTS_ME_Condition,
    GTS_ME_Reaction,
    GTS_ME_Event,
    GTS_ME_Interval,
    GTS_ME_Move,
    GTS_ME_EventGroup,
    GTS_ME_ReactionGroup,
    GTS_ME_SoundEntry,
    GTS_ME_Ref,
    GTS_ME_Settings,
    GTS_OT_me_load,
    GTS_OT_me_save,
    GTS_OT_me_save_as,
    GTS_OT_me_list,
    GTS_OT_me_move_add,
    GTS_OT_me_entry_add,
    GTS_OT_me_interval_add,
    GTS_OT_me_event_add,
    GTS_OT_me_reaction_add,
    GTS_OT_me_condition_add,
    GTS_OT_me_condition_remove,
    GTS_OT_me_sound_add,
    GTS_OT_me_sound_remove,
    GTS_OT_me_pick,
    GTS_OT_me_find_refs,
    GTS_OT_me_go_ref,
    GTS_OT_me_clear_refs,
    GTS_OT_me_set_frame,
    GTS_OT_me_preview,
    GTS_UL_me_moves,
    GTS_UL_me_intervals,
    GTS_UL_me_events,
    GTS_UL_me_reactions,
    GTS_UL_me_event_groups,
    GTS_UL_me_reaction_groups,
    GTS_UL_me_sounds,
    GTS_UL_me_refs,
    GTS_PT_me_preview_options,
    GTS_PT_move_editor,
    GTS_PT_me_move,
    GTS_PT_me_intervals,
    GTS_PT_me_events,
    GTS_PT_me_reactions,
    GTS_PT_me_group_events,
    GTS_PT_me_group_event_reactions,
    GTS_PT_me_group_reactions,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.gymnast_move_editor = PointerProperty(type=GTS_ME_Settings)


def unregister():
    if bpy.app.timers.is_registered(_auto_preview):
        bpy.app.timers.unregister(_auto_preview)
    del bpy.types.Scene.gymnast_move_editor
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()