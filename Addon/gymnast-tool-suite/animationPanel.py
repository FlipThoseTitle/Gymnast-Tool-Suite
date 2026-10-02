# #################### #
# Animation Panel
# #################### #

import bpy
import os
import struct
import xml.etree.ElementTree as ET

# ------------- Constants & Node Mappings -------------

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

IGNORE_NODES = [
    f"MacroNode{i}_{j}" for i in range(1, 7) for j in (1, 2)
] + [
    f"Weapon-Node{i}_{j}" for i in range(1, 5) for j in (1, 2)
]

# ------------- Helper Functions -------------

def create_constraint(bone, c_type, target_obj, subtarget="", track_axis="", lock_axis=""):
    """Helper function to create and setup a bone constraint."""
    if not bone or not target_obj:
        return None
    
    c = bone.constraints.new(type=c_type)
    c.target = target_obj
    if subtarget: c.subtarget = subtarget
    if track_axis: c.track_axis = track_axis
    if lock_axis: c.lock_axis = lock_axis
    return c

def parse_nodes_from_xml(filepath):
    if not filepath or not os.path.exists(filepath):
        return []
    
    tree = ET.parse(filepath)
    root = tree.getroot()
    nodes_section = root.find("Nodes")
    return [node.tag for node in nodes_section] if nodes_section is not None else []

def get_combined_node_order(dependencies_xml, model_xml):
    """Parses and merges nodes from both XMLs with check for duplicate"""
    node_order = parse_nodes_from_xml(dependencies_xml)
    model_nodes = parse_nodes_from_xml(model_xml)
    
    duplicate_nodes = set(node_order) & set(model_nodes)
    if duplicate_nodes:
        raise ValueError(f"Duplicate nodes found in both XML files: {', '.join(duplicate_nodes)}")

    node_order.extend(model_nodes)
    if not node_order:
        raise ValueError("At least one XML file must contain nodes.")
    
    return node_order

# ------------- Core Logic -------------

def setup_armature_follow_node(dependencies_xml="", model_xml=""):
    settings = bpy.context.scene.gymnast_tool_props
    armature = settings.armature_object
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='POSE')
    
    node_order = get_combined_node_order(dependencies_xml, model_xml)
    
    # Bone
    ik_map = {
        "NWrist_1": "HandIK_1", "NWrist_2": "HandIK_2", 
        "NAnkle_1": "HeelIK_1", "NAnkle_2": "HeelIK_2",
        "COM": "COM", "NPivot": "Root"
    }
    
    locked_track_map = {
        "NToeS_1": "Foot_1", "NToeS_2": "Foot_2", "NHeadS_2": "Head",
        "NKnucklesS_1": "Hand_1", "NKnucklesS_2": "Hand_2"
    }

    damped_track_hierarchy = {
        "Pelvis": "NStomach", "Stomach": "NChest", "Chest": "NNeck",
        "Neck": "NHead", "Head": "NTop"
    }
    
    for name in node_order:
        node = bpy.data.objects.get(name)
        if not node: continue
            
        # Clear child_of constraints
        for c in list(node.constraints):
            if c.type == 'CHILD_OF':
                node.constraints.remove(c)

        if settings.use_armature_ik and name in ik_map:
            create_constraint(armature.pose.bones.get(ik_map[name]), 'COPY_LOCATION', node)

        if name in locked_track_map:
            create_constraint(armature.pose.bones.get(locked_track_map[name]), 'LOCKED_TRACK', node, track_axis='TRACK_Z', lock_axis='LOCK_Y')

        # Shadow Fight 2
        if settings.armature_rig_type == "SHADOW FIGHT 2":
            sf2_damped = {"NFingertipsSS_2": "FingersS_2", "NFingertipsSS_1": "FingersS_1"}
            sf2_locked = {"NFingertipsS_1": "Fingers_1", "NFingertipsS_2": "Fingers_2", "MacroNode5_1": "FingersS_1", "MacroNode5_2": "FingersS_2"}
            
            if name in sf2_damped:
                create_constraint(armature.pose.bones.get(sf2_damped[name]), 'DAMPED_TRACK', node)
            if name in sf2_locked:
                create_constraint(armature.pose.bones.get(sf2_locked[name]), 'LOCKED_TRACK', node, track_axis='TRACK_Z', lock_axis='LOCK_Y')
            
            if settings.affect_weaponnode:
                weap_bones = {"1": "Weapon_1", "2": "Weapon_2"}
                for suffix, bone_name in weap_bones.items():
                    bone = armature.pose.bones.get(bone_name)
                    if name == f"Weapon-Node2_{suffix}":
                        create_constraint(bone, 'COPY_LOCATION', node)
                    elif name == f"Weapon-Node3_{suffix}":
                        create_constraint(bone, 'DAMPED_TRACK', node)
                    elif name == f"Weapon-Node4_{suffix}":
                        create_constraint(bone, 'LOCKED_TRACK', node, track_axis='TRACK_Z', lock_axis='LOCK_Y')
            
        if name.endswith(("S_1", "S_2")) or name == "NTop":
            continue
            
        if settings.armature_rig_type == "VECTOR" and name in ("Camera", "DetectorH", "DetectorV"):
            continue
        elif settings.armature_rig_type != "VECTOR" and name in IGNORE_NODES:
            continue
        
        if name == "NHeadF":
            create_constraint(armature.pose.bones.get("HeadF"), 'DAMPED_TRACK', node)
            continue
            
        is_fbone = name.endswith("F")
        bone_id = NODE_TO_BONE_VECTOR.get(name) if settings.armature_rig_type == "VECTOR" else NODE_TO_BONE_SF2.get(name)
        bone = armature.pose.bones.get(bone_id) if bone_id else None
        
        if bone:
            if is_fbone:
                create_constraint(bone, 'LOCKED_TRACK', node, track_axis='TRACK_Z', lock_axis='LOCK_Y')
                continue
            
            if bone_id in ("Pelvis", "Hip_1", "Hip_2"):         
                create_constraint(bone, 'COPY_LOCATION', bpy.data.objects.get("NPivot"))
                
            target_obj = bpy.data.objects.get(damped_track_hierarchy.get(bone_id, name))
            create_constraint(bone, 'DAMPED_TRACK', target_obj)
                
    # Fix NPivot LockedTrack constraint
    pivotbone = armature.pose.bones.get("Pelvis")
    if pivotbone: 
        index = pivotbone.constraints.find("Locked Track")
        if index != -1: 
            last_index = len(pivotbone.constraints) - 1
            while index < last_index:
                pivotbone.constraints.move(index, index + 1)
                index += 1

