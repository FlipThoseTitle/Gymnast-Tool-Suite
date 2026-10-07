# #################### #
# Animation Panel
# #################### #

#  Axis convention: .bin (X, Y, Z)  <->  Blender (x, -z, y)
#  Exporter: X = x,  Y = z,  Z = -y


import math
import os
import re
import struct
import xml.dom.minidom as minidom
import xml.etree.ElementTree as ET

import bmesh
import bpy
import numpy as np

from bpy.props import (BoolProperty, EnumProperty, FloatProperty, IntProperty, PointerProperty, StringProperty)





# ============================================================================ #
#  Constants
# ============================================================================ #

CATEGORY = "Gymnast Tool Suite"

FORMAT_ITEMS = [
    ('.bin', ".bin", "Export as a .bin file"),
    ('.bytes', ".bytes", "Export as a .bytes file"),
]

# Node name -> bone it drives
COMMON_NODES = {
    "NTop": "Head", "NHead": "Head", "NHeadF": "HeadF", "NHeadS_2": "HeadF", "NHeadS_1": "HeadF",
    "NNeck": "Neck", "NShoulder_2": "Clavicle_2", "NShoulder_1": "Clavicle_1",
    "NElbow_2": "Arm_2", "NElbow_1": "Arm_1", "NWrist_2": "Forearm_2", "NWrist_1": "Forearm_1",
    "NKnuckles_2": "Hand_2", "NKnuckles_1": "Hand_1", "NKnucklesS_2": "Hand_2", "NKnucklesS_1": "Hand_1",
    "NFingertips_2": "Fingers_2", "NFingertips_1": "Fingers_1",
    "NChest": "Chest", "NChestF": "Chest", "NChestS_2": "Chest", "NChestS_1": "Chest",
    "NStomach": "Stomach", "NStomachF": "Stomach", "NStomachS_2": "Stomach", "NStomachS_1": "Stomach",
    "NPivot": "Pelvis", "NPelvisF": "Pelvis", "NHip_2": "Hip_2", "NHip_1": "Hip_1",
    "NKnee_2": "Thigh_2", "NKnee_1": "Thigh_1", "NAnkle_2": "Calf_2", "NAnkle_1": "Calf_1",
    "NHeel_2": "Heel_2", "NHeel_1": "Heel_1", "NToe_2": "Foot_2", "NToe_1": "Foot_1",
    "NToeS_2": "Foot_2", "NToeS_1": "Foot_1", "NToeTip_2": "Toes_2", "NToeTip_1": "Toes_1",
    "COM": "COM"
}

NODE_TO_BONE_VECTOR = COMMON_NODES.copy()

NODE_TO_BONE_SF2 = COMMON_NODES.copy()
NODE_TO_BONE_SF2.update({
    "NFingertipsS_2": "Fingers_2", "NFingertipsS_1": "Fingers_1",
    "NFingertipsSS_2": "FingersS_2", "NFingertipsSS_1": "FingersS_1",
    "MacroNode1_1": "Hand_1", "MacroNode1_2": "Hand_2",
    "MacroNode2_1": "Hand_1", "MacroNode2_2": "Hand_2",
    "MacroNode3_1": "Hand_1", "MacroNode3_2": "Hand_2",
    "MacroNode4_1": "Fingers_1", "MacroNode4_2": "Fingers_2",
    "MacroNode5_1": "FingersS_1", "MacroNode5_2": "FingersS_2",
    "MacroNode6_1": "FingersS_1", "MacroNode6_2": "FingersS_2",
    "Weapon-Node1_1": "Weapon_1", "Weapon-Node2_1": "Weapon_1",
    "Weapon-Node3_1": "Weapon_1", "Weapon-Node4_1": "Weapon_1",
    "Weapon-Node1_2": "Weapon_2", "Weapon-Node2_2": "Weapon_2",
    "Weapon-Node3_2": "Weapon_2", "Weapon-Node4_2": "Weapon_2"
})

# Nodes the rig never follows in SF2
IGNORE_NODES = [
    f"MacroNode{i}_{j}" for i in range(1, 7) for j in (1, 2)
] + [
    f"Weapon-Node{i}_{j}" for i in range(1, 5) for j in (1, 2)
]

# Nodes the rig never follows in Vector
VECTOR_SKIP_NODES = ("Camera", "DetectorH", "DetectorV")

# Node -> bone that copies its location. Only used when "Use IK" is on.
IK_NODES = {
    "NWrist_1": "HandIK_1", "NWrist_2": "HandIK_2",
    "NAnkle_1": "HeelIK_1", "NAnkle_2": "HeelIK_2",
    "COM": "COM", "NPivot": "Root"
}

