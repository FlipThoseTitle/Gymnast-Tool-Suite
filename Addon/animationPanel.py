# #################### #
# Animation Panel
# #################### #


import bpy
import os
import mathutils
import shutil
import struct
import xml.etree.ElementTree as ET

# Node to Bone
NODE_TO_BONE_VECTOR = {
    "NTop": "Head",
    "NHead": "Head",
    "NHeadF": "HeadF",
    "NHeadS_2": "HeadF",
    "NHeadS_1": "HeadF",
    "NNeck": "Neck",
    "NShoulder_2": "Clavicle_2",
    "NShoulder_1": "Clavicle_1",
    "NElbow_2": "Arm_2",
    "NElbow_1": "Arm_1",
    "NWrist_2": "Forearm_2",
    "NWrist_1": "Forearm_1",
    "NKnuckles_2": "Hand_2",
    "NKnuckles_1": "Hand_1",
    "NKnucklesS_2": "Hand_2",
    "NKnucklesS_1": "Hand_1",
    "NFingertips_2": "Fingers_2",
    "NFingertips_1": "Fingers_1",
    "NChest": "Chest",
    "NChestF": "Chest",
    "NChestS_2": "Chest",
    "NChestS_1": "Chest",
    "NStomach": "Stomach",
    "NStomachF": "Stomach",
    "NStomachS_2": "Stomach",
    "NStomachS_1": "Stomach",
    "NPivot": "Pelvis",
    "NPelvisF": "Pelvis",
    "NHip_2": "Hip_2",
    "NHip_1": "Hip_1",
    "NKnee_2": "Thigh_2",
    "NKnee_1": "Thigh_1",
    "NAnkle_2": "Calf_2",
    "NAnkle_1": "Calf_1",
    "NHeel_2": "Heel_2",
    "NHeel_1": "Heel_1",
    "NToe_2": "Foot_2",
    "NToe_1": "Foot_1",
    "NToeS_2": "Foot_2",
    "NToeS_1": "Foot_1",
    "NToeTip_2": "Toes_2",
    "NToeTip_1": "Toes_1",
    "COM": "COM"
}

NODE_TO_BONE_SF2 = {
    "NTop": "Head",
    "NHead": "Head",
    "NHeadF": "HeadF",
    "NHeadS_2": "HeadF",
    "NHeadS_1": "HeadF",
    "NNeck": "Neck",
    "NShoulder_2": "Clavicle_2",
    "NShoulder_1": "Clavicle_1",
    "NElbow_2": "Arm_2",
    "NElbow_1": "Arm_1",
    "NWrist_2": "Forearm_2",
    "NWrist_1": "Forearm_1",
    "NKnuckles_2": "Hand_2",
    "NKnuckles_1": "Hand_1",
    "NKnucklesS_2": "Hand_2",
    "NKnucklesS_1": "Hand_1",
    "NFingertips_2": "Fingers_2",
    "NFingertips_1": "Fingers_1",
    "NFingertipsS_2": "Fingers_2",
    "NFingertipsS_1": "Fingers_1",
    "NFingertipsSS_2": "FingersS_2",
    "NFingertipsSS_1": "FingersS_1",
    "NChest": "Chest",
    "NChestF": "Chest",
    "NChestS_2": "Chest",
    "NChestS_1": "Chest",
    "NStomach": "Stomach",
    "NStomachF": "Stomach",
    "NStomachS_2": "Stomach",
    "NStomachS_1": "Stomach",
    "NPivot": "Pelvis",
    "NPelvisF": "Pelvis",
    "NHip_2": "Hip_2",
    "NHip_1": "Hip_1",
    "NKnee_2": "Thigh_2",
    "NKnee_1": "Thigh_1",
    "NAnkle_2": "Calf_2",
    "NAnkle_1": "Calf_1",
    "NHeel_2": "Heel_2",
    "NHeel_1": "Heel_1",
    "NToe_2": "Foot_2",
    "NToe_1": "Foot_1",
    "NToeS_2": "Foot_2",
    "NToeS_1": "Foot_1",
    "NToeTip_2": "Toes_2",
    "NToeTip_1": "Toes_1",
    "COM": "COM",
    "MacroNode1_1": "Hand_1",
    "MacroNode1_2": "Hand_2",
    "MacroNode2_1": "Hand_1",
    "MacroNode2_2": "Hand_2",
    "MacroNode3_1": "Hand_1",
    "MacroNode3_2": "Hand_2",
    "MacroNode4_1": "Fingers_1",
    "MacroNode4_2": "Fingers_2",
    "MacroNode5_1": "FingersS_1",
    "MacroNode5_2": "FingersS_2",
    "MacroNode6_1": "FingersS_1",
    "MacroNode6_2": "FingersS_2",
    "Weapon-Node1_1": "Weapon_1",
    "Weapon-Node2_1": "Weapon_1",
    "Weapon-Node3_1": "Weapon_1",
    "Weapon-Node4_1": "Weapon_1",
    "Weapon-Node1_2": "Weapon_2",
    "Weapon-Node2_2": "Weapon_2",
    "Weapon-Node3_2": "Weapon_2",
    "Weapon-Node4_2": "Weapon_2"
}