def armature_bake(dependencies_xml="", model_xml="", bake_start=None):
    settings = bpy.context.scene.gymnast_tool_props
    scene = bpy.context.scene
    armature = settings.armature_object
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='POSE')
    
    node_order = get_combined_node_order(dependencies_xml, model_xml)
    bake_start = bake_start if bake_start is not None else scene.frame_start
    
    bpy.ops.nla.bake(
        frame_start=bake_start, frame_end=scene.frame_end, only_selected=False,
        visual_keying=True, clear_constraints=True, use_current_action=True, bake_types={'POSE'}
    )
    
    # after baking, we need to reapply the constraints for the next frames to work properly, but we should ignore certain nodes that are not meant to be constrained or baked.
    ignore_bake_nodes = {"COM"}
    if settings.armature_rig_type == "VECTOR":
        ignore_bake_nodes.update({"DetectorH", "DetectorV", "Camera"})

    for frame in range(bake_start, scene.frame_end + 1):
        for name in node_order:
            if name in ignore_bake_nodes: continue
            node = bpy.data.objects.get(name)
            if node: node.keyframe_delete(data_path="location", frame=frame)
    
    for name in node_order:
        if name in ignore_bake_nodes: continue
        node = bpy.data.objects.get(name)
        if not node: continue
        
        bone_id = NODE_TO_BONE_VECTOR.get(name) if settings.armature_rig_type == "VECTOR" else NODE_TO_BONE_SF2.get(name)
        create_constraint(node, 'CHILD_OF', armature, subtarget=bone_id)
        
    if settings.use_armature_ik:
        ik_targets = {"Calf_1": "HeelIK_1", "Calf_2": "HeelIK_2", "Forearm_1": "HandIK_1", "Forearm_2": "HandIK_2"}
        for bone_name, subtarget in ik_targets.items():
            bone = armature.pose.bones.get(bone_name)
            if bone:
                c = create_constraint(bone, 'IK', armature, subtarget=subtarget)
                if c: c.chain_count = 2

def correct_constraint():
    armature = bpy.context.scene.gymnast_tool_props.armature_object
    if not armature or armature.type != 'ARMATURE': return

    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='POSE')

    pairs = [("Hand_1", "Forearm_1"), ("Hand_2", "Forearm_2"), ("Heel_1", "Calf_1"), ("Heel_2", "Calf_2")]

    for bone_name, target_bone_name in pairs:
        pbone = armature.pose.bones.get(bone_name)
        if not pbone: continue

        for c in list(pbone.constraints):
            if c.type == 'COPY_LOCATION':
                pbone.constraints.remove(c)

        c = create_constraint(pbone, 'COPY_LOCATION', armature, subtarget=target_bone_name)
        if c: 
            c.name = f"CopyLoc_{target_bone_name}"
            c.head_tail = 1.0 

