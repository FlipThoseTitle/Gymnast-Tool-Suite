# #################### #
# Model Panel
# #################### #

#  Axis convention:   XML (X, Y, Z)  <->  Blender (x, -z, y)
#  Exporter:  X = x,  Y = z,  Z = -y


import math
import os
import xml.dom.minidom as minidom
import xml.etree.ElementTree as ET
from collections import Counter, namedtuple

import bmesh
import bpy
from bpy.props import (BoolProperty, CollectionProperty, EnumProperty, FloatProperty, IntProperty, PointerProperty, StringProperty)
from mathutils import Matrix




# ============================================================================ #
#  Constants
# ============================================================================ #

CATEGORY = "Gymnast Tool Suite"
ROOT_COLLECTION = "Model"
CAPSULE_GROUP = "Smooth Capsules"     # geometry node group used by capsule objects
RIG_GROUP = "GTS LCC Rig"             # geometry node group used by "Bind to Skeleton"
RIG_PREFIX = "LCC_"                   # name prefix of every vertex group / modifier the binder creates

# The four ChildNodes (in LCC order) each gear type is attached to.
NODE_SETS = {
    'HEAD':     ("NTop", "NHeadS_2", "NHeadS_1", "NHeadF"),
    'FOOT_1':   ("NToeS_1", "NToe_1", "NHeel_1", "NAnkle_1"),
    'FOOT_2':   ("NToeS_2", "NToe_2", "NHeel_2", "NAnkle_2"),
    'WEAPON_1': ("Weapon-Node4_1", "Weapon-Node3_1", "Weapon-Node2_1", "Weapon-Node1_1"),
    'WEAPON_2': ("Weapon-Node4_2", "Weapon-Node3_2", "Weapon-Node2_2", "Weapon-Node1_2"),
    'RANGED':   ("Ranged-Node1_1", "Ranged-Node2_1", "Ranged-Node3_1", "Ranged-Node4_1"),
}

# Body gear is split by height into Top / Middle / Bottom, each one attached to one of these profiles.
BODY_PROFILES = {
    'CHEST':   ("NChestS_1", "NChestF", "NChestS_2", "NNeck"),
    'STOMACH': ("NStomachS_1", "NStomachF", "NStomachS_2", "NChest"),
    'HIP':     ("NPelvisF", "NHip_1", "NHip_2", "NStomach"),
}

# (suffix, Node1, Node2, Node3) - optional triangles that hide the hole next to SF2 feet.
FOOT_TRIANGLES = (
    ("1_1", "NHeel_1", "NToe_1", "NAnkle_1"),
    ("2_1", "NToeS_1", "NToe_1", "NHeel_1"),
    ("1_2", "NHeel_2", "NToe_2", "NAnkle_2"),
    ("2_2", "NHeel_2", "NToeS_2", "NToe_2"),
    ("3_2", "NToeS_2", "NToe_2", "NAnkle_2"),
)

MACRO_TEMPLATES = {
    'ARMOR': (
        ("Armor_Top", "NChestS_2,NChestF,NChestS_1,NNeck"),
        ("Armor_Middle", "NStomachS_2,NStomachF,NStomachS_1,NChest"),
        ("Armor_Bottom", "NHip_1,NPelvisF,NHip_2,NStomach"),
    ),
    'WEAPON': (
        ("Weapon_1", ",".join(NODE_SETS['WEAPON_1'])),
        ("Weapon_2", ",".join(NODE_SETS['WEAPON_2'])),
    ),
}

BODY_ITEMS = [
    ('CHEST', "Chest", "Chest area, from the upper torso to the neck."),
    ('STOMACH', "Stomach", "Stomach area, between the chest and the hip."),
    ('HIP', "Hip", "Hip area, below the middle torso."),
]




# ============================================================================ #
#  Helpers
# ============================================================================ #

class ModelError(Exception):
    """A problem shown in Blender's status bar."""

def safe_float(val, default=0.0):
    """XML text -> float. Accepts comma decimals, 'Null' and missing values."""
    if val is None or val in ("", "Null"):
        return default
    try:
        return float(str(val).replace(',', '.'))
    except ValueError:
        return default

def xml_to_blender(x, y, z):
    return (x, -z, y)

def xml_pos(element):
    return (safe_float(element.get('X')), safe_float(element.get('Y')), safe_float(element.get('Z')))

def xml_attribs(pos):
    """Blender position -> XML coordinates (Y = z, Z = -y)."""
    return {"X": str(pos.x), "Y": str(pos.z), "Z": str(-pos.y)}

def load_xml(path):
    try:
        return ET.parse(path).getroot()
    except (ET.ParseError, OSError) as err:
        raise ModelError(f"Could not read '{os.path.basename(path)}': {err}")

def section(root, name):
    sec = root.find(name)
    return list(sec) if sec is not None else []

def get_collection(parent, name):
    col = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    if col.name not in parent.children:
        parent.children.link(col)
    return col

def clear_collection(col):
    for obj in list(col.objects):
        bpy.data.objects.remove(obj, do_unlink=True)

def target_collection(context, model_name, sub=None, replace=False):
    """Model / <model_name> / <sub>_<model_name>   (created on demand)."""
    col = get_collection(get_collection(context.scene.collection, ROOT_COLLECTION), model_name)
    if sub:
        col = get_collection(col, f"{sub}_{model_name}")
        if replace:
            clear_collection(col)
    return col

def make_mesh_object(name, coords, edges=(), faces=()):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(coords, edges, faces)
    mesh.update()
    mesh.validate()
    return bpy.data.objects.new(name, mesh)

def focus(context, obj):
    try:
        for other in context.selected_objects:
            other.select_set(False)
        obj.select_set(True)
        context.view_layer.objects.active = obj
    except RuntimeError:      # object lives in a hidden collection
        pass

def vertex_group_indices(obj, name):
    """Indices of every vertex that belongs to the vertex group `name`."""
    if not obj or obj.type != 'MESH' or not name or name == "None":
        return set()
    vg = obj.vertex_groups.get(name)
    if not vg:
        return set()
    return {v.index for v in obj.data.vertices if any(g.group == vg.index for g in v.groups)}

def require_nodes(names):
    missing = [n for n in dict.fromkeys(names) if n not in bpy.data.objects]
    if missing:
        raise ModelError(f"Missing required child nodes: {', '.join(missing)}")



# ----------------------------------------------------------------------------- #
#  Linear Combination Coefficients
# ----------------------------------------------------------------------------- #

def tetrahedron_volume(p1, p2, p3, p4):
    u, v, w = p2 - p1, p3 - p1, p4 - p1
    return (u.x * (v.y * w.z - v.z * w.y) - u.y * (v.x * w.z - v.z * w.x) + u.z * (v.x * w.y - v.y * w.x)) / 6.0

def calculate_normalized_lcc(pos, p1, p2, p3, p4):
    volume = tetrahedron_volume(p1, p2, p3, p4)
    if abs(volume) < 1e-12:
        return [0.25, 0.25, 0.25, 0.25]
    lcc = [
        tetrahedron_volume(pos, p2, p3, p4) / volume,
        tetrahedron_volume(p1, pos, p3, p4) / volume,
        tetrahedron_volume(p1, p2, pos, p4) / volume,
        tetrahedron_volume(p1, p2, p3, pos) / volume,
    ]
    total = sum(lcc)
    return [c / total for c in lcc] if total != 0 else [0.25] * 4

class ChildSet:
    """Four child node objects + their world positions (the gizmo of a MacroNode)"""

    def __init__(self, objects):
        self.objects = list(objects)
        self.names = [o.name for o in self.objects]
        self.points = [o.matrix_world.translation.copy() for o in self.objects]

    @classmethod
    def from_names(cls, names):
        return cls([bpy.data.objects[n] for n in names])

    def lcc(self, pos):
        return calculate_normalized_lcc(pos, *self.points)

def custom_childset(st, report=None):
    """The user defined ChildNodes, or None when disabled or incomplete."""
    if not st.model_custom_childnode:
        return None
    objs = [st.childnode_1_object, st.childnode_2_object, st.childnode_3_object, st.childnode_4_object]
    if all(objs):
        return ChildSet(objs)
    if report:
        report({'WARNING'}, "Custom ChildNodes enabled but missing object references. Using the standard ChildNodes.")
    return None

class BodyGear:
    """Height based region picker, shared by the exporter and the binder."""

    def __init__(self, st):
        self.sets = {key: ChildSet.from_names(names) for key, names in BODY_PROFILES.items()}
        self.chest_z = self.sets['STOMACH'].points[3].z      # NChest
        self.stomach_z = self.sets['HIP'].points[3].z        # NStomach
        self.choice = {'Top': st.model_body_top, 'Middle': st.model_body_middle, 'Bottom': st.model_body_bottom}

    def region(self, z):
        if z >= self.chest_z:
            return 'Top'
        return 'Middle' if z >= self.stomach_z else 'Bottom'

    def children(self, region):
        return self.sets[self.choice[region]]



# ----------------------------------------------------------------------------- #
#  What each model type exports
# ----------------------------------------------------------------------------- #

# children: tuple of node names | () for stand-alone models | None for body gear (picked by height)
Slot = namedtuple("Slot", "obj children cloth macro attack ranged second", defaults=(False, False, False))