# Node -> bone that twists towards it (Locked Track)
LOCKED_TRACK_NODES = {
    "NToeS_1": "Foot_1", "NToeS_2": "Foot_2", "NHeadS_2": "Head",
    "NKnucklesS_1": "Hand_1", "NKnucklesS_2": "Hand_2"
}

# Bone -> node it points at, instead of its own node
BODY_CHAIN = {
    "Pelvis": "NStomach", "Stomach": "NChest", "Chest": "NNeck",
    "Neck": "NHead", "Head": "NTop"
}

# These bones also follow NPivot
PIVOT_FOLLOW_BONES = ("Pelvis", "Hip_1", "Hip_2")

# SF2 only: node -> (bone, constraint)
SF2_NODES = {
    "NFingertipsSS_2": ("FingersS_2", 'DAMPED_TRACK'), "NFingertipsSS_1": ("FingersS_1", 'DAMPED_TRACK'),
    "NFingertipsS_2": ("Fingers_2", 'LOCKED_TRACK'), "NFingertipsS_1": ("Fingers_1", 'LOCKED_TRACK'),
    "MacroNode5_2": ("FingersS_2", 'LOCKED_TRACK'), "MacroNode5_1": ("FingersS_1", 'LOCKED_TRACK'),
}

# SF2 only, needs "Affect WeaponNode"
SF2_WEAPON_NODES = {
    f"Weapon-Node{n}_{side}": (f"Weapon_{side}", kind)
    for side in (1, 2)
    for n, kind in ((2, 'COPY_LOCATION'), (3, 'DAMPED_TRACK'), (4, 'LOCKED_TRACK'))
}

# After the bake, these bones go back onto the IK handles
IK_BONES = {"Calf_1": "HeelIK_1", "Calf_2": "HeelIK_2", "Forearm_1": "HandIK_1", "Forearm_2": "HandIK_2"}

# (bone, bone it should sit on the tip of) - used by "Use IK"
LIMB_ENDS = [("Hand_1", "Forearm_1"), ("Hand_2", "Forearm_2"), ("Heel_1", "Calf_1"), ("Heel_2", "Calf_2")]

# Mirrored import: what to multiply (x, y, z) by
FLIP_SIGNS = {'X': (-1.0, 1.0, 1.0), 'Y': (1.0, 1.0, -1.0), 'Z': (1.0, -1.0, 1.0)}






# ============================================================================ #
#  Helpers
# ============================================================================ #

class AnimationError(Exception):
    """A problem shown in Blender's status bar."""

def resolve_path(path):
    return bpy.path.abspath(path) if path else ""

def create_constraint(owner, kind, target, subtarget=""):
    """Adds a constraint to a bone or object. Does nothing when either one is missing."""
    if not owner or not target:
        return None
    c = owner.constraints.new(type=kind)
    c.target = target
    if subtarget:
        c.subtarget = subtarget
    if kind == 'LOCKED_TRACK':
        c.track_axis = 'TRACK_Z'
        c.lock_axis = 'LOCK_Y'
    return c

def enter_pose_mode(armature):
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='POSE')

def require_armature(settings):
    armature = settings.armature_object
    if not armature or armature.type != 'ARMATURE':
        raise AnimationError("Pick an Armature in Import Settings first.")
    return armature

def parse_nodes_from_xml(path):
    """Node names of an XML, in file order."""
    if not path:
        return []
    if not os.path.exists(path):
        raise AnimationError(f"Could not find '{path}'.")
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as err:
        raise AnimationError(f"Could not read '{os.path.basename(path)}': {err}")
    nodes = root.find("Nodes")
    return [node.tag for node in nodes] if nodes is not None else []

def get_node_order(settings):
    """Dependencies nodes first, then the Model nodes. This is the order the .bin stores them in."""
    node_order = parse_nodes_from_xml(resolve_path(settings.dependencies_xml))
    model_nodes = parse_nodes_from_xml(resolve_path(settings.model_xml))

    duplicates = sorted(set(node_order) & set(model_nodes))
    if duplicates:
        raise AnimationError(f"Duplicate nodes found in both XML files: {', '.join(duplicates)}")

    node_order += model_nodes
    if not node_order:
        raise AnimationError("At least one XML file must contain nodes.")
    return node_order

def bone_name(settings, node_name):
    mapping = NODE_TO_BONE_VECTOR if settings.armature_rig_type == "VECTOR" else NODE_TO_BONE_SF2
    return mapping.get(node_name)







# ============================================================================ #
#  Armature
# ============================================================================ #