def export_bin(filepath, dependencies_xml, model_xml):
    nodepoint_order = get_combined_node_order(dependencies_xml, model_xml)
    limit = len(nodepoint_order)
    scene = bpy.context.scene

    frames = range(scene.frame_start, scene.frame_end + 1)
    frame_count = len(frames)

    with open(filepath, 'wb') as file:
        # Write binary blocks count (frameCount)
        file.write(struct.pack("i", frame_count))

        for frame in frames:
            scene.frame_set(frame)
            
            # Write padding byte (skip) and node count
            file.write(struct.pack("B", 0))
            file.write(struct.pack("i", limit))
            
            for name in nodepoint_order:
                obj = bpy.data.objects.get(name)
                if obj:
                    pos = obj.matrix_world.translation
                    file.write(struct.pack("fff", pos.x, pos.z, -pos.y))
                else:
                    file.write(struct.pack("fff", 0.0, 0.0, 0.0))

def import_bin(filepath, dependencies_xml="", model_xml=""):
    settings = bpy.context.scene.gymnast_tool_props
    if settings.use_armature: setup_armature_follow_node(dependencies_xml, model_xml)
    
    node_order = get_combined_node_order(dependencies_xml, model_xml)
    limit = len(node_order)
    
    # Read the block count early to set frame limits
    with open(filepath, 'rb') as file:
        try:
            binary_blocks_count = struct.unpack("i", file.read(4))[0]
        except struct.error:
            return {'CANCELLED'}
            
    scene = bpy.context.scene
    pivot_node_obj = bpy.data.objects.get(settings.pivot_node) if (settings.use_spline or settings.stay_in_place) else None
    
    last_pivot_pos = None
    stay_target_pos = None
    new_start_frame = scene.frame_start

    if settings.use_spline and pivot_node_obj:
        new_start_frame = scene.frame_current
        if settings.stay_in_place:
            stay_target_pos = pivot_node_obj.matrix_world.translation.copy()
        else:
            last_pivot_pos = pivot_node_obj.matrix_world.translation.copy()
    
    pivot_offset = (0, 0, 0)
    frames_to_import = max(0, binary_blocks_count - settings.start_frame)
    actual_frames_imported = 0
    fps_ratio = scene.render.fps / 20.0
    frame_step = fps_ratio / settings.animation_speed

    # We find all objects before the loop starts to avoid querying 
    # Blender database thousands of times per second
    cached_objects = [bpy.data.objects.get(name) for name in node_order[:limit]]

    with open(filepath, 'rb') as file:
        file.read(4) 
        
        # Fast forward through frames that are before settings.start_frame
        for _ in range(settings.start_frame):
            try:
                file.read(1) # Skip byte
                node_count = struct.unpack("i", file.read(4))[0]
                file.read(12 * node_count) # Skip 12 bytes per node (3 floats)
            except struct.error:
                break

        # Removed frame from the loop iterable because frame counts are dynamic now
        for file_frame_idx in range(frames_to_import):
            try:
                skip_byte = file.read(1)
                if not skip_byte: break
                node_count = struct.unpack("i", file.read(4))[0]
                
                raw_data = file.read(12 * node_count)
                if len(raw_data) < 12 * node_count:
                    break
                    
                positions_flat = struct.unpack(f"{node_count * 3}f", raw_data)
                positions = [positions_flat[i*3 : i*3+3] for i in range(node_count)]
                
            except struct.error:
                break
                
            target_frame = new_start_frame + (actual_frames_imported * frame_step)
            actual_frames_imported += 1
            
            # Pad empty nodes if the node count in the frame is less than expected limits
            if len(positions) < limit:
                positions.extend([(0.0, 0.0, 0.0)] * (limit - len(positions)))

            offset = (0,0,0)
            if (settings.use_spline or settings.stay_in_place) and pivot_node_obj and settings.pivot_node in node_order:
                p_idx = node_order.index(settings.pivot_node)
                # Remap the target position back from bin coordinates
                p_new_pos = (positions[p_idx][0], -positions[p_idx][2], positions[p_idx][1])
                
                if settings.stay_in_place:
                    if stay_target_pos is None:
                        # Captures the pivot's position on the first frame as the anchor
                        stay_target_pos = p_new_pos
                    offset = (stay_target_pos[0] - p_new_pos[0], stay_target_pos[1] - p_new_pos[1], stay_target_pos[2] - p_new_pos[2])
                elif settings.use_spline and last_pivot_pos and actual_frames_imported == 1:
                    pivot_offset = (last_pivot_pos[0] - p_new_pos[0], last_pivot_pos[1] - p_new_pos[1], last_pivot_pos[2] - p_new_pos[2])
            
            active_offset = offset if settings.stay_in_place else pivot_offset

            # Loop directly through our prefetched objects
            for i, obj in enumerate(cached_objects):
                if obj:
                    x = positions[i][0] + active_offset[0]
                    z = positions[i][1] + active_offset[2]
                    y = -positions[i][2] + active_offset[1]
                    
                    # Update location reliably so the dependency graph catches it
                    if settings.flipped_animation:
                        if settings.flipped_type == 'X': obj.location = (-x, y, z)
                        elif settings.flipped_type == 'Y': obj.location = (x, y, -z)
                        elif settings.flipped_type == 'Z': obj.location = (x, -y, z)
                    else:
                        obj.location = (x, y, z)
                        
                    obj.keyframe_insert(data_path="location", frame=target_frame)
    
    if actual_frames_imported > 0:
        # Scale end-frame properly
        scene.frame_end = int(new_start_frame + (actual_frames_imported - 1) * frame_step)
        
    scene.frame_set(new_start_frame)
    
    if settings.use_armature:
        armature_bake(dependencies_xml, model_xml, bake_start=new_start_frame)
        if settings.use_armature_ik: correct_constraint()