def export_slots(st, active=None):
    """Every (object, childnodes, vertex groups) combination the selected model type consists of."""
    t = st.model_type_export
    main = st.selected_object or active
    cloth, macro = st.model_export_cloth_general_folder, st.macronode_vertex_group

    if t == 'MODEL':
        return [Slot(main, (), cloth, macro)]
    if t == 'HEAD_GEAR':
        return [Slot(main, NODE_SETS['HEAD'], cloth, macro)]
    if t == 'BODY_GEAR':
        return [Slot(main, None, cloth, macro)]
    if t == 'RANGED':
        slots = [Slot(main, NODE_SETS['RANGED'], cloth, macro)]
        if st.model_include_attack_edges:
            slots.append(Slot(st.model_attack_edges_object_1, NODE_SETS['RANGED'], "", macro, attack=True, ranged=True))
        return slots
    if t == 'FOOT_GEAR':
        return [Slot(st.foot_object_1, NODE_SETS['FOOT_1'], st.model_export_cloth_foot1_folder, st.macronode_vertex_group_foot_1),
                Slot(st.foot_object_2, NODE_SETS['FOOT_2'], st.model_export_cloth_foot2_folder, st.macronode_vertex_group_foot_2)]
    if t == 'WEAPON':
        slots = [Slot(st.weapon_object_1, NODE_SETS['WEAPON_1'], st.model_export_cloth_weapon1_folder, st.macronode_vertex_group_weapon_1),
                 Slot(st.weapon_object_2, NODE_SETS['WEAPON_2'], st.model_export_cloth_weapon2_folder, st.macronode_vertex_group_weapon_2)]
        if st.model_include_attack_edges:
            slots += [Slot(st.model_attack_edges_object_1, NODE_SETS['WEAPON_1'], "", "", attack=True),
                      Slot(st.model_attack_edges_object_2, NODE_SETS['WEAPON_2'], "", "", attack=True, second=True)]
        return slots
    return []

def usable_slots(st, active=None):
    return [s for s in export_slots(st, active) if s.obj and s.obj.type == 'MESH']

def slot_node_names(slots):
    names = []
    for s in slots:
        names += sum(BODY_PROFILES.values(), ()) if s.children is None else s.children
    return names





# ============================================================================ #
#  XML import
# ============================================================================ #

class XMLModel:
    """Model XML (+ optional Dependencies XML) with every node position resolved."""

    def __init__(self, context):
        scene = context.scene
        st = scene.gymnast_tool_model_props
        path = bpy.path.abspath(scene.gymnast_normal_xml) if scene.gymnast_normal_xml else ""
        if not os.path.isfile(path):
            raise ModelError("Model XML path is missing or invalid.")
        self.root = load_xml(path)
        self.name = os.path.splitext(os.path.basename(path))[0]

        self.deps_root, self.deps = None, {}
        dep_path = bpy.path.abspath(scene.gymnast_dependencies_xml) if scene.gymnast_dependencies_xml else ""
        if st.model_use_dependencies and dep_path:
            if not os.path.isfile(dep_path):
                raise ModelError("Dependencies XML path is missing or invalid.")
            self.deps_root = load_xml(dep_path)
            self.deps = {n.tag: n for n in section(self.deps_root, 'Nodes')}
        self.positions = {}

    def section(self, name):
        return section(self.root, name)

    def lookup(self, name, local):
        """Position (XML space) of a node: this XML -> dependencies -> object in the Blender scene."""
        pos = local.get(name)
        if pos:
            return pos
        dep = self.deps.get(name)
        if dep is not None:
            return xml_pos(dep)
        obj = bpy.data.objects.get(name)
        if obj:
            t = obj.matrix_world.translation
            return (t.x, t.z, -t.y)
        return None

    def resolve(self, apply_lcc):
        """Fill self.positions = {node name: (x, y, z)} in file order."""
        nodes = self.section('Nodes')
        if not nodes:
            raise ModelError("No <Nodes> section found in XML")
        local, macros = {}, []
        for n in nodes:
            ntype = n.get('Type')
            if ntype == 'MacroNode' and apply_lcc:
                macros.append(n)
            elif ntype in ('Node', 'CenterOfMass', 'MacroNode') or all(n.get(k) for k in 'XYZ'):
                local[n.tag] = xml_pos(n)
        for n in macros:                       # Position = sum(LCC_i * child_i)
            acc = [0.0, 0.0, 0.0]
            for i in range(1, 5):
                child, lcc = n.get(f'ChildNode{i}'), n.get(f'LCC{i}')
                if not child or child == "Null" or not lcc:
                    continue
                p = self.lookup(child, local)
                if p is None:
                    continue
                w = safe_float(lcc)
                acc = [acc[0] + p[0] * w, acc[1] + p[1] * w, acc[2] + p[2] * w]
            local[n.tag] = tuple(acc)
        self.positions = {n.tag: local[n.tag] for n in nodes if n.tag in local}
        return self

class VertexTable:
    """Vertex list for an imported mesh. Nodes that only exist in the dependencies are added on demand."""

    def __init__(self, model):
        self.model = model
        self.names = list(model.positions)
        self.index = {n: i for i, n in enumerate(self.names)}
        self.coords = [xml_to_blender(*p) for p in model.positions.values()]

    def has(self, name):
        return name in self.index or name in self.model.deps

    def require(self, name):
        i = self.index.get(name)
        if i is None and name in self.model.deps:
            i = len(self.names)
            self.names.append(name)
            self.index[name] = i
            self.coords.append(xml_to_blender(*xml_pos(self.model.deps[name])))
        return i

def add_import_groups(obj, model, table, rules, include_cloth):
    """Vertex groups from the macro rules (child node sets) and from cloth nodes."""
    parsed = [({n.strip() for n in r.names.split(",") if n.strip()}, r.group.strip()) for r in rules]
    parsed = [(names, grp) for names, grp in parsed if names and grp]
    groups = {}
    for n in model.section('Nodes'):
        i = table.index.get(n.tag)
        if i is None:
            continue
        ntype = n.get('Type')
        if ntype == 'MacroNode' and parsed:
            kids = {n.get(f'ChildNode{k}') for k in range(1, 5)} - {None, "Null"}
            for names, grp in parsed:
                if names <= kids:
                    groups.setdefault(grp, []).append(i)
        elif include_cloth and ntype == 'Node' and n.get('Cloth') == '1':
            groups.setdefault("Cloth", []).append(i)
    for grp, indices in groups.items():
        obj.vertex_groups.new(name=grp).add(indices, 1.0, 'REPLACE')





# ----------------------------------------------------------------------------- #
#  Capsule geometry node group
# ----------------------------------------------------------------------------- #

def add_node(tree, idname, loc, **props):
    node = tree.nodes.new(idname)
    node.location = loc
    for key, value in props.items():
        setattr(node, key, value)
    return node

def out(node, name):
    """Output socket by name (skips the hidden duplicates some nodes carry)"""
    return next((s for s in node.outputs if s.name == name and s.enabled), node.outputs[name])

def socket_ids(group):
    return {it.name: it.identifier for it in group.interface.items_tree if getattr(it, "in_out", None) == 'INPUT'}

def _gn_inputs(mod):
    props = getattr(mod, "properties", None)
    return getattr(props, "inputs", None)

def set_input(mod, ident, value):
    inputs = _gn_inputs(mod)
    if inputs is not None:
        getattr(inputs, ident).value = value
    else:
        mod[ident] = value

def get_input(mod, ident):
    inputs = _gn_inputs(mod)
    if inputs is None:
        return mod[ident]
    try:
        return getattr(inputs, ident).value
    except AttributeError:
        raise KeyError(ident)