def setup_armature_follow_node(node_order):
    """Makes the bones follow the node objects."""
    settings = bpy.context.scene.gymnast_tool_props
    armature = require_armature(settings)
    pose_bones = armature.pose.bones
    is_vector = settings.armature_rig_type == "VECTOR"
    enter_pose_mode(armature)

    for name in node_order:
        node = bpy.data.objects.get(name)
        if not node:
            continue

        # a previous bake leaves Child Of constraints on the nodes
        for c in list(node.constraints):
            if c.type == 'CHILD_OF':
                node.constraints.remove(c)

        if settings.use_armature_ik and name in IK_NODES:
            create_constraint(pose_bones.get(IK_NODES[name]), 'COPY_LOCATION', node)

        if name in LOCKED_TRACK_NODES:
            create_constraint(pose_bones.get(LOCKED_TRACK_NODES[name]), 'LOCKED_TRACK', node)

        if not is_vector:
            extra = SF2_NODES.get(name)
            if not extra and settings.affect_weaponnode:
                extra = SF2_WEAPON_NODES.get(name)
            if extra:
                create_constraint(pose_bones.get(extra[0]), extra[1], node)

        # the "S" nodes are only there to twist a bone, the top of the head has nothing to follow
        if name.endswith(("S_1", "S_2")) or name == "NTop":
            continue

        if is_vector and name in VECTOR_SKIP_NODES:
            continue
        if not is_vector and name in IGNORE_NODES:
            continue

        if name == "NHeadF":
            create_constraint(pose_bones.get("HeadF"), 'DAMPED_TRACK', node)
            continue

        bone_id = bone_name(settings, name)
        bone = pose_bones.get(bone_id) if bone_id else None
        if not bone:
            continue

        # "F" nodes only twist their bone
        if name.endswith("F"):
            create_constraint(bone, 'LOCKED_TRACK', node)
            continue

        if bone_id in PIVOT_FOLLOW_BONES:
            create_constraint(bone, 'COPY_LOCATION', bpy.data.objects.get("NPivot"))
        create_constraint(bone, 'DAMPED_TRACK', bpy.data.objects.get(BODY_CHAIN.get(bone_id, name)))

    # the pelvis Locked Track has to be evaluated last or the pelvis flips
    pelvis = pose_bones.get("Pelvis")
    if pelvis:
        index = pelvis.constraints.find("Locked Track")
        last = len(pelvis.constraints) - 1
        if 0 <= index < last:
            pelvis.constraints.move(index, last)

def armature_bake(node_order, bake_start):
    """Bakes the bones, then hands the nodes over to the bones so they follow the baked pose."""
    scene = bpy.context.scene
    settings = scene.gymnast_tool_props
    armature = require_armature(settings)
    enter_pose_mode(armature)

    bpy.ops.nla.bake(
        frame_start=bake_start, frame_end=scene.frame_end, only_selected=False,
        visual_keying=True, clear_constraints=True, use_current_action=True, bake_types={'POSE'}
    )

    # COM keeps its own animation, and Vector's camera / detectors are not part of the rig
    skipped = {"COM"}
    if settings.armature_rig_type == "VECTOR":
        skipped.update(VECTOR_SKIP_NODES)

    nodes = []
    for name in node_order:
        node = bpy.data.objects.get(name)
        if node and name not in skipped:
            nodes.append(node)

    # the bone now carries the motion, so the imported location keys have to go
    for node in nodes:
        if node.animation_data:
            for frame in range(bake_start, scene.frame_end + 1):
                node.keyframe_delete(data_path="location", frame=frame)

    for node in nodes:
        create_constraint(node, 'CHILD_OF', armature, subtarget=bone_name(settings, node.name))

    if settings.use_armature_ik:
        for bone_id, handle in IK_BONES.items():
            c = create_constraint(armature.pose.bones.get(bone_id), 'IK', armature, subtarget=handle)
            if c:
                c.chain_count = 2

def correct_constraint():
    """Hands and heels sit on the tip of their limb once IK is on."""
    settings = bpy.context.scene.gymnast_tool_props
    armature = require_armature(settings)
    enter_pose_mode(armature)

    for bone_id, limb_id in LIMB_ENDS:
        bone = armature.pose.bones.get(bone_id)
        if not bone:
            continue

        for c in list(bone.constraints):
            if c.type == 'COPY_LOCATION':
                bone.constraints.remove(c)

        c = create_constraint(bone, 'COPY_LOCATION', armature, subtarget=limb_id)
        if c:
            c.name = f"CopyLoc_{limb_id}"
            c.head_tail = 1.0