# Xml
def parse_nodes_from_xml(filepath):
    if not filepath or not os.path.exists(filepath):
        return []
    
    tree = ET.parse(filepath)
    root = tree.getroot()

    nodes = []
    nodes_section = root.find("Nodes")
    if nodes_section is not None:
        for node in nodes_section:
            nodes.append(node.tag)  # Node name is the tag

    return nodes

def get_node_order_from_xml(dependencies_xml, model_xml):
    node_order = []
    seen_nodes = set()  # To track duplicate names

    def extract_nodes(xml_path):
        if not xml_path:
            return  # Skip if no file is provided
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            nodes_section = root.find("Nodes")
            if nodes_section is not None:
                for node in nodes_section:
                    node_name = node.tag  # Node name is the tag
                    if node_name in seen_nodes:
                        raise ValueError(f"Duplicate node found in both XMLs: {node_name}")
                    seen_nodes.add(node_name)
                    node_order.append(node_name)
        except ET.ParseError as e:
            raise ValueError(f"Failed to parse XML file: {xml_path}\nError: {str(e)}")

    extract_nodes(dependencies_xml)
    extract_nodes(model_xml)

    if not node_order:
        raise ValueError("No valid nodes found in the provided XML files.")

    return node_order


# Decompile .bin Animation into a temporary .bindec
def decompile_bin(filepath):
    bindec_path = filepath.replace(".bin", ".bindec")

    with open(filepath, "rb") as file:
        block_count = struct.unpack("i", file.read(4))[0]
        
        lines = [f"Binary blocks count: {block_count}"]

        for _ in range(block_count):
            file.read(1)  # Skip a byte
            set_count = struct.unpack("i", file.read(4))[0]
            frame_data = [f"[{set_count}]"]

            for _ in range(set_count):
                x, y, z = struct.unpack("fff", file.read(12))
                frame_data.append(f"{{{x},{y},{z}}}")

            lines.append("".join(frame_data) + "END")

    with open(bindec_path, "w") as output_file:
        output_file.write("\n".join(lines))

    return bindec_path

# Compile animation into .bin file
def compile_bin(filepath):
    bin_path = filepath.replace(".bindec", ".bin")

    with open(filepath, "r") as file:
        lines = file.readlines()

    if not lines[0].startswith("Binary blocks count:"):
        return

    block_count = int(lines[0].split(":")[1].strip())

    with open(bin_path, "wb") as file:
        file.write(struct.pack("i", block_count))  # Write block count

        for line in lines[1:]:
            line = line.strip()
            if line == "END":  # Ignore standalone "END" lines
                continue
            if not line.startswith("[") or "{" not in line:
                continue

            try:
                # Extract set count inside "[...]"
                set_count = int(line[line.index("[")+1:line.index("]")])

                # Extract positions
                positions_str = line[line.index("{") + 1:line.rindex("}")].split("}{")
                positions = [list(map(float, p.split(","))) for p in positions_str]

                file.write(struct.pack("B", 0))  # Write byte 0
                file.write(struct.pack("i", set_count))  # Write number of positions

                for pos in positions:
                    file.write(struct.pack("fff", pos[0], pos[1], pos[2]))  

            except ValueError:
                print(f"Error processing line: {line}")

    
    # Remove the .bindec file after compilation
    try:
        os.remove(filepath)
    except OSError as e:
        print(f"Error deleting {filepath}: {e}")