def ensure_capsule_group():
    existing = bpy.data.node_groups.get(CAPSULE_GROUP)
    if existing and existing.bl_idname == 'GeometryNodeTree':
        return existing

    ng = bpy.data.node_groups.new(CAPSULE_GROUP, 'GeometryNodeTree')
    ng.is_modifier = True
    ng.use_fake_user = True
    nodes, links, iface = ng.nodes, ng.links, ng.interface

    def add_input(name, socket_type, default=None, subtype=None, min_val=None, max_val=None):
        sock = iface.new_socket(name=name, in_out='INPUT', socket_type=socket_type)
        if socket_type == 'NodeSocketFloat':
            if default is not None: sock.default_value = default
            if subtype: sock.subtype = subtype
            if min_val is not None: sock.min_value = min_val
            if max_val is not None: sock.max_value = max_val

    gi = add_node(ng, "NodeGroupInput", (0, 0))
    add_input("End1", "NodeSocketObject")
    add_input("End2", "NodeSocketObject")
    add_input("Margin1", "NodeSocketFloat", 0.0, 'FACTOR', 0.0, 1.0)
    add_input("Margin2", "NodeSocketFloat", 1.0, 'FACTOR', 0.0, 1.0)
    add_input("Radius", "NodeSocketFloat", 0.0, 'DISTANCE', 0.0)
    add_input("Edge", "NodeSocketString")
    gi2 = add_node(ng, gi.bl_idname, (-190, -500))
    go = add_node(ng, "NodeGroupOutput", (1750, 0))
    iface.new_socket(name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')

    info1 = add_node(ng, "GeometryNodeObjectInfo", (200, 0))
    info2 = add_node(ng, "GeometryNodeObjectInfo", (200, -220))
    info1.inputs["As Instance"].default_value = False
    info2.inputs["As Instance"].default_value = False
    inv_margin = add_node(ng, "ShaderNodeMath", (450, -220), operation='SUBTRACT', use_clamp=True)
    inv_margin.inputs[0].default_value = 1
    line = add_node(ng, "GeometryNodeCurvePrimitiveLine", (450, 0))
    trim = add_node(ng, "GeometryNodeTrimCurve", (650, 0))
    circle = add_node(ng, "GeometryNodeCurvePrimitiveCircle", (800, 0))
    circle.inputs["Resolution"].default_value = 16
    to_mesh = add_node(ng, "GeometryNodeCurveToMesh", (1000, 0))
    to_mesh.inputs["Fill Caps"].default_value = False
    store_body = add_node(ng, "GeometryNodeStoreNamedAttribute", (1250, 0), data_type='FLOAT_VECTOR', domain='POINT')
    store_body.inputs["Name"].default_value = "nor"
    normal_body = add_node(ng, "GeometryNodeInputNormal", (1000, -200))

    sphere = add_node(ng, "GeometryNodeMeshUVSphere", (0, -500))
    sphere.inputs["Segments"].default_value = 16
    sphere.inputs["Rings"].default_value = 8
    store_cap = add_node(ng, "GeometryNodeStoreNamedAttribute", (200, -500), data_type='FLOAT_VECTOR', domain='POINT')
    store_cap.inputs["Name"].default_value = "nor"
    normal_cap = add_node(ng, "GeometryNodeInputNormal", (0, -680))
    delete = add_node(ng, "GeometryNodeDeleteGeometry", (450, -500), domain='FACE', mode='ALL')
    position = add_node(ng, "GeometryNodeInputPosition", (0, -800))
    separate = add_node(ng, "ShaderNodeSeparateXYZ", (180, -800))
    compare = add_node(ng, "FunctionNodeCompare", (350, -800), data_type='FLOAT', operation='LESS_THAN')
    smooth = add_node(ng, "GeometryNodeSetShadeSmooth", (710, -500))
    end_cap = add_node(ng, "GeometryNodeCurveEndpointSelection", (880, -500))
    instance = add_node(ng, "GeometryNodeInstanceOnPoints", (1100, -500))
    store_inst = add_node(ng, "GeometryNodeStoreNamedAttribute", (1350, -500), data_type='FLOAT_VECTOR', domain='INSTANCE')
    store_inst.inputs["Name"].default_value = "inst_rot"
    inst_rot = add_node(ng, "GeometryNodeInputInstanceRotation", (1350, -780))
    euler = add_node(ng, "FunctionNodeEulerToRotation", (1020, -300))
    tangent = add_node(ng, "GeometryNodeInputTangent", (0, -1500))
    end_align = add_node(ng, "GeometryNodeCurveEndpointSelection", (200, -1400))
    end_align.inputs["End Size"].default_value = 0
    flip = add_node(ng, "ShaderNodeVectorMath", (200, -1650), operation='SCALE')
    flip.inputs["Scale"].default_value = -1
    switch = add_node(ng, "GeometryNodeSwitch", (420, -1500), input_type='VECTOR')
    align1 = add_node(ng, "FunctionNodeAlignRotationToVector", (630, -1500), axis='Z', pivot_axis='AUTO')
    align2 = add_node(ng, "FunctionNodeAlignRotationToVector", (820, -1500), axis='X', pivot_axis='AUTO')
    normal_align = add_node(ng, "GeometryNodeInputNormal", (420, -1800))
    join = add_node(ng, "GeometryNodeJoinGeometry", (1500, 0))

    wiring = [
        (gi, "End1", info1, 0), (gi, "End2", info2, 0),
        (info1, "Location", line, "Start"), (info2, "Location", line, "End"),
        (line, "Curve", trim, "Curve"), (gi, "Margin1", trim, "Start"),
        (gi, "Margin2", inv_margin, 1), (inv_margin, "Value", trim, "End"),
        (trim, "Curve", to_mesh, "Curve"), (gi, "Radius", circle, "Radius"),
        (circle, "Curve", to_mesh, "Profile Curve"), (to_mesh, "Mesh", store_body, "Geometry"),
        (normal_body, "Normal", store_body, "Value"), (store_body, "Geometry", join, "Geometry"),
        (gi2, "Radius", sphere, "Radius"), (sphere, "Mesh", store_cap, "Geometry"),
        (normal_cap, "Normal", store_cap, "Value"), (store_cap, "Geometry", delete, "Geometry"),
        (position, "Position", separate, "Vector"), (separate, "Z", compare, "A"),
        (compare, "Result", delete, "Selection"), (delete, "Geometry", smooth, "Geometry"),
        (smooth, "Geometry", instance, "Instance"), (end_cap, "Selection", instance, "Selection"),
        (trim, "Curve", instance, "Points"), (euler, "Rotation", instance, "Rotation"),
        (align2, "Rotation", euler, "Euler"), (instance, "Instances", store_inst, "Geometry"),
        (inst_rot, "Rotation", store_inst, "Value"), (store_inst, "Geometry", join, "Geometry"),
        (tangent, "Tangent", flip, "Vector"), (tangent, "Tangent", switch, "False"),
        (flip, "Vector", switch, "True"), (end_align, "Selection", switch, "Switch"),
        (switch, "Output", align1, "Vector"), (align1, "Rotation", align2, "Rotation"),
        (normal_align, "Normal", align2, "Vector"), (join, "Geometry", go, "Geometry"),
    ]
    for src, src_name, dst, dst_name in wiring:
        links.new(out(src, src_name), dst.inputs[dst_name])
    return ng





# ----------------------------------------------------------------------------- #
#  Operators base class
# ----------------------------------------------------------------------------- #

class GymnastOperator(bpy.types.Operator):
    """Subclasses implement run(); a ModelError becomes a normal Blender error message."""
    bl_options = {'REGISTER', 'UNDO'}

    def run(self, context):
        raise NotImplementedError

    def execute(self, context):
        try:
            return self.run(context) or {'FINISHED'}
        except ModelError as err:
            self.report({'ERROR'}, str(err))
            return {'CANCELLED'}





# ----------------------------------------------------------------------------- #
#  Import operators
# ----------------------------------------------------------------------------- #

class ImportMeshOperator(GymnastOperator):
    bl_idname = "model.convert_xml"
    bl_label = "Import Mesh (Triangles)"
    bl_description = "Build one mesh object from the Triangle figures of the Model XML"

    def run(self, context):
        st = context.scene.gymnast_tool_model_props
        model = XMLModel(context).resolve(st.calculate_macronode)
        table = VertexTable(model)
        faces = []
        for fig in model.section('Figures'):
            if fig.get('Type') != 'Triangle':
                continue
            names = [fig.get(k) for k in ("Node1", "Node2", "Node3")]
            if all(table.has(n) for n in names):
                faces.append(tuple(table.require(n) for n in names))

        obj = make_mesh_object(f"OBJ_{model.name}", table.coords, faces=faces)
        target_collection(context, model.name, "Triangle", st.import_replace_existing).objects.link(obj)
        if st.add_vertex_group:
            add_import_groups(obj, model, table, context.scene.macro_rules, st.add_vertex_group_include_cloth)
        focus(context, obj)
        self.report({'INFO'}, f"Imported {len(faces)} triangles ({len(table.names)} nodes)")


class ImportNodesOperator(GymnastOperator):
    bl_idname = "model.add_nodes"
    bl_label = "Import Nodes"
    bl_description = "Add every node of the Model XML to Blender."

    def run(self, context):
        st = context.scene.gymnast_tool_model_props
        model = XMLModel(context).resolve(st.calculate_macronode)
        col = target_collection(context, model.name, "Nodes", st.import_replace_existing)

        if st.import_node_as_vertex:
            col.objects.link(make_mesh_object(f"Nodes_{model.name}", [xml_to_blender(*p) for p in model.positions.values()]))
        else:
            bm = bmesh.new()
            bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=8, radius=1.0)
            sphere_mesh = bpy.data.meshes.new("NodeSphereData")
            bm.to_mesh(sphere_mesh)
            bm.free()
            size = st.import_node_size
            for name, pos in model.positions.items():
                sphere = bpy.data.objects.new(name, sphere_mesh)       # object name == node name
                sphere.location = xml_to_blender(*pos)
                sphere.scale = (size, size, size)
                sphere.display.show_shadows = False
                col.objects.link(sphere)
        self.report({'INFO'}, f"Imported {len(model.positions)} nodes")


class ImportEdgesOperator(GymnastOperator):
    bl_idname = "model.add_edges"
    bl_label = "Import Nodes and Edges"
    bl_description = "Add the nodes and edges of the Model XML as one wire mesh"

    def run(self, context):
        st = context.scene.gymnast_tool_model_props
        model = XMLModel(context).resolve(st.calculate_macronode)
        table = VertexTable(model)
        edges = []
        for e in model.section('Edges'):
            a, b = e.get('End1'), e.get('End2')
            if table.has(a) and table.has(b):
                edges.append((table.require(a), table.require(b)))
        obj = make_mesh_object(f"Edges_{model.name}", table.coords, edges=edges)
        target_collection(context, model.name, "Edges", st.import_replace_existing).objects.link(obj)
        self.report({'INFO'}, f"Imported {len(edges)} edges")