# ============================================================================ #
#  Export / Import .bin
# ============================================================================ #

def export_bin(filepath, node_order):
    """Writes every node's position for every frame. Returns the nodes that were not found in the scene."""
    scene = bpy.context.scene
    frames = range(scene.frame_start, scene.frame_end + 1)
    original_frame = scene.frame_current

    nodes = [bpy.data.objects.get(name) for name in node_order]
    missing = [name for name, node in zip(node_order, nodes) if not node]
    frame_header = b"\x00" + struct.pack("<i", len(nodes))

    try:
        with open(filepath, 'wb') as file:
            file.write(struct.pack("<i", len(frames)))
            for frame in frames:
                scene.frame_set(frame)

                # a missing node stays at 0, 0, 0
                points = np.zeros((len(nodes), 3), dtype="<f4")
                for i, node in enumerate(nodes):
                    if node:
                        pos = node.matrix_world.translation
                        points[i] = (pos.x, pos.z, -pos.y)

                file.write(frame_header)
                file.write(points.tobytes())
    finally:
        scene.frame_set(original_frame)

    return missing

def read_frames(file, frame_count, skip):
    """Yields an (nodes, 3) array for every frame after the first `skip`. Stops quietly if the file ends early."""
    for _ in range(skip):
        head = file.read(5)
        if len(head) < 5:
            return
        node_count = struct.unpack("<i", head[1:])[0]
        if node_count < 0:
            return
        file.seek(12 * node_count, os.SEEK_CUR)

    for _ in range(max(0, frame_count - skip)):
        head = file.read(5)
        if len(head) < 5:
            return
        node_count = struct.unpack("<i", head[1:])[0]
        if node_count < 0:
            return
        raw = file.read(12 * node_count)
        if len(raw) < 12 * node_count:
            return
        yield np.frombuffer(raw, dtype="<f4").reshape(node_count, 3).astype(np.float64)

def import_bin(filepath, node_order):
    scene = bpy.context.scene
    settings = scene.gymnast_tool_props
    limit = len(node_order)

    if settings.use_armature:
        require_armature(settings)

    # looking the objects up once is a lot faster than doing it for every frame
    nodes = [bpy.data.objects.get(name) for name in node_order]

    with open(filepath, 'rb') as file:
        header = file.read(4)
        if len(header) < 4:
            raise AnimationError("This file is empty, it is not an animation file.")
        frame_count = struct.unpack("<i", header)[0]

        if settings.use_armature:
            setup_armature_follow_node(node_order)

        # ---- pivot (Use Spline / Stay in Place)
        pivot_obj = None
        if settings.use_spline or settings.stay_in_place:
            pivot_obj = bpy.data.objects.get(settings.pivot_node)
        pivot_index = node_order.index(settings.pivot_node) if pivot_obj and settings.pivot_node in node_order else None

        start_frame = scene.frame_start
        stay_anchor = None          # where Stay in Place keeps the pivot
        spline_origin = None        # where Use Spline continues from
        if settings.use_spline and pivot_obj:
            start_frame = scene.frame_current
            here = np.array(pivot_obj.matrix_world.translation, dtype=np.float64)
            if settings.stay_in_place:
                stay_anchor = here
            else:
                spline_origin = here

        spline_offset = np.zeros(3)
        frame_step = (scene.render.fps / 20.0) / settings.animation_speed
        flip = np.array(FLIP_SIGNS[settings.flipped_type]) if settings.flipped_animation else None
        imported = 0

        for index, raw in enumerate(read_frames(file, frame_count, settings.start_frame)):
            # a frame with fewer nodes than the XML gets zeros, extra nodes are dropped
            points = np.zeros((limit, 3))
            used = min(len(raw), limit)
            points[:used] = raw[:used]
            imported += 1

            # .bin (X, Y, Z) -> Blender (x, y, z)
            location = np.column_stack((points[:, 0], -points[:, 2], points[:, 1]))

            stay_offset = np.zeros(3)
            if pivot_index is not None:
                pivot = location[pivot_index]
                if settings.stay_in_place:
                    if stay_anchor is None:
                        stay_anchor = pivot.copy()      # first frame sets the anchor
                    stay_offset = stay_anchor - pivot
                elif settings.use_spline and spline_origin is not None and index == 0:
                    spline_offset = spline_origin - pivot

            location = location + (stay_offset if settings.stay_in_place else spline_offset)
            if flip is not None:
                location = location * flip

            frame = start_frame + (index * frame_step)
            for node, row in zip(nodes, location.tolist()):
                if node:
                    node.location = row
                    node.keyframe_insert(data_path="location", frame=frame)

    if imported > 0:
        scene.frame_end = int(start_frame + (imported - 1) * frame_step)
    scene.frame_set(start_frame)

    if settings.use_armature:
        armature_bake(node_order, start_frame)
        if settings.use_armature_ik:
            correct_constraint()