# Set-up Armature to follow Node Point
def setup_armature_follow_node(dependencies_xml="", model_xml=""):
    settings = bpy.context.scene.gymnast_tool_props
    armature = settings.armature_object
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='POSE')
    fbone = False
    
    # Generate node order from XML files
    node_order = parse_nodes_from_xml(dependencies_xml)
    model_nodes = parse_nodes_from_xml(model_xml)
    
    # Check for duplicate nodes
    duplicate_nodes = set(node_order) & set(model_nodes)
    if duplicate_nodes:
       raise ValueError(f"Duplicate nodes found in both XML files: {', '.join(duplicate_nodes)}")

    node_order.extend(model_nodes)  # Merge both lists
    if not node_order:
        raise ValueError("At least one XML file must contain nodes.")

    limit = len(node_order)  # Use node count as limit
    
    IgnoreList = [
        "MacroNode1_1",
        "MacroNode1_2",
        "MacroNode2_1",
        "MacroNode2_2",
        "MacroNode3_1",
        "MacroNode3_2",
        "MacroNode4_1",
        "MacroNode4_2",
        "MacroNode5_1",
        "MacroNode5_2",
        "MacroNode6_1",
        "MacroNode6_2",
        "Weapon-Node1_1",
        "Weapon-Node2_1",
        "Weapon-Node3_1",
        "Weapon-Node4_1",
        "Weapon-Node1_2",
        "Weapon-Node2_2",
        "Weapon-Node3_2",
        "Weapon-Node4_2"
    ]
    
    for i, name in enumerate(node_order[:limit]):
        node = bpy.data.objects.get(name)
        if node:
            for constraint in node.constraints:
                if constraint.type == 'CHILD_OF':
                    node.constraints.remove(constraint)
                    
        node_name = name
        
        if settings.use_armature_ik:
            if node_name == "NWrist_1":
                bone = armature.pose.bones.get("HandIK_1")
                constraint = bone.constraints.new(type='COPY_LOCATION')
                constraint.target = node
            if node_name == "NWrist_2":
                bone = armature.pose.bones.get("HandIK_2")
                constraint = bone.constraints.new(type='COPY_LOCATION')
                constraint.target = node
            
            if node_name == "NAnkle_1":
                bone = armature.pose.bones.get("HeelIK_1")
                constraint = bone.constraints.new(type='COPY_LOCATION')
                constraint.target = node
            if node_name == "NAnkle_2":
                bone = armature.pose.bones.get("HeelIK_2")
                constraint = bone.constraints.new(type='COPY_LOCATION')
                constraint.target = node
            
            if node_name == "COM":
                bone = armature.pose.bones.get("COM")
                constraint = bone.constraints.new(type='COPY_LOCATION')
                constraint.target = node
                
            if node_name == "NPivot":
                bone = armature.pose.bones.get("Root")
                constraint = bone.constraints.new(type='COPY_LOCATION')
                constraint.target = node

        if node_name == "NToeS_1":
            bone = armature.pose.bones.get("Foot_1")
            constraint = bone.constraints.new(type='LOCKED_TRACK')
            constraint.target = node
            constraint.track_axis = 'TRACK_Z'
            constraint.lock_axis = 'LOCK_Y'
        elif node_name == "NToeS_2":
            bone = armature.pose.bones.get("Foot_2")
            constraint = bone.constraints.new(type='LOCKED_TRACK')
            constraint.target = node
            constraint.track_axis = 'TRACK_Z'
            constraint.lock_axis = 'LOCK_Y'
            
        if node_name == "NHeadS_2":
            bone = armature.pose.bones.get("Head")
            constraint = bone.constraints.new(type='LOCKED_TRACK')
            constraint.target = node
            constraint.track_axis = 'TRACK_Z'
            constraint.lock_axis = 'LOCK_Y'
        
        if node_name == "NKnucklesS_1":
            bone = armature.pose.bones.get("Hand_1")
            constraint = bone.constraints.new(type='LOCKED_TRACK')
            constraint.target = node
            constraint.track_axis = 'TRACK_Z'
            constraint.lock_axis = 'LOCK_Y'
        elif node_name == "NKnucklesS_2":
            bone = armature.pose.bones.get("Hand_2")
            constraint = bone.constraints.new(type='LOCKED_TRACK')
            constraint.target = node
            constraint.track_axis = 'TRACK_Z'
            constraint.lock_axis = 'LOCK_Y'
        
        if settings.armature_rig_type == "SHADOW FIGHT 2":
            if node_name == "NFingertipsSS_2":
                bone = armature.pose.bones.get("FingersS_2")
                constraint = bone.constraints.new(type='DAMPED_TRACK')
                constraint.target = bpy.data.objects.get(node_name)
            elif node_name == "NFingertipsSS_1":
                bone = armature.pose.bones.get("FingersS_1")
                constraint = bone.constraints.new(type='DAMPED_TRACK')
                constraint.target = bpy.data.objects.get(node_name)
            
            if node_name == "NFingertipsS_1":
                bone = armature.pose.bones.get("Fingers_1")
                constraint = bone.constraints.new(type='LOCKED_TRACK')
                constraint.target = node
                constraint.track_axis = 'TRACK_Z'
                constraint.lock_axis = 'LOCK_Y'
            elif node_name == "NFingertipsS_2":
                bone = armature.pose.bones.get("Fingers_2")
                constraint = bone.constraints.new(type='LOCKED_TRACK')
                constraint.target = node
                constraint.track_axis = 'TRACK_Z'
                constraint.lock_axis = 'LOCK_Y'
            
            if node_name == "MacroNode5_1":
                bone = armature.pose.bones.get("FingersS_1")
                constraint = bone.constraints.new(type='LOCKED_TRACK')
                constraint.target = node
                constraint.track_axis = 'TRACK_Z'
                constraint.lock_axis = 'LOCK_Y'
            elif node_name == "MacroNode5_2":
                bone = armature.pose.bones.get("FingersS_2")
                constraint = bone.constraints.new(type='LOCKED_TRACK')
                constraint.target = node
                constraint.track_axis = 'TRACK_Z'
                constraint.lock_axis = 'LOCK_Y'
            
            if settings.affect_weaponnode:
            
                if node_name == "Weapon-Node2_1":
                    bone = armature.pose.bones.get("Weapon_1")
                    constraint = bone.constraints.new(type='COPY_LOCATION')
                    constraint.target = node
                elif node_name == "Weapon-Node2_2":
                    bone = armature.pose.bones.get("Weapon_2")
                    constraint = bone.constraints.new(type='COPY_LOCATION')
                    constraint.target = node
                
                if node_name == "Weapon-Node3_1":
                    bone = armature.pose.bones.get("Weapon_1")
                    constraint = bone.constraints.new(type='DAMPED_TRACK')
                    constraint.target = bpy.data.objects.get(node_name)
                elif node_name == "Weapon-Node3_2":
                    bone = armature.pose.bones.get("Weapon_2")
                    constraint = bone.constraints.new(type='DAMPED_TRACK')
                    constraint.target = bpy.data.objects.get(node_name)
                
                if node_name == "Weapon-Node4_1":
                    bone = armature.pose.bones.get("Weapon_1")
                    constraint = bone.constraints.new(type='LOCKED_TRACK')
                    constraint.target = node
                    constraint.track_axis = 'TRACK_Z'
                    constraint.lock_axis = 'LOCK_Y'
                elif node_name == "Weapon-Node4_2":
                    bone = armature.pose.bones.get("Weapon_2")
                    constraint = bone.constraints.new(type='LOCKED_TRACK')
                    constraint.target = node
                    constraint.track_axis = 'TRACK_Z'
                    constraint.lock_axis = 'LOCK_Y'
            
        if node_name.endswith("S_1") or node_name.endswith("S_2") or node_name == "NTop":
            continue
            
        if settings.armature_rig_type == "VECTOR":
            if node_name == "Camera" or node_name == "DetectorH" or node_name == "DetectorV":
                continue
        else:
            if node_name in IgnoreList:
                continue
        
        if node_name == "NHeadF":
            bone = armature.pose.bones.get("HeadF")
            constraint = bone.constraints.new(type='DAMPED_TRACK')
            constraint.target = bpy.data.objects.get(node_name)
            continue
            
        if node_name.endswith("F"):
            fbone = True
        else:
            fbone = False
        
        if settings.armature_rig_type == "VECTOR":
            bone_id = NODE_TO_BONE_VECTOR.get(node_name)
        else:
            bone_id = NODE_TO_BONE_SF2.get(node_name)
        bone = armature.pose.bones.get(bone_id)
        if bone:
            if fbone:
                constraint = bone.constraints.new(type='LOCKED_TRACK')
                constraint.target = node
                constraint.track_axis = 'TRACK_Z'
                constraint.lock_axis = 'LOCK_Y'
                    
                continue
            
            if bone_id == "Pelvis" or bone_id == "Hip_1" or bone_id == "Hip_2" and fbone is not True:         
                constraint2 = bone.constraints.new(type='COPY_LOCATION')
                constraint2.target = bpy.data.objects.get("NPivot")
                
            constraint = bone.constraints.new(type='DAMPED_TRACK')
            
            if bone_id == "Pelvis":
                constraint.target = bpy.data.objects.get("NStomach")
            elif bone_id == "Stomach":
                constraint.target = bpy.data.objects.get("NChest")
            elif bone_id == "Chest":
                constraint.target = bpy.data.objects.get("NNeck")
            elif bone_id == "Neck":
                constraint.target = bpy.data.objects.get("NHead")
            elif bone_id == "Head":
                constraint.target = bpy.data.objects.get("NTop")
            else:
                constraint.target = node
                
    #Fix NPivot LockedTrack constraint
    pivotbone = armature.pose.bones.get("Pelvis")
    index = pivotbone.constraints.find("Locked Track")
    last_index = len(pivotbone.constraints) - 1
    
    while index < last_index:
        pivotbone.constraints.move(index, index + 1)
        index += 1