class ImportCapsulesOperator(GymnastOperator):
    bl_idname = "model.add_capsules"
    bl_label = "Import Capsules"
    bl_description = "Add the Capsule figures of the Model XML (their edge ends must exist as node objects)"

    def run(self, context):
        st = context.scene.gymnast_tool_model_props
        model = XMLModel(context)

        def edge_ends(root):
            return {e.tag: (e.get('End1'), e.get('End2')) for e in section(root, 'Edges')}

        edges = edge_ends(model.deps_root) if model.deps_root is not None else {}
        edges.update(edge_ends(model.root))

        group = ensure_capsule_group()
        ids = socket_ids(group)
        if not {"End1", "End2", "Margin1", "Margin2", "Radius", "Edge"} <= set(ids):
            raise ModelError(f"Node group '{CAPSULE_GROUP}' has missing sockets. Delete it and import again.")

        col = target_collection(context, model.name, "Capsules", st.import_replace_existing)
        base = bpy.data.meshes.new("CapsuleBaseMesh")     # needs one vertex or Geometry Nodes will not evaluate
        base.from_pydata([(0.0, 0.0, 0.0)], [], [])
        base.update()

        made = skipped = 0
        for fig in model.section('Figures'):
            if fig.get('Type') != 'Capsule':
                continue
            edge_name = fig.get('Edge')
            ends = edges.get(edge_name)
            objs = [bpy.data.objects.get(n) for n in ends] if ends else None
            if not objs or not all(objs):
                skipped += 1
                continue
            obj = bpy.data.objects.new(fig.tag, base)
            col.objects.link(obj)
            mod = obj.modifiers.new(name="GeometryNodes", type='NODES')
            mod.node_group = group
            set_input(mod, ids["End1"], objs[0])
            set_input(mod, ids["End2"], objs[1])
            set_input(mod, ids["Margin1"], safe_float(fig.get("Margin1")))
            set_input(mod, ids["Margin2"], safe_float(fig.get("Margin2")))
            set_input(mod, ids["Radius"], safe_float(fig.get("Radius1"), 1.0))
            set_input(mod, ids["Edge"], edge_name)
            made += 1

        context.view_layer.update()
        note = f", skipped {skipped} (edge or node objects missing - import the Nodes first)" if skipped else ""
        self.report({'INFO' if made or not skipped else 'WARNING'}, f"Imported {made} capsules{note}")


class ImportAllOperator(GymnastOperator):
    bl_idname = "model.import_all"
    bl_label = "Import Everything"
    bl_description = "Nodes, edges, triangles and capsules in one click"

    def run(self, context):
        for name in ("add_nodes", "add_edges", "convert_xml", "add_capsules"):
            if getattr(bpy.ops.model, name)() != {'FINISHED'}:
                return {'CANCELLED'}
        self.report({'INFO'}, "Model imported")




# ============================================================================ #
#  XML export
# ============================================================================ #

def write_macronode(parent, name, pos, mass, fixed, children):
    lcc = children.lcc(pos)
    ET.SubElement(parent, name, Type="MacroNode", **xml_attribs(pos), Mass=str(mass), Fixed="1" if fixed else "0",
                  Visible="1", NodesCount="4",
                  ChildNode1=children.names[0], ChildNode2=children.names[1],
                  ChildNode3=children.names[2], ChildNode4=children.names[3],
                  LCC1=str(lcc[0]), LCC2=str(lcc[1]), LCC3=str(lcc[2]), LCC4=str(lcc[3]))


def write_clothnode(parent, name, pos, mass, attenuation):
    ET.SubElement(parent, name, Type="Node", **xml_attribs(pos), Mass=str(mass), Fixed="0", PinFixed="0",
                  Visible="1", Collisible="0", Passive="0", Cloth="1", Attenuation=f"{attenuation:.2f}", Rank="0")


def write_xml_file(root, filepath, compact):
    if not filepath.lower().endswith(".xml"):
        filepath += ".xml"
    raw = ET.tostring(root, encoding="unicode")
    text = '<?xml version="1.0" ?>\n' + raw if compact else minidom.parseString(raw).toprettyxml(indent="  ")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(text)
    return filepath


class ModelExporter:
    """Builds the <Scene> tree for the selected model type."""

    def __init__(self, context, report):
        self.context, self.report = context, report
        self.st = st = context.scene.gymnast_tool_model_props
        self.prefix = st.model_string_name
        self.n0, self.e0, self.t0 = st.model_node_offset, st.model_edge_offset, st.model_tri_offset
        self.root = ET.Element("Scene")
        self.nodes_el = ET.SubElement(self.root, "Nodes")
        self.edges_el = ET.SubElement(self.root, "Edges")
        self.figs_el = ET.SubElement(self.root, "Figures")
        self.custom = custom_childset(st, report)
        self.body = None

    # ---- main entry ------------------------------------------------------------
    def build(self):
        st = self.st
        slots = usable_slots(st, self.context.active_object)
        if not slots:
            raise ModelError("Nothing to export: pick a mesh object for the selected model type.")
        require_nodes(slot_node_names(slots))
        if st.model_type_export == 'BODY_GEAR':
            self.body = BodyGear(st)

        for slot in slots:
            self.export_slot(slot)
        if st.model_type_export == 'BODY_GEAR' and st.model_include_necessary_tri_body:
            for suffix, a, b, c in FOOT_TRIANGLES:
                ET.SubElement(self.figs_el, f"{self.prefix}Foot-Triangle{suffix}", Type="Triangle", Shading="0",
                              Node1=a, Node2=b, Node3=c)
        if st.model_export_capsules and st.model_export_capsules_folder:
            self.export_capsules()
        self.check_names()
        return self.root

    # ---- one object ------------------------------------------------------------
    def export_slot(self, slot):
        st, o, t = self.st, slot.obj, self.st.model_type_export
        mesh = o.to_mesh()
        try:
            bm = bmesh.new()
            bm.from_mesh(mesh)
            bmesh.ops.triangulate(bm, faces=bm.faces[:])
            bm.to_mesh(mesh)
            bm.free()
            verts, edges, faces = mesh.vertices, mesh.edges, mesh.polygons

            mw = o.matrix_world
            world = [mw @ v.co for v in verts]
            names = [f"{self.prefix}Node-{self.n0 + i}" for i in range(len(verts))]
            cloth = vertex_group_indices(o, slot.cloth) if st.model_export_cloth and not slot.attack else set()
            macro = vertex_group_indices(o, slot.macro) if self.custom else set()

            if slot.attack:
                self.write_attack_edges(slot, names, edges, world)
                self.write_gear_nodes(slot, names, world, cloth, macro)
            elif t == 'MODEL':
                self.write_model_nodes(o, names, world, cloth, macro)
                self.write_edges(names, edges, world)
                self.write_faces(names, faces)
            else:
                if t != 'WEAPON' or st.model_edge_include:
                    self.write_edges(names, edges, world)
                    self.e0 += len(edges)
                self.write_faces(names, faces)
                self.t0 += len(faces)
                self.write_gear_nodes(slot, names, world, cloth, macro)
            self.n0 += len(verts)
        finally:
            o.to_mesh_clear()

    # ---- nodes -----------------------------------------------------------------
    def write_gear_nodes(self, slot, names, world, cloth, macro):
        st = self.st
        fixed_set = ChildSet.from_names(slot.children) if slot.children else None
        for i, pos in enumerate(world):
            if i in cloth:
                write_clothnode(self.nodes_el, names[i], pos, st.model_export_cloth_mass, st.model_export_cloth_attenuation)
                continue
            if self.custom and i in macro:
                children = self.custom
            elif slot.children is None:
                children = self.body.children(self.body.region(pos.z))
            else:
                children = fixed_set
            write_macronode(self.nodes_el, names[i], pos, st.model_node_mass, st.model_node_fixed, children)

    def write_plain_node(self, name, pos, is_cloth):
        st = self.st
        attribs = {"Type": "Node", **xml_attribs(pos),
                   "Mass": str(st.model_export_cloth_mass if is_cloth else st.model_node_mass),
                   "Fixed": "0" if is_cloth else ("1" if st.model_node_fixed else "0"),
                   "PinFixed": "0", "Visible": "1", "Passive": "0", "Cloth": "1" if is_cloth else "0",
                   "Collisible": "0" if is_cloth else ("1" if st.model_node_collisible else "0")}
        if is_cloth:
            attribs.update(Attenuation=f"{st.model_export_cloth_attenuation:.2f}", Rank="0")
        ET.SubElement(self.nodes_el, name, **attribs)

    def write_model_nodes(self, o, names, world, cloth, macro):
        st = self.st
        pivot = set()
        if st.model_use_pivot:
            if st.model_pivot_source == 'GROUP':
                pivot = vertex_group_indices(o, st.model_pivot)
                if len(pivot) > 1:
                    raise ModelError(f"Pivot group '{st.model_pivot}' has {len(pivot)} vertices - a model has exactly one NPivot.")
                if not pivot:
                    self.report({'WARNING'}, "No NPivot defined. Models placed in the world need exactly one (see 'Set Pivot').")
            for i in pivot:
                names[i] = "NPivot"

        for i, pos in enumerate(world):
            if self.custom and i in macro and i not in cloth:
                write_macronode(self.nodes_el, names[i], pos, st.model_node_mass, st.model_node_fixed, self.custom)
            else:
                self.write_plain_node(names[i], pos, i in cloth)

        if st.model_use_pivot and st.model_pivot_source != 'GROUP':     # extra NPivot node, no vertex needed
            where = o.matrix_world.translation if st.model_pivot_source == 'ORIGIN' else self.context.scene.cursor.location
            self.write_plain_node("NPivot", where, False)

    # ---- edges / triangles -------------------------------------------------------
    def write_edges(self, names, edges, world):
        coll = "1" if self.st.model_edge_collisible else "0"
        for i, e in enumerate(edges, start=self.e0):
            a, b = e.vertices
            ET.SubElement(self.edges_el, f"{self.prefix}Edge-{i}", Type="Edge", Length=str(math.dist(world[a], world[b])),
                          WithSign="0", Fixed="0", Visible="1", Collisible=coll, SubNodesCount="0",
                          End1=names[a], End2=names[b])

    def write_attack_edges(self, slot, names, edges, world):
        coll = "1" if self.st.model_edge_collisible else "0"
        suffix = "" if slot.ranged else ("_2" if slot.second else "_1")
        for i, e in enumerate(edges, start=1):
            a, b = e.vertices
            ET.SubElement(self.edges_el, f"{self.prefix}AttackEdge-{i}{suffix}", Type="Edge",
                          Length=str(math.dist(world[a], world[b])), WithSign="0", Fixed="0", Visible="1",
                          Collisible=coll, SubNodesCount="0", End1=names[a], End2=names[b])

    def write_faces(self, names, faces):
        for i, f in enumerate(faces, start=self.t0):
            if len(f.vertices) == 3:
                a, b, c = f.vertices
                ET.SubElement(self.figs_el, f"{self.prefix}Triangle-{i}", Type="Triangle",
                              Node1=names[a], Node2=names[b], Node3=names[c])

    # ---- capsules ----------------------------------------------------------------
    def export_capsules(self):
        st = self.st
        for o in st.model_export_capsules_folder.all_objects:
            mod = next((m for m in o.modifiers if m.type == 'NODES' and m.node_group), None) if o.type == 'MESH' else None
            if not mod:
                continue
            ids = socket_ids(mod.node_group)
            try:
                e1, e2 = get_input(mod, ids["End1"]), get_input(mod, ids["End2"])
                m1, m2 = get_input(mod, ids["Margin1"]), get_input(mod, ids["Margin2"])
                rad = get_input(mod, ids["Radius"])
            except KeyError:
                continue
            if not e1 or not e2:
                continue

            edge_val = None
            if st.model_export_capsules_predefined:
                edge_val = get_input(mod, ids["Edge"]) if "Edge" in ids else None
            else:
                for e in self.edges_el:
                    if e.get('End1') == e1.name and e.get('End2') == e2.name:
                        edge_val = e.tag
                        break
                    if e.get('End2') == e1.name and e.get('End1') == e2.name:
                        edge_val, m1, m2 = e.tag, m2, m1
                        break
            if edge_val:
                ET.SubElement(self.figs_el, o.name.replace(" ", "_"), Type="Capsule", Edge=edge_val,
                              Radius1=f"{rad:.2f}", Radius2=f"{rad:.2f}", Margin1=str(m1), Margin2=str(m2))

    # ---- sanity check --------------------------------------------------------------
    def check_names(self):
        """Names must be unique inside this XML and against the Dependencies XML (they are merged in-game)."""
        tags = [e.tag for sec in (self.nodes_el, self.edges_el, self.figs_el) for e in sec]
        dupes = sorted(t for t, c in Counter(tags).items() if c > 1)
        scene = self.context.scene
        dep_path = bpy.path.abspath(scene.gymnast_dependencies_xml) if scene.gymnast_dependencies_xml else ""
        if self.st.model_use_dependencies and os.path.isfile(dep_path):
            try:
                root = load_xml(dep_path)
                theirs = {e.tag for name in ("Nodes", "Edges", "Figures") for e in section(root, name)}
                dupes += sorted((set(tags) & theirs) - {"NPivot"} - set(dupes))
            except ModelError:
                pass
        if dupes:
            shown = ", ".join(dupes[:6]) + (" ..." if len(dupes) > 6 else "")
            self.report({'WARNING'}, f"Name conflict ({len(dupes)}): {shown}. Change the Prefix or the Start numbers.")