# ============================================================================ #
#  Quick Export
# ============================================================================ #
#
#  Export Animation needs an XML so it knows the node order. Quick Export makes that XML
#  itself from the model you select, so the XML and the animation file always match

class QuickModel:
    """What a quick export collected: names, first frame positions, topology and the animation."""
    def __init__(self):
        self.node_names = []        # one per vertex, NPivot not included
        self.positions = None       # (nodes, 3) array in .bin space, first frame. NPivot is the last row
        self.edges = []             # (node index, node index)
        self.triangles = []         # (node index, node index, node index)
        self.has_pivot = False
        self.frame_blobs = []       # ready to write bytes, one per frame
        self.moved = False          # stays False when every frame is the same


def clean_xml_name(text):
    """XML tag names cannot hold spaces or odd symbols, and cannot start with a digit."""
    text = re.sub(r"[^A-Za-z0-9_.\-]", "_", text)
    return text if text and (text[0].isalpha() or text[0] == "_") else "_" + text

def get_quick_export_objects(context):
    """Selected meshes, sorted by name so the node order never changes between exports.
    Falls back to the active object when nothing is selected."""
    objs = [o for o in context.selected_objects if o.type == 'MESH']
    if not objs and context.active_object and context.active_object.type == 'MESH':
        objs = [context.active_object]
    return sorted(objs, key=lambda o: o.name)

def model_setting(scene, name, default):
    """Node / edge flags come from Model Tools > Settings, when that part of the suite is installed."""
    settings = getattr(scene, "gymnast_tool_model_props", None)
    return getattr(settings, name, default) if settings else default

def world_positions(obj_eval, mesh):
    """Vertex positions of an evaluated object in world space, as an (n, 3) array."""
    count = len(mesh.vertices)
    co = np.empty(count * 3, dtype=np.float32)
    mesh.vertices.foreach_get("co", co)
    matrix = np.array(obj_eval.matrix_world, dtype=np.float64)
    return co.reshape(count, 3).astype(np.float64) @ matrix[:3, :3].T + matrix[:3, 3]

def to_bin_space(points):
    """Blender (x, y, z) -> .bin (x, z, -y). Same as Export Animation."""
    return np.column_stack((points[:, 0], points[:, 2], -points[:, 1]))

def read_topology(mesh):
    """Edges and triangles of a mesh. Triangulating can add diagonal edges, which the triangles need."""
    bm = bmesh.new()
    try:
        bm.from_mesh(mesh)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
        bm.verts.index_update()
        edges = [(e.verts[0].index, e.verts[1].index) for e in bm.edges]
        triangles = [tuple(v.index for v in f.verts) for f in bm.faces]
    finally:
        bm.free()
    return edges, triangles

def sample_model(context, objects, pivot_obj, prefix, add_pivot, frames, keep_animation):
    """Steps through the frames once. The first one gives the topology, every one gives the node positions."""
    scene = context.scene
    original_frame = scene.frame_current
    model = QuickModel()
    model.has_pivot = add_pivot
    vertex_counts = None

    try:
        for index, frame in enumerate(frames):
            scene.frame_set(frame)
            depsgraph = context.evaluated_depsgraph_get()
            chunks, counts = [], []

            for obj in objects:
                try:
                    obj_eval = obj.evaluated_get(depsgraph)
                    mesh = obj_eval.to_mesh()
                except (RuntimeError, ReferenceError):
                    raise AnimationError(f"'{obj.name}' is not part of the current view layer.")
                try:
                    chunks.append(world_positions(obj_eval, mesh))
                    counts.append(len(mesh.vertices))
                    if index == 0:
                        offset = sum(counts[:-1])
                        edges, triangles = read_topology(mesh)
                        model.edges += [(a + offset, b + offset) for a, b in edges]
                        model.triangles += [tuple(i + offset for i in tri) for tri in triangles]
                finally:
                    obj_eval.to_mesh_clear()

            if index == 0:
                if sum(counts) == 0:
                    raise AnimationError("The selected model has no vertices.")
                vertex_counts = counts
            elif counts != vertex_counts:
                bad = next(o.name for o, new, old in zip(objects, counts, vertex_counts) if new != old)
                raise AnimationError(
                    f"'{bad}' changes its vertex count at frame {frame}. The node order would break. "
                    "Check modifiers that add or remove geometry (Boolean, Decimate, Build...).")

            points = to_bin_space(np.vstack(chunks))
            if add_pivot:
                origin = pivot_obj.evaluated_get(depsgraph).matrix_world.translation
                points = np.vstack((points, [origin.x, origin.z, -origin.y]))

            if index == 0:
                model.positions = points
                model.node_names = [f"{prefix}Node-{i}" for i in range(1, sum(vertex_counts) + 1)]
            elif not model.moved and not np.allclose(points, model.positions, atol=1e-6):
                model.moved = True

            if keep_animation:
                # same layout as Export Animation: skipped byte, node count, then X Y Z for every node
                model.frame_blobs.append(b"\x00" + struct.pack("<i", len(points)) + points.astype("<f4").tobytes())
    finally:
        scene.frame_set(original_frame)

    return model