# ------------- Operators -------------

class ExportBinOperator(bpy.types.Operator):
    bl_idname = "export.bin"
    bl_label = "Export Animation"
    bl_description = "Export the positions of node points in every frame directly to a file"
    
    bl_options = {'REGISTER', 'UNDO'}
    
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    
    filter_glob: bpy.props.StringProperty(
        default="*.bin;*.bytes",
        options={'HIDDEN'},
        maxlen=255,
    )

    # include dropdown to the export window sidebar
    export_format: bpy.props.EnumProperty(
        name="Format",
        description="Choose the export file format",
        items=[
            ('.bin', ".bin", "Export as a .bin file"),
            ('.bytes', ".bytes", "Export as a .bytes file")
        ],
        default='.bin'
    )

    def execute(self, context):
        settings = context.scene.gymnast_tool_props
        deps_xml = bpy.path.abspath(settings.dependencies_xml) if settings.dependencies_xml else None
        mod_xml = bpy.path.abspath(settings.model_xml) if settings.model_xml else None
    
        # force an extension based on the dropdown.
        base_path, _ = os.path.splitext(self.filepath)
        final_filepath = base_path + self.export_format
        
        try:
            export_bin(final_filepath, deps_xml, mod_xml)
        except ValueError as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}
        
        return {'FINISHED'}

    def invoke(self, context, event):
        scene_name = os.path.splitext(bpy.path.basename(context.blend_data.filepath))[0]
        self.filepath = bpy.path.abspath("//") + scene_name
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    
class ImportBinOperator(bpy.types.Operator):
    bl_idname = "import.bin"
    bl_label = "Import Animation"
    bl_description = "Import positions of node points directly from a .bin file"
    
    bl_options = {'REGISTER', 'UNDO'}
    
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    
    filter_glob: bpy.props.StringProperty(
        default="*.bin;*.bytes",
        options={'HIDDEN'},
        maxlen=255,
    )

    def execute(self, context):
        settings = context.scene.gymnast_tool_props
        deps_xml = bpy.path.abspath(settings.dependencies_xml) if settings.dependencies_xml else None
        mod_xml = bpy.path.abspath(settings.model_xml) if settings.model_xml else None
            
        try:
            import_bin(self.filepath, deps_xml, mod_xml)
        except ValueError as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}
        
        return {'FINISHED'}

    def invoke(self, context, event):
        self.filepath = bpy.path.abspath("//")
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

# ------------- Settings & UI Panels -------------