class ExportModelOperator(GymnastOperator):
    bl_idname = "model.export_to_xml"
    bl_label = "Export Model to XML"
    bl_description = "Write the selected model type to a Model XML file"
    filename_ext = ".xml"
    filepath: StringProperty(subtype="FILE_PATH")
    filter_glob: StringProperty(default="*.xml", options={'HIDDEN'})

    def run(self, context):
        st = context.scene.gymnast_tool_model_props
        root = ModelExporter(context, self.report).build()
        path = write_xml_file(root, self.filepath, st.model_optimize_xml)
        self.report({'INFO'}, f"Model exported to {path}")

    def invoke(self, context, event):
        self.filepath = bpy.path.abspath("//") + "exported_model.xml"
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class SetPivotOperator(GymnastOperator):
    bl_idname = "model.set_pivot"
    bl_label = "Set Pivot from Selection"
    bl_description = "Turn the selected vertex (Edit Mode) into the NPivot vertex group."

    def run(self, context):
        st = context.scene.gymnast_tool_model_props
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            raise ModelError("Select the model object and one vertex in Edit Mode.")
        mode = obj.mode
        if mode == 'EDIT':
            obj.update_from_editmode()
        selected = [v.index for v in obj.data.vertices if v.select]
        if len(selected) != 1:
            raise ModelError(f"Select exactly one vertex (currently {len(selected)}).")
        if mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        vg = obj.vertex_groups.get("NPivot") or obj.vertex_groups.new(name="NPivot")
        old = list(vertex_group_indices(obj, "NPivot"))
        if old:
            vg.remove(old)
        vg.add(selected, 1.0, 'REPLACE')
        if mode != 'OBJECT':
            bpy.ops.object.mode_set(mode=mode)
        if not st.selected_object:
            st.selected_object = obj
        st.model_use_pivot, st.model_pivot_source, st.model_pivot = True, 'GROUP', "NPivot"
        self.report({'INFO'}, f"Vertex {selected[0]} is now the NPivot.")




# =========================================== #
#  Skeleton binding
# =========================================== #
#  A vertex v is stored in the XML as  v = sum(LCC_i * child_i).  The same formula is evaluated live by a
#  Geometry Nodes modifier, so negative LCCs and badly shaped tetrahedrons functions like in the game.

def ensure_rig_group():
    existing = bpy.data.node_groups.get(RIG_GROUP)
    if existing and existing.bl_idname == 'GeometryNodeTree':
        return existing
    if existing:
        bpy.data.node_groups.remove(existing)

    ng = bpy.data.node_groups.new(RIG_GROUP, 'GeometryNodeTree')
    ng.is_modifier = True
    ng.use_fake_user = True
    iface, links = ng.interface, ng.links

    def socket(name, kind, io='INPUT'):
        iface.new_socket(name=name, in_out=io, socket_type=kind)

    socket("Geometry", 'NodeSocketGeometry')
    socket("Selection Group", 'NodeSocketString')
    for k in range(1, 5):
        socket(f"Child {k}", 'NodeSocketObject')
    socket("Rest Origin", 'NodeSocketVector')
    for k in range(1, 4):
        socket(f"Row {k}", 'NodeSocketVector')
    socket("Geometry", 'NodeSocketGeometry', 'OUTPUT')

    gi = add_node(ng, "NodeGroupInput", (-1500, 0))
    go = add_node(ng, "NodeGroupOutput", (1000, 0))

    # barycentric weights from the rest pose:  l1..l3 = row_k . (p - R4),   l4 = 1 - l1 - l2 - l3
    position = add_node(ng, "GeometryNodeInputPosition", (-1300, -300))
    offset = add_node(ng, "ShaderNodeVectorMath", (-1100, -300), operation='SUBTRACT')
    links.new(out(position, "Position"), offset.inputs[0])
    links.new(gi.outputs["Rest Origin"], offset.inputs[1])
    weights = []
    for k in range(3):
        dot = add_node(ng, "ShaderNodeVectorMath", (-900, -300 - 180 * k), operation='DOT_PRODUCT')
        links.new(out(offset, "Vector"), dot.inputs[0])
        links.new(gi.outputs[f"Row {k + 1}"], dot.inputs[1])
        weights.append(out(dot, "Value"))
    rest = None
    for k in range(3):
        sub = add_node(ng, "ShaderNodeMath", (-700, -300 - 150 * k), operation='SUBTRACT')
        if rest is None:
            sub.inputs[0].default_value = 1.0
        else:
            links.new(rest, sub.inputs[0])
        links.new(weights[k], sub.inputs[1])
        rest = out(sub, "Value")
    weights.append(rest)

    # new position = sum(l_i * child_i)   (child positions relative to the modified object)
    total = None
    for k in range(4):
        info = add_node(ng, "GeometryNodeObjectInfo", (-700, 400 - 200 * k), transform_space='RELATIVE')
        links.new(gi.outputs[f"Child {k + 1}"], info.inputs["Object"])
        scaled = add_node(ng, "ShaderNodeVectorMath", (-400, 400 - 200 * k), operation='SCALE')
        links.new(out(info, "Location"), scaled.inputs[0])
        links.new(weights[k], scaled.inputs["Scale"])
        if total is None:
            total = out(scaled, "Vector")
        else:
            added = add_node(ng, "ShaderNodeVectorMath", (-150, 400 - 200 * k), operation='ADD')
            links.new(total, added.inputs[0])
            links.new(out(scaled, "Vector"), added.inputs[1])
            total = out(added, "Vector")

    named = add_node(ng, "GeometryNodeInputNamedAttribute", (200, -300), data_type='FLOAT')
    links.new(gi.outputs["Selection Group"], named.inputs["Name"])
    setpos = add_node(ng, "GeometryNodeSetPosition", (600, 0))
    links.new(gi.outputs["Geometry"], setpos.inputs["Geometry"])
    links.new(out(named, "Attribute"), setpos.inputs["Selection"])
    links.new(total, setpos.inputs["Position"])
    links.new(setpos.outputs["Geometry"], go.inputs["Geometry"])
    return ng