def build_quick_xml(scene, model, prefix):
    """The <Scene> tree: Nodes, Edges, Figures. Names follow Model Tools (Prefix + Node-1, Edge-1...)."""
    mass = model_setting(scene, "model_node_mass", 1.0)
    fixed = "1" if model_setting(scene, "model_node_fixed", False) else "0"
    node_hit = "1" if model_setting(scene, "model_node_collisible", False) else "0"
    edge_hit = "1" if model_setting(scene, "model_edge_collisible", False) else "0"

    root = ET.Element("Scene")
    nodes_el = ET.SubElement(root, "Nodes")
    edges_el = ET.SubElement(root, "Edges")
    figures_el = ET.SubElement(root, "Figures")

    names = list(model.node_names)
    if model.has_pivot:
        names.append("NPivot")          # always last, same place the .bin keeps it

    for name, pos in zip(names, model.positions):
        ET.SubElement(nodes_el, name, Type="Node", X=str(float(pos[0])), Y=str(float(pos[1])), Z=str(float(pos[2])),
                      Mass=str(mass), Fixed=fixed, PinFixed="0", Visible="1", Passive="0", Cloth="0", Collisible=node_hit)

    for i, (a, b) in enumerate(model.edges, start=1):
        ET.SubElement(edges_el, f"{prefix}Edge-{i}", Type="Edge", Length=str(math.dist(model.positions[a], model.positions[b])),
                      WithSign="0", Fixed="0", Visible="1", Collisible=edge_hit, SubNodesCount="0",
                      End1=names[a], End2=names[b])

    for i, (a, b, c) in enumerate(model.triangles, start=1):
        ET.SubElement(figures_el, f"{prefix}Triangle-{i}", Type="Triangle", Node1=names[a], Node2=names[b], Node3=names[c])

    return root

def write_quick_xml(root, filepath, compact):
    raw = ET.tostring(root, encoding="unicode")
    text = '<?xml version="1.0" ?>\n' + raw if compact else minidom.parseString(raw).toprettyxml(indent="  ")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(text)





# ============================================================================ #
#  Operators
# ============================================================================ #

class AnimationOperator(bpy.types.Operator):
    """Subclasses implement run(); an AnimationError becomes a normal Blender error message."""
    bl_options = {'REGISTER', 'UNDO'}

    def run(self, context):
        raise NotImplementedError

    def execute(self, context):
        try:
            return self.run(context) or {'FINISHED'}
        except AnimationError as err:
            self.report({'ERROR'}, str(err))
            return {'CANCELLED'}
        except OSError as err:
            self.report({'ERROR'}, f"Could not read or write the file: {err}")
            return {'CANCELLED'}