class GymnastToolSettings(bpy.types.PropertyGroup):
    dependencies_xml: bpy.props.StringProperty(name="Dependencies XML", subtype="FILE_PATH")
    model_xml: bpy.props.StringProperty(name="Model XML", subtype="FILE_PATH")
    use_spline: bpy.props.BoolProperty(name="Use Spline", default=False)
    stay_in_place: bpy.props.BoolProperty(name="Stay in Place", default=False)
    pivot_node: bpy.props.StringProperty(name="Pivot Node", default="")
    start_frame: bpy.props.IntProperty(name="Start Frame", default=0, min=0)
    use_armature: bpy.props.BoolProperty(name="Use Armature", default=False)
    use_armature_ik: bpy.props.BoolProperty(name="Use IK", default=False)
    armature_object: bpy.props.PointerProperty(name="Armature", type=bpy.types.Object, poll=lambda s, o: o.type == 'ARMATURE')
    armature_rig_type: bpy.props.EnumProperty(
        name="Type",
        items=[('VECTOR', "Vector", ""), ('SHADOW FIGHT 2', "Shadow Fight 2", "")],
        default='VECTOR',
    )
    affect_weaponnode: bpy.props.BoolProperty(name="Affect WeaponNode", default=False)
    flipped_animation: bpy.props.BoolProperty(name="Mirrored", default=False)
    flipped_type: bpy.props.EnumProperty(
        name="Axis", items=[('X', "X", ""), ('Y', "Y", ""), ('Z', "Z", "")], default='Z',
    )
    animation_speed: bpy.props.FloatProperty(
        name="Animation Speed", 
        description="Playback speed factor.", 
        default=1.0, 
        min=0.01
    )

class VIEW3D_PT_gymnast_animation_panel(bpy.types.Panel):
    bl_label, bl_idname, bl_space_type, bl_region_type, bl_category = "Animation Tools", "VIEW3D_PT_gymnast_animation_panel", 'VIEW_3D', 'UI', 'Gymnast Tool Suite'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout, settings = self.layout, context.scene.gymnast_tool_props
        layout.prop(settings, "dependencies_xml")
        layout.prop(settings, "model_xml")
        box = layout.box()
        box.label(text="Animation Options", icon='ARMATURE_DATA')
        box.operator(ImportBinOperator.bl_idname, text="Import Animation")
        box.operator(ExportBinOperator.bl_idname, text="Export Animation")
        
class VIEW3D_PT_gymnast_animation_settings(bpy.types.Panel):
    bl_label, bl_idname, bl_space_type, bl_region_type, bl_category, bl_parent_id = "Settings", "VIEW3D_PT_gymnast_animation_settings", 'VIEW_3D', 'UI', 'Gymnast Tool Suite', "VIEW3D_PT_gymnast_animation_panel"
    bl_options = {'DEFAULT_CLOSED'}
    def draw(self, context): pass

class VIEW3D_PT_gymnast_animation_settings_import(bpy.types.Panel):
    bl_label, bl_idname, bl_space_type, bl_region_type, bl_category, bl_parent_id = "Import Settings", "VIEW3D_PT_gymnast_animation_settings_import", 'VIEW_3D', 'UI', 'Gymnast Tool Suite', "VIEW3D_PT_gymnast_animation_settings"
    bl_options = {'DEFAULT_CLOSED'}
    def draw(self, context):
        props = context.scene.gymnast_tool_props
        box3, box2, box = self.layout.box(), self.layout.box(), self.layout.box()
        
        box3.label(text="Import Settings")
        box3.prop(props, "flipped_animation")
        if props.flipped_animation: box3.prop(props, "flipped_type")
        box3.prop(props, "animation_speed")
        
        box2.label(text="Armature")
        box2.prop(props, "use_armature")
        if props.use_armature:
            box2.prop(props, "use_armature_ik")
            if props.armature_rig_type == "SHADOW FIGHT 2": box2.prop(props, "affect_weaponnode")
            box2.prop(props, "armature_object")
            box2.prop(props, "armature_rig_type")
        
        box.label(text="Splining & Positioning")
        box.prop(props, "use_spline")
        box.prop(props, "stay_in_place")
        
        if props.use_spline or props.stay_in_place:
            box.prop(props, "pivot_node")
            
        if props.use_spline:
            box.prop(props, "start_frame")

# ------------- Registration -------------

classes = [
    ImportBinOperator, ExportBinOperator,
    GymnastToolSettings, VIEW3D_PT_gymnast_animation_panel, VIEW3D_PT_gymnast_animation_settings,
    VIEW3D_PT_gymnast_animation_settings_import
]

def register():
    for cls in classes: bpy.utils.register_class(cls)
    bpy.types.Scene.gymnast_tool_props = bpy.props.PointerProperty(type=GymnastToolSettings)

def unregister():
    for cls in reversed(classes): bpy.utils.unregister_class(cls)
    del bpy.types.Scene.gymnast_tool_props

if __name__ == "__main__":
    register()