def clear_rig(obj):
    for mod in [m for m in obj.modifiers if m.name.startswith(RIG_PREFIX)]:
        obj.modifiers.remove(mod)
    for vg in [g for g in obj.vertex_groups if g.name.startswith(RIG_PREFIX)]:
        obj.vertex_groups.remove(vg)


def add_rig_modifier(obj, key, children, report):
    group = ensure_rig_group()
    ids = socket_ids(group)
    inv = obj.matrix_world.inverted()
    rest = [inv @ p for p in children.points]                       # rest tetrahedron in object space
    basis = Matrix((rest[0] - rest[3], rest[1] - rest[3], rest[2] - rest[3])).transposed()
    if abs(basis.determinant()) < 1e-9:
        report({'WARNING'}, f"'{key}': the four child nodes are (almost) flat - the result may jitter.")
    rows = basis.inverted_safe()

    mod = obj.modifiers.new(name=f"{RIG_PREFIX}Rig {key}", type='NODES')
    mod.node_group = group
    set_input(mod, ids["Selection Group"], f"{RIG_PREFIX}{key}")
    for k in range(4):
        set_input(mod, ids[f"Child {k + 1}"], children.objects[k])
    set_input(mod, ids["Rest Origin"], tuple(rest[3]))
    for k in range(3):
        set_input(mod, ids[f"Row {k + 1}"], tuple(rows[k]))
    obj.update_tag()


def bind_slot(slot, custom, body, report):
    obj = slot.obj
    clear_rig(obj)
    mw = obj.matrix_world
    macro = vertex_group_indices(obj, slot.macro) if custom else set()
    fixed = ChildSet.from_names(slot.children) if slot.children else None
    buckets = {}
    for v in obj.data.vertices:
        if v.index in macro:
            key, children = "Custom", custom
        elif body:
            key = body.region((mw @ v.co).z)
            children = body.children(key)
        elif fixed:
            key, children = "All", fixed
        else:
            continue
        buckets.setdefault(key, (children, []))[1].append(v.index)
    for key, (children, indices) in buckets.items():
        obj.vertex_groups.new(name=f"{RIG_PREFIX}{key}").add(indices, 1.0, 'REPLACE')
        add_rig_modifier(obj, key, children, report)
    return len(buckets)


class BindLCCOperator(GymnastOperator):
    bl_idname = "model.bind_lcc"
    bl_label = "Bind to Skeleton"
    bl_description = ("Make the model follow its child nodes\n"
                      "Do this while the skeleton is in its rest pose")

    def run(self, context):
        st = context.scene.gymnast_tool_model_props
        slots = usable_slots(st, context.active_object)
        if not slots:
            raise ModelError("Pick the object(s) to bind in the Export Settings first.")
        require_nodes(slot_node_names(slots))
        custom = custom_childset(st, self.report)
        body = BodyGear(st) if st.model_type_export == 'BODY_GEAR' else None
        count = sum(bind_slot(s, custom, body, self.report) for s in slots)
        if not count:
            raise ModelError("Nothing to bind. This type has no standard child nodes - enable Custom ChildNodes.")
        self.report({'INFO'}, f"Bound {count} vertex region(s) with {len(slots)} object(s).")


class UnbindLCCOperator(GymnastOperator):
    bl_idname = "model.unbind_lcc"
    bl_label = "Remove Binding"
    bl_description = "Remove the LCC modifiers and vertex groups created by Bind to Skeleton"

    def run(self, context):
        st = context.scene.gymnast_tool_model_props
        targets = {s.obj for s in usable_slots(st, context.active_object)} | set(context.selected_objects)
        for obj in targets:
            if obj.type == 'MESH':
                clear_rig(obj)
        self.report({'INFO'}, "Binding removed.")




# ----------------------------------------------------------------------------- #
#  Rigid follow, for standalone models without child nodes
# ----------------------------------------------------------------------------- #

def reframe_object(obj, new_world):
    """Give `obj` a new origin / orientation without moving its mesh in world space."""
    old = obj.matrix_world.copy()
    if obj.type == 'MESH':
        if obj.data.users > 1:
            obj.data = obj.data.copy()
        obj.data.transform(new_world.inverted() @ old)
    obj.matrix_world = new_world


class SetOrientation(GymnastOperator):
    bl_idname = "model.set_orientation"
    bl_label = "Set Origin / Rigid Follow"
    bl_description = ("Move the object's origin to the Origin object.\nWith 'Add Constraint', the object also follows the Origin object's Z and Y axes.")

    def run(self, context):
        st = context.scene.gymnast_tool_model_props
        obj, origin = st.model_orientation, st.model_origin_object
        if not obj or not origin:
            raise ModelError("Both the Object and the Origin object must be specified.")
        origin_loc = origin.matrix_world.translation.copy()

        new_world = obj.matrix_world.copy()
        new_world.translation = origin_loc
        if not st.model_apply_constraint:
            reframe_object(obj, new_world)
            self.report({'INFO'}, "Origin moved.")
            return

        tz, ty = st.model_target_z, st.model_target_y
        if not (tz and ty):                                  # old workflow: two other selected objects
            others = [o for o in context.selected_objects if o != obj]
            if len(others) != 2:
                raise ModelError("Set the Z / Y targets, or select exactly two other objects.")
            tz, ty = others
        z_dir = (tz.matrix_world.translation - origin_loc).normalized()
        y_dir = (ty.matrix_world.translation - origin_loc).normalized()
        x_dir = y_dir.cross(z_dir).normalized()
        y_dir = z_dir.cross(x_dir).normalized()
        new_world = Matrix.Translation(origin_loc) @ Matrix((x_dir, y_dir, z_dir)).transposed().to_4x4()
        reframe_object(obj, new_world)

        obj.constraints.clear()
        obj.constraints.new('COPY_LOCATION').target = origin
        track_z = obj.constraints.new('DAMPED_TRACK')
        track_z.target, track_z.track_axis = tz, 'TRACK_Z'
        track_y = obj.constraints.new('LOCKED_TRACK')     # keeps Z fixed, so a non-perpendicular Y target cannot tilt it
        track_y.target, track_y.track_axis, track_y.lock_axis = ty, 'TRACK_Y', 'LOCK_Z'
        self.report({'INFO'}, "Origin moved and follow constraints added.")




# ----------------------------------------------------------------------------- #
#  Macro rule list
# ----------------------------------------------------------------------------- #

class AddRuleOperator(bpy.types.Operator):
    bl_idname = "macro_rules.add_rule"
    bl_label = "Add Rule"
    bl_description = "Add a new group rule."
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        context.scene.macro_rules.add()
        context.scene.macro_rules_index = len(context.scene.macro_rules) - 1
        return {'FINISHED'}


class RemoveRuleOperator(bpy.types.Operator):
    bl_idname = "macro_rules.remove_rule"
    bl_label = "Remove Rule"
    bl_description = "Remove the selected group rule."
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        if 0 <= scene.macro_rules_index < len(scene.macro_rules):
            scene.macro_rules.remove(scene.macro_rules_index)
            scene.macro_rules_index = max(0, min(scene.macro_rules_index, len(scene.macro_rules) - 1))
        return {'FINISHED'}


class AddTemplateGroupsOperator(bpy.types.Operator):
    bl_idname = "macro_rules.add_templates"
    bl_label = "Preset Groups"
    bl_description = "Add the preset armor / weapon rules."
    bl_options = {'REGISTER', 'UNDO'}

    group_type: EnumProperty(
        name="Group Type", default='ALL',
        items=[('ARMOR', "Armor", "Armor groups only"), ('WEAPON', "Weapon", "Weapon groups only"),
               ('ALL', "All", "Every preset")])

    def execute(self, context):
        scene = context.scene
        existing = {item.group for item in scene.macro_rules}
        wanted = [k for k in MACRO_TEMPLATES if self.group_type in (k, 'ALL')]
        added = 0
        for key in wanted:
            for grp, names in MACRO_TEMPLATES[key]:
                if grp not in existing:
                    rule = scene.macro_rules.add()
                    rule.group, rule.names = grp, names
                    added += 1
        self.report({'INFO'}, f"Added {added} preset rule(s)")
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)


class ClearMacroRulesOperator(bpy.types.Operator):
    bl_idname = "macro_rules.clear_rules"
    bl_label = "Clear All Rules"
    bl_description = "Remove every rule from the list"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        context.scene.macro_rules.clear()
        context.scene.macro_rules_index = 0
        return {'FINISHED'}





# ============================================================================ #
#  Settings
# ============================================================================ #

class MacroRuleItem(bpy.types.PropertyGroup):
    group: StringProperty(name="Group", description="Name of the vertex group.")
    names: StringProperty(name="Child Nodes", description="Names of the ChildNodes separated by commas, no spaces.\nEx. NChestS_2,NChestF,NChestS_1,NNeck")