class ExportBinOperator(AnimationOperator):
    bl_idname = "export.bin"
    bl_label = "Export Animation"
    bl_description = "Export the positions of node points in every frame directly to a file"

    filepath: StringProperty(subtype="FILE_PATH")
    filter_glob: StringProperty(default="*.bin;*.bytes", options={'HIDDEN'}, maxlen=255)
    export_format: EnumProperty(name="Format", description="Choose the export file format", items=FORMAT_ITEMS, default='.bin')

    def run(self, context):
        node_order = get_node_order(context.scene.gymnast_tool_props)

        # the extension always follows the dropdown
        base, _ = os.path.splitext(self.filepath)
        missing = export_bin(base + self.export_format, node_order)

        if missing:
            shown = ", ".join(missing[:6]) + (" ..." if len(missing) > 6 else "")
            self.report({'WARNING'}, f"{len(missing)} node(s) not found in the scene, written as 0, 0, 0: {shown}")

    def invoke(self, context, event):
        scene_name = os.path.splitext(bpy.path.basename(context.blend_data.filepath))[0]
        self.filepath = bpy.path.abspath("//") + scene_name
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class ImportBinOperator(AnimationOperator):
    bl_idname = "import.bin"
    bl_label = "Import Animation"
    bl_description = "Import positions of node points directly from a .bin file"

    filepath: StringProperty(subtype="FILE_PATH")
    filter_glob: StringProperty(default="*.bin;*.bytes", options={'HIDDEN'}, maxlen=255)

    def run(self, context):
        import_bin(self.filepath, get_node_order(context.scene.gymnast_tool_props))

    def invoke(self, context, event):
        self.filepath = bpy.path.abspath("//")
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class QuickExportOperator(AnimationOperator):
    bl_idname = "export.quick_model_animation"
    bl_label = "Quick Export Model + Animation"
    bl_description = ("Export the selected model together with its animation.\n"
                      "Node mass, Fixed, Collisible and Optimize XML follow Model Tools > Settings")

    filepath: StringProperty(subtype="FILE_PATH")
    filter_glob: StringProperty(default="*.bin;*.bytes;*.xml", options={'HIDDEN'}, maxlen=255)

    # these four show up in the file browser's side panel
    export_what: EnumProperty(
        name="Export", description="What to write next to each other", default='BOTH',
        items=[('BOTH', "Model + Animation", "Write the XML and the animation file"),
               ('ANIMATION', "Animation Only", "Only write the animation file. Handy when you just tweaked the animation and the model has not changed"),
               ('MODEL', "Model XML Only", "Only write the XML (uses the first frame of the frame range)")])
    export_format: EnumProperty(name="Animation Format", description="Choose the animation file format", items=FORMAT_ITEMS, default='.bin')
    prefix: StringProperty(
        name="Prefix",
        description="Added in front of every Node / Edge / Figure name.\nEx. 'CoolBox-'.\nLeave empty to use the object's name")
    add_pivot: BoolProperty(
        name="Add NPivot",
        description="Add the NPivot node at the object's origin (it follows the object's animation).\nModels placed in the game world need exactly one",
        default=True)

    def run(self, context):
        scene = context.scene

        objects = get_quick_export_objects(context)
        if not objects:
            raise AnimationError("Select the animated model (a mesh object) in the viewport first.")
        pivot_obj = context.active_object if context.active_object in objects else objects[0]

        base, _ = os.path.splitext(self.filepath)
        if not os.path.basename(base):
            raise AnimationError("Choose a file name.")

        want_xml = self.export_what in {'BOTH', 'MODEL'}
        want_bin = self.export_what in {'BOTH', 'ANIMATION'}
        frames = range(scene.frame_start, scene.frame_end + 1) if want_bin else [scene.frame_start]
        if len(frames) == 0:
            raise AnimationError("The frame range is empty. Frame End must not be lower than Frame Start.")

        prefix = clean_xml_name(self.prefix.strip()) if self.prefix.strip() else f"{clean_xml_name(pivot_obj.name)}-"

        # an object in Edit Mode gives out of date meshes, so leave it first
        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        # everything is collected before anything is written, so a failure never leaves half a file behind
        model = sample_model(context, objects, pivot_obj, prefix, self.add_pivot, frames, want_bin)

        written = []
        if want_xml:
            xml_path = base + ".xml"
            write_quick_xml(build_quick_xml(scene, model, prefix), xml_path, model_setting(scene, "model_optimize_xml", False))
            written.append(os.path.basename(xml_path))
        if want_bin:
            bin_path = base + self.export_format
            with open(bin_path, 'wb') as file:
                file.write(struct.pack("<i", len(model.frame_blobs)))
                for blob in model.frame_blobs:
                    file.write(blob)
            written.append(os.path.basename(bin_path))

        node_total = len(model.node_names) + (1 if model.has_pivot else 0)
        self.report({'INFO'}, f"Exported {', '.join(written)}: {node_total} nodes, {len(model.edges)} edges, "
                              f"{len(model.triangles)} triangles, {len(frames) if want_bin else 0} frames")
        if want_bin and not model.moved:
            self.report({'WARNING'}, f"Nothing moves between frame {frames[0]} and {frames[-1]}, so every frame is identical. "
                                     "Did you forget to keyframe the model?")

    def invoke(self, context, event):
        objects = get_quick_export_objects(context)
        name = clean_xml_name(objects[0].name) if objects else "exported_model"
        self.filepath = bpy.path.abspath("//") + name
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}





# ============================================================================ #
#  Settings
# ============================================================================ #