# Armature Baking
def armature_bake(dependencies_xml="", model_xml="", bake_start=None):
    settings = bpy.context.scene.gymnast_tool_props
    scene = bpy.context.scene
    armature = settings.armature_object
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='POSE')
    
    # Generate node order from XML files
    node_order = parse_nodes_from_xml(dependencies_xml)
    model_nodes = parse_nodes_from_xml(model_xml)
    
    # Check for duplicate nodes
    duplicate_nodes = set(node_order) & set(model_nodes)
    if duplicate_nodes:
       raise ValueError(f"Duplicate nodes found in both XML files: {', '.join(duplicate_nodes)}")

    node_order.extend(model_nodes)  # Merge both lists
    if not node_order:
        raise ValueError("At least one XML file must contain nodes.")

    limit = len(node_order)  # Use node count as limit
    
    bake_start = bake_start if bake_start is not None else scene.frame_start # Spline Support
    
    # Bake animation
    bpy.ops.nla.bake(
        frame_start=bake_start,
        frame_end=scene.frame_end,
        only_selected=False,
        visual_keying=True,
        clear_constraints=True,
        use_current_action=True,
        bake_types={'POSE'}
    )
    
    for frame in range(bake_start, scene.frame_end):
        for i, name in enumerate(node_order[:limit]):
            if settings.armature_rig_type == "VECTOR":
                if name == "DetectorH" or name == "DetectorV" or name == "COM" or name == "Camera":
                    continue
            else:
                if name == "COM":
                    continue
                    
            node = bpy.data.objects.get(name)
            node.keyframe_delete(data_path="location", frame=frame)
    
    if settings.use_armature_ik:
        for i, name in enumerate(node_order[:limit]):
            if settings.armature_rig_type == "VECTOR":
                if name == "DetectorH" or name == "DetectorV" or name == "COM" or name == "Camera":
                    continue
            else:
                if name == "COM":
                    continue
                
            node = bpy.data.objects.get(name)
            constraint = node.constraints.new(type='CHILD_OF')
            constraint.target = armature
            
            if settings.armature_rig_type == "VECTOR":
                bone_id = NODE_TO_BONE_VECTOR.get(name)
            else:
                bone_id = NODE_TO_BONE_SF2.get(name)
                
            constraint.subtarget = bone_id
            
        IK_BONES = ["Calf_1", "Calf_2", "Forearm_1", "Forearm_2"]
        for i, name in enumerate(IK_BONES[:4]):
            bone = armature.pose.bones.get(name)
            constraint = bone.constraints.new(type='IK')
            constraint.chain_count = 2
            constraint.target = armature
            
            if name == "Calf_1":
                constraint.subtarget = "HeelIK_1"
            if name == "Calf_2":
                constraint.subtarget = "HeelIK_2"
            if name == "Forearm_1":
                constraint.subtarget = "HandIK_1"
            if name == "Forearm_2":
                constraint.subtarget = "HandIK_2"
    else:
        for i, name in enumerate(node_order[:limit]):
            if settings.armature_rig_type == "VECTOR":
                if name == "DetectorH" or name == "DetectorV" or name == "COM" or name == "Camera":
                    continue
            else:
                if name == "COM":
                    continue
                
            node = bpy.data.objects.get(name)
            constraint = node.constraints.new(type='CHILD_OF')
            constraint.target = armature

            if settings.armature_rig_type == "VECTOR":
                bone_id = NODE_TO_BONE_VECTOR.get(name)
            else:
                bone_id = NODE_TO_BONE_SF2.get(name)
            
            constraint.subtarget = bone_id