class GymnastToolModelSettings(bpy.types.PropertyGroup):
    # ---- general
    model_string_name: StringProperty(name="Prefix", description="Added in front of every Node / Edge / Figure name.\nEx. 'Cloth-', 'CoolStaff-'")
    model_type_export: EnumProperty(
        name="Type", default='MODEL', description="Type of Model for export",
        items=[('MODEL', "Model", "Standalone model placed in the world"),
               ('HEAD_GEAR', "Head Gear", "Head Accessory"),
               ('BODY_GEAR', "Body Gear", "Body Accessory"),
               ('FOOT_GEAR', "Foot Gear", "Shoes"),
               ('WEAPON', "Weapon", "Weapon Model (SF2 only)"),
               ('RANGED', "Ranged", "Ranged Weapon (SF2 only)")])

    selected_object: PointerProperty(name="Object", type=bpy.types.Object, description="Object to export\nActive Object is used if this is empty.")
    weapon_object_1: PointerProperty(name="Weapon 1", type=bpy.types.Object, description="Weapon attached to the left hand")
    weapon_object_2: PointerProperty(name="Weapon 2", type=bpy.types.Object, description="Weapon attached to the right hand")
    foot_object_1: PointerProperty(name="Footwear 1", type=bpy.types.Object, description="Right foot (Vector) / left foot (SF2)")
    foot_object_2: PointerProperty(name="Footwear 2", type=bpy.types.Object, description="Left foot (Vector) / right foot (SF2)")

    # ---- nodes / edges
    model_node_mass: FloatProperty(name="Node Mass", description="Mass of every node", default=1.0, min=0.0, max=10000.0, precision=2)
    model_node_collisible: BoolProperty(name="Node Collisible", description="Every node is collisible (Model type only)", default=False)
    model_node_fixed: BoolProperty(name="Node Fixed", description="Nodes never move unless animated", default=False)
    model_edge_collisible: BoolProperty(name="Edge Collisible", description="Every edge is collisible", default=False)
    model_edge_include: BoolProperty(name="Include Edges", description="Weapons only: write the edges of the weapon (attack edges are always written)", default=True)
    model_node_offset: IntProperty(name="Start Node", description="First node number", default=1, min=1)
    model_edge_offset: IntProperty(name="Start Edge", description="First edge number", default=1, min=1)
    model_tri_offset: IntProperty(name="Start Tri", description="First triangle number", default=1, min=1)

    # ---- cloth (vertex group NAMES)
    model_export_cloth: BoolProperty(name="Export Cloth", description="Vertices in the cloth vertex group become cloth nodes", default=False)
    model_export_cloth_attenuation: FloatProperty(name="Attenuation", description="How much a cloth node resists deformation.\n0 = soft, 1 = stiff", default=0, min=0.0, max=2.0, precision=2)
    model_export_cloth_mass: FloatProperty(name="Cloth Mass", description="Mass of every cloth node", default=0.1, min=0.0, max=10000.0, precision=2)
    model_export_cloth_general_folder: StringProperty(name="Cloth Group", description="Vertex group holding the cloth vertices")
    model_export_cloth_weapon1_folder: StringProperty(name="Cloth Group 1", description="Vertex group holding the cloth vertices of weapon 1")
    model_export_cloth_weapon2_folder: StringProperty(name="Cloth Group 2", description="Vertex group holding the cloth vertices of weapon 2")
    model_export_cloth_foot1_folder: StringProperty(name="Cloth Group 1", description="Vertex group holding the cloth vertices of footwear 1")
    model_export_cloth_foot2_folder: StringProperty(name="Cloth Group 2", description="Vertex group holding the cloth vertices of footwear 2")

    # ---- capsules
    model_export_capsules: BoolProperty(name="Export Capsules", description="Export the capsules of a collection", default=False)
    model_export_capsules_predefined: BoolProperty(name="Use Predefined Edge", description="Use the edge name typed in the capsule's 'Edge' socket instead of searching for a matching edge", default=False)
    model_export_capsules_folder: PointerProperty(name="Capsules", type=bpy.types.Collection, description="Collection containing the capsules to export")

    # ---- rigid follow
    model_is_advanced: BoolProperty(name="Advanced Options", description="Show the rigid follow tools for stand-alone models", default=False)
    model_orientation: PointerProperty(name="Object", type=bpy.types.Object, description="Object that gets the new origin / follow constraints")
    model_origin_object: PointerProperty(name="Origin", type=bpy.types.Object, description="The object's origin is moved onto this object")
    model_target_z: PointerProperty(name="Z Target", type=bpy.types.Object, description="The object's Z axis points to this object")
    model_target_y: PointerProperty(name="Y Target", type=bpy.types.Object, description="The object's Y axis points as close as possible to this object")
    model_apply_constraint: BoolProperty(name="Add Constraint", description="Also rotate the object and add Copy Location\nDamped Track (Z) and Locked Track (Y)", default=False)

    # ---- body gear
    model_body_top: EnumProperty(name="Top", items=BODY_ITEMS, default='CHEST', description="Child nodes used above the chest")
    model_body_middle: EnumProperty(name="Middle", items=BODY_ITEMS, default='STOMACH', description="Child nodes used between stomach and chest")
    model_body_bottom: EnumProperty(name="Bottom", items=BODY_ITEMS, default='HIP', description="Child nodes used below the stomach")
    model_include_necessary_tri_body: BoolProperty(name="Include Foot Triangle (SF2)", description="Hides the visible hole at the side of the SF2 foot", default=False)

    # ---- attack edges
    model_include_attack_edges: BoolProperty(name="Add Attack Edges", description="Edges that define the damaging part", default=True)
    model_attack_edges_object_1: PointerProperty(name="Edges 1", type=bpy.types.Object, description="Attack edges of weapon 1 (or of the ranged weapon)")
    model_attack_edges_object_2: PointerProperty(name="Edges 2", type=bpy.types.Object, description="Attack edges of weapon 2")

    # ---- pivot
    model_use_pivot: BoolProperty(name="Use Pivot", description="Writes an NPivot node.\nModels without one can crash the game", default=True)
    model_pivot_source: EnumProperty(
        name="Pivot From", default='GROUP', description="Where the NPivot comes from",
        items=[('GROUP', "Vertex Group", "A single vertex in a vertex group becomes the NPivot."),
               ('ORIGIN', "Object Origin", "An extra NPivot node is added at the object's origin"),
               ('CURSOR', "3D Cursor", "An extra NPivot node is added at the 3D cursor")])
    model_pivot: StringProperty(name="Pivot Group", description="Vertex group holding the single NPivot vertex")

    # ---- import
    calculate_macronode: BoolProperty(name="Apply LCCs", description="Calculate MacroNode positions from their child nodes + LCCs.\nOff = use the stored X, Y, Z", default=True)
    model_use_dependencies: BoolProperty(name="Use Dependencies", description="Model XML will use the nodes, edges in the Dependencies XML", default=True)
    import_node_as_vertex: BoolProperty(name="Import Nodes as Vertices", description="Nodes become vertices instead of spheres.", default=False)
    import_node_size: FloatProperty(name="Node Size", description="Radius of the node spheres", default=1.0, min=0.001, precision=3)
    import_replace_existing: BoolProperty(name="Replace Previous Import", description="Delete what the last import of this model put in its collection first", default=True)
    add_vertex_group: BoolProperty(name="Add Vertex Groups", description="Create vertex groups from the rules below when importing triangles", default=True)
    add_vertex_group_include_cloth: BoolProperty(name="Include Cloth", description="Also create a 'Cloth' group from cloth nodes", default=True)
    model_optimize_xml: BoolProperty(name="Optimize XML", description="Optimize the XML to have the smallest possible file size.\nThis makes it so there are no indentation or newlines", default=False)

    # ---- custom child nodes
    model_custom_childnode: BoolProperty(name="Custom ChildNodes", description="Use four objects of your choice as ChildNodes for the vertices of the Macronode group", default=False)
    childnode_1_object: PointerProperty(name="Childnode 1", type=bpy.types.Object)
    childnode_2_object: PointerProperty(name="Childnode 2", type=bpy.types.Object)
    childnode_3_object: PointerProperty(name="Childnode 3", type=bpy.types.Object)
    childnode_4_object: PointerProperty(name="Childnode 4", type=bpy.types.Object)
    macronode_vertex_group: StringProperty(name="Macronode Group", description="Vertices in this group use the custom ChildNodes")
    macronode_vertex_group_weapon_1: StringProperty(name="Macronode Group 1", description="Macronode group of weapon 1")
    macronode_vertex_group_weapon_2: StringProperty(name="Macronode Group 2", description="Macronode group of weapon 2")
    macronode_vertex_group_foot_1: StringProperty(name="Macronode Group 1", description="Macronode group of footwear 1")
    macronode_vertex_group_foot_2: StringProperty(name="Macronode Group 2", description="Macronode group of footwear 2")





# ============================================================================ #
#  UI
# ============================================================================ #

def draw_group_field(layout, st, prop, obj, text):
    """Vertex group name field with a dropdown of the object's groups."""
    if obj and obj.type == 'MESH':
        layout.prop_search(st, prop, obj, "vertex_groups", text=text)
    else:
        row = layout.row()
        row.enabled = False
        row.prop(st, prop, text=text)


def ui_slots(st):
    """(object, cloth property, macro property, label suffix) for the current model type."""
    t = st.model_type_export
    if t == 'WEAPON':
        return [(st.weapon_object_1, "model_export_cloth_weapon1_folder", "macronode_vertex_group_weapon_1", " 1"),
                (st.weapon_object_2, "model_export_cloth_weapon2_folder", "macronode_vertex_group_weapon_2", " 2")]
    if t == 'FOOT_GEAR':
        return [(st.foot_object_1, "model_export_cloth_foot1_folder", "macronode_vertex_group_foot_1", " 1"),
                (st.foot_object_2, "model_export_cloth_foot2_folder", "macronode_vertex_group_foot_2", " 2")]
    return [(st.selected_object, "model_export_cloth_general_folder", "macronode_vertex_group", "")]