class GymnastToolSettings(bpy.types.PropertyGroup):
    dependencies_xml: StringProperty(name="Dependencies XML", subtype="FILE_PATH")
    model_xml: StringProperty(name="Model XML", subtype="FILE_PATH")
    use_spline: BoolProperty(name="Use Spline", default=False)
    stay_in_place: BoolProperty(name="Stay in Place", default=False)
    pivot_node: StringProperty(name="Pivot Node", default="")
    start_frame: IntProperty(name="Start Frame", default=0, min=0)
    use_armature: BoolProperty(name="Use Armature", default=False)
    use_armature_ik: BoolProperty(name="Use IK", default=False)
    armature_object: PointerProperty(name="Armature", type=bpy.types.Object, poll=lambda self, obj: obj.type == 'ARMATURE')
    armature_rig_type: EnumProperty(
        name="Game", default='VECTOR',
        items=[('VECTOR', "Vector", ""), ('SHADOW FIGHT 2', "Shadow Fight 2", "")])
    affect_weaponnode: BoolProperty(name="Affect WeaponNode", default=False)
    flipped_animation: BoolProperty(name="Mirrored", default=False)
    flipped_type: EnumProperty(name="Axis", items=[('X', "X", ""), ('Y', "Y", ""), ('Z', "Z", "")], default='Z')
    animation_speed: FloatProperty(name="Animation Speed", description="Playback speed factor.", default=1.0, min=0.01)





# ============================================================================ #
#  UI
# ============================================================================ #

class VIEW3D_PT_gymnast_animation_panel(bpy.types.Panel):
    bl_label = "Animation Tools"
    bl_idname = "VIEW3D_PT_gymnast_animation_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = CATEGORY
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout, settings = self.layout, context.scene.gymnast_tool_props
        layout.prop(settings, "dependencies_xml")
        layout.prop(settings, "model_xml")

        box = layout.box()
        box.label(text="Animation Options", icon='ARMATURE_DATA')
        box.operator(ImportBinOperator.bl_idname, text="Import Animation")
        box.operator(ExportBinOperator.bl_idname, text="Export Animation")

        box = layout.box()
        box.label(text="Quick Export", icon='EXPORT')
        objects = get_quick_export_objects(context)
        col = box.column(align=True)
        if objects:
            shown = objects[0].name if len(objects) == 1 else f"{len(objects)} objects"
            col.label(text=f"Selected: {shown}", icon='OBJECT_DATA')
        else:
            col.label(text="Select your animated model first", icon='INFO')
        row = box.row()
        row.enabled = bool(objects)
        row.operator(QuickExportOperator.bl_idname, text="Export Model + Animation")


class VIEW3D_PT_gymnast_animation_settings(bpy.types.Panel):
    bl_label = "Settings"
    bl_idname = "VIEW3D_PT_gymnast_animation_settings"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = CATEGORY
    bl_parent_id = "VIEW3D_PT_gymnast_animation_panel"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        pass


class VIEW3D_PT_gymnast_animation_settings_import(bpy.types.Panel):
    bl_label = "Import Settings"
    bl_idname = "VIEW3D_PT_gymnast_animation_settings_import"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = CATEGORY
    bl_parent_id = "VIEW3D_PT_gymnast_animation_settings"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        props, layout = context.scene.gymnast_tool_props, self.layout

        box = layout.box()
        box.label(text="Import Settings")
        box.prop(props, "flipped_animation")
        if props.flipped_animation:
            box.prop(props, "flipped_type")
        box.prop(props, "animation_speed")

        box = layout.box()
        box.label(text="Armature")
        box.prop(props, "use_armature")
        if props.use_armature:
            box.prop(props, "use_armature_ik")
            if props.armature_rig_type == "SHADOW FIGHT 2":
                box.prop(props, "affect_weaponnode")
            box.prop(props, "armature_object")
            box.prop(props, "armature_rig_type")

        box = layout.box()
        box.label(text="Splining & Positioning")
        box.prop(props, "use_spline")
        box.prop(props, "stay_in_place")
        if props.use_spline or props.stay_in_place:
            box.prop(props, "pivot_node")
        if props.use_spline:
            box.prop(props, "start_frame")






# ============================================================================ #
#  Registration
# ============================================================================ #

classes = (
    GymnastToolSettings,
    ImportBinOperator,
    ExportBinOperator,
    QuickExportOperator,
    VIEW3D_PT_gymnast_animation_panel,
    VIEW3D_PT_gymnast_animation_settings,
    VIEW3D_PT_gymnast_animation_settings_import,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.gymnast_tool_props = PointerProperty(type=GymnastToolSettings)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.gymnast_tool_props


if __name__ == "__main__":
    register()