# Correct Constraint after Baking
def correct_constraint():
    settings = bpy.context.scene.gymnast_tool_props
    armature = settings.armature_object

    if armature is None or armature.type != 'ARMATURE':
        print("Invalid armature")
        return

    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='POSE')

    pairs = [
        ("Hand_1", "Forearm_1"),
        ("Hand_2", "Forearm_2"),
        ("Heel_1", "Calf_1"),
        ("Heel_2", "Calf_2")
    ]

    for bone_name, target_bone_name in pairs:
        try:
            pbone = armature.pose.bones[bone_name]
        except KeyError:
            print(f"Bone '{bone_name}' not found.")
            continue

        # Clear constraint
        for c in pbone.constraints:
            if c.type == 'COPY_LOCATION':
                pbone.constraints.remove(c)

        # Add new Copy Location constraint
        constraint = pbone.constraints.new(type='COPY_LOCATION')
        constraint.name = f"CopyLoc_{target_bone_name}"
        constraint.target = armature
        constraint.subtarget = target_bone_name
        constraint.head_tail = 1.0 
  
# Export Node Point positions to .bindec file
def export_bindec(filepath, dependencies_xml, model_xml):
    
    # Get the node order from XMLs
    nodepoint_order = get_node_order_from_xml(dependencies_xml, model_xml)
    limit = len(nodepoint_order)  # Set limit based on detected nodes

    scene = bpy.context.scene
    start_frame = scene.frame_start
    end_frame = scene.frame_end

    lines = []

    for frame in range(start_frame, end_frame + 1):
        scene.frame_set(frame)
        positions = []

        for name in nodepoint_order:
            obj = bpy.data.objects.get(name)
            if obj:
                pos = obj.matrix_world.translation
                x = pos.x
                z = -pos.y  # Flip the Z-axis
                y = pos.z 
                positions.append(f"{x:.8f},{y:.8f},{z:.8f}")
            else:
                positions.append("0,0,0")

        line = f"[{limit}]{{{'}{'.join(positions)}}}END"
        lines.append(line)

    with open(filepath, 'w') as file:
        file.write(f"Binary blocks count: {len(lines)}\n")
        for line in lines:
            file.write(f"{line}\n")

# Import .bindec file
def import_bindec(filepath, dependencies_xml="", model_xml=""):
    settings = bpy.context.scene.gymnast_tool_props
    
    if settings.use_armature:
        setup_armature_follow_node(dependencies_xml, model_xml)
    
    use_spline = settings.use_spline
    pivot_node_name = settings.pivot_node
    start_frame = settings.start_frame
    
    # Generate node order from XML files
    node_order = parse_nodes_from_xml(dependencies_xml)
    model_nodes = parse_nodes_from_xml(model_xml)
    
    # Check for duplicate nodes
    duplicate_nodes = set(node_order) & set(model_nodes)
    if duplicate_nodes:
       raise ValueError(f"Duplicate nodes found in both XML files: {', '.join(duplicate_nodes)}")

    node_order.extend(model_nodes)  # Merge both lists
    if not node_order:
        raise ValueError("At least one XML file must contain nodes.")

    limit = len(node_order)  # Use node count as limit
    
    with open(filepath, 'r') as file:
        lines = file.readlines()
    
    if not lines or not lines[0].startswith("Binary blocks count:"):
        return {'CANCELLED'}
    
    binary_blocks_count = int(lines[0].split(":")[1].strip())
    
    scene = bpy.context.scene
    pivot_node_obj = bpy.data.objects.get(pivot_node_name) if use_spline else None
    
    # Determine the last known position of the pivot node
    if use_spline and pivot_node_obj:
        if pivot_node_obj.animation_data and pivot_node_obj.animation_data.action:
            fcurves = pivot_node_obj.animation_data.action.fcurves
            location_curves = [curve for curve in fcurves if curve.data_path == "location"]
            keyframes = [kp.co.x for curve in location_curves for kp in curve.keyframe_points]
            last_pivot_frame = max(keyframes, default=scene.frame_start)
        else:
            last_pivot_frame = scene.frame_start
            
        if not settings.stay_in_place:
            last_pivot_pos = pivot_node_obj.matrix_world.translation.copy()
        new_start_frame = int(last_pivot_frame) + 1
    else:
        if not settings.stay_in_place:
            last_pivot_pos = None
        new_start_frame = scene.frame_start
    
    frame_index = start_frame  # Adjusting based on the specified Start Frame
    if not settings.stay_in_place:
        pivot_offset = (0, 0, 0)
    
    for frame in range(new_start_frame, new_start_frame + (binary_blocks_count - start_frame)):
        if frame_index >= len(lines):
            break
        
        line = lines[frame_index].strip()
        frame_index += 1
        
        if line.startswith("[") and line.endswith("END"):
            try:
                positions_str = line[line.index("{") + 1:line.rindex("}")].split("}{")
                positions = [p.split(",") for p in positions_str[:limit]]
                positions += [["0", "0", "0"]] * (limit - len(positions))
                
                if use_spline and pivot_node_obj:
                    pivot_index = node_order.index(pivot_node_name) if pivot_node_name in node_order else None
                    if settings.stay_in_place:
                        if pivot_index is not None:
                            pivot_last_pos = pivot_node_obj.matrix_world.translation
                            pivot_new_pos = (float(positions[pivot_index][0]), -float(positions[pivot_index][2]), float(positions[pivot_index][1]))
                            offset = (pivot_last_pos[0] - pivot_new_pos[0], pivot_last_pos[1] - pivot_new_pos[1], pivot_last_pos[2] - pivot_new_pos[2])
                        else:
                            offset = (0, 0, 0)
                    else:
                        pivot_new_pos = (
                            float(positions[pivot_index][0]),
                            -float(positions[pivot_index][2]),
                            float(positions[pivot_index][1])
                        )
                        
                        # Compute offset only at the first frame
                        if last_pivot_pos and frame == new_start_frame:
                            pivot_offset = (
                                last_pivot_pos[0] - pivot_new_pos[0],
                                last_pivot_pos[1] - pivot_new_pos[1],
                                last_pivot_pos[2] - pivot_new_pos[2]
                            )
                
                for i, name in enumerate(node_order[:limit]):
                    obj = bpy.data.objects.get(name)
                    if obj:
                        if settings.stay_in_place:
                            x = float(positions[i][0]) + offset[0]
                            z = float(positions[i][1]) + offset[2]
                            y = -float(positions[i][2]) + offset[1]
                        else:
                            x = float(positions[i][0]) + pivot_offset[0]
                            z = float(positions[i][1]) + pivot_offset[2]
                            y = -float(positions[i][2]) + pivot_offset[1]
                        
                        if settings.flipped_animation: # note: (x,y,z) is actually (x,-z,y) converted from bin
                            if settings.flipped_type == 'X':
                                obj.location = (-x, y, z)
                            elif settings.flipped_type == 'Y':
                                obj.location = (x, y, -z)
                            elif settings.flipped_type == 'Z':
                                obj.location = (x, -y, z)
                        else:
                            obj.location = (x, y, z)
                        obj.keyframe_insert(data_path="location", frame=frame)
                        
            except ValueError:
                continue
    
    scene.frame_end = new_start_frame + (binary_blocks_count - start_frame)
    scene.frame_set(new_start_frame)
    
    if settings.use_armature:
        armature_bake(dependencies_xml, model_xml, bake_start=new_start_frame)
        correct_constraint()


# #################### #
# Operator
# #################### #


# Operator to export node point positions
class ExportBindecOperator(bpy.types.Operator):
    bl_idname = "export.bindec"
    bl_label = "Export Animation"
    bl_description = "Export the positions of node points in every frames to a .bin"

    filepath: bpy.props.StringProperty(
        name="File Path",
        description="Filepath used for exporting the .bin file",
        subtype="FILE_PATH"
    )

    def execute(self, context):
        settings = context.scene.gymnast_tool_props
        dependencies_xml = None
        model_xml = None
        dependencies_xml_unconvert = settings.dependencies_xml
        model_xml_unconvert = settings.model_xml
        
        if dependencies_xml_unconvert:
            dependencies_xml = bpy.path.abspath(dependencies_xml_unconvert)
            
        if model_xml_unconvert:
            model_xml = bpy.path.abspath(model_xml_unconvert)
    
        if not self.filepath.endswith(".bin"):
            self.filepath += ".bin"
        
        bindec_path = self.filepath.replace(".bin", ".bindec")
        
        try:
            export_bindec(bindec_path, dependencies_xml, model_xml)
        except ValueError as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}
        
        if not context.scene.gymnast_tool_props.export_as_bindec:
            compile_bin(bindec_path)  # Compile to .bin and remove .bindec
        
        return {'FINISHED'}

    def invoke(self, context, event):
        scene_name = bpy.path.basename(context.blend_data.filepath)
        scene_name = os.path.splitext(scene_name)[0]
        self.filepath = bpy.path.abspath("//") + scene_name + ".bin"
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    
# Operator to import node point positions
class ImportBindecOperator(bpy.types.Operator):
    bl_idname = "import.bindec"
    bl_label = "Import Animation"
    bl_description = "Import positions of node points from a .bin"

    filepath: bpy.props.StringProperty(
        name="File Path",
        description="Filepath used for importing the .bin file",
        subtype="FILE_PATH"
    )

    def execute(self, context):
        settings = context.scene.gymnast_tool_props  # Access global properties
        dependencies_xml = None
        model_xml = None
        dependencies_xml_unconvert = settings.dependencies_xml
        model_xml_unconvert = settings.model_xml
        
        if dependencies_xml_unconvert:
            dependencies_xml = bpy.path.abspath(dependencies_xml_unconvert)
            
        if model_xml_unconvert:
            model_xml = bpy.path.abspath(model_xml_unconvert)
        
        if self.filepath.endswith(".bin"):
            bindec_path = decompile_bin(self.filepath)
        else:
            bindec_path = self.filepath
            
        try:
            import_bindec(bindec_path, dependencies_xml, model_xml)
        except ValueError as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}
        
        # Remove temporary .bindec
        if self.filepath.endswith(".bin"):
            os.remove(bindec_path)
            
        return {'FINISHED'}


    def invoke(self, context, event):
        # Set the default file path
        self.filepath = bpy.path.abspath("//")  # Start with current blend file directory
        wm = context.window_manager
        wm.fileselect_add(self)
        return {'RUNNING_MODAL'}

# Settings
class GymnastToolSettings(bpy.types.PropertyGroup):
    dependencies_xml: bpy.props.StringProperty(
        name="Dependencies XML",
        description="Path to the Dependencies XML file",
        subtype="FILE_PATH"
    )
    model_xml: bpy.props.StringProperty(
        name="Model XML",
        description="Path to the Model XML file",
        subtype="FILE_PATH"
    )
    export_as_bindec: bpy.props.BoolProperty(
        name="Export as Bindec", 
        description="Export only as .bindec without compiling to .bin\nDefault: False", 
        default=False
    )
    use_spline: bpy.props.BoolProperty(
        name="Use Spline",
        description="Align new animation based on pivot node's last position\nDefault: False",
        default=False
    )
    stay_in_place: bpy.props.BoolProperty(
        name="Stay in Place",
        description="Align new animation based on pivot node as an anchor point.\nDefault: False",
        default=False
    )
    pivot_node: bpy.props.StringProperty(
        name="Pivot Node",
        description="Name of the pivot node used for alignment",
        default=""
    )
    start_frame: bpy.props.IntProperty(
        name="Start Frame",
        description="Starting frame for imported animation",
        default=1,
        min=1
    )
    use_armature: bpy.props.BoolProperty(
        name="Use Armature",
        description="Apply the animation to Armature instead of node point.\nNote: This feature isn't compatible with custom rigs and spline.\nDefault: False",
        default=False
    )
    use_armature_ik: bpy.props.BoolProperty(
        name="Use IK",
        description="Use IK Rig.\nDefault: False",
        default=False
    )
    armature_object: bpy.props.PointerProperty(
        name="Armature",
        description="The Armature for the animation to be imported into.",
        type=bpy.types.Object,
        poll=lambda self, obj: obj.type == 'ARMATURE'
    )
    armature_rig_type: bpy.props.EnumProperty(
        name="Type",
        description="Choose the type of rig\nDefault: VECTOR",
        items=[
            ('VECTOR', "Vector", "Vector's Rig"),
            ('SHADOW FIGHT 2', "Shadow Fight 2", "Shadow Fight 2's Rig")
        ],
        default='VECTOR',
    )
    affect_weaponnode: bpy.props.BoolProperty(
        name="Affect WeaponNode",
        description="Import animations to the character and weapon's armature.\nDisabling this will make the the importing ignore the Weapon Bone.\nDefault: False",
        default=False
    )
    flipped_animation: bpy.props.BoolProperty(
        name="Mirrored",
        description="Mirror the imported animation.\nDefault: False",
        default=False
    )
    flipped_type: bpy.props.EnumProperty(
        name="Axis",
        description="Axis to be mirrored\nDefault: Z",
        items=[
            ('X', "X", "Flip the X Axis."),
            ('Y', "Y", "Flip the Y Axis."),
            ('Z', "Z", "Flip the Z Axis.")
        ],
        default='Z',
    )


class CompileBinOperator(bpy.types.Operator):
    bl_idname = "file.compile_bindec"
    bl_label = "Compile to .bin"
    bl_description = "Select a .bindec file to compile into .bin"
    
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    
    def execute(self, context):
        if not self.filepath.endswith(".bindec"):
            self.report({'ERROR'}, "Please select a .bindec file")
            return {'CANCELLED'}
        
        compile_bin(self.filepath)
        return {'FINISHED'}
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class DecompileBinOperator(bpy.types.Operator):
    bl_idname = "file.decompile_bin"
    bl_label = "Decompile to .bindec"
    bl_description = "Select a .bin file to decompile into .bindec"
    
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    
    def execute(self, context):
        if not self.filepath.endswith(".bin"):
            self.report({'ERROR'}, "Please select a .bin file")
            return {'CANCELLED'}
        
        decompile_bin(self.filepath)
        return {'FINISHED'}
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


# #################### #
# Sideview Panel Menu  #
# #################### #


class VIEW3D_PT_gymnast_animation_panel(bpy.types.Panel):
    bl_label = "Animation Tools"
    bl_idname = "VIEW3D_PT_gymnast_animation_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Gymnast Tool Suite'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        settings = context.scene.gymnast_tool_props

        layout.prop(settings, "dependencies_xml")
        layout.prop(settings, "model_xml")
        
        # Actual bits n bop
        box = layout.box()
        box.label(text="Animation Options", icon='ARMATURE_DATA')
        box.operator(ImportBindecOperator.bl_idname, text="Import Animation")
        box.operator(ExportBindecOperator.bl_idname, text="Export Animation")
        
class VIEW3D_PT_gymnast_animation_settings(bpy.types.Panel):
    bl_label = "Settings"
    bl_idname = "VIEW3D_PT_gymnast_animation_settings"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Gymnast Tool Suite'
    bl_parent_id = "VIEW3D_PT_gymnast_animation_panel"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout

class VIEW3D_PT_gymnast_animation_settings_export(bpy.types.Panel):
    bl_label = "Export Settings"
    bl_idname = "VIEW3D_PT_gymnast_animation_settings_export"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Gymnast Tool Suite'
    bl_parent_id = "VIEW3D_PT_gymnast_animation_settings"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text="Export Settings")
        box.prop(context.scene.gymnast_tool_props, "export_as_bindec")

class VIEW3D_PT_gymnast_animation_settings_import(bpy.types.Panel):
    bl_label = "Import Settings"
    bl_idname = "VIEW3D_PT_gymnast_animation_settings_import"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Gymnast Tool Suite'
    bl_parent_id = "VIEW3D_PT_gymnast_animation_settings"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        props = context.scene.gymnast_tool_props
        layout = self.layout
        box3 = layout.box()
        box2 = layout.box()
        box = layout.box()
        
        box3.label(text="Import Settings")
        box3.prop(context.scene.gymnast_tool_props, "flipped_animation")
        if props.flipped_animation:
            box3.prop(context.scene.gymnast_tool_props, "flipped_type")
        
        box2.label(text="Armature")
        box2.prop(context.scene.gymnast_tool_props, "use_armature")
        if props.use_armature:
            box2.prop(context.scene.gymnast_tool_props, "use_armature_ik")
            if props.armature_rig_type == "SHADOW FIGHT 2":
                box2.prop(context.scene.gymnast_tool_props, "affect_weaponnode")
            box2.prop(context.scene.gymnast_tool_props, "armature_object")
            box2.prop(context.scene.gymnast_tool_props, "armature_rig_type")
        
        box.label(text="Splining")
        box.prop(context.scene.gymnast_tool_props, "use_spline")
        if props.use_spline:
            box.prop(context.scene.gymnast_tool_props, "stay_in_place")
            box.prop(context.scene.gymnast_tool_props, "pivot_node")
            box.prop(context.scene.gymnast_tool_props, "start_frame")

class VIEW3D_PT_gymnast_animation_settings_miscellaneous(bpy.types.Panel):
    bl_label = "Miscellaneous"
    bl_idname = "VIEW3D_PT_gymnast_animation_settings_miscellaneous"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Gymnast Tool Suite'
    bl_parent_id = "VIEW3D_PT_gymnast_animation_settings"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text="Options")
        box.operator("file.compile_bindec", text="Compile .Bindec")
        box.operator("file.decompile_bin", text="Decompile .Bin")


#register
classes = [
    ImportBindecOperator,
    ExportBindecOperator,
    CompileBinOperator,
    DecompileBinOperator,
    GymnastToolSettings,
    VIEW3D_PT_gymnast_animation_panel,
    VIEW3D_PT_gymnast_animation_settings,
    VIEW3D_PT_gymnast_animation_settings_export,
    VIEW3D_PT_gymnast_animation_settings_import,
    VIEW3D_PT_gymnast_animation_settings_miscellaneous,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.gymnast_tool_props = bpy.props.PointerProperty(type=GymnastToolSettings)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.gymnast_tool_props

if __name__ == "__main__":
    register()