class MACRO_UL_rules(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        layout.label(text=item.group)


class VIEW3D_PT_gymnast_model_panel(bpy.types.Panel):
    bl_label = "Model Tools"
    bl_idname = "VIEW3D_PT_gymnast_model_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = CATEGORY
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout, scene = self.layout, context.scene
        layout.prop(scene, "gymnast_dependencies_xml")
        layout.prop(scene, "gymnast_normal_xml")

        box = layout.box()
        box.label(text="Import", icon='IMPORT')
        box.operator("model.import_all", text="Import Everything")
        col = box.column(align=True)
        col.operator("model.add_nodes", text="Nodes")
        col.operator("model.add_edges", text="Nodes + Edges")
        col.operator("model.convert_xml", text="Mesh")
        col.operator("model.add_capsules", text="Capsules")

        box = layout.box()
        box.label(text="Export", icon='EXPORT')
        box.operator("model.export_to_xml", text="Export Model to XML")


class VIEW3D_PT_gymnast_model_settings(bpy.types.Panel):
    bl_label = "Settings"
    bl_idname = "VIEW3D_PT_gymnast_model_settings"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = CATEGORY
    bl_parent_id = "VIEW3D_PT_gymnast_model_panel"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        pass      # parent panel only


class VIEW3D_PT_gymnast_model_settings_import(bpy.types.Panel):
    bl_label = "Import Settings"
    bl_idname = "VIEW3D_PT_gymnast_model_settings_import"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = CATEGORY
    bl_parent_id = "VIEW3D_PT_gymnast_model_settings"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        st, scene, layout = context.scene.gymnast_tool_model_props, context.scene, self.layout
        box = layout.box()
        for prop in ("calculate_macronode", "model_use_dependencies", "import_replace_existing", "import_node_as_vertex"):
            box.prop(st, prop)
        if not st.import_node_as_vertex:
            box.prop(st, "import_node_size")
        box.prop(st, "add_vertex_group")
        if st.add_vertex_group:
            box.prop(st, "add_vertex_group_include_cloth")
            row = box.row()
            row.template_list("MACRO_UL_rules", "", scene, "macro_rules", scene, "macro_rules_index", rows=3)
            col = row.column(align=True)
            col.operator("macro_rules.add_rule", icon='ADD', text="")
            col.operator("macro_rules.remove_rule", icon='REMOVE', text="")
            col.operator("macro_rules.add_templates", icon='PRESET', text="")
            col.operator("macro_rules.clear_rules", icon='TRASH', text="")
            if 0 <= scene.macro_rules_index < len(scene.macro_rules):
                item = scene.macro_rules[scene.macro_rules_index]
                box.prop(item, "group")
                box.prop(item, "names")


class VIEW3D_PT_gymnast_model_settings_export(bpy.types.Panel):
    bl_label = "Export Settings"
    bl_idname = "VIEW3D_PT_gymnast_model_settings_export"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = CATEGORY
    bl_parent_id = "VIEW3D_PT_gymnast_model_settings"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        st, layout = context.scene.gymnast_tool_model_props, self.layout
        t = st.model_type_export
        slots = ui_slots(st)

        box = layout.box()
        box.prop(st, "model_string_name")
        box.prop(st, "model_type_export")
        if t == 'WEAPON':
            box.prop(st, "weapon_object_1")
            box.prop(st, "weapon_object_2")
        elif t == 'FOOT_GEAR':
            box.prop(st, "foot_object_1")
            box.prop(st, "foot_object_2")
        else:
            box.prop(st, "selected_object")
        for prop in ("model_node_mass", "model_node_fixed", "model_edge_collisible"):
            box.prop(st, prop)

        if t == 'MODEL':
            box.prop(st, "model_node_collisible")
            box.prop(st, "model_use_pivot")
            if st.model_use_pivot:
                box.prop(st, "model_pivot_source")
                if st.model_pivot_source == 'GROUP':
                    draw_group_field(box, st, "model_pivot", st.selected_object, "Pivot Group")
                    box.operator("model.set_pivot")
        elif t == 'BODY_GEAR':
            for prop in ("model_body_top", "model_body_middle", "model_body_bottom"):
                box.prop(st, prop)
        elif t == 'WEAPON':
            box.prop(st, "model_edge_include")

        if t in {'WEAPON', 'RANGED'}:
            box = layout.box()
            box.label(text="Attack Edges")
            box.prop(st, "model_include_attack_edges")
            if st.model_include_attack_edges:
                box.prop(st, "model_attack_edges_object_1")
                if t == 'WEAPON':
                    box.prop(st, "model_attack_edges_object_2")

        box = layout.box()
        box.label(text="Additional Settings")
        if t == 'BODY_GEAR':
            box.prop(st, "model_include_necessary_tri_body")
        box.prop(st, "model_export_capsules")
        if st.model_export_capsules:
            box.prop(st, "model_export_capsules_predefined")
            box.prop(st, "model_export_capsules_folder")
        box.prop(st, "model_export_cloth")
        if st.model_export_cloth:
            box.prop(st, "model_export_cloth_attenuation")
            box.prop(st, "model_export_cloth_mass")
            for obj, cloth_prop, _macro_prop, suffix in slots:
                draw_group_field(box, st, cloth_prop, obj, f"Cloth Group{suffix}")
        box.prop(st, "model_optimize_xml")

        box = layout.box()
        box.label(text="Childnode")
        box.prop(st, "model_custom_childnode")
        if st.model_custom_childnode:
            for obj, _cloth_prop, macro_prop, suffix in slots:
                draw_group_field(box, st, macro_prop, obj, f"Macronode Group{suffix}")
            for k in range(1, 5):
                box.prop(st, f"childnode_{k}_object")


class VIEW3D_PT_gymnast_settings_object_settings(bpy.types.Panel):
    bl_label = "Object Alignment"
    bl_idname = "VIEW3D_PT_gymnast_settings_object_settings"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = CATEGORY
    bl_parent_id = "VIEW3D_PT_gymnast_model_settings"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        st, layout = context.scene.gymnast_tool_model_props, self.layout
        t = st.model_type_export

        box = layout.box()
        box.label(text="Bind to Skeleton")
        box.prop(st, "model_type_export")
        if t == 'WEAPON':
            box.prop(st, "weapon_object_1")
            box.prop(st, "weapon_object_2")
        elif t == 'FOOT_GEAR':
            box.prop(st, "foot_object_1")
            box.prop(st, "foot_object_2")
        elif t != 'MODEL' or st.model_custom_childnode:
            box.prop(st, "selected_object")
        if t == 'BODY_GEAR':
            for prop in ("model_body_top", "model_body_middle", "model_body_bottom"):
                box.prop(st, prop)
        if t == 'MODEL' and not st.model_custom_childnode:
            box.label(text="Models have no child nodes.")
            box.label(text="Use Custom ChildNodes or Rigid Follow.")
        row = box.row(align=True)
        row.operator("model.bind_lcc")
        row.operator("model.unbind_lcc", text="", icon='X')

        layout.prop(st, "model_is_advanced")
        if st.model_is_advanced or t == 'MODEL':
            box = layout.box()
            box.label(text="Rigid Follow")
            for prop in ("model_orientation", "model_origin_object", "model_apply_constraint"):
                box.prop(st, prop)
            if st.model_apply_constraint:
                box.prop(st, "model_target_z")
                box.prop(st, "model_target_y")
            box.operator("model.set_orientation")


class VIEW3D_PT_gymnast_model_settings_misc(bpy.types.Panel):
    bl_label = "Miscellaneous"
    bl_idname = "VIEW3D_PT_gymnast_model_settings_misc"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = CATEGORY
    bl_parent_id = "VIEW3D_PT_gymnast_model_settings"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        st = context.scene.gymnast_tool_model_props
        box = self.layout.box()
        box.label(text="Offset")
        for prop in ("model_node_offset", "model_edge_offset", "model_tri_offset"):
            box.prop(st, prop)





# ============================================================================ #
#  Registration
# ============================================================================ #

classes = (
    MacroRuleItem,
    GymnastToolModelSettings,
    ImportMeshOperator,
    ImportNodesOperator,
    ImportEdgesOperator,
    ImportCapsulesOperator,
    ImportAllOperator,
    ExportModelOperator,
    SetPivotOperator,
    BindLCCOperator,
    UnbindLCCOperator,
    SetOrientation,
    AddRuleOperator,
    RemoveRuleOperator,
    AddTemplateGroupsOperator,
    ClearMacroRulesOperator,
    MACRO_UL_rules,
    VIEW3D_PT_gymnast_model_panel,
    VIEW3D_PT_gymnast_model_settings,
    VIEW3D_PT_gymnast_model_settings_import,
    VIEW3D_PT_gymnast_model_settings_export,
    VIEW3D_PT_gymnast_settings_object_settings,
    VIEW3D_PT_gymnast_model_settings_misc,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.gymnast_dependencies_xml = StringProperty(
        name="Dependencies XML", description="Skeleton / Reference XML that the Model XML points to", subtype="FILE_PATH")
    bpy.types.Scene.gymnast_normal_xml = StringProperty(
        name="Model XML", description="The Model XML to import", subtype="FILE_PATH")
    bpy.types.Scene.gymnast_tool_model_props = PointerProperty(type=GymnastToolModelSettings)
    bpy.types.Scene.macro_rules = CollectionProperty(type=MacroRuleItem)
    bpy.types.Scene.macro_rules_index = IntProperty()


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.gymnast_dependencies_xml
    del bpy.types.Scene.gymnast_normal_xml
    del bpy.types.Scene.gymnast_tool_model_props
    del bpy.types.Scene.macro_rules
    del bpy.types.Scene.macro_rules_index


if __name__ == "__main__":
    register()