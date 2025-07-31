# #################### #
# Model Panel
# #################### #

import bpy
import bmesh
import os
import math
import mathutils
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom

from mathutils import Vector


# #################### #
# Function
# #################### #


# for property group

def get_general_vertex_groups(self, context):
    settings = context.scene.gymnast_tool_model_props
    model_type = settings.model_type_export
    obj = settings.selected_object
    
    if model_type == 'HEAD_GEAR' or model_type == 'MODEL' or model_type == 'BODY_GEAR' or model_type == 'RANGED':
        if obj and obj.type == 'MESH':
            return [(vg.name, vg.name, "") for vg in obj.vertex_groups]
        else:
            return [("None", "None", "No vertex groups available")]
    else:
        return [("None", "None", "Not applicable")]

def get_weapon1_vertex_groups(self, context):
    settings = context.scene.gymnast_tool_model_props
    model_type = settings.model_type_export
    weapon_1_obj = settings.weapon_object_1
    
    if model_type == 'WEAPON':
        if weapon_1_obj and weapon_1_obj.type == 'MESH':
            return [(vg.name, vg.name, "") for vg in weapon_1_obj.vertex_groups]
        else:
            return [("None", "None", "No vertex groups available")]
    else:
        return [("None", "None", "Not applicable")]
    
def get_weapon2_vertex_groups(self, context):
    settings = context.scene.gymnast_tool_model_props
    model_type = settings.model_type_export
    weapon_2_obj = settings.weapon_object_2
    
    if model_type == 'WEAPON':
        if weapon_2_obj and weapon_2_obj.type == 'MESH':
            return [(vg.name, vg.name, "") for vg in weapon_2_obj.vertex_groups]
        else:
            return [("None", "None", "No vertex groups available")]
    else:
        return [("None", "None", "Not applicable")]

def get_foot1_vertex_groups(self, context):
    settings = context.scene.gymnast_tool_model_props
    model_type = settings.model_type_export
    foot_1_obj = settings.foot_object_1
    
    if model_type == 'FOOT_GEAR':
        if foot_1_obj and foot_1_obj.type == 'MESH':
            return [(vg.name, vg.name, "") for vg in foot_1_obj.vertex_groups]
        else:
            return [("None", "None", "No vertex groups available")]
    else:
        return [("None", "None", "Not applicable")]

def get_foot2_vertex_groups(self, context):
    settings = context.scene.gymnast_tool_model_props
    model_type = settings.model_type_export
    foot_2_obj = settings.foot_object_2
    
    if model_type == 'FOOT_GEAR':
        if foot_2_obj and foot_2_obj.type == 'MESH':
            return [(vg.name, vg.name, "") for vg in foot_2_obj.vertex_groups]
        else:
            return [("None", "None", "No vertex groups available")]
    else:
        return [("None", "None", "Not applicable")]

def refresh_enum(self, context):
    # Force UI redraw
    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            area.tag_redraw()


# for exporting

def add_necessary_triangle_body_gear(context, prefix, figures_element):
    def write_triangle():
        ET.SubElement(figures_element, f"{prefix}Foot-Triangle1_1",
                    Type="Triangle",
                    Shading="0",
                    Node1="NHeel_1",
                    Node2="NToe_1",
                    Node3="NAnkle_1")
                    
        ET.SubElement(figures_element, f"{prefix}Foot-Triangle2_1",
                    Type="Triangle",
                    Shading="0",
                    Node1="NToeS_1",
                    Node2="NToe_1",
                    Node3="NHeel_1")
        
        ET.SubElement(figures_element, f"{prefix}Foot-Triangle1_2",
                    Type="Triangle",
                    Shading="0",
                    Node1="NHeel_2",
                    Node2="NToe_2",
                    Node3="NAnkle_2")
                           
        ET.SubElement(figures_element, f"{prefix}Foot-Triangle2_2",
                    Type="Triangle",
                    Shading="0",
                    Node1="NHeel_2",
                    Node2="NToeS_2",
                    Node3="NToe_2")
                    
        ET.SubElement(figures_element, f"{prefix}Foot-Triangle3_2",
                    Type="Triangle",
                    Shading="0",
                    Node1="NToeS_2",
                    Node2="NToe_2",
                    Node3="NAnkle_2")
                    
    write_triangle()

def store_edge(context, edges, vertices, model_type, edges_element, starting_edge, starting_node, node_name_map=None):
    settings = context.scene.gymnast_tool_model_props
    prefix = settings.model_string_name
    
    for i, edge in enumerate(edges, start=starting_edge):
        v1, v2 = edge.vertices
        if model_type == "HEAD_GEAR" or model_type == "WEAPON" or model_type == "BODY_GEAR" or model_type == "FOOT_GEAR" or model_type == "RANGED":
            node1 = f"{prefix}Node{v1 + starting_node}"
            node2 = f"{prefix}Node{v2 + starting_node}"
        elif model_type == "MODEL":
            if settings.model_use_pivot:
                node1 = node_name_map.get(v1)
                node2 = node_name_map.get(v2)
            else:
                node1 = f"{prefix}Node{v1 + starting_node}"
                node2 = f"{prefix}Node{v2 + starting_node}"
        else:
            continue

        edge_length = math.dist(vertices[v1].co, vertices[v2].co)
        
        if node1 is None or node2 is None:
            raise ValueError(f"store_edge: Node mapping failed: node1={node1}, node2={node2}, v1={v1}, v2={v2}")
       
        ET.SubElement(edges_element, f"{prefix}Edge{i}",
            Type="Edge",
            Length=str(edge_length),
            WithSign="0",
            Fixed="0",
            Visible="1",
            Collisible="1" if settings.model_edge_collisible else "0",
            SubNodesCount="0",
            End1=node1,
            End2=node2)

def store_edge_attack(context, edges, vertices, edges_element, starting_edge, starting_node, is_first, is_ranged=None):
    settings = context.scene.gymnast_tool_model_props
    prefix = settings.model_string_name
    
    for i, edge in enumerate(edges, start=1):
        v1, v2 = edge.vertices
        node1 = f"{prefix}MacroNode{v1 + starting_node}"
        node2 = f"{prefix}MacroNode{v2 + starting_node}"
        edge_length = math.dist(vertices[v1].co, vertices[v2].co)
        
        if is_first and is_ranged is None:
            ET.SubElement(edges_element, f"{prefix}AttackEdge{i}_1",
                Type="Edge",
                Length=str(edge_length),
                WithSign="0",
                Fixed="0",
                Visible="1",
                Collisible="1" if settings.model_edge_collisible else "0",
                SubNodesCount="0",
                End1=node1,
                End2=node2)

        elif not is_first and is_ranged is None:
            ET.SubElement(edges_element, f"{prefix}AttackEdge{i}_2",
                Type="Edge",
                Length=str(edge_length),
                WithSign="0",
                Fixed="0",
                Visible="1",
                Collisible="1" if settings.model_edge_collisible else "0",
                SubNodesCount="0",
                End1=node1,
                End2=node2)
        
        if is_ranged:
            ET.SubElement(edges_element, f"{prefix}AttackEdge{i}",
                Type="Edge",
                Length=str(edge_length),
                WithSign="0",
                Fixed="0",
                Visible="1",
                Collisible="1" if settings.model_edge_collisible else "0",
                SubNodesCount="0",
                End1=node1,
                End2=node2)
 
def store_face(context, faces, vertices, model_type, figures_element, starting_tri, starting_node, node_name_map=None):
    settings = context.scene.gymnast_tool_model_props
    prefix = settings.model_string_name
    
    for i, face in enumerate(faces, start=starting_tri):
        if len(face.vertices) == 3:
            v1, v2, v3 = face.vertices
            if model_type == "HEAD_GEAR" or model_type == "WEAPON" or model_type == "BODY_GEAR" or model_type == "FOOT_GEAR" or model_type == "RANGED":
                node1 = f"{prefix}Node{v1 + starting_node}"
                node2 = f"{prefix}Node{v2 + starting_node}"
                node3 = f"{prefix}Node{v3 + starting_node}"
            elif model_type == "MODEL":
                if settings.model_use_pivot:
                    node1 = node_name_map.get(v1)
                    node2 = node_name_map.get(v2)
                    node3 = node_name_map.get(v3)
                else:
                    node1 = f"{prefix}Node{v1 + starting_node}"
                    node2 = f"{prefix}Node{v2 + starting_node}"
                    node3 = f"{prefix}Node{v3 + starting_node}"
            else:
                continue
                
            if node1 is None or node2 is None or node3 is None:
                raise ValueError(f"store_face: Node mapping failed: node1={node1}, node2={node2}, node3={node3}, v1={v1}, v2={v2}, v3={v3}")
            
            ET.SubElement(figures_element, f"{prefix}Triangle-{i}",
                Type="Triangle",
                Shading="0",
                Node1=node1,
                Node2=node2,
                Node3=node3)


# #################### #
# Operator
# #################### #


class ConvertXMLOperator(bpy.types.Operator):
    bl_idname = "model.convert_xml"
    bl_label = "Convert XML to OBJ"
    bl_description = "Convert the Model XML into a Blender object"
    
    def execute(self, context):
        dependencies_path = None
        model_path = None
        
        dependencies_path_unconvert = context.scene.gymnast_dependencies_xml
        model_path_unconvert = context.scene.gymnast_normal_xml
        props = context.scene.gymnast_tool_model_props
        
        if dependencies_path_unconvert:
            dependencies_path = bpy.path.abspath(dependencies_path_unconvert)
            
        if model_path_unconvert:
            model_path = bpy.path.abspath(model_path_unconvert)
        else:
            self.report({'ERROR'}, "No model XML file selected")
            return {'CANCELLED'}
        
        if not os.path.exists(model_path):
            raise Exception("Model XML path is missing or invalid.")
            
        if props.model_use_dependencies and dependencies_path is not None and not os.path.exists(dependencies_path):
            raise Exception("Dependencies XML path is missing or invalid.")
        
        # Create the "Model" collection if it doesn't exist
        model_collection = bpy.data.collections.get("Model")
        if not model_collection:
            model_collection = bpy.data.collections.new("Model")
            context.scene.collection.children.link(model_collection)

        # Create a child collection named after the model file
        model_name = os.path.basename(model_path).split('.')[0]
        child_collection = bpy.data.collections.get(model_name)
        if not child_collection:
            child_collection = bpy.data.collections.new(model_name)
            model_collection.children.link(child_collection)

        # Create temporary .obj file path
        temp_obj_path = os.path.join(bpy.path.abspath("//"), f"{model_name}.obj")

        # Parse the XML file
        tree = ET.parse(model_path)
        root = tree.getroot()
        
        if dependencies_path is not None:
            dep_tree = ET.parse(dependencies_path)
            dep_root = dep_tree.getroot()

        nodes = {}
        with open(temp_obj_path, 'w') as obj_file:
            obj_file.write("# Temporary OBJ file generated by Blender Addon\n")
            
            if props.calculate_macronode:
                # Process Nodes
                nodes_section = root.find('Nodes')
                if nodes_section is not None:
                    macro_nodes = []  # Defer MacroNodes to second pass
                    
                    # First pass: Add Node and CenterOfMass
                    for node in nodes_section:
                        node_type = node.get('Type')
                        node_name = node.tag
                        
                        if node_type in ['Node', 'CenterOfMass']:
                            x = float(node.get('X'))
                            y = float(node.get('Y'))
                            z = float(node.get('Z'))
                            nodes[node_name] = (x, y, z)
                            obj_file.write(f"v {x} {-z} {y}\n")
                            
                        elif node_type == 'MacroNode':
                            macro_nodes.append(node)  # Defer for second pass    
                        
                    # Second pass: Process MacroNodes
                    for node in macro_nodes:
                        node_name = node.tag
                        lcc_pos = [0.0, 0.0, 0.0]
                        total_lcc = 0.0

                        for i in range(1, 5):
                            child_attr = f'ChildNode{i}'
                            lcc_attr = f'LCC{i}'
                            if child_attr in node.attrib and lcc_attr in node.attrib:
                                child_name = node.get(child_attr)
                                lcc = float(node.get(lcc_attr))
                                total_lcc += lcc

                                if child_name and child_name != "Null":
                                    if child_name in nodes:
                                        cx, cy, cz = nodes[child_name]
                                        cx, cy, cz = cx, cy, cz
                                        lcc_pos[0] += cx * lcc
                                        lcc_pos[1] += cy * lcc
                                        lcc_pos[2] += cz * lcc
                                    elif props.model_use_dependencies and child_name not in nodes:
                                        if dependencies_path is None:
                                            self.report({'ERROR'}, "No dependencies path provided!")
                                            return {'CANCELLED'}
                                        if os.path.exists(dependencies_path):
                                            dep_nodes = dep_root.find('Nodes')
                                            if dep_nodes:
                                                for dep_node in dep_nodes:
                                                    if dep_node.tag == child_name and dep_node.get('Type') in ['Node', 'CenterOfMass', 'MacroNode']:
                                                        x = float(dep_node.get('X'))
                                                        y = float(dep_node.get('Y'))
                                                        z = float(dep_node.get('Z'))
                                                        cx, cy, cz = x, y, z
                                                        lcc_pos[0] += cx * lcc
                                                        lcc_pos[1] += cy * lcc
                                                        lcc_pos[2] += cz * lcc
                                                        break
                                        else:
                                            self.report({'ERROR'}, "No dependencies path provided!")
                                            return {'CANCELLED'}
                                    else:
                                        blender_obj = bpy.data.objects.get(child_name)
                                        if blender_obj:
                                            cx, cz, cy = blender_obj.location  # Blender uses x,z,y
                                            lcc_pos[0] += cx * lcc
                                            lcc_pos[1] += cy * lcc
                                            lcc_pos[2] += -cz * lcc
                                        else:
                                            continue

                        x, y, z = lcc_pos
                        nodes[node_name] = (x, y, z)
                        obj_file.write(f"v {x} {-z} {y}\n")
                
            else:
                # Process Nodes
                nodes_section = root.find('Nodes')
                for node in nodes_section:
                    node_type = node.get('Type')
                    node_name = node.tag
                    
                    if node_type in ['Node', 'CenterOfMass', 'MacroNode']:
                        x = float(node.get('X'))
                        y = float(node.get('Y'))
                        z = float(node.get('Z'))
                        nodes[node_name] = (x, y, z)
                        obj_file.write(f"v {x} {-z} {y}\n")
                            
                    
            # Process Figures (Triangles)
            figures_section = root.find('Figures')
            if figures_section is not None:
                obj_file.write("\n# Faces\n")
                for figure in figures_section:
                    if figure.get('Type') == 'Triangle':
                        n1 = figure.get('Node1')
                        n2 = figure.get('Node2')
                        n3 = figure.get('Node3')
                        
                        if props.model_use_dependencies:
                            for n in [n1, n2, n3]:
                                if n not in nodes and dependencies_path and os.path.exists(dependencies_path):
                                    dep_nodes = dep_root.find('Nodes')
                                    if dep_nodes:
                                        for dep_node in dep_nodes:
                                            if dep_node.tag == n and dep_node.get('Type') in ['Node', 'CenterOfMass']:
                                                x = float(dep_node.get('X'))
                                                y = float(dep_node.get('Y'))
                                                z = float(dep_node.get('Z'))
                                                nodes[n] = (x, y, z)
                                                obj_file.write(f"v {x} {-z} {y}\n")
                                                break

                        if n1 in nodes and n2 in nodes and n3 in nodes:
                            v1 = list(nodes.keys()).index(n1) + 1
                            v2 = list(nodes.keys()).index(n2) + 1
                            v3 = list(nodes.keys()).index(n3) + 1
                            obj_file.write(f"f {v1} {v2} {v3}\n")

        # Import the OBJ file into Blender
        bpy.ops.wm.obj_import(filepath=temp_obj_path)
        imported_obj = context.selected_objects[0]
        imported_obj.name = f"OBJ_{model_name}"
        imported_obj.rotation_euler = (0, 0, 0)
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)

        # Create a "Triangle_" collection if it doesn't exist
        triangle_collection = bpy.data.collections.get(f"Triangle_{model_name}")
        if not triangle_collection:
            triangle_collection = bpy.data.collections.new(f"Triangle_{model_name}")
            child_collection.children.link(triangle_collection)

        # Link imported object to triangle collection
        for col in imported_obj.users_collection:
            col.objects.unlink(imported_obj)
            
        # Add to triangle collection only
        triangle_collection.objects.link(imported_obj)
        
        # --Vertex Group--
        if props.add_vertex_group:
            
            def assign_macro_node_vertex_groups(obj, model_path, dependencies_path=None):
                def parse_nodes(path):
                    try:
                        tree = ET.parse(path)
                        root = tree.getroot()
                        nodes_section = root.find('Nodes')
                        if not nodes_section:
                            return {}
                        positions = {}
                        for node in nodes_section:
                            if node.get('Type') == 'Node':
                                name = node.tag
                                pos = (
                                    float(node.get('X')),
                                    float(node.get('Y')),
                                    float(node.get('Z'))
                                )
                                positions[name] = pos
                        return positions
                    except:
                        return {}
                   
                node_positions_primary = parse_nodes(model_path)
                node_positions_backup = parse_nodes(dependencies_path) if dependencies_path else {}
                node_positions = {**node_positions_backup, **node_positions_primary}
                
                scene = context.scene
                macro_rules = []
                for item in scene.macro_rules:
                    names_set = set(name.strip() for name in item.names.split(",") if name.strip())
                    macro_rules.append({
                        "names": names_set,
                        "group": item.group
                    })
                
                mesh = obj.data
                vert_lut = {
                    (round(v.co.x, 4), round(v.co.z, 4), round(-v.co.y, 4)): v.index
                    for v in mesh.vertices
                }
                    
                try:
                    tree = ET.parse(model_path)
                    root = tree.getroot()
                    nodes_section = root.find('Nodes')
                    if not nodes_section:
                        return
                except:
                    return

                for node in nodes_section:
                    if node.get('Type') != 'MacroNode':
                        continue

                    child_nodes = []
                    lcc_values = []

                    for i in range(1, 5):
                        cname = node.get(f"ChildNode{i}")
                        lcc = node.get(f"LCC{i}")
                        if not cname or not lcc or cname == "Null":
                            continue
                        if cname in child_nodes:
                            continue
                        child_nodes.append(cname)
                        lcc_values.append(float(lcc))

                    if not child_nodes or sum(lcc_values) == 0.0:
                        continue

                    total_weight = sum(lcc_values)
                    lcc_values = [w / total_weight for w in lcc_values]

                    mx, my, mz = 0.0, 0.0, 0.0
                    valid_children = 0
                    for i, cname in enumerate(child_nodes):
                        if cname not in node_positions:
                            continue
                        x, y, z = node_positions[cname]
                        mx += x * lcc_values[i]
                        my += y * lcc_values[i]
                        mz += z * lcc_values[i]
                        valid_children += 1
                        
                    if valid_children == 0:
                        continue

                    target_pos = Vector((mx, -mz, my))

                    child_set = set(child_nodes)
                    for rule in macro_rules:
                        if rule["names"].issubset(child_set):
                            group_name = rule["group"]
                            if group_name not in obj.vertex_groups:
                                vg = obj.vertex_groups.new(name=group_name)
                            else:
                                vg = obj.vertex_groups[group_name]

                            match_idx = None
                            for v in mesh.vertices:
                                vert_world = obj.matrix_world @ v.co
                                if (vert_world - target_pos).length < 0.01:
                                    match_idx = v.index
                                    break

                            if match_idx is not None:
                                vg.add([match_idx], 1.0, 'REPLACE')
            
            assign_macro_node_vertex_groups(imported_obj, model_path, dependencies_path)
            
            if props.add_vertex_group_include_cloth:
                # Cloth Vertex Group
                cloth_verts = []
                nodes_section = root.find('Nodes')
                if nodes_section is not None:
                    mesh = imported_obj.data
                    world_matrix = imported_obj.matrix_world
                    for node in nodes_section:
                        if node.get('Type') == 'Node' and node.get('Cloth') == '1':
                            xml_x = float(node.get('X'))
                            xml_y = float(node.get('Y'))
                            xml_z = float(node.get('Z'))
                            target_pos = Vector((xml_x, xml_z * -1, xml_y))
                            
                            for i, vert in enumerate(mesh.vertices):
                                vert_world = world_matrix @ vert.co
                                if (vert_world - target_pos).length < 0.001:  # small tolerance
                                    cloth_verts.append(i)
                                
                    if cloth_verts:
                        vgroup = imported_obj.vertex_groups.new(name="Cloth")
                        vgroup.add(cloth_verts, 1.0, 'REPLACE')
                    
        # --------------------

        # Clean up temp obj file
        os.remove(temp_obj_path)

        self.report({'INFO'}, "Model conversion completed")
        return {'FINISHED'}

class ExportModelToXML(bpy.types.Operator):
    bl_idname = "model.export_to_xml"
    bl_label = "Export OBJ to XML"
    bl_description = "Convert the selected Blender object into an XML file"
    filename_ext = ".xml"
    filter_glob: bpy.props.StringProperty(default="*.xml", options={'HIDDEN'})
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    def execute(self, context):
        settings = context.scene.gymnast_tool_model_props
        model_type = settings.model_type_export
        obj = settings.selected_object
        weapon_1_obj = settings.weapon_object_1
        weapon_2_obj = settings.weapon_object_2
        foot_1_obj = settings.foot_object_1
        foot_2_obj = settings.foot_object_2
        starting_node = settings.model_node_offset
        starting_edge = settings.model_edge_offset
        starting_tri = settings.model_tri_offset
        prefix = settings.model_string_name
        model_body_top = settings.model_body_top
        model_body_middle = settings.model_body_middle
        model_body_bottom = settings.model_body_bottom
        model_include_attack_edges = settings.model_include_attack_edges
        model_attack_edges_object_1 = settings.model_attack_edges_object_1
        model_attack_edges_object_2 = settings.model_attack_edges_object_2
        model_export_cloth = settings.model_export_cloth
        model_export_cloth_general_folder = settings.model_export_cloth_general_folder
        model_export_cloth_weapon1_folder = settings.model_export_cloth_weapon1_folder
        model_export_cloth_weapon2_folder = settings.model_export_cloth_weapon2_folder
        model_export_cloth_foot1_folder = settings.model_export_cloth_foot1_folder
        model_export_cloth_foot2_folder = settings.model_export_cloth_foot2_folder
        model_export_capsules = settings.model_export_capsules
        model_export_capsules_folder = settings.model_export_capsules_folder
        pivot_name = settings.model_pivot
        use_pivot = settings.model_use_pivot
        
        # Create XML structure
        root = ET.Element("Scene")
        nodes_element = ET.SubElement(root, "Nodes")
        edges_element = ET.SubElement(root, "Edges")
        figures_element = ET.SubElement(root, "Figures")
        
        # Check if object exists
        if model_type == "MODEL":
            if not obj:
                self.report({'ERROR'}, "No object selected for export")
                return {'CANCELLED'}
                
            if obj.type != 'MESH':
                self.report({'ERROR'}, "Selected object is not a mesh")
                return {'CANCELLED'}
                
            mesh = obj.to_mesh()
            bm = bmesh.new()
            bm.from_mesh(mesh)
            bmesh.ops.triangulate(bm, faces=bm.faces[:])
            
            bm.to_mesh(mesh)
            bm.free()
            
            vertices = mesh.vertices
            edges = mesh.edges
            faces = mesh.polygons
            
            vertex_index_to_node_name = {}
            cloth_indices = set()
            pivot_indices = set()
            
            if model_export_cloth:
                if model_export_cloth_general_folder == "None" or model_export_cloth_general_folder == "":
                    self.report({'ERROR'}, "Cloth's vertex group must be selected for export")
                    return {'CANCELLED'}
                
                cloth_group = obj.vertex_groups.get(model_export_cloth_general_folder)
                if cloth_group:
                    for v in obj.data.vertices:
                        for g in v.groups:
                            if g.group == cloth_group.index:
                                cloth_indices.add(v.index)
                                break
            
            if use_pivot:
                pivot_group = obj.vertex_groups.get(settings.model_pivot)
                if pivot_group:
                    for v in obj.data.vertices:
                        for g in v.groups:
                            if g.group == pivot_group.index:
                                pivot_indices.add(v.index)
                                break
            
        if model_type == "HEAD_GEAR":
            if not obj:
                self.report({'ERROR'}, "No object selected for export")
                return {'CANCELLED'}
                
            if obj.type != 'MESH':
                self.report({'ERROR'}, "Selected object is not a mesh")
                return {'CANCELLED'}
                
            mesh = obj.to_mesh()
            bm = bmesh.new()
            bm.from_mesh(mesh)
            bmesh.ops.triangulate(bm, faces=bm.faces[:])
            
            bm.to_mesh(mesh)
            bm.free()
            
            vertices = mesh.vertices
            edges = mesh.edges
            faces = mesh.polygons
        
        elif model_type == "WEAPON":
            if not weapon_1_obj and not weapon_2_obj:
                self.report({'ERROR'}, "At least one weapon object must be selected for export")
                return {'CANCELLED'}
            
            if model_include_attack_edges:
                if not model_attack_edges_object_1 and not model_attack_edges_object_2:
                    self.report({'ERROR'}, "At least one attack edges object must be selected for export")
                    return {'CANCELLED'}
                
                if model_attack_edges_object_1:
                    mesh_atk1 = model_attack_edges_object_1.to_mesh()
                    bm_atk1 = bmesh.new()
                    bm_atk1.from_mesh(mesh_atk1)
                    bmesh.ops.triangulate(bm_atk1, faces=bm_atk1.faces[:])
                    
                    bm_atk1.to_mesh(mesh_atk1)
                    bm_atk1.free()
                    
                    vertices_atk1 = mesh_atk1.vertices
                    edges_atk1 = mesh_atk1.edges
                    faces_atk1 = mesh_atk1.polygons
                    
                if model_attack_edges_object_2:
                    mesh_atk2 = model_attack_edges_object_2.to_mesh()
                    bm_atk2 = bmesh.new()
                    bm_atk2.from_mesh(mesh_atk2)
                    bmesh.ops.triangulate(bm_atk2, faces=bm_atk2.faces[:])
                    
                    bm_atk2.to_mesh(mesh_atk2)
                    bm_atk2.free()
                    
                    vertices_atk2 = mesh_atk2.vertices
                    edges_atk2 = mesh_atk2.edges
                    faces_atk2 = mesh_atk2.polygons
                    
            
            if weapon_1_obj:
                mesh_1 = weapon_1_obj.to_mesh()
                bm_1 = bmesh.new()
                bm_1.from_mesh(mesh_1)
                bmesh.ops.triangulate(bm_1, faces=bm_1.faces[:])
                
                bm_1.to_mesh(mesh_1)
                bm_1.free()
                
                vertices_1 = mesh_1.vertices
                edges_1 = mesh_1.edges
                faces_1 = mesh_1.polygons
            
            if weapon_2_obj:
                mesh_2 = weapon_2_obj.to_mesh()
                bm_2 = bmesh.new()
                bm_2.from_mesh(mesh_2)
                bmesh.ops.triangulate(bm_2, faces=bm_2.faces[:])
                
                bm_2.to_mesh(mesh_2)
                bm_2.free()
                
                vertices_2 = mesh_2.vertices
                edges_2 = mesh_2.edges
                faces_2 = mesh_2.polygons
        
        elif model_type == "FOOT_GEAR":
            if not foot_1_obj and not foot_2_obj:
                self.report({'ERROR'}, "At least one footwear object must be selected for export")
                return {'CANCELLED'}
            
            if foot_1_obj:
                mesh_1 = foot_1_obj.to_mesh()
                bm_1 = bmesh.new()
                bm_1.from_mesh(mesh_1)
                bmesh.ops.triangulate(bm_1, faces=bm_1.faces[:])
                
                bm_1.to_mesh(mesh_1)
                bm_1.free()
                
                vertices_1 = mesh_1.vertices
                edges_1 = mesh_1.edges
                faces_1 = mesh_1.polygons
            
            if foot_2_obj:
                mesh_2 = foot_2_obj.to_mesh()
                bm_2 = bmesh.new()
                bm_2.from_mesh(mesh_2)
                bmesh.ops.triangulate(bm_2, faces=bm_2.faces[:])
                
                bm_2.to_mesh(mesh_2)
                bm_2.free()
                
                vertices_2 = mesh_2.vertices
                edges_2 = mesh_2.edges
                faces_2 = mesh_2.polygons
        
        elif model_type == "BODY_GEAR":
            if not obj:
                self.report({'ERROR'}, "No object selected for export")
                return {'CANCELLED'}
                
            if obj.type != 'MESH':
                self.report({'ERROR'}, "Selected object is not a mesh")
                return {'CANCELLED'}
                
            mesh = obj.to_mesh()
            bm = bmesh.new()
            bm.from_mesh(mesh)
            bmesh.ops.triangulate(bm, faces=bm.faces[:])
            
            bm.to_mesh(mesh)
            bm.free()
            
            # VERTICES
            vertices = mesh.vertices
            
            chest_node = bpy.data.objects.get("NChest")
            stomach_node = bpy.data.objects.get("NStomach")
            
            if not chest_node or not stomach_node:
                self.report({'ERROR'}, "NChest or NStomach not found")
                return {'CANCELLED'}
            
            z_nchest = chest_node.location.z
            z_nstomach = stomach_node.location.z
            
            top_vertices = []
            mid_vertices = []
            low_vertices = []

            for v in vertices:
                world_pos = obj.matrix_world @ v.co
                z = world_pos.z

                if z >= z_nchest:
                    top_vertices.append(v)
                elif z_nstomach <= z < z_nchest:
                    mid_vertices.append(v)
                else:
                    low_vertices.append(v)
            
            edges = mesh.edges
            faces = mesh.polygons
        
        elif model_type == "RANGED":
            if model_include_attack_edges:
                if not model_attack_edges_object_1:
                    self.report({'ERROR'}, "Attack edges object must be selected for export")
                    return {'CANCELLED'}
                
                if model_attack_edges_object_1:
                    mesh_atk1 = model_attack_edges_object_1.to_mesh()
                    bm_atk1 = bmesh.new()
                    bm_atk1.from_mesh(mesh_atk1)
                    bmesh.ops.triangulate(bm_atk1, faces=bm_atk1.faces[:])
                    
                    bm_atk1.to_mesh(mesh_atk1)
                    bm_atk1.free()
                    
                    vertices_atk1 = mesh_atk1.vertices
                    edges_atk1 = mesh_atk1.edges
                    faces_atk1 = mesh_atk1.polygons
                
            if not obj:
                self.report({'ERROR'}, "No object selected for export")
                return {'CANCELLED'}
                
            if obj.type != 'MESH':
                self.report({'ERROR'}, "Selected object is not a mesh")
                return {'CANCELLED'}
                
            mesh = obj.to_mesh()
            bm = bmesh.new()
            bm.from_mesh(mesh)
            bmesh.ops.triangulate(bm, faces=bm.faces[:])
            
            bm.to_mesh(mesh)
            bm.free()
            
            vertices = mesh.vertices
            edges = mesh.edges
            faces = mesh.polygons
            
            vertex_index_to_node_name = {}
            cloth_indices = set()
            pivot_indices = set()
        
        # Node Function
        if model_type == "HEAD_GEAR" or model_type == "MODEL":
            if model_type == "HEAD_GEAR":
                # Find the required child nodes in the scene
                child_nodes = {
                    "NTop": None,
                    "NHeadS_2": None,
                    "NHeadS_1": None,
                    "NHeadF": None
                }
                
                for obj_childnode in bpy.data.objects:
                    if obj_childnode.name in child_nodes:
                        child_nodes[obj_childnode.name] = obj_childnode.matrix_world.translation
                        
                # Ensure all child nodes exist
                if None in child_nodes.values():
                    missing = [key for key, val in child_nodes.items() if val is None]
                    self.report({'ERROR'}, f"Missing required child nodes: {', '.join(missing)}")
                    return {'CANCELLED'}
                    
                # Child nodes
                p1, p2, p3, p4 = (child_nodes["NTop"], child_nodes["NHeadS_2"], 
                                  child_nodes["NHeadS_1"], child_nodes["NHeadF"])
                
                if model_export_cloth:
                    if model_export_cloth_general_folder == "None" or model_export_cloth_general_folder == "":
                        self.report({'ERROR'}, "Cloth's vertex group must be selected for export")
                        return {'CANCELLED'}
                        
                    cloth_group = obj.vertex_groups.get(model_export_cloth_general_folder)
                    cloth_indices = set()

                    if cloth_group:
                        for v in obj.data.vertices:
                            for g in v.groups:
                                if g.group == cloth_group.index:
                                    cloth_indices.add(v.index)
                                    break
                
                    # Process each vertex as a MacroNode
                    for i, vertex in enumerate(vertices, start=starting_node):
                        if vertex.index in cloth_indices:
                            node_name = f"{prefix}Node{i}"
                            world_pos = obj.matrix_world @ vertex.co

                            ET.SubElement(nodes_element, node_name,
                                          Type="Node",
                                          X=str(world_pos.x),
                                          Y=str(world_pos.z),
                                          Z=str(-world_pos.y),
                                          Mass=str(settings.model_export_cloth_mass),
                                          Fixed="0",
                                          PinFixed="0",
                                          Visible="1",
                                          Collisible="0",
                                          Passive="0",
                                          Cloth="1",
                                          Attenuation=f"{settings.model_export_cloth_attenuation:.2f}",
                                          Rank="0")
                        else:
                            macro_node_name = f"{prefix}Node{i}"
                            macro_pos = obj.matrix_world @ vertex.co
                            
                            # Compute LCC values using tetrahedron volume
                            lcc_values = self.calculate_lcc(macro_pos, p1, p2, p3, p4)
                            
                            # LCC sums to 1 (floating-point precision fix)
                            total_lcc = sum(lcc_values)
                            if total_lcc != 0:
                                lcc_values = [v / total_lcc for v in lcc_values]
                            
                            ET.SubElement(nodes_element, macro_node_name,
                                          Type="MacroNode",
                                          X=str(macro_pos.x),
                                          Y=str(macro_pos.z),
                                          Z=str(-macro_pos.y),
                                          Mass=str(settings.model_node_mass),
                                          Fixed="0",
                                          Visible="1",
                                          Selectable="1",
                                          NodesCount="4",
                                          ChildNode1="NTop",
                                          ChildNode2="NHeadS_2",
                                          ChildNode3="NHeadS_1",
                                          ChildNode4="NHeadF",
                                          LCC1=str(lcc_values[0]),
                                          LCC2=str(lcc_values[1]),
                                          LCC3=str(lcc_values[2]),
                                          LCC4=str(lcc_values[3]))
                
                else:
                    for i, vertex in enumerate(vertices, start=starting_node):
                        macro_node_name = f"{prefix}Node{i}"
                        macro_pos = obj.matrix_world @ vertex.co
                        
                        # Compute LCC values using tetrahedron volume
                        lcc_values = self.calculate_lcc(macro_pos, p1, p2, p3, p4)
                        
                        # LCC sums to 1 (floating-point precision fix)
                        total_lcc = sum(lcc_values)
                        if total_lcc != 0:
                            lcc_values = [v / total_lcc for v in lcc_values]
                        
                        ET.SubElement(nodes_element, macro_node_name,
                                      Type="MacroNode",
                                      X=str(macro_pos.x),
                                      Y=str(macro_pos.z),
                                      Z=str(-macro_pos.y),
                                      Mass=str(settings.model_node_mass),
                                      Fixed="0",
                                      Visible="1",
                                      Selectable="1",
                                      NodesCount="4",
                                      ChildNode1="NTop",
                                      ChildNode2="NHeadS_2",
                                      ChildNode3="NHeadS_1",
                                      ChildNode4="NHeadF",
                                      LCC1=str(lcc_values[0]),
                                      LCC2=str(lcc_values[1]),
                                      LCC3=str(lcc_values[2]),
                                      LCC4=str(lcc_values[3]))
            
                store_edge(context, edges, vertices, "HEAD_GEAR", edges_element, starting_edge, starting_node)
                store_face(context, faces, vertices, "HEAD_GEAR", figures_element, starting_tri, starting_node)
                
            elif model_type == "MODEL":
                for vertex in vertices:
                    idx = vertex.index
                    world_pos = obj.matrix_world @ vertex.co
                    
                    if idx in pivot_indices:
                        node_name = "NPivot"
                    else:
                        node_name = f"{prefix}Node{starting_node + idx}"
                        
                    vertex_index_to_node_name[vertex.index] = node_name
                    
                    is_cloth = idx in cloth_indices
                    
                    attribs = {
                        "Type": "Node",
                        "X": str(world_pos.x),
                        "Y": str(world_pos.z),
                        "Z": str(-world_pos.y),
                        "Mass": str(settings.model_export_cloth_mass) if is_cloth else str(settings.model_node_mass),
                        "Fixed": "0" if is_cloth else ("1" if settings.model_node_fixed else "0"),
                        "PinFixed": "0",
                        "Visible": "1",
                        "Collisible": "0" if is_cloth else ("1" if settings.model_node_collisible else "0"),
                        "Passive": "0",
                        "Cloth": "1" if is_cloth else "0",
                    }
                    
                    if is_cloth:
                        attribs["Attenuation"] = f"{settings.model_export_cloth_attenuation:.2f}"
                        attribs["Rank"] = "0"
                    
                    if node_name is None:
                        raise ValueError(f"Node name is None for vertex index {vertex.index}")
                    
                    ET.SubElement(nodes_element, node_name, **attribs)

                store_edge(context, edges, vertices, "MODEL", edges_element, starting_edge, starting_node, vertex_index_to_node_name)
                store_face(context, faces, vertices, "MODEL", figures_element, starting_tri, starting_node, vertex_index_to_node_name)

        elif model_type == "WEAPON":
            if weapon_1_obj:
                child_nodes = {
                    "Weapon-Node4_1": None,
                    "Weapon-Node3_1": None,
                    "Weapon-Node2_1": None,
                    "Weapon-Node1_1": None
                }
                
                for obj_childnode in bpy.data.objects:
                    if obj_childnode.name in child_nodes:
                        child_nodes[obj_childnode.name] = obj_childnode.matrix_world.translation
                        
                # Ensure all child nodes exist
                if None in child_nodes.values():
                    missing = [key for key, val in child_nodes.items() if val is None]
                    self.report({'ERROR'}, f"Missing required child nodes: {', '.join(missing)}")
                    return {'CANCELLED'}
                    
                # Child nodes
                p1, p2, p3, p4 = (child_nodes["Weapon-Node4_1"], child_nodes["Weapon-Node3_1"], 
                                  child_nodes["Weapon-Node2_1"], child_nodes["Weapon-Node1_1"])
                                  
                store_edge(context, edges_1, vertices_1, "WEAPON", edges_element, settings.model_edge_offset, settings.model_node_offset)
                starting_edge += len(edges_1)
                store_face(context, faces_1, vertices_1, "WEAPON", figures_element, settings.model_tri_offset, settings.model_node_offset)
                starting_tri += len(faces_1)
                    
                if model_export_cloth:
                    if model_export_cloth_weapon1_folder == "None" or model_export_cloth_weapon1_folder == "":
                        self.report({'ERROR'}, "Cloth's vertex group must be selected for export")
                        return {'CANCELLED'}
                        
                    cloth_group_1 = weapon_1_obj.vertex_groups.get(model_export_cloth_weapon1_folder)
                    cloth_indices_1 = set()

                    if cloth_group_1:
                        for v in weapon_1_obj.data.vertices:
                            for g in v.groups:
                                if g.group == cloth_group_1.index:
                                    cloth_indices_1.add(v.index)
                                    break
                    
                    # Process each vertex as a MacroNode
                    for i, vertex in enumerate(vertices_1, start=starting_node):
                        macro_node_name = f"{prefix}Node{i}"
                        macro_pos = weapon_1_obj.matrix_world @ vertex.co
                        
                        if vertex.index in cloth_indices_1:
                            ET.SubElement(nodes_element, macro_node_name,
                                          Type="Node",
                                          X=str(macro_pos.x),
                                          Y=str(macro_pos.z),
                                          Z=str(-macro_pos.y),
                                          Mass=str(settings.model_export_cloth_mass),
                                          Fixed="0",
                                          PinFixed="0",
                                          Visible="1",
                                          Collisible="0",
                                          Passive="0",
                                          Cloth="1",
                                          Attenuation=f"{settings.model_export_cloth_attenuation:.2f}",
                                          Rank="0")
                            
                            starting_node += 1  # Increment the node index
                        else:
                            # Compute LCC values using tetrahedron volume
                            lcc_values = self.calculate_lcc(macro_pos, p1, p2, p3, p4)
                            
                            # LCC sums to 1 (floating-point precision fix)
                            total_lcc = sum(lcc_values)
                            if total_lcc != 0:
                                lcc_values = [v / total_lcc for v in lcc_values]
                            
                            ET.SubElement(nodes_element, macro_node_name,
                                          Type="MacroNode",
                                          X=str(macro_pos.x),
                                          Y=str(macro_pos.z),
                                          Z=str(-macro_pos.y),
                                          Mass=str(settings.model_node_mass),
                                          Fixed="1" if settings.model_node_fixed else "0",
                                          Visible="1",
                                          Selectable="1",
                                          NodesCount="4",
                                          ChildNode1="Weapon-Node4_1",
                                          ChildNode2="Weapon-Node3_1",
                                          ChildNode3="Weapon-Node2_1",
                                          ChildNode4="Weapon-Node1_1",
                                          LCC1=str(lcc_values[0]),
                                          LCC2=str(lcc_values[1]),
                                          LCC3=str(lcc_values[2]),
                                          LCC4=str(lcc_values[3]))
                                          
                            starting_node += 1  # Increment the node index
                            
                else:
                    for i, vertex in enumerate(vertices_1, start=starting_node):
                        macro_node_name = f"{prefix}Node{i}"
                        macro_pos = weapon_1_obj.matrix_world @ vertex.co
                        
                        # Compute LCC values using tetrahedron volume
                        lcc_values = self.calculate_lcc(macro_pos, p1, p2, p3, p4)
                        
                        # LCC sums to 1 (floating-point precision fix)
                        total_lcc = sum(lcc_values)
                        if total_lcc != 0:
                            lcc_values = [v / total_lcc for v in lcc_values]
                        
                        ET.SubElement(nodes_element, macro_node_name,
                                      Type="MacroNode",
                                      X=str(macro_pos.x),
                                      Y=str(macro_pos.z),
                                      Z=str(-macro_pos.y),
                                      Mass=str(settings.model_node_mass),
                                      Fixed="1" if settings.model_node_fixed else "0",
                                      Visible="1",
                                      Selectable="1",
                                      NodesCount="4",
                                      ChildNode1="Weapon-Node4_1",
                                      ChildNode2="Weapon-Node3_1",
                                      ChildNode3="Weapon-Node2_1",
                                      ChildNode4="Weapon-Node1_1",
                                      LCC1=str(lcc_values[0]),
                                      LCC2=str(lcc_values[1]),
                                      LCC3=str(lcc_values[2]),
                                      LCC4=str(lcc_values[3]))
                                      
                        starting_node += 1  # Increment the node index

            if weapon_2_obj:
                child_nodes = {
                    "Weapon-Node4_2": None,
                    "Weapon-Node3_2": None,
                    "Weapon-Node2_2": None,
                    "Weapon-Node1_2": None
                }
                
                for obj_childnode in bpy.data.objects:
                    if obj_childnode.name in child_nodes:
                        child_nodes[obj_childnode.name] = obj_childnode.matrix_world.translation
                        
                # Ensure all child nodes exist
                if None in child_nodes.values():
                    missing = [key for key, val in child_nodes.items() if val is None]
                    self.report({'ERROR'}, f"Missing required child nodes: {', '.join(missing)}")
                    return {'CANCELLED'}
                    
                # Child nodes
                p1, p2, p3, p4 = (child_nodes["Weapon-Node4_2"], child_nodes["Weapon-Node3_2"], 
                                  child_nodes["Weapon-Node2_2"], child_nodes["Weapon-Node1_2"])    
                
                
                store_edge(context, edges_2, vertices_2, "WEAPON", edges_element, starting_edge, starting_node)
                store_face(context, faces_2, vertices_2, "WEAPON", figures_element, starting_tri, starting_node)
                
                if model_export_cloth:
                    if model_export_cloth_weapon2_folder == "None" or model_export_cloth_weapon2_folder == "":
                        self.report({'ERROR'}, "Cloth's vertex group must be selected for export")
                        return {'CANCELLED'}
                        
                    cloth_group_2 = weapon_2_obj.vertex_groups.get(model_export_cloth_weapon2_folder)
                    cloth_indices_2 = set()

                    if cloth_group_2:
                        for v in weapon_2_obj.data.vertices:
                            for g in v.groups:
                                if g.group == cloth_group_2.index:
                                    cloth_indices_2.add(v.index)
                                    break
                                    
                    for i, vertex in enumerate(vertices_2, start=starting_node):
                        macro_node_name = f"{prefix}Node{i}"
                        macro_pos = weapon_2_obj.matrix_world @ vertex.co
                        
                        if vertex.index in cloth_indices_2:
                            ET.SubElement(nodes_element, macro_node_name,
                                          Type="Node",
                                          X=str(macro_pos.x),
                                          Y=str(macro_pos.z),
                                          Z=str(-macro_pos.y),
                                          Mass=str(settings.model_export_cloth_mass),
                                          Fixed="0",
                                          PinFixed="0",
                                          Visible="1",
                                          Collisible="0",
                                          Passive="0",
                                          Cloth="1",
                                          Attenuation=f"{settings.model_export_cloth_attenuation:.2f}",
                                          Rank="0")
                            
                            starting_node += 1  # Increment the node index
                        else:
                            # Compute LCC values using tetrahedron volume
                            lcc_values = self.calculate_lcc(macro_pos, p1, p2, p3, p4)
                            
                            # LCC sums to 1 (floating-point precision fix)
                            total_lcc = sum(lcc_values)
                            if total_lcc != 0:
                                lcc_values = [v / total_lcc for v in lcc_values]
                            
                            ET.SubElement(nodes_element, macro_node_name,
                                          Type="MacroNode",
                                          X=str(macro_pos.x),
                                          Y=str(macro_pos.z),
                                          Z=str(-macro_pos.y),
                                          Mass=str(settings.model_node_mass),
                                          Fixed="1" if settings.model_node_fixed else "0",
                                          Visible="1",
                                          Selectable="1",
                                          NodesCount="4",
                                          ChildNode1="Weapon-Node4_2",
                                          ChildNode2="Weapon-Node3_2",
                                          ChildNode3="Weapon-Node2_2",
                                          ChildNode4="Weapon-Node1_2",
                                          LCC1=str(lcc_values[0]),
                                          LCC2=str(lcc_values[1]),
                                          LCC3=str(lcc_values[2]),
                                          LCC4=str(lcc_values[3]))
                                          
                            starting_node += 1  # Increment the node index
                    
                else:
                    # Process each vertex as a MacroNode
                    for i, vertex in enumerate(vertices_2, start=starting_node):
                        macro_node_name = f"{prefix}Node{i}"
                        macro_pos = weapon_2_obj.matrix_world @ vertex.co

                        # Compute LCC values using tetrahedron volume
                        lcc_values = self.calculate_lcc(macro_pos, p1, p2, p3, p4)
                        
                        # LCC sums to 1 (floating-point precision fix)
                        total_lcc = sum(lcc_values)
                        if total_lcc != 0:
                            lcc_values = [v / total_lcc for v in lcc_values]
                        
                        ET.SubElement(nodes_element, macro_node_name,
                                      Type="MacroNode",
                                      X=str(macro_pos.x),
                                      Y=str(macro_pos.z),
                                      Z=str(-macro_pos.y),
                                      Mass=str(settings.model_node_mass),
                                      Fixed="1" if settings.model_node_fixed else "0",
                                      Visible="1",
                                      Selectable="1",
                                      NodesCount="4",
                                      ChildNode1="Weapon-Node4_2",
                                      ChildNode2="Weapon-Node3_2",
                                      ChildNode3="Weapon-Node2_2",
                                      ChildNode4="Weapon-Node1_2",
                                      LCC1=str(lcc_values[0]),
                                      LCC2=str(lcc_values[1]),
                                      LCC3=str(lcc_values[2]),
                                      LCC4=str(lcc_values[3]))
                                      
                        starting_node += 1  # Increment the node index
            
            if weapon_1_obj and model_include_attack_edges and model_attack_edges_object_1:
                child_nodes = {
                    "Weapon-Node4_1": None,
                    "Weapon-Node3_1": None,
                    "Weapon-Node2_1": None,
                    "Weapon-Node1_1": None
                }
                
                for obj_childnode in bpy.data.objects:
                    if obj_childnode.name in child_nodes:
                        child_nodes[obj_childnode.name] = obj_childnode.matrix_world.translation
                
                # Ensure all child nodes exist
                if None in child_nodes.values():
                    missing = [key for key, val in child_nodes.items() if val is None]
                    self.report({'ERROR'}, f"Missing required child nodes: {', '.join(missing)}")
                    return {'CANCELLED'}
                
                # Child nodes
                p1, p2, p3, p4 = (child_nodes["Weapon-Node4_1"], child_nodes["Weapon-Node3_1"], 
                                  child_nodes["Weapon-Node2_1"], child_nodes["Weapon-Node1_1"])
                                  
                store_edge_attack(context, edges_atk1, vertices_atk1, edges_element, starting_edge, starting_node, True)
                
                # Process each vertex as a MacroNode
                for i, vertex in enumerate(vertices_atk1, start=starting_node):
                    macro_node_name = f"{prefix}Node{i}"
                    macro_pos = model_attack_edges_object_1.matrix_world @ vertex.co

                    # Compute LCC values using tetrahedron volume
                    lcc_values = self.calculate_lcc(macro_pos, p1, p2, p3, p4)
                    
                    # LCC sums to 1 (floating-point precision fix)
                    total_lcc = sum(lcc_values)
                    if total_lcc != 0:
                        lcc_values = [v / total_lcc for v in lcc_values]
                    
                    ET.SubElement(nodes_element, macro_node_name,
                                  Type="MacroNode",
                                  X=str(macro_pos.x),
                                  Y=str(macro_pos.z),
                                  Z=str(-macro_pos.y),
                                  Mass=str(settings.model_node_mass),
                                  Fixed="1" if settings.model_node_fixed else "0",
                                  Visible="1",
                                  Selectable="1",
                                  NodesCount="4",
                                  ChildNode1="Weapon-Node4_1",
                                  ChildNode2="Weapon-Node3_1",
                                  ChildNode3="Weapon-Node2_1",
                                  ChildNode4="Weapon-Node1_1",
                                  LCC1=str(lcc_values[0]),
                                  LCC2=str(lcc_values[1]),
                                  LCC3=str(lcc_values[2]),
                                  LCC4=str(lcc_values[3]))
                                  
                    starting_node += 1  # Increment the node index
              
            if weapon_2_obj and model_include_attack_edges and model_attack_edges_object_2:
                child_nodes = {
                    "Weapon-Node4_2": None,
                    "Weapon-Node3_2": None,
                    "Weapon-Node2_2": None,
                    "Weapon-Node1_2": None
                }
                
                for obj_childnode in bpy.data.objects:
                    if obj_childnode.name in child_nodes:
                        child_nodes[obj_childnode.name] = obj_childnode.matrix_world.translation
                
                # Ensure all child nodes exist
                if None in child_nodes.values():
                    missing = [key for key, val in child_nodes.items() if val is None]
                    self.report({'ERROR'}, f"Missing required child nodes: {', '.join(missing)}")
                    return {'CANCELLED'}
                
                # Child nodes
                p1, p2, p3, p4 = (child_nodes["Weapon-Node4_2"], child_nodes["Weapon-Node3_2"], 
                                  child_nodes["Weapon-Node2_2"], child_nodes["Weapon-Node1_2"])
                                  
                store_edge_attack(context, edges_atk2, vertices_atk2, edges_element, starting_edge, starting_node, False)
                
                # Process each vertex as a MacroNode
                for i, vertex in enumerate(vertices_atk2, start=starting_node):
                    macro_node_name = f"{prefix}Node{i}"
                    macro_pos = model_attack_edges_object_2.matrix_world @ vertex.co

                    # Compute LCC values using tetrahedron volume
                    lcc_values = self.calculate_lcc(macro_pos, p1, p2, p3, p4)
                    
                    # LCC sums to 1 (floating-point precision fix)
                    total_lcc = sum(lcc_values)
                    if total_lcc != 0:
                        lcc_values = [v / total_lcc for v in lcc_values]
                    
                    ET.SubElement(nodes_element, macro_node_name,
                                  Type="MacroNode",
                                  X=str(macro_pos.x),
                                  Y=str(macro_pos.z),
                                  Z=str(-macro_pos.y),
                                  Mass=str(settings.model_node_mass),
                                  Fixed="1" if settings.model_node_fixed else "0",
                                  Visible="1",
                                  Selectable="1",
                                  NodesCount="4",
                                  ChildNode1="Weapon-Node4_2",
                                  ChildNode2="Weapon-Node3_2",
                                  ChildNode3="Weapon-Node2_2",
                                  ChildNode4="Weapon-Node1_2",
                                  LCC1=str(lcc_values[0]),
                                  LCC2=str(lcc_values[1]),
                                  LCC3=str(lcc_values[2]),
                                  LCC4=str(lcc_values[3]))
                
        elif model_type == "FOOT_GEAR":
            
            if foot_1_obj:
                child_nodes = {
                    "NToeS_1": None,
                    "NToe_1": None,
                    "NHeel_1": None,
                    "NAnkle_1": None
                }
                
                for obj_childnode in bpy.data.objects:
                    if obj_childnode.name in child_nodes:
                        child_nodes[obj_childnode.name] = obj_childnode.matrix_world.translation
                        
                # Ensure all child nodes exist
                if None in child_nodes.values():
                    missing = [key for key, val in child_nodes.items() if val is None]
                    self.report({'ERROR'}, f"Missing required child nodes: {', '.join(missing)}")
                    return {'CANCELLED'}
                    
                # Child nodes
                p1, p2, p3, p4 = (child_nodes["NToeS_1"], child_nodes["NToe_1"], 
                                  child_nodes["NHeel_1"], child_nodes["NAnkle_1"])
                                  
                store_edge(context, edges_1, vertices_1, "FOOT_GEAR", edges_element, 1, settings.model_node_offset)
                starting_edge += len(edges_1)
                store_face(context, faces_1, vertices_1, "FOOT_GEAR", figures_element, 1, settings.model_node_offset)
                starting_tri += len(faces_1)

                if model_export_cloth:
                    if model_export_cloth_foot1_folder == "None" or model_export_cloth_foot1_folder == "":
                        self.report({'ERROR'}, "Cloth's vertex group must be selected for export")
                        return {'CANCELLED'}
                        
                    cloth_group_1 = foot_1_obj.vertex_groups.get(model_export_cloth_foot1_folder)
                    cloth_indices_1 = set()

                    if cloth_group_1:
                        for v in foot_1_obj.data.vertices:
                            for g in v.groups:
                                if g.group == cloth_group_1.index:
                                    cloth_indices_1.add(v.index)
                                    break
                    
                    for i, vertex in enumerate(vertices_1, start=starting_node):
                        macro_node_name = f"{prefix}Node{i}"
                        macro_pos = foot_1_obj.matrix_world @ vertex.co
                        
                        if vertex.index in cloth_indices_1:
                            ET.SubElement(nodes_element, macro_node_name,
                                          Type="Node",
                                          X=str(macro_pos.x),
                                          Y=str(macro_pos.z),
                                          Z=str(-macro_pos.y),
                                          Mass=str(settings.model_export_cloth_mass),
                                          Fixed="0",
                                          PinFixed="0",
                                          Visible="1",
                                          Collisible="0",
                                          Passive="0",
                                          Cloth="1",
                                          Attenuation=f"{settings.model_export_cloth_attenuation:.2f}",
                                          Rank="0")
                            
                            starting_node += 1  # Increment the node index
                            
                        else:
                            # Compute LCC values using tetrahedron volume
                            lcc_values = self.calculate_lcc(macro_pos, p1, p2, p3, p4)
                            
                            # LCC sums to 1 (floating-point precision fix)
                            total_lcc = sum(lcc_values)
                            if total_lcc != 0:
                                lcc_values = [v / total_lcc for v in lcc_values]
                            
                            ET.SubElement(nodes_element, macro_node_name,
                                          Type="MacroNode",
                                          X=str(macro_pos.x),
                                          Y=str(macro_pos.z),
                                          Z=str(-macro_pos.y),
                                          Mass=str(settings.model_node_mass),
                                          Fixed="0",
                                          Visible="1",
                                          Selectable="1",
                                          NodesCount="4",
                                          ChildNode1="NToeS_1",
                                          ChildNode2="NToe_1",
                                          ChildNode3="NHeel_1",
                                          ChildNode4="NAnkle_1",
                                          LCC1=str(lcc_values[0]),
                                          LCC2=str(lcc_values[1]),
                                          LCC3=str(lcc_values[2]),
                                          LCC4=str(lcc_values[3]))
                                          
                            starting_node += 1  # Increment the node index
                    
                else:
                    # Process each vertex as a MacroNode
                    for i, vertex in enumerate(vertices_1, start=starting_node):
                        macro_node_name = f"{prefix}Node{i}"
                        macro_pos = foot_1_obj.matrix_world @ vertex.co

                        # Compute LCC values using tetrahedron volume
                        lcc_values = self.calculate_lcc(macro_pos, p1, p2, p3, p4)
                        
                        # LCC sums to 1 (floating-point precision fix)
                        total_lcc = sum(lcc_values)
                        if total_lcc != 0:
                            lcc_values = [v / total_lcc for v in lcc_values]
                        
                        ET.SubElement(nodes_element, macro_node_name,
                                      Type="MacroNode",
                                      X=str(macro_pos.x),
                                      Y=str(macro_pos.z),
                                      Z=str(-macro_pos.y),
                                      Mass=str(settings.model_node_mass),
                                      Fixed="0",
                                      Visible="1",
                                      Selectable="1",
                                      NodesCount="4",
                                      ChildNode1="NToeS_1",
                                      ChildNode2="NToe_1",
                                      ChildNode3="NHeel_1",
                                      ChildNode4="NAnkle_1",
                                      LCC1=str(lcc_values[0]),
                                      LCC2=str(lcc_values[1]),
                                      LCC3=str(lcc_values[2]),
                                      LCC4=str(lcc_values[3]))
                                      
                        starting_node += 1  # Increment the node index
                        
                    
            if foot_2_obj:
                child_nodes = {
                    "NToeS_2": None,
                    "NToe_2": None,
                    "NHeel_2": None,
                    "NAnkle_2": None
                }
                
                for obj_childnode in bpy.data.objects:
                    if obj_childnode.name in child_nodes:
                        child_nodes[obj_childnode.name] = obj_childnode.matrix_world.translation
                        
                # Ensure all child nodes exist
                if None in child_nodes.values():
                    missing = [key for key, val in child_nodes.items() if val is None]
                    self.report({'ERROR'}, f"Missing required child nodes: {', '.join(missing)}")
                    return {'CANCELLED'}
                    
                # Child nodes
                p1, p2, p3, p4 = (child_nodes["NToeS_2"], child_nodes["NToe_2"], 
                                  child_nodes["NHeel_2"], child_nodes["NAnkle_2"])
                
                store_edge(context, edges_2, vertices_2, "FOOT_GEAR", edges_element, starting_edge, starting_node)
                store_face(context, faces_2, vertices_2, "FOOT_GEAR", figures_element, starting_tri, starting_node)
                
                if model_export_cloth:
                    if model_export_cloth_foot2_folder == "None" or model_export_cloth_foot2_folder == "":
                        self.report({'ERROR'}, "Cloth's vertex group must be selected for export")
                        return {'CANCELLED'}
                        
                    cloth_group_2 = foot_1_obj.vertex_groups.get(model_export_cloth_foot2_folder)
                    cloth_indices_2 = set()

                    if cloth_group_2:
                        for v in foot_2_obj.data.vertices:
                            for g in v.groups:
                                if g.group == cloth_group_2.index:
                                    cloth_indices_2.add(v.index)
                                    break
                                    
                    for i, vertex in enumerate(vertices_2, start=starting_node):
                        macro_node_name = f"{prefix}Node{i}"
                        macro_pos = foot_1_obj.matrix_world @ vertex.co
                        
                        if vertex.index in cloth_indices_2:
                            ET.SubElement(nodes_element, macro_node_name,
                                          Type="Node",
                                          X=str(macro_pos.x),
                                          Y=str(macro_pos.z),
                                          Z=str(-macro_pos.y),
                                          Mass=str(settings.model_export_cloth_mass),
                                          Fixed="0",
                                          PinFixed="0",
                                          Visible="1",
                                          Collisible="0",
                                          Passive="0",
                                          Cloth="1",
                                          Attenuation=f"{settings.model_export_cloth_attenuation:.2f}",
                                          Rank="0")
                        else:
                            # Compute LCC values using tetrahedron volume
                            lcc_values = self.calculate_lcc(macro_pos, p1, p2, p3, p4)
                            
                            # LCC sums to 1 (floating-point precision fix)
                            total_lcc = sum(lcc_values)
                            if total_lcc != 0:
                                lcc_values = [v / total_lcc for v in lcc_values]
                            
                            ET.SubElement(nodes_element, macro_node_name,
                                          Type="MacroNode",
                                          X=str(macro_pos.x),
                                          Y=str(macro_pos.z),
                                          Z=str(-macro_pos.y),
                                          Mass=str(settings.model_node_mass),
                                          Fixed="0",
                                          Visible="1",
                                          Selectable="1",
                                          NodesCount="4",
                                          ChildNode1="NToeS_2",
                                          ChildNode2="NToe_2",
                                          ChildNode3="NHeel_2",
                                          ChildNode4="NAnkle_2",
                                          LCC1=str(lcc_values[0]),
                                          LCC2=str(lcc_values[1]),
                                          LCC3=str(lcc_values[2]),
                                          LCC4=str(lcc_values[3]))
                                      
                    
                else:
                    # Process each vertex as a MacroNode
                    for i, vertex in enumerate(vertices_2, start=starting_node):
                        macro_node_name = f"{prefix}Node{i}"
                        macro_pos = foot_2_obj.matrix_world @ vertex.co

                        # Compute LCC values using tetrahedron volume
                        lcc_values = self.calculate_lcc(macro_pos, p1, p2, p3, p4)
                        
                        # LCC sums to 1 (floating-point precision fix)
                        total_lcc = sum(lcc_values)
                        if total_lcc != 0:
                            lcc_values = [v / total_lcc for v in lcc_values]
                        
                        ET.SubElement(nodes_element, macro_node_name,
                                      Type="MacroNode",
                                      X=str(macro_pos.x),
                                      Y=str(macro_pos.z),
                                      Z=str(-macro_pos.y),
                                      Mass=str(settings.model_node_mass),
                                      Fixed="0",
                                      Visible="1",
                                      Selectable="1",
                                      NodesCount="4",
                                      ChildNode1="NToeS_2",
                                      ChildNode2="NToe_2",
                                      ChildNode3="NHeel_2",
                                      ChildNode4="NAnkle_2",
                                      LCC1=str(lcc_values[0]),
                                      LCC2=str(lcc_values[1]),
                                      LCC3=str(lcc_values[2]),
                                      LCC4=str(lcc_values[3]))
        
        elif model_type == "BODY_GEAR":
            child_nodes_upper = {
                "NChestS_1": None,
                "NChestF": None,
                "NChestS_2": None,
                "NNeck": None
            }
            
            child_nodes_middle = {
                "NStomachS_1": None,
                "NStomachF": None,
                "NStomachS_2": None,
                "NChest": None
            }
            
            child_nodes_lower = {
                "NPelvisF": None,
                "NHip_1": None,
                "NHip_2": None,
                "NStomach": None
            }
            
            # child_nodes_upper
            for obj_childnode in bpy.data.objects:
                if obj_childnode.name in child_nodes_upper:
                    child_nodes_upper[obj_childnode.name] = obj_childnode.matrix_world.translation

            # child_nodes_middle
            for obj_childnode in bpy.data.objects:
                if obj_childnode.name in child_nodes_middle:
                    child_nodes_middle[obj_childnode.name] = obj_childnode.matrix_world.translation

            # child_nodes_lower
            for obj_childnode in bpy.data.objects:
                if obj_childnode.name in child_nodes_lower:
                    child_nodes_lower[obj_childnode.name] = obj_childnode.matrix_world.translation

            # Validate all child node groups
            missing_upper = [key for key, val in child_nodes_upper.items() if val is None]
            missing_middle = [key for key, val in child_nodes_middle.items() if val is None]
            missing_lower = [key for key, val in child_nodes_lower.items() if val is None]
            
            missing = missing_upper + missing_middle + missing_lower
            if missing:
                self.report({'ERROR'}, f"Missing required child nodes: {', '.join(missing)}")
                return {'CANCELLED'}
            
            # Child nodes
            p1_upper, p2_upper, p3_upper, p4_upper = (
                child_nodes_upper["NChestS_1"], child_nodes_upper["NChestF"],
                child_nodes_upper["NChestS_2"], child_nodes_upper["NNeck"]
            )

            p1_middle, p2_middle, p3_middle, p4_middle = (
                child_nodes_middle["NStomachS_1"], child_nodes_middle["NStomachF"],
                child_nodes_middle["NStomachS_2"], child_nodes_middle["NChest"]
            )

            p1_lower, p2_lower, p3_lower, p4_lower = (
                child_nodes_lower["NPelvisF"], child_nodes_lower["NHip_1"],
                child_nodes_lower["NHip_2"], child_nodes_lower["NStomach"]
            )
            
            store_edge(context, edges, vertices, "BODY_GEAR", edges_element, starting_edge, starting_node)
            store_face(context, faces, vertices, "BODY_GEAR", figures_element, starting_tri, starting_node)
            
            if model_export_cloth:
                if model_export_cloth_general_folder == "None" or model_export_cloth_general_folder == "":
                    self.report({'ERROR'}, "Cloth's vertex group must be selected for export")
                    return {'CANCELLED'}
                    
                cloth_group = obj.vertex_groups.get(model_export_cloth_general_folder)
                cloth_indices = set()

                if cloth_group:
                    for v in obj.data.vertices:
                        for g in v.groups:
                            if g.group == cloth_group.index:
                                cloth_indices.add(v.index)
                                break
                
                for i, vertex in enumerate(vertices, start=starting_node):
                    macro_node_name = f"{prefix}Node{i}"
                    macro_pos = obj.matrix_world @ vertex.co
                    
                    if vertex.index in cloth_indices:

                        ET.SubElement(nodes_element, macro_node_name,
                                      Type="Node",
                                      X=str(macro_pos.x),
                                      Y=str(macro_pos.z),
                                      Z=str(-macro_pos.y),
                                      Mass=str(settings.model_export_cloth_mass),
                                      Fixed="0",
                                      PinFixed="0",
                                      Visible="1",
                                      Collisible="0",
                                      Passive="0",
                                      Cloth="1",
                                      Attenuation=f"{settings.model_export_cloth_attenuation:.2f}",
                                      Rank="0")
                    else:
                        z = macro_pos.z
                        
                        # Decide which child nodes to use
                        if z >= p4_middle.z:  # highest group
                            if model_body_top == 'CHEST':
                                p1, p2, p3, p4 = p1_upper, p2_upper, p3_upper, p4_upper
                                cn1, cn2, cn3, cn4 = "NChestS_1", "NChestF", "NChestS_2", "NNeck"
                            elif model_body_top == 'STOMACH':
                                p1, p2, p3, p4 = p1_middle, p2_middle, p3_middle, p4_middle
                                cn1, cn2, cn3, cn4 = "NStomachS_1", "NStomachF", "NStomachS_2", "NChest"
                            elif model_body_top == 'HIP':
                                p1, p2, p3, p4 = p1_lower, p2_lower, p3_lower, p4_lower
                                cn1, cn2, cn3, cn4 = "NPelvisF", "NHip_1", "NHip_2", "NStomach"
                                
                        elif p4_lower.z <= z < p4_middle.z:  # middle group
                            if model_body_middle == 'CHEST':
                                p1, p2, p3, p4 = p1_upper, p2_upper, p3_upper, p4_upper
                                cn1, cn2, cn3, cn4 = "NChestS_1", "NChestF", "NChestS_2", "NNeck"
                            elif model_body_middle == 'STOMACH':
                                p1, p2, p3, p4 = p1_middle, p2_middle, p3_middle, p4_middle
                                cn1, cn2, cn3, cn4 = "NStomachS_1", "NStomachF", "NStomachS_2", "NChest"
                            elif model_body_middle == 'HIP':
                                p1, p2, p3, p4 = p1_lower, p2_lower, p3_lower, p4_lower
                                cn1, cn2, cn3, cn4 = "NPelvisF", "NHip_1", "NHip_2", "NStomach"
                                
                        else:  # lowest group
                            if model_body_bottom == 'CHEST':
                                p1, p2, p3, p4 = p1_upper, p2_upper, p3_upper, p4_upper
                                cn1, cn2, cn3, cn4 = "NChestS_1", "NChestF", "NChestS_2", "NNeck"
                            elif model_body_bottom == 'STOMACH':
                                p1, p2, p3, p4 = p1_middle, p2_middle, p3_middle, p4_middle
                                cn1, cn2, cn3, cn4 = "NStomachS_1", "NStomachF", "NStomachS_2", "NChest"
                            elif model_body_bottom == 'HIP':
                                p1, p2, p3, p4 = p1_lower, p2_lower, p3_lower, p4_lower
                                cn1, cn2, cn3, cn4 = "NPelvisF", "NHip_1", "NHip_2", "NStomach"

                        # Compute LCC values using tetrahedron volume
                        lcc_values = self.calculate_lcc(macro_pos, p1, p2, p3, p4)
                        
                        # LCC sums to 1 (floating-point precision fix)
                        total_lcc = sum(lcc_values)
                        if total_lcc != 0:
                            lcc_values = [v / total_lcc for v in lcc_values]
                        
                        ET.SubElement(nodes_element, macro_node_name,
                                      Type="MacroNode",
                                      X=str(macro_pos.x),
                                      Y=str(macro_pos.z),
                                      Z=str(-macro_pos.y),
                                      Mass=str(settings.model_node_mass),
                                      Fixed="0",
                                      Visible="1",
                                      Selectable="1",
                                      NodesCount="4",
                                      ChildNode1=cn1,
                                      ChildNode2=cn2,
                                      ChildNode3=cn3,
                                      ChildNode4=cn4,
                                      LCC1=str(lcc_values[0]),
                                      LCC2=str(lcc_values[1]),
                                      LCC3=str(lcc_values[2]),
                                      LCC4=str(lcc_values[3]))
                
            else:
                for i, vertex in enumerate(vertices, start=starting_node):
                        macro_node_name = f"{prefix}Node{i}"
                        macro_pos = obj.matrix_world @ vertex.co
                        z = macro_pos.z
                        
                        # Decide which child nodes to use
                        if z >= p4_middle.z:  # highest group
                            if model_body_top == 'CHEST':
                                p1, p2, p3, p4 = p1_upper, p2_upper, p3_upper, p4_upper
                                cn1, cn2, cn3, cn4 = "NChestS_1", "NChestF", "NChestS_2", "NNeck"
                            elif model_body_top == 'STOMACH':
                                p1, p2, p3, p4 = p1_middle, p2_middle, p3_middle, p4_middle
                                cn1, cn2, cn3, cn4 = "NStomachS_1", "NStomachF", "NStomachS_2", "NChest"
                            elif model_body_top == 'HIP':
                                p1, p2, p3, p4 = p1_lower, p2_lower, p3_lower, p4_lower
                                cn1, cn2, cn3, cn4 = "NPelvisF", "NHip_1", "NHip_2", "NStomach"
                                
                        elif p4_lower.z <= z < p4_middle.z:  # middle group
                            if model_body_middle == 'CHEST':
                                p1, p2, p3, p4 = p1_upper, p2_upper, p3_upper, p4_upper
                                cn1, cn2, cn3, cn4 = "NChestS_1", "NChestF", "NChestS_2", "NNeck"
                            elif model_body_middle == 'STOMACH':
                                p1, p2, p3, p4 = p1_middle, p2_middle, p3_middle, p4_middle
                                cn1, cn2, cn3, cn4 = "NStomachS_1", "NStomachF", "NStomachS_2", "NChest"
                            elif model_body_middle == 'HIP':
                                p1, p2, p3, p4 = p1_lower, p2_lower, p3_lower, p4_lower
                                cn1, cn2, cn3, cn4 = "NPelvisF", "NHip_1", "NHip_2", "NStomach"
                                
                        else:  # lowest group
                            if model_body_bottom == 'CHEST':
                                p1, p2, p3, p4 = p1_upper, p2_upper, p3_upper, p4_upper
                                cn1, cn2, cn3, cn4 = "NChestS_1", "NChestF", "NChestS_2", "NNeck"
                            elif model_body_bottom == 'STOMACH':
                                p1, p2, p3, p4 = p1_middle, p2_middle, p3_middle, p4_middle
                                cn1, cn2, cn3, cn4 = "NStomachS_1", "NStomachF", "NStomachS_2", "NChest"
                            elif model_body_bottom == 'HIP':
                                p1, p2, p3, p4 = p1_lower, p2_lower, p3_lower, p4_lower
                                cn1, cn2, cn3, cn4 = "NPelvisF", "NHip_1", "NHip_2", "NStomach"

                        # Compute LCC values using tetrahedron volume
                        lcc_values = self.calculate_lcc(macro_pos, p1, p2, p3, p4)
                        
                        # LCC sums to 1 (floating-point precision fix)
                        total_lcc = sum(lcc_values)
                        if total_lcc != 0:
                            lcc_values = [v / total_lcc for v in lcc_values]
                        
                        ET.SubElement(nodes_element, macro_node_name,
                                      Type="MacroNode",
                                      X=str(macro_pos.x),
                                      Y=str(macro_pos.z),
                                      Z=str(-macro_pos.y),
                                      Mass=str(settings.model_node_mass),
                                      Fixed="0",
                                      Visible="1",
                                      Selectable="1",
                                      NodesCount="4",
                                      ChildNode1=cn1,
                                      ChildNode2=cn2,
                                      ChildNode3=cn3,
                                      ChildNode4=cn4,
                                      LCC1=str(lcc_values[0]),
                                      LCC2=str(lcc_values[1]),
                                      LCC3=str(lcc_values[2]),
                                      LCC4=str(lcc_values[3]))
            
            if settings.model_include_necessary_tri_body:
                add_necessary_triangle_body_gear(context, prefix, figures_element)
        
        elif model_type == "RANGED":
            if obj:
                child_nodes = {
                    "Ranged-Node1_1": None,
                    "Ranged-Node2_1": None,
                    "Ranged-Node3_1": None,
                    "Ranged-Node4_1": None
                }
                
                for obj_childnode in bpy.data.objects:
                    if obj_childnode.name in child_nodes:
                        child_nodes[obj_childnode.name] = obj_childnode.matrix_world.translation
                        
                # Ensure all child nodes exist
                if None in child_nodes.values():
                    missing = [key for key, val in child_nodes.items() if val is None]
                    self.report({'ERROR'}, f"Missing required child nodes in blender scene: {', '.join(missing)}")
                    return {'CANCELLED'}
                    
                # Child nodes
                p1, p2, p3, p4 = (child_nodes["Ranged-Node1_1"], child_nodes["Ranged-Node2_1"], 
                                  child_nodes["Ranged-Node3_1"], child_nodes["Ranged-Node4_1"])
                                  
                store_edge(context, edges, vertices, "RANGED", edges_element, settings.model_edge_offset, settings.model_node_offset)
                starting_edge += len(edges)
                store_face(context, faces, vertices, "RANGED", figures_element, settings.model_tri_offset, settings.model_node_offset)
                starting_tri += len(faces)
                    
                if model_export_cloth:
                    if model_export_cloth_general_folder == "None" or model_export_cloth_general_folder == "":
                        self.report({'ERROR'}, "Cloth's vertex group must be selected for export")
                        return {'CANCELLED'}
                        
                    cloth_group = obj.vertex_groups.get(model_export_cloth_general_folder)
                    cloth_indices = set()

                    if cloth_group:
                        for v in obj.data.vertices:
                            for g in v.groups:
                                if g.group == cloth_group.index:
                                    cloth_indices.add(v.index)
                                    break
                
                    # Process each vertex as a MacroNode
                    for i, vertex in enumerate(vertices, start=starting_node):
                        if vertex.index in cloth_indices:
                            node_name = f"{prefix}Node{i}"
                            world_pos = obj.matrix_world @ vertex.co

                            ET.SubElement(nodes_element, node_name,
                                          Type="Node",
                                          X=str(world_pos.x),
                                          Y=str(world_pos.z),
                                          Z=str(-world_pos.y),
                                          Mass=str(settings.model_export_cloth_mass),
                                          Fixed="0",
                                          PinFixed="0",
                                          Visible="1",
                                          Collisible="0",
                                          Passive="0",
                                          Cloth="1",
                                          Attenuation=f"{settings.model_export_cloth_attenuation:.2f}",
                                          Rank="0")
                        else:
                            macro_node_name = f"{prefix}Node{i}"
                            macro_pos = obj.matrix_world @ vertex.co
                            
                            # Compute LCC values using tetrahedron volume
                            lcc_values = self.calculate_lcc(macro_pos, p1, p2, p3, p4)
                            
                            # LCC sums to 1 (floating-point precision fix)
                            total_lcc = sum(lcc_values)
                            if total_lcc != 0:
                                lcc_values = [v / total_lcc for v in lcc_values]
                            
                            ET.SubElement(nodes_element, macro_node_name,
                                Type="MacroNode",
                                X=str(macro_pos.x),
                                Y=str(macro_pos.z),
                                Z=str(-macro_pos.y),
                                Mass=str(settings.model_node_mass),
                                Fixed="1" if settings.model_node_fixed else "0",
                                Visible="1",
                                Selectable="1",
                                NodesCount="4",
                                ChildNode1="Ranged-Node1_1",
                                ChildNode2="Ranged-Node2_1",
                                ChildNode3="Ranged-Node3_1",
                                ChildNode4="Ranged-Node4_1",
                                LCC1=str(lcc_values[0]),
                                LCC2=str(lcc_values[1]),
                                LCC3=str(lcc_values[2]),
                                LCC4=str(lcc_values[3])
                            )
                
                else:
                    for i, vertex in enumerate(vertices, start=starting_node):
                        macro_node_name = f"{prefix}Node{i}"
                        macro_pos = obj.matrix_world @ vertex.co
                        
                        # Compute LCC values using tetrahedron volume
                        lcc_values = self.calculate_lcc(macro_pos, p1, p2, p3, p4)
                        
                        # LCC sums to 1 (floating-point precision fix)
                        total_lcc = sum(lcc_values)
                        if total_lcc != 0:
                            lcc_values = [v / total_lcc for v in lcc_values]
                        
                        ET.SubElement(nodes_element, macro_node_name,
                                      Type="MacroNode",
                                      X=str(macro_pos.x),
                                      Y=str(macro_pos.z),
                                      Z=str(-macro_pos.y),
                                      Mass=str(settings.model_node_mass),
                                      Fixed="1" if settings.model_node_fixed else "0",
                                      Visible="1",
                                      Selectable="1",
                                      NodesCount="4",
                                      ChildNode1="Ranged-Node1_1",
                                      ChildNode2="Ranged-Node2_1",
                                      ChildNode3="Ranged-Node3_1",
                                      ChildNode4="Ranged-Node4_1",
                                      LCC1=str(lcc_values[0]),
                                      LCC2=str(lcc_values[1]),
                                      LCC3=str(lcc_values[2]),
                                      LCC4=str(lcc_values[3]))
                                      
                        starting_node += 1  # Increment the node index
            
            if obj and model_include_attack_edges and model_attack_edges_object_1:
                child_nodes = {
                    "Ranged-Node1_1": None,
                    "Ranged-Node2_1": None,
                    "Ranged-Node3_1": None,
                    "Ranged-Node4_1": None
                }
                
                for obj_childnode in bpy.data.objects:
                    if obj_childnode.name in child_nodes:
                        child_nodes[obj_childnode.name] = obj_childnode.matrix_world.translation
                
                # Ensure all child nodes exist
                if None in child_nodes.values():
                    missing = [key for key, val in child_nodes.items() if val is None]
                    self.report({'ERROR'}, f"Missing required child nodes in blender scene: {', '.join(missing)}")
                    return {'CANCELLED'}
                
                # Child nodes
                p1, p2, p3, p4 = (child_nodes["Ranged-Node1_1"], child_nodes["Ranged-Node2_1"], 
                                  child_nodes["Ranged-Node3_1"], child_nodes["Ranged-Node4_1"])
                                  
                store_edge_attack(context, edges_atk1, vertices_atk1, edges_element, starting_edge, starting_node, True, True)
                
                # Process each vertex as a MacroNode
                for i, vertex in enumerate(vertices_atk1, start=starting_node):
                    macro_node_name = f"{prefix}Node{i}"
                    macro_pos = model_attack_edges_object_1.matrix_world @ vertex.co

                    # Compute LCC values using tetrahedron volume
                    lcc_values = self.calculate_lcc(macro_pos, p1, p2, p3, p4)
                    
                    # LCC sums to 1 (floating-point precision fix)
                    total_lcc = sum(lcc_values)
                    if total_lcc != 0:
                        lcc_values = [v / total_lcc for v in lcc_values]
                    
                    ET.SubElement(nodes_element, macro_node_name,
                                  Type="MacroNode",
                                  X=str(macro_pos.x),
                                  Y=str(macro_pos.z),
                                  Z=str(-macro_pos.y),
                                  Mass=str(settings.model_node_mass),
                                  Fixed="1" if settings.model_node_fixed else "0",
                                  Visible="1",
                                  Selectable="1",
                                  NodesCount="4",
                                  ChildNode1="Ranged-Node1_1",
                                  ChildNode2="Ranged-Node2_1",
                                  ChildNode3="Ranged-Node3_1",
                                  ChildNode4="Ranged-Node4_1",
                                  LCC1=str(lcc_values[0]),
                                  LCC2=str(lcc_values[1]),
                                  LCC3=str(lcc_values[2]),
                                  LCC4=str(lcc_values[3]))
                                  
                    starting_node += 1  # Increment the node index
              
        if model_export_capsules:
            # Capsules
            
            if settings.model_export_capsules_predefined:
                capsule_collection = model_export_capsules_folder
                if capsule_collection:
                    for obj_cap in capsule_collection.objects:
                        if obj_cap.type != 'MESH':
                            continue  # Only mesh objects
                            
                        # Find a geometry nodes modifier
                        modifier = next((m for m in obj_cap.modifiers if m.type == 'NODES'), None)
                        if not modifier or not modifier.node_group:
                            continue  # No geometry nodes

                        inputs = modifier.node_group.interface.items_tree
                        
                        # Helper to find socket by name
                        def find_socket(name):
                            for item in inputs:
                                if item.name == name:
                                    return item
                            return None
                            
                        # Find sockets
                        end1_socket = find_socket("End1")
                        end2_socket = find_socket("End2")
                        margin1_socket = find_socket("Margin1")
                        margin2_socket = find_socket("Margin2")
                        radius_socket = find_socket("Radius")
                        edge_socket = find_socket("Edge")
                        
                        # Get values
                        try:
                            end1_obj = modifier[end1_socket.identifier] if end1_socket else None
                            end2_obj = modifier[end2_socket.identifier] if end2_socket else None
                            margin1 = modifier[margin1_socket.identifier] if margin1_socket else 0.0
                            margin2 = modifier[margin2_socket.identifier] if margin2_socket else 0.0
                            radius = modifier[radius_socket.identifier] if radius_socket else 0.0
                            edge_soc = modifier[edge_socket.identifier] if edge_socket else None
                        except Exception as e:
                            continue

                        if not end1_obj or not end2_obj:
                            continue  # Missing connection

                        end1_name = end1_obj.name
                        end2_name = end2_obj.name
                        
                        # Write XML
                        ET.SubElement(
                            figures_element,
                            obj_cap.name,
                            Type="Capsule",
                            Edge=edge_soc,
                            Radius1=f"{radius:.2f}",
                            Radius2=f"{radius:.2f}",
                            Margin1=str(margin1),
                            Margin2=str(margin2)
                        )
            else:
                # Build edge lookup for faster matching
                edge_lookup = {}
                for edge_elem in edges_element:
                    if edge_elem.tag.startswith("E"):
                        end1 = edge_elem.attrib.get('End1')
                        end2 = edge_elem.attrib.get('End2')
                        tag_name = edge_elem.tag
                        if end1 and end2:
                            edge_lookup[(end1, end2)] = (tag_name, False)  # Not swapped
                            edge_lookup[(end2, end1)] = (tag_name, True)   # Swapped
                        
                # === Handle Capsules ===
                capsule_collection = model_export_capsules_folder
                if capsule_collection:
                    for obj_cap in capsule_collection.objects:
                        if obj_cap.type != 'MESH':
                            continue  # Only mesh objects

                        # Find a geometry nodes modifier
                        modifier = next((m for m in obj_cap.modifiers if m.type == 'NODES'), None)
                        if not modifier or not modifier.node_group:
                            continue  # No geometry nodes

                        inputs = modifier.node_group.interface.items_tree

                        # Helper to find socket by name
                        def find_socket(name):
                            for item in inputs:
                                if item.name == name:
                                    return item
                            return None

                        # Find sockets
                        end1_socket = find_socket("End1")
                        end2_socket = find_socket("End2")
                        margin1_socket = find_socket("Margin1")
                        margin2_socket = find_socket("Margin2")
                        radius_socket = find_socket("Radius")

                        # Get values
                        try:
                            end1_obj = modifier[end1_socket.identifier] if end1_socket else None
                            end2_obj = modifier[end2_socket.identifier] if end2_socket else None
                            margin1 = modifier[margin1_socket.identifier] if margin1_socket else 0.0
                            margin2 = modifier[margin2_socket.identifier] if margin2_socket else 0.0
                            radius = modifier[radius_socket.identifier] if radius_socket else 0.0
                        except Exception as e:
                            continue

                        if not end1_obj or not end2_obj:
                            continue  # Missing connection

                        end1_name = end1_obj.name
                        end2_name = end2_obj.name

                        # Match edge
                        matched = edge_lookup.get((end1_name, end2_name))
                        
                        if not matched:
                            matched = edge_lookup.get((end2_name, end1_name))
                        
                        if matched:
                            matched_edge_name, swap_margins = matched
                            
                            # Margin conversion
                            margin1_converted = margin1
                            margin2_converted = margin2

                            if swap_margins:
                                margin1_xml = margin2_converted
                                margin2_xml = margin1_converted
                            else:
                                margin1_xml = margin1_converted
                                margin2_xml = margin2_converted
                        
                            # Write XML
                            ET.SubElement(
                                figures_element,
                                obj_cap.name,
                                Type="Capsule",
                                Edge=matched_edge_name,
                                Radius1=f"{radius:.2f}",
                                Radius2=f"{radius:.2f}",
                                Margin1=str(margin1_xml),
                                Margin2=str(margin2_xml)
                            )
                        
        # Ensure file path has .xml extension
        file_path = self.filepath
        if not file_path.lower().endswith(".xml"):
            file_path += ".xml"

        # Convert XML tree to string with formatting
        raw_xml = ET.tostring(root, encoding="unicode")
        formatted_xml = minidom.parseString(raw_xml).toprettyxml(indent="  ")

        # Save formatted XML to file
        with open(file_path, "w", encoding="utf-8") as xml_file:
            xml_file.write(formatted_xml)

        self.report({'INFO'}, f"Model exported to {file_path}")
        return {'FINISHED'}

    def calculate_lcc(self, macro_pos, p1, p2, p3, p4):
        """ Compute LCC values using tetrahedron volume ratios. """
        V = self.tetrahedron_volume(p1, p2, p3, p4)

        if V == 0:
            return [0.25, 0.25, 0.25, 0.25] #Fallback value

        V1 = self.tetrahedron_volume(macro_pos, p2, p3, p4)
        V2 = self.tetrahedron_volume(p1, macro_pos, p3, p4)
        V3 = self.tetrahedron_volume(p1, p2, macro_pos, p4)
        V4 = self.tetrahedron_volume(p1, p2, p3, macro_pos)

        return [V1 / V, V2 / V, V3 / V, V4 / V]

    def tetrahedron_volume(self, p1, p2, p3, p4):
        """ Compute the signed volume of a tetrahedron given 4 points. """
        u = p2 - p1
        v = p3 - p1
        w = p4 - p1
        return (u.x * (v.y * w.z - v.z * w.y) -
                u.y * (v.x * w.z - v.z * w.x) +
                u.z * (v.x * w.y - v.y * w.x)) / 6.0

    def invoke(self, context, event):
        self.filepath = bpy.path.abspath("//") + "exported_model.xml"
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class AddNodesOperator(bpy.types.Operator):
    bl_idname = "model.add_nodes"
    bl_label = "Import Nodes"
    bl_description = "Add nodes from the Model XML into Blender as spheres"
    
    def execute(self, context):
        model_path = None
        model_path_unconvert = context.scene.gymnast_normal_xml
        
        if model_path_unconvert:
            model_path = bpy.path.abspath(model_path_unconvert)
        else:
            self.report({'ERROR'}, "No model XML file selected")
            return {'CANCELLED'}
        
        if not os.path.exists(model_path):
            raise Exception("Model XML path is missing or invalid.")
        
        props = context.scene.gymnast_tool_model_props

        # Create or get the "Model" collection
        model_collection = bpy.data.collections.get("Model")
        if not model_collection:
            model_collection = bpy.data.collections.new("Model")
            context.scene.collection.children.link(model_collection)

        # Create or get the child collection named after the model file
        model_name = os.path.basename(model_path).split('.')[0]
        child_collection = bpy.data.collections.get(model_name)
        if not child_collection:
            child_collection = bpy.data.collections.new(model_name)
            model_collection.children.link(child_collection)

        # Create or get the "Nodes_" collection
        nodes_collection_name = f"Nodes_{model_name}"
        nodes_collection = bpy.data.collections.get(nodes_collection_name)
        if not nodes_collection:
            nodes_collection = bpy.data.collections.new(nodes_collection_name)
            child_collection.children.link(nodes_collection)

        # Parse the XML file
        tree = ET.parse(model_path)
        root = tree.getroot()

        nodes_section = root.find('Nodes')
        if nodes_section is None:
            self.report({'ERROR'}, "No <Nodes> section found in XML")
            return {'CANCELLED'}
        
        # Store node positions for referencing in MacroNodes
        node_positions = {}
        
        if props.calculate_macronode:
            if props.import_node_as_vertex:
                mesh = bpy.data.meshes.new(f"Nodes_{model_name}")
                obj = bpy.data.objects.new(f"Nodes_{model_name}", mesh)
                nodes_collection.objects.link(obj)
                
                verts = []
            
            # First pass: process all regular nodes
            for node in nodes_section:
                if node.get('Type') in ['Node', 'CenterOfMass']:
                    x = float(node.get('X'))
                    y = float(node.get('Y'))
                    z = float(node.get('Z')) 
                    node_name = node.tag
                    node_positions[node_name] = (x, y, z)
            
            # Second pass: process both Node and MacroNode
            for node in nodes_section:
                node_name = node.tag
                
                if node.get('Type') == 'Node' or node.get('Type') == 'CenterOfMass':
                    x, y, z = node_positions[node_name]
                    
                elif node.get('Type') == 'MacroNode':
                    lcc_pos = [0.0, 0.0, 0.0]
                    total_lcc = 0.0
                    
                    for i in range(1, 5):
                        child_attr = f'ChildNode{i}'
                        lcc_attr = f'LCC{i}'
                        if child_attr in node.attrib and lcc_attr in node.attrib:
                            child_name = node.get(child_attr)
                            if not child_name or child_name == "Null":
                                continue

                            lcc = float(node.get(lcc_attr))
                            total_lcc += lcc

                            if child_name in node_positions:
                                cx, cy, cz = node_positions[child_name]
                                cx, cy, cz = cx, cy, cz
                                lcc_pos[0] += cx * lcc
                                lcc_pos[1] += cy * lcc
                                lcc_pos[2] += cz * lcc
                            else:
                                blender_obj = bpy.data.objects.get(child_name)
                                if blender_obj:
                                    cx, cz, cy = blender_obj.location  # Blender is x,z,y
                                    lcc_pos[0] += cx * lcc
                                    lcc_pos[1] += cy * lcc
                                    lcc_pos[2] += -cz * lcc
                                else:
                                    continue

                    x, y, z = lcc_pos
                    node_positions[node_name] = (x, y, z)

                else:
                    continue
                    
                if not props.import_node_as_vertex:
                    # Create a UV sphere
                    bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, location=(x, -z, y))  # Swap Y and Z
                    sphere = context.object
                    sphere.name = node_name

                    # Set the scale so the final dimensions are 2m on XYZ
                    sphere.scale = (1, 1, 1)

                    # Disable object shadow in Viewport Display
                    sphere.display.show_shadows = False

                    # Move object to the correct collection
                    for col in sphere.users_collection:
                        col.objects.unlink(sphere)
                    
                    nodes_collection.objects.link(sphere)
                    
            if props.import_node_as_vertex:
                for node_name, (x, y, z) in node_positions.items():
                    verts.append((x, -z, y))  # Swap Y and Z

                mesh.from_pydata(verts, [], [])  # Only vertices, no edges/faces
                mesh.update()
        
        else:
            if props.import_node_as_vertex:
                mesh = bpy.data.meshes.new(f"Nodes_{model_name}")
                obj = bpy.data.objects.new(f"Nodes_{model_name}", mesh)
                nodes_collection.objects.link(obj)
                
                verts = []
            
            for node in nodes_section:
                if node.get('Type') in ['Node', 'CenterOfMass', 'MacroNode']:
                    x = float(node.get('X'))
                    y = float(node.get('Y'))
                    z = float(node.get('Z')) 
                    node_name = node.tag
                    node_positions[node_name] = (x, y, z)
                    
            for node in nodes_section:
                node_name = node.tag
                
                if node.get('Type') == 'Node' or node.get('Type') == 'CenterOfMass' or node.get('Type') == 'MacroNode':
                    x, y, z = node_positions[node_name]
                else:
                    continue

                if not props.import_node_as_vertex:
                    # Create a UV sphere
                    bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, location=(x, -z, y))  # Swap Y and Z
                    sphere = context.object
                    sphere.name = node_name

                    # Set the scale so the final dimensions are 2m on XYZ
                    sphere.scale = (1, 1, 1)

                    # Disable object shadow in Viewport Display
                    sphere.display.show_shadows = False

                    # Move object to the correct collection
                    for col in sphere.users_collection:
                        col.objects.unlink(sphere)
                    
                    nodes_collection.objects.link(sphere)
            
            if props.import_node_as_vertex:
                for node_name, (x, y, z) in node_positions.items():
                    verts.append((x, -z, y))  # Swap Y and Z

                mesh.from_pydata(verts, [], [])  # Only vertices, no edges/faces
                mesh.update()
            
        self.report({'INFO'}, "Nodes added successfully")
        return {'FINISHED'}

class AddEdgesOperator(bpy.types.Operator):
    bl_idname = "model.add_edges"
    bl_label = "Import Nodes and Edges"
    bl_description = "Add nodes as vertices and edges from the Model XML into blender as an object."

    def execute(self, context):
        model_path = None
        model_path_unconvert = context.scene.gymnast_normal_xml
        
        if model_path_unconvert:
            model_path = bpy.path.abspath(model_path_unconvert)
        else:
            self.report({'ERROR'}, "No model XML file selected")
            return {'CANCELLED'}
            
        if not os.path.exists(model_path):
            raise Exception("Model XML path is missing or invalid.")
            
        props = context.scene.gymnast_tool_model_props
        model_name = os.path.basename(model_path).split('.')[0]

        # Parse the XML file
        tree = ET.parse(model_path)
        root = tree.getroot()

        nodes_section = root.find('Nodes')
        edges_section = root.find('Edges')

        if nodes_section is None:
            self.report({'ERROR'}, "No Nodes section found in XML")
            return {'CANCELLED'}
        
        verts = []
        node_name_to_index = {}
        nodes = {}

        if props.calculate_macronode:
            macro_nodes = []

            # First pass: regular nodes
            for node in nodes_section:
                node_type = node.get('Type')
                node_name = node.tag

                if node_type in ['Node', 'CenterOfMass']:
                    x = float(node.get('X'))
                    y = float(node.get('Y'))
                    z = float(node.get('Z'))
                    nodes[node_name] = (x, y, z)
                elif node_type == 'MacroNode':
                    macro_nodes.append(node)

            # Second pass: macro nodes
            for node in macro_nodes:
                node_name = node.tag
                lcc_pos = [0.0, 0.0, 0.0]
                total_lcc = 0.0

                for i in range(1, 5):
                    child_attr = f'ChildNode{i}'
                    lcc_attr = f'LCC{i}'
                    if child_attr in node.attrib and lcc_attr in node.attrib:
                        child_name = node.get(child_attr)
                        lcc = float(node.get(lcc_attr))
                        total_lcc += lcc

                        if child_name and child_name != "Null":
                            if child_name in nodes:
                                cx, cy, cz = nodes[child_name]
                                cx, cy, cz = cx, cy, cz
                                lcc_pos[0] += cx * lcc
                                lcc_pos[1] += cy * lcc
                                lcc_pos[2] += cz * lcc
                            else:
                                blender_obj = bpy.data.objects.get(child_name)
                                if blender_obj:
                                    cx, cz, cy = blender_obj.location
                                    lcc_pos[0] += cx * lcc
                                    lcc_pos[1] += cy * lcc
                                    lcc_pos[2] += -cz * lcc
                                else:
                                    continue

                            

                x, y, z = lcc_pos
                nodes[node_name] = (x, y, z)

        else:
            for node in nodes_section:
                node_name = node.tag
                x = float(node.get('X'))
                y = float(node.get('Y'))
                z = float(node.get('Z'))
                nodes[node_name] = (x, y, z)

        # Create verts
        for node_name, (x, y, z) in nodes.items():
            verts.append((x, -z, y))  # flip Y
            node_name_to_index[node_name] = len(verts) - 1

        edges = []
        if edges_section is not None:
            for edge in edges_section:
                end1 = edge.get('End1')
                end2 = edge.get('End2')
                if end1 in node_name_to_index and end2 in node_name_to_index:
                    idx1 = node_name_to_index[end1]
                    idx2 = node_name_to_index[end2]
                    edges.append((idx1, idx2))
                    
        # Create the mesh
        mesh = bpy.data.meshes.new(f"Edges_{model_name}")
        mesh.from_pydata(verts, edges, [])
        mesh.update()

        # Create the object
        obj = bpy.data.objects.new(f"Edges_{model_name}", mesh)

        # Link to collection
        model_collection = bpy.data.collections.get("Model")
        if not model_collection:
            model_collection = bpy.data.collections.new("Model")
            context.scene.collection.children.link(model_collection)

        child_collection = bpy.data.collections.get(model_name)
        if not child_collection:
            child_collection = bpy.data.collections.new(model_name)
            model_collection.children.link(child_collection)
            
        edges_collection_name = f"Edges_{model_name}"
        edges_collection = bpy.data.collections.get(edges_collection_name)
        if not edges_collection:
            edges_collection = bpy.data.collections.new(edges_collection_name)
            child_collection.children.link(edges_collection)

        edges_collection.objects.link(obj)

        self.report({'INFO'}, "Edges imported successfully")
        return {'FINISHED'}

class AddCapsulesOperator(bpy.types.Operator):
    bl_idname = "model.add_capsules"
    bl_label = "Import Capsules"
    bl_description = "Add Capsules from the model XML into Blender"
    
    def execute(self, context):
        dependencies_path = None
        model_path = None
        props = context.scene.gymnast_tool_model_props
        
        dependencies_path_unconvert = context.scene.gymnast_dependencies_xml
        model_path_unconvert = context.scene.gymnast_normal_xml
        
        if dependencies_path_unconvert:
            dependencies_path = bpy.path.abspath(dependencies_path_unconvert)
            
        if model_path_unconvert:
            model_path = bpy.path.abspath(model_path_unconvert)
        else:
            self.report({'ERROR'}, "No model XML file selected")
            return {'CANCELLED'}
        
        NODE_GROUP_NAME = "Smooth Capsules"
        
        if not os.path.exists(model_path):
            raise Exception("Model XML path is missing or invalid.")
        
        if props.model_use_dependencies and dependencies_path is None:
            raise Exception("Dependencies path is missing or invalid.")
        
        if props.model_use_dependencies and dependencies_path is not None and not os.path.exists(dependencies_path):
            raise Exception("Dependencies XML path is missing or invalid.")
        
        def check_smooth_capsules():
            node_group = bpy.data.node_groups.get("Smooth Capsules")
            if node_group and node_group.bl_idname == 'GeometryNodeTree':
                return True
            return False
        
        def add_geometry_node():
            
            misc_collection = bpy.data.collections.get("Misc")
            if not misc_collection:
                misc_collection = bpy.data.collections.new("Misc")
                context.scene.collection.children.link(misc_collection)
                
            # Create empty mesh object with modifier
            mesh_name = "GeometryNodeHolder"
            mesh_data = bpy.data.meshes.new(mesh_name)
            geometryNodeHolder_obj = bpy.data.objects.new(mesh_name, mesh_data)
            misc_collection.objects.link(geometryNodeHolder_obj)
            
            node_tree_name = "Smooth Capsules"

            #create if not exist
            if node_tree_name not in bpy.data.node_groups:
                node_tree = bpy.data.node_groups.new(name=node_tree_name, type='GeometryNodeTree')
            else:
                node_tree = bpy.data.node_groups[node_tree_name]
                
            node_tree.is_modifier = True
            
            # Assign to modifier
            modifier = geometryNodeHolder_obj.modifiers.new(name="GeometryNodes", type='NODES')
            modifier.node_group = node_tree

            # Clear default nodes
            node_tree.nodes.clear()

            nodes = node_tree.nodes
            links = node_tree.links
            
            # === Node Set Up ===
            
            # input socket
            interface = node_tree.interface
            
            def add_input(name, socket_type, default=None, subtype=None, min_val=None, max_val=None):
                socket = interface.new_socket(name=name, in_out='INPUT', socket_type=socket_type)
                if socket_type == 'NodeSocketFloat':
                    if default is not None:
                        socket.default_value = default
                    if subtype:
                        socket.subtype = subtype
                    if min_val is not None:
                        socket.min_value = min_val
                    if max_val is not None:
                        socket.max_value = max_val
            
            # group input
            group_input = nodes.new("NodeGroupInput")
            group_input.location = (0, 0)
            add_input("End1", "NodeSocketObject")
            add_input("End2", "NodeSocketObject")
            add_input("Margin1", "NodeSocketFloat", default=0.0, subtype='FACTOR', min_val=0.0, max_val=1.0)
            add_input("Margin2", "NodeSocketFloat", default=1.0, subtype='FACTOR', min_val=0.0, max_val=1.0)
            add_input("Radius",  "NodeSocketFloat", default=0.0, subtype='DISTANCE', min_val=0.0)
            add_input("Edge",  "NodeSocketString")
            
            # group input
            group_input_2 = nodes.new(type=group_input.bl_idname)
            group_input_2.location = (-190, -500)
            
            # group output
            group_output = nodes.new("NodeGroupOutput")
            group_output.location = (1750, 0)
            if "Geometry" not in [s.name for s in node_tree.interface.items_tree]:
                interface.new_socket(name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
            
            # Object Info Nodes 
            obj_info1 = nodes.new("GeometryNodeObjectInfo")
            obj_info1.location = (200, 0)
            obj_info1.inputs["As Instance"].default_value = False

            obj_info2 = nodes.new("GeometryNodeObjectInfo")
            obj_info2.location = (200, -220)
            obj_info2.inputs["As Instance"].default_value = False
            
            # === Subtract Math ===
            shader_node_math_thing = nodes.new("ShaderNodeMath")
            shader_node_math_thing.location = (450, -220)
            shader_node_math_thing.operation = 'SUBTRACT'
            shader_node_math_thing.use_clamp = True
            shader_node_math_thing.inputs[0].default_value = 1
            
            # === Curve Line ===
            curve_line = nodes.new("GeometryNodeCurvePrimitiveLine")
            curve_line.location = (450, 0)
            
            # === Trim Curve ===
            trim_curve = nodes.new("GeometryNodeTrimCurve")
            trim_curve.location = (650, 0)
            
            # === Curve Circle ===
            curve_circle = nodes.new("GeometryNodeCurvePrimitiveCircle")
            curve_circle.location = (800, 0)
            curve_circle.inputs["Resolution"].default_value = 16
            
            # === Curve to Mesh ===
            curve_to_mesh = nodes.new("GeometryNodeCurveToMesh")
            curve_to_mesh.location = (1000, 0)
            curve_to_mesh.inputs["Fill Caps"].default_value = False
            
            # === Store Named Attribute BevelInputCurve ===
            store_named_attribute_bevelinputcurve = nodes.new("GeometryNodeStoreNamedAttribute")
            store_named_attribute_bevelinputcurve.location = (1250, 0)
            store_named_attribute_bevelinputcurve.data_type = 'FLOAT_VECTOR'
            store_named_attribute_bevelinputcurve.domain = 'POINT'
            store_named_attribute_bevelinputcurve.inputs["Name"].default_value = "nor"
            
            # === Normal BevelInputCurve ===
            normal_bevelinputcurve = nodes.new("GeometryNodeInputNormal")
            normal_bevelinputcurve.location = (1000, -200)
            
            # === UV Sphere ===
            uv_sphere = nodes.new("GeometryNodeMeshUVSphere")
            uv_sphere.location = (0, -500)
            uv_sphere.inputs["Segments"].default_value = 16
            uv_sphere.inputs["Rings"].default_value = 8
            
            # === Store Named Attribute Half-Sphere Cap ===
            store_named_attribute_halfspherecap = nodes.new("GeometryNodeStoreNamedAttribute")
            store_named_attribute_halfspherecap.location = (200, -500)
            store_named_attribute_halfspherecap.data_type = 'FLOAT_VECTOR'
            store_named_attribute_halfspherecap.domain = 'POINT'
            store_named_attribute_halfspherecap.inputs["Name"].default_value = "nor"
            
            # === Normal Half-Sphere Cap ===
            normal_halfspherecap = nodes.new("GeometryNodeInputNormal")
            normal_halfspherecap.location = (0, -680)
            
            # === Delete Geometry ===
            delete_geometry = nodes.new("GeometryNodeDeleteGeometry")
            delete_geometry.location = (450, -500)
            delete_geometry.domain = 'FACE'
            delete_geometry.mode = 'ALL'
            
            # === Position ===
            input_position = nodes.new("GeometryNodeInputPosition")
            input_position.location = (0, -800)

            # === Separate XYZ ===
            separate_xyz = node_tree.nodes.new("ShaderNodeSeparateXYZ")
            separate_xyz.location = (180, -800)
            
            # === Compare ===
            compare_node = node_tree.nodes.new("FunctionNodeCompare")
            compare_node.location = (350, -800)
            compare_node.data_type = 'FLOAT'
            compare_node.operation = 'LESS_THAN'
            
            # === Set Shade Smooth ===
            set_shade_smooth = nodes.new("GeometryNodeSetShadeSmooth")
            set_shade_smooth.location = (710, -500)
            
            # == End Point Selection Half-Sphere Cap ==
            end_point_selection_halfspherecap = nodes.new("GeometryNodeCurveEndpointSelection")
            end_point_selection_halfspherecap.location = (880, -500)
            
            # == Instance on Points ==
            instance_on_points = nodes.new("GeometryNodeInstanceOnPoints")
            instance_on_points.location = (1100, -500)
            
            # === Store Named Attribute Half-Sphere Cap 2===
            store_named_attribute_halfspherecap2 = nodes.new("GeometryNodeStoreNamedAttribute")
            store_named_attribute_halfspherecap2.location = (1350, -500)
            store_named_attribute_halfspherecap2.data_type = 'FLOAT_VECTOR'
            store_named_attribute_halfspherecap2.domain = 'INSTANCE'
            store_named_attribute_halfspherecap2.inputs["Name"].default_value = "inst_rot"
            
            # == Instance Rotation ==
            instance_rotation = nodes.new("GeometryNodeInputInstanceRotation")
            instance_rotation.location = (1350, -780)
            
            # == Euler To Rotation == 
            euler_to_rotation = nodes.new("FunctionNodeEulerToRotation")
            euler_to_rotation.location = (1020, -300)
            
            # == Curve Tangent ==
            curve_tangent = nodes.new("GeometryNodeInputTangent")
            curve_tangent.location = (0, -1500)
            
            # == End Point Selection Align Cap ==
            end_point_selection_aligncap = nodes.new("GeometryNodeCurveEndpointSelection")
            end_point_selection_aligncap.location = (200, -1400)
            end_point_selection_aligncap.inputs["End Size"].default_value = 0
            
            # == Vector Math ==
            vector_math = nodes.new("ShaderNodeVectorMath")
            vector_math.location = (200, -1650)
            vector_math.operation = 'SCALE'
            vector_math.inputs["Scale"].default_value = -1
            
            # == Switch ==
            switch_node = nodes.new("GeometryNodeSwitch")
            switch_node.location = (420, -1500)
            switch_node.input_type = 'VECTOR'
            
            # == Align Rotation To Vector 1 ==
            align_rotation_to_vector_1 = nodes.new("FunctionNodeAlignRotationToVector")
            align_rotation_to_vector_1.location = (630, -1500)
            align_rotation_to_vector_1.axis = 'Z'
            align_rotation_to_vector_1.pivot_axis = 'AUTO'
            
            # == Align Rotation To Vector 2 ==
            align_rotation_to_vector_2 = nodes.new("FunctionNodeAlignRotationToVector")
            align_rotation_to_vector_2.location = (820, -1500)
            align_rotation_to_vector_2.axis = 'X'
            align_rotation_to_vector_2.pivot_axis = 'AUTO'
            
            # === Normal Align Cap ===
            normal_aligncap = nodes.new("GeometryNodeInputNormal")
            normal_aligncap.location = (420, -1800)
            
            # === Join Geometry ===
            join_geo = nodes.new("GeometryNodeJoinGeometry")
            join_geo.location = (1500, 0)
            
            # === Link Bevel Input Curve ===
            links.new(group_input.outputs["End1"], obj_info1.inputs[0])
            links.new(group_input.outputs["End2"], obj_info2.inputs[0])
            links.new(obj_info1.outputs["Location"], curve_line.inputs["Start"])
            links.new(obj_info2.outputs["Location"], curve_line.inputs["End"])
            links.new(curve_line.outputs["Curve"], trim_curve.inputs["Curve"])
            links.new(group_input.outputs["Margin1"], trim_curve.inputs["Start"])
            links.new(group_input.outputs["Margin2"], shader_node_math_thing.inputs[1])
            links.new(shader_node_math_thing.outputs["Value"], trim_curve.inputs["End"])
            links.new(trim_curve.outputs["Curve"], curve_to_mesh.inputs["Curve"])
            links.new(group_input.outputs["Radius"], curve_circle.inputs["Radius"])
            links.new(curve_circle.outputs["Curve"], curve_to_mesh.inputs["Profile Curve"])
            links.new(curve_to_mesh.outputs["Mesh"], store_named_attribute_bevelinputcurve.inputs["Geometry"])
            links.new(normal_bevelinputcurve.outputs["Normal"], store_named_attribute_bevelinputcurve.inputs["Value"])
            links.new(store_named_attribute_bevelinputcurve.outputs["Geometry"], join_geo.inputs["Geometry"])
            
            # === Link Half-Sphere Cap ===
            links.new(group_input_2.outputs["Radius"], uv_sphere.inputs["Radius"])
            links.new(uv_sphere.outputs["Mesh"], store_named_attribute_halfspherecap.inputs["Geometry"])
            links.new(normal_halfspherecap.outputs["Normal"], store_named_attribute_halfspherecap.inputs["Value"])
            links.new(store_named_attribute_halfspherecap.outputs["Geometry"], delete_geometry.inputs["Geometry"])
            links.new(input_position.outputs["Position"], separate_xyz.inputs["Vector"])
            links.new(separate_xyz.outputs["Z"], compare_node.inputs["A"])
            links.new(compare_node.outputs["Result"], delete_geometry.inputs["Selection"])
            links.new(delete_geometry.outputs["Geometry"], set_shade_smooth.inputs["Geometry"])
            links.new(set_shade_smooth.outputs["Geometry"], instance_on_points.inputs["Instance"])
            links.new(end_point_selection_halfspherecap.outputs["Selection"], instance_on_points.inputs["Selection"])
            links.new(trim_curve.outputs["Curve"], instance_on_points.inputs["Points"])
            links.new(euler_to_rotation.outputs["Rotation"], instance_on_points.inputs["Rotation"])
            links.new(align_rotation_to_vector_2.outputs["Rotation"], euler_to_rotation.inputs["Euler"])
            links.new(instance_on_points.outputs["Instances"], store_named_attribute_halfspherecap2.inputs["Geometry"])
            links.new(instance_rotation.outputs["Rotation"], store_named_attribute_halfspherecap2.inputs["Value"])
            links.new(store_named_attribute_halfspherecap2.outputs["Geometry"], join_geo.inputs["Geometry"])
            
            # === Align Cap ===
            links.new(curve_tangent.outputs["Tangent"], vector_math.inputs["Vector"])
            links.new(curve_tangent.outputs["Tangent"], switch_node.inputs["False"])
            links.new(vector_math.outputs["Vector"], switch_node.inputs["True"])
            links.new(end_point_selection_aligncap.outputs["Selection"], switch_node.inputs["Switch"])
            links.new(switch_node.outputs["Output"], align_rotation_to_vector_1.inputs["Vector"])
            links.new(align_rotation_to_vector_1.outputs["Rotation"], align_rotation_to_vector_2.inputs["Rotation"])
            links.new(normal_aligncap.outputs["Normal"], align_rotation_to_vector_2.inputs["Vector"])
            
            # == Join Geometry to Group Output ==
            links.new(join_geo.outputs["Geometry"], group_output.inputs["Geometry"])
            
            node_tree.use_fake_user = True
        
        def load_edges_from_xml(path):
            tree = ET.parse(path)
            root = tree.getroot()
            edge_dict = {}

            edges_elem = root.find("Edges")
            if edges_elem is not None:
                for edge in edges_elem:
                    edge_dict[edge.tag] = {
                        'End1': edge.attrib['End1'],
                        'End2': edge.attrib['End2']
                    }

            return root, edge_dict
        
        # check smooth capsules
        if not check_smooth_capsules():
            add_geometry_node()
        
        # Create collection
        model_filename = os.path.splitext(os.path.basename(model_path))[0]
        model_collection_name = model_filename
        capsule_collection_name = f"Capsules_{model_filename}"
        
        model_root = bpy.data.collections.get("Model")
        if not model_root:
            model_root = bpy.data.collections.new("Model")
            context.scene.collection.children.link(model_root)

        model_sub = bpy.data.collections.get(model_collection_name)
        if not model_sub:
            model_sub = bpy.data.collections.new(model_collection_name)
            model_root.children.link(model_sub)

        capsule_collection = bpy.data.collections.get(capsule_collection_name)
        if not capsule_collection:
            capsule_collection = bpy.data.collections.new(capsule_collection_name)
            model_sub.children.link(capsule_collection)
        
        
        root_primary, edges_primary = load_edges_from_xml(model_path)
        if props.model_use_dependencies and dependencies_path is not None and os.path.exists(dependencies_path):
            edges_secondary = {}
            _, edges_secondary = load_edges_from_xml(dependencies_path)
        
        # Merge the dictionaries, giving priority to primary edges
        if props.model_use_dependencies:
            edges = {**edges_secondary, **edges_primary}
        else:
            edges = dict(edges_primary)
        
        node_group = bpy.data.node_groups.get(NODE_GROUP_NAME)
        if not node_group:
            raise Exception(f"Geometry Node Group '{NODE_GROUP_NAME}' not found.")
            
        # Get input socket identifiers
        socket_map = {}
        for socket in node_group.interface.items_tree:
            if socket.in_out == 'INPUT':
                socket_map[socket.name] = socket.identifier
        
        # === PROCESS CAPSULES ===
        for capsule in list(root_primary.find("Figures")):
            if capsule.attrib.get("Type") != "Capsule":
                continue

            capsule_name = capsule.tag
            edge_name = capsule.attrib["Edge"]
            radius1 = float(capsule.attrib.get("Radius1", 1.0))
            margin1 = float(capsule.attrib.get("Margin1", 0.0))
            margin2 = float(capsule.attrib.get("Margin2", 0.0))

            edge_info = edges.get(edge_name)
            if not edge_info:
                continue

            end1_obj = bpy.data.objects.get(edge_info["End1"])
            end2_obj = bpy.data.objects.get(edge_info["End2"])
            if not end1_obj or not end2_obj:
                continue

            # Create a plane
            bpy.ops.mesh.primitive_plane_add(size=1)
            plane_obj = context.active_object
            plane_obj.name = capsule_name
            for col in plane_obj.users_collection:
                col.objects.unlink(plane_obj)
            capsule_collection.objects.link(plane_obj)

            # Add Geometry Nodes modifier and assign the node group
            modifier = plane_obj.modifiers.new(name="GeometryNodes", type='NODES')
            modifier.node_group = node_group

            # Set inputs using socket identifiers
            try:
                modifier[socket_map["End1"]] = end1_obj
                modifier[socket_map["End2"]] = end2_obj
                modifier[socket_map["Margin1"]] = margin1
                modifier[socket_map["Margin2"]] = margin2
                modifier[socket_map["Radius"]] = radius1
                modifier[socket_map["Edge"]] = edge_name
            except KeyError as e:
                print(f"Socket name missing in Geometry Node Group: {e}")
        
        
        return {'FINISHED'}
 
class SetOrientation(bpy.types.Operator):
    bl_idname = "model.set_orientation"
    bl_label = "Set Orientation"
    bl_description = "Set the Orientation of the Object's Origin"

    def execute(self, context):
        model_path = None
        model_path_unconvert = context.scene.gymnast_normal_xml
        
        if model_path_unconvert:
            model_path = bpy.path.abspath(model_path_unconvert)
        else:
            self.report({'ERROR'}, "No model XML file selected")
            return {'CANCELLED'}
            
        if model_path is None or not os.path.exists(model_path):
            raise Exception("Model XML path is missing or invalid.")
            
        settings = context.scene.gymnast_tool_model_props
        obj_orientation = settings.model_orientation
        reference_obj = settings.model_origin_object
        model_type = settings.model_type_export
        advanced_options = settings.model_is_advanced
        weapon_left_obj =  settings.weapon_object_1
        weapon_right_obj = settings.weapon_object_2
        foot_1_obj = settings.foot_object_1
        foot_2_obj = settings.foot_object_2
        selected_object = settings.selected_object
        use_existing_object = settings.model_use_existing_object
        model_body_top = settings.model_body_top
        model_body_middle = settings.model_body_middle
        model_body_bottom = settings.model_body_bottom
        flipped = settings.model_align_flipped
        
            
        def add_constraint():
            if use_existing_object:
                
                if not advanced_options:
                    if model_type == 'WEAPON':
                            
                        object_weapon_node2_1 = bpy.data.objects.get("Weapon-Node2_1") # Left Hand Origin
                        object_weapon_node1_1 = bpy.data.objects.get("Weapon-Node1_1") # Left Hand Z
                        object_weapon_node3_1 = bpy.data.objects.get("Weapon-Node3_1") # Left Hand Y
                        object_weapon_node4_1 = bpy.data.objects.get("Weapon-Node4_1") # Left Hand X
                        
                        object_weapon_node2_2 = bpy.data.objects.get("Weapon-Node2_2") # Right Hand Origin
                        object_weapon_node1_2 = bpy.data.objects.get("Weapon-Node1_2") # Right Hand Z
                        object_weapon_node3_2 = bpy.data.objects.get("Weapon-Node3_2") # Right Hand Y
                        object_weapon_node4_2 = bpy.data.objects.get("Weapon-Node4_2") # Right Hand X
                        
                        if weapon_left_obj:
                            weapon_left_obj.constraints.clear()
                            copy_loc = weapon_left_obj.constraints.new(type='COPY_LOCATION')
                            copy_loc.target = object_weapon_node2_1
                            
                            # Add Damped Track (Z Axis)
                            damped_z = weapon_left_obj.constraints.new(type='DAMPED_TRACK')
                            damped_z.target = object_weapon_node1_1
                            damped_z.track_axis = 'TRACK_Z'

                            # Add Damped Track (Y Axis)
                            damped_y = weapon_left_obj.constraints.new(type='DAMPED_TRACK')
                            damped_y.target = object_weapon_node3_1
                            damped_y.track_axis = 'TRACK_Y'
                            
                            # Add Damped Track (X Axis)
                            damped_x = weapon_left_obj.constraints.new(type='DAMPED_TRACK')
                            damped_x.target = object_weapon_node4_1
                            damped_x.track_axis = 'TRACK_NEGATIVE_X'
                            
                        if weapon_right_obj:
                            weapon_right_obj.constraints.clear()
                            copy_loc = weapon_right_obj.constraints.new(type='COPY_LOCATION')
                            copy_loc.target = object_weapon_node2_2
                            
                            # Add Damped Track (Z Axis)
                            damped_z = weapon_right_obj.constraints.new(type='DAMPED_TRACK')
                            damped_z.target = object_weapon_node1_2
                            damped_z.track_axis = 'TRACK_Z'

                            # Add Damped Track (Y Axis)
                            damped_y = weapon_right_obj.constraints.new(type='DAMPED_TRACK')
                            damped_y.target = object_weapon_node3_2
                            damped_y.track_axis = 'TRACK_Y'
                            
                            # Add Damped Track (X Axis)
                            damped_x = weapon_right_obj.constraints.new(type='DAMPED_TRACK')
                            damped_x.target = object_weapon_node4_2
                            damped_x.track_axis = 'TRACK_X'
                    
                    elif model_type == 'FOOT_GEAR':
                        object_ntoe_1 = bpy.data.objects.get("NToe_1") # foot 1 origin
                        object_ntoes_1 = bpy.data.objects.get("NToeS_1") # foot 1 Y
                        object_nheel_1 = bpy.data.objects.get("NHeel_1") # foot 1 Z
                        
                        object_ntoe_2 = bpy.data.objects.get("NToe_2") # foot 2 origin
                        object_ntoes_2 = bpy.data.objects.get("NToeS_2") # foot 2 Y
                        object_nheel_2 = bpy.data.objects.get("NHeel_2") # foot 2 Z
                        
                        if foot_1_obj:
                            foot_1_obj.constraints.clear()
                            copy_loc = foot_1_obj.constraints.new(type='COPY_LOCATION')
                            copy_loc.target = object_ntoe_1
                            
                            # Add Damped Track (Z Axis)
                            damped_z = foot_1_obj.constraints.new(type='DAMPED_TRACK')
                            damped_z.target = object_nheel_1
                            damped_z.track_axis = 'TRACK_Z'

                            # Add Damped Track (Y Axis)
                            damped_y = foot_1_obj.constraints.new(type='DAMPED_TRACK')
                            damped_y.target = object_ntoes_1
                            damped_y.track_axis = 'TRACK_Y'
                        
                        if foot_2_obj:
                            foot_2_obj.constraints.clear()
                            copy_loc = foot_2_obj.constraints.new(type='COPY_LOCATION')
                            copy_loc.target = object_ntoe_2
                            
                            # Add Damped Track (Z Axis)
                            damped_z = foot_2_obj.constraints.new(type='DAMPED_TRACK')
                            damped_z.target = object_nheel_2
                            damped_z.track_axis = 'TRACK_Z'

                            # Add Damped Track (Y Axis)
                            damped_y = foot_2_obj.constraints.new(type='DAMPED_TRACK')
                            damped_y.target = object_ntoes_2
                            damped_y.track_axis = 'TRACK_Y'
                    
                    elif model_type == 'HEAD_GEAR':
                        object_nhead = bpy.data.objects.get("NHead") # head origin
                        object_ntop = bpy.data.objects.get("NTop") # head Z
                        object_nheadf = bpy.data.objects.get("NHeadF") # head Y
                        object_nheads_2 = bpy.data.objects.get("NHeadS_2") # head X
                        
                        selected_object.constraints.clear()
                        copy_loc = selected_object.constraints.new(type='COPY_LOCATION')
                        copy_loc.target = object_nhead
                        
                        # Add Damped Track (Z Axis)
                        damped_z = selected_object.constraints.new(type='DAMPED_TRACK')
                        damped_z.target = object_ntop
                        damped_z.track_axis = 'TRACK_Z'

                        # Add Damped Track (Y Axis)
                        damped_y = selected_object.constraints.new(type='DAMPED_TRACK')
                        damped_y.target = object_nheadf
                        damped_y.track_axis = 'TRACK_Y'
                        
                        # Add Damped Track (Y Axis)
                        damped_x = selected_object.constraints.new(type='DAMPED_TRACK')
                        damped_x.target = object_nheads_2
                        damped_x.track_axis = 'TRACK_X' if not flipped else 'TRACK_NEGATIVE_X'
                    
                    elif model_type == 'RANGED':
                        object_ranged2 = bpy.data.objects.get("Ranged-Node2_1") # origin
                        object_ranged1 = bpy.data.objects.get("Ranged-Node1_1") # Z
                        object_ranged4 = bpy.data.objects.get("Ranged-Node4_1") #  Y
                        object_ranged3 = bpy.data.objects.get("Ranged-Node3_1") # X
                        
                        selected_object.constraints.clear()
                        copy_loc = selected_object.constraints.new(type='COPY_LOCATION')
                        copy_loc.target = object_ranged2
                        
                        # Add Damped Track (Z Axis)
                        damped_z = selected_object.constraints.new(type='DAMPED_TRACK')
                        damped_z.target = object_ranged1
                        damped_z.track_axis = 'TRACK_Z'

                        # Add Damped Track (Y Axis)
                        damped_y = selected_object.constraints.new(type='DAMPED_TRACK')
                        damped_y.target = object_ranged4
                        damped_y.track_axis = 'TRACK_Y'
                        
                        # Add Damped Track (Y Axis)
                        damped_x = selected_object.constraints.new(type='DAMPED_TRACK')
                        damped_x.target = object_ranged3
                        damped_x.track_axis = 'TRACK_X'
                    
                    else:
                        if settings.model_apply_constraint:
                            selected = [o for o in context.selected_objects if o != obj_orientation]
                            if len(selected) != 2:
                                self.report({'ERROR'}, "Select exactly two other objects to define orientation.")
                                return

                            target_z = selected[0]
                            target_y = selected[1]
                            
                            obj_orientation.constraints.clear()
                            copy_loc = obj_orientation.constraints.new(type='COPY_LOCATION')
                            copy_loc.target = reference_obj
                            
                            # Add Damped Track (Z Axis)
                            damped_z = obj_orientation.constraints.new(type='DAMPED_TRACK')
                            damped_z.target = target_z
                            damped_z.track_axis = 'TRACK_Z'

                            # Add Damped Track (Y Axis)
                            damped_y = obj_orientation.constraints.new(type='DAMPED_TRACK')
                            damped_y.target = target_y
                            damped_y.track_axis = 'TRACK_Y'
                
                else:
                    if settings.model_apply_constraint:
                        selected = [o for o in context.selected_objects if o != obj_orientation]
                        if len(selected) != 2:
                            self.report({'ERROR'}, "Select exactly two other objects to define orientation.")
                            return

                        target_z = selected[0]
                        target_y = selected[1]
                        
                        obj_orientation.constraints.clear()
                        copy_loc = obj_orientation.constraints.new(type='COPY_LOCATION')
                        copy_loc.target = reference_obj
                        
                        # Add Damped Track (Z Axis)
                        damped_z = obj_orientation.constraints.new(type='DAMPED_TRACK')
                        damped_z.target = target_z
                        damped_z.track_axis = 'TRACK_Z'

                        # Add Damped Track (Y Axis)
                        damped_y = obj_orientation.constraints.new(type='DAMPED_TRACK')
                        damped_y.target = target_y
                        damped_y.track_axis = 'TRACK_Y'
            
            else:
                if settings.model_apply_constraint:
                    selected = [o for o in context.selected_objects if o != obj_orientation]
                    if len(selected) != 2:
                        self.report({'ERROR'}, "Select exactly two other objects to define orientation.")
                        return

                    target_z = selected[0]
                    target_y = selected[1]
                    
                    obj_orientation.constraints.clear()
                    copy_loc = obj_orientation.constraints.new(type='COPY_LOCATION')
                    copy_loc.target = reference_obj
                    
                    # Add Damped Track (Z Axis)
                    damped_z = obj_orientation.constraints.new(type='DAMPED_TRACK')
                    damped_z.target = target_z
                    damped_z.track_axis = 'TRACK_Z'

                    # Add Damped Track (Y Axis)
                    damped_y = obj_orientation.constraints.new(type='DAMPED_TRACK')
                    damped_y.target = target_y
                    damped_y.track_axis = 'TRACK_Y'
            
        def align_origin():
            if use_existing_object:
                
                if not advanced_options:
                    
                    if model_type == 'WEAPON':
                        object_weapon_node2_1 = bpy.data.objects.get("Weapon-Node2_1") # Left Hand Origin
                        object_weapon_node2_2 = bpy.data.objects.get("Weapon-Node2_2") # Right Hand Origin
                        
                        if weapon_left_obj:
                            # Compute offset
                            delta_left = object_weapon_node2_1.location - weapon_left_obj.location
                            
                            # Apply inverse translation to mesh
                            if weapon_left_obj.type == 'MESH':
                                mesh_left = weapon_left_obj.data
                                for vert_left in mesh_left.vertices:
                                    vert_left.co -= delta_left
                                mesh_left.update()

                            # Move the object to new origin
                            weapon_left_obj.location += delta_left
                        
                        if weapon_right_obj:
                            # Compute offset
                            delta_right = object_weapon_node2_2.location - weapon_right_obj.location

                            # Apply inverse translation to mesh
                            if weapon_right_obj.type == 'MESH':
                                mesh_right = weapon_right_obj.data
                                for vert_right in mesh_right.vertices:
                                    vert_right.co -= delta_right
                                mesh_right.update()

                            # Move the object to new origin
                            weapon_right_obj.location += delta_right
                    
                    elif model_type == 'FOOT_GEAR':
                        object_ntoe_1 = bpy.data.objects.get("NToe_1") # foot 1 origin
                        object_ntoe_2 = bpy.data.objects.get("NToe_2") # foot 2 origin
                        
                        if foot_1_obj:
                            # Compute offset
                            delta_left = object_ntoe_1.location - foot_1_obj.location
                            
                            # Apply inverse translation to mesh
                            if foot_1_obj.type == 'MESH':
                                mesh_left = foot_1_obj.data
                                for vert_left in mesh_left.vertices:
                                    vert_left.co -= delta_left
                                mesh_left.update()

                            # Move the object to new origin
                            foot_1_obj.location += delta_left
                        
                        if foot_2_obj:
                            # Compute offset
                            delta_right = object_ntoe_2.location - foot_2_obj.location

                            # Apply inverse translation to mesh
                            if foot_2_obj.type == 'MESH':
                                mesh_right = foot_2_obj.data
                                for vert_right in mesh_right.vertices:
                                    vert_right.co -= delta_right
                                mesh_right.update()

                            # Move the object to new origin
                            foot_2_obj.location += delta_right
                    
                    elif model_type == 'HEAD_GEAR':
                        object_nhead = bpy.data.objects.get("NHead") # head origin
                        
                        # Compute offset
                        delta = object_nhead.location - selected_object.location

                        # Apply inverse translation to mesh
                        if selected_object.type == 'MESH':
                            mesh = selected_object.data
                            for vert in mesh.vertices:
                                vert.co -= delta
                            mesh.update()

                        # Move the object to new origin
                        selected_object.location += delta
                    
                    elif model_type == 'RANGED':
                        object_ranged2 = bpy.data.objects.get("Ranged-Node2_1") # head origin
                        
                        # Compute offset
                        delta = object_ranged2.location - selected_object.location

                        # Apply inverse translation to mesh
                        if selected_object.type == 'MESH':
                            mesh = selected_object.data
                            for vert in mesh.vertices:
                                vert.co -= delta
                            mesh.update()

                        # Move the object to new origin
                        selected_object.location += delta
                    
                    else:
                        if not obj_orientation or not reference_obj:
                            self.report({'ERROR'}, "Both objects must be specified in the settings.")
                            return {'CANCELLED'}
                        
                        selected = [o for o in context.selected_objects if o != obj_orientation]
                        if len(selected) != 2:
                            self.report({'ERROR'}, "Select exactly two other objects to define orientation.")
                            return
                        
                        # Compute offset
                        delta = reference_obj.location - obj_orientation.location

                        # Apply inverse translation to mesh
                        if obj_orientation.type == 'MESH':
                            mesh = obj_orientation.data
                            for vert in mesh.vertices:
                                vert.co -= delta
                            mesh.update()

                        # Move the object to new origin
                        obj_orientation.location += delta
     
                else:
                    if not obj_orientation or not reference_obj:
                        self.report({'ERROR'}, "Both objects must be specified in the settings.")
                        return {'CANCELLED'}
                        
                    selected = [o for o in context.selected_objects if o != obj_orientation]
                    if len(selected) != 2:
                        self.report({'ERROR'}, "Select exactly two other objects to define orientation.")
                        return
                    
                    # Compute offset
                    delta = reference_obj.location - obj_orientation.location

                    # Apply inverse translation to mesh
                    if obj_orientation.type == 'MESH':
                        mesh = obj_orientation.data
                        for vert in mesh.vertices:
                            vert.co -= delta
                        mesh.update()

                    # Move the object to new origin
                    obj_orientation.location += delta
            
            else:
                if not obj_orientation or not reference_obj:
                    self.report({'ERROR'}, "Both objects must be specified in the settings.")
                    return {'CANCELLED'}
                    
                selected = [o for o in context.selected_objects if o != obj_orientation]
                if len(selected) != 2:
                    self.report({'ERROR'}, "Select exactly two other objects to define orientation.")
                    return
                
                # Compute offset
                delta = reference_obj.location - obj_orientation.location

                # Apply inverse translation to mesh
                if obj_orientation.type == 'MESH':
                    mesh = obj_orientation.data
                    for vert in mesh.vertices:
                        vert.co -= delta
                    mesh.update()

                # Move the object to new origin
                obj_orientation.location += delta

        def align_origin_orientation():
            if use_existing_object:
                
                if not advanced_options:
                    
                    if model_type == 'WEAPON':
                        if not weapon_left_obj and not weapon_right_obj:
                            self.report({'ERROR'}, "At least one weapon must be selected.")
                            return
                        
                        object_weapon_node2_1 = bpy.data.objects.get("Weapon-Node2_1") # Left Hand Origin
                        object_weapon_node1_1 = bpy.data.objects.get("Weapon-Node1_1") # Left Hand Z
                        object_weapon_node3_1 = bpy.data.objects.get("Weapon-Node3_1") # Left Hand Y
                        
                        object_weapon_node2_2 = bpy.data.objects.get("Weapon-Node2_2") # Right Hand Origin
                        object_weapon_node1_2 = bpy.data.objects.get("Weapon-Node1_2") # Right Hand Z
                        object_weapon_node3_2 = bpy.data.objects.get("Weapon-Node3_2") # Right Hand Y
                        
                        required_objects = [
                            object_weapon_node2_1,
                            object_weapon_node1_1,
                            object_weapon_node3_1,
                            object_weapon_node2_2,
                            object_weapon_node1_2,
                            object_weapon_node3_2
                        ]

                        # Check if all are not None
                        if not all(required_objects):
                            self.report({'ERROR'}, "One or more required Weapon-Node objects were not found in the scene.\n Please make sure SF2's Rig is correct.")
                            return {'CANCELLED'}
                        
                        align_origin()
                        
                        if weapon_left_obj:
                            
                            target_z = object_weapon_node1_1
                            target_y = object_weapon_node3_1

                            # Build orthonormal basis
                            z_dir = (target_z.location - weapon_left_obj.location).normalized()
                            y_dir = (target_y.location - weapon_left_obj.location).normalized()
                            x_dir = y_dir.cross(z_dir).normalized()
                            y_dir = z_dir.cross(x_dir).normalized()

                            rot_matrix = mathutils.Matrix((x_dir, y_dir, z_dir)).transposed()
                            new_quat = rot_matrix.to_quaternion()

                            # Store old rotation and compute delta
                            old_quat = weapon_left_obj.rotation_quaternion.copy()
                            delta_quat = new_quat @ old_quat.inverted()

                            # Set new origin rotation
                            weapon_left_obj.rotation_mode = 'QUATERNION'
                            weapon_left_obj.rotation_quaternion = new_quat

                            # Apply inverse delta to mesh vertices to visually preserve mesh
                            if weapon_left_obj.type == 'MESH' and weapon_left_obj.data:
                                mesh = weapon_left_obj.data
                                for vert in mesh.vertices:
                                    vert.co.rotate(delta_quat.inverted())
                                mesh.update()

                            
                        
                        if weapon_right_obj:
                            
                            target_z = object_weapon_node1_2
                            target_y = object_weapon_node3_2

                            # Build orthonormal basis
                            z_dir = (target_z.location - weapon_right_obj.location).normalized()
                            y_dir = (target_y.location - weapon_right_obj.location).normalized()
                            x_dir = y_dir.cross(z_dir).normalized()
                            y_dir = z_dir.cross(x_dir).normalized()

                            rot_matrix = mathutils.Matrix((x_dir, y_dir, z_dir)).transposed()
                            new_quat = rot_matrix.to_quaternion()

                            # Store old rotation and compute delta
                            old_quat = weapon_right_obj.rotation_quaternion.copy()
                            delta_quat = new_quat @ old_quat.inverted()

                            # Set new origin rotation
                            weapon_right_obj.rotation_mode = 'QUATERNION'
                            weapon_right_obj.rotation_quaternion = new_quat

                            # Apply inverse delta to mesh vertices to visually preserve mesh
                            if weapon_right_obj.type == 'MESH' and weapon_right_obj.data:
                                mesh = weapon_right_obj.data
                                for vert in mesh.vertices:
                                    vert.co.rotate(delta_quat.inverted())
                                mesh.update()
                        
                        self.report({'INFO'}, "Origin orientation updated.")
                        return
                        
                    elif model_type == 'FOOT_GEAR':
                        if not foot_1_obj and not foot_2_obj:
                            self.report({'ERROR'}, "At least one footgear must be specified.")
                            return
                        
                        object_ntoe_1 = bpy.data.objects.get("NToe_1") # foot 1 origin
                        object_ntoes_1 = bpy.data.objects.get("NToeS_1") # foot 1 Y
                        object_nheel_1 = bpy.data.objects.get("NHeel_1") # foot 1 Z
                        
                        object_ntoe_2 = bpy.data.objects.get("NToe_2") # foot 2 origin
                        object_ntoes_2 = bpy.data.objects.get("NToeS_2") # foot 2 Y
                        object_nheel_2 = bpy.data.objects.get("NHeel_2") # foot 2 Z
                        
                        required_objects = [
                            object_ntoe_1,
                            object_ntoes_1,
                            object_nheel_1,
                            object_ntoe_2,
                            object_ntoes_2,
                            object_nheel_2
                        ]

                        # Check if all are not None
                        if not all(required_objects):
                            self.report({'ERROR'}, "NToe, NToeS or NHeel isn't found in the scene.\n Please make sure the Rig is correct.")
                            return {'CANCELLED'}
                        
                        align_origin()
                        
                        if foot_1_obj:
                            
                            target_z = object_nheel_1
                            target_y = object_ntoes_1

                            # Build orthonormal basis
                            z_dir = (target_z.location - foot_1_obj.location).normalized()
                            y_dir = (target_y.location - foot_1_obj.location).normalized()
                            x_dir = y_dir.cross(z_dir).normalized()
                            y_dir = z_dir.cross(x_dir).normalized()

                            rot_matrix = mathutils.Matrix((x_dir, y_dir, z_dir)).transposed()
                            new_quat = rot_matrix.to_quaternion()

                            # Store old rotation and compute delta
                            old_quat = foot_1_obj.rotation_quaternion.copy()
                            delta_quat = new_quat @ old_quat.inverted()

                            # Set new origin rotation
                            foot_1_obj.rotation_mode = 'QUATERNION'
                            foot_1_obj.rotation_quaternion = new_quat

                            # Apply inverse delta to mesh vertices to visually preserve mesh
                            if foot_1_obj.type == 'MESH' and foot_1_obj.data:
                                mesh = foot_1_obj.data
                                for vert in mesh.vertices:
                                    vert.co.rotate(delta_quat.inverted())
                                mesh.update()

                            
                        if foot_2_obj:
                            
                            target_z = object_nheel_2
                            target_y = object_ntoes_2

                            # Build orthonormal basis
                            z_dir = (target_z.location - foot_2_obj.location).normalized()
                            y_dir = (target_y.location - foot_2_obj.location).normalized()
                            x_dir = y_dir.cross(z_dir).normalized()
                            y_dir = z_dir.cross(x_dir).normalized()

                            rot_matrix = mathutils.Matrix((x_dir, y_dir, z_dir)).transposed()
                            new_quat = rot_matrix.to_quaternion()

                            # Store old rotation and compute delta
                            old_quat = foot_2_obj.rotation_quaternion.copy()
                            delta_quat = new_quat @ old_quat.inverted()

                            # Set new origin rotation
                            foot_2_obj.rotation_mode = 'QUATERNION'
                            foot_2_obj.rotation_quaternion = new_quat

                            # Apply inverse delta to mesh vertices to visually preserve mesh
                            if foot_2_obj.type == 'MESH' and foot_2_obj.data:
                                mesh = foot_2_obj.data
                                for vert in mesh.vertices:
                                    vert.co.rotate(delta_quat.inverted())
                                mesh.update()

                        self.report({'INFO'}, "Origin orientation updated.")
                        return
                    
                    elif model_type == 'HEAD_GEAR':
                        if not selected_object:
                            self.report({'ERROR'}, "No Head Gear selected for orientation.")
                            return
                        
                        object_nhead = bpy.data.objects.get("NHead") # head origin
                        object_ntop = bpy.data.objects.get("NTop") # head Z
                        object_nheadf = bpy.data.objects.get("NHeadF") # head Y
                        
                        required_objects = [
                            object_nhead,
                            object_ntop,
                            object_nheadf
                        ]

                        # Check if all are not None
                        if not all(required_objects):
                            self.report({'ERROR'}, "NHead, NTop or NHeadF isn't found in the scene.\n Please make sure the Rig is correct.")
                            return {'CANCELLED'}
                        
                        align_origin()
                        
                        target_z = object_ntop
                        target_y = object_nheadf

                        # Build orthonormal basis
                        z_dir = (target_z.location - selected_object.location).normalized()
                        y_dir = (target_y.location - selected_object.location).normalized()
                        x_dir = y_dir.cross(z_dir).normalized()
                        y_dir = z_dir.cross(x_dir).normalized()

                        rot_matrix = mathutils.Matrix((x_dir, y_dir, z_dir)).transposed()
                        new_quat = rot_matrix.to_quaternion()

                        # Store old rotation and compute delta
                        old_quat = selected_object.rotation_quaternion.copy()
                        delta_quat = new_quat @ old_quat.inverted()

                        # Set new origin rotation
                        selected_object.rotation_mode = 'QUATERNION'
                        selected_object.rotation_quaternion = new_quat

                        # Apply inverse delta to mesh vertices to visually preserve mesh
                        if selected_object.type == 'MESH' and selected_object.data:
                            mesh = selected_object.data
                            for vert in mesh.vertices:
                                vert.co.rotate(delta_quat.inverted())
                            mesh.update()

                        self.report({'INFO'}, "Origin orientation updated.")
                        return
                    
                    elif model_type == 'RANGED':
                        if not selected_object:
                            self.report({'ERROR'}, "No Ranged selected for orientation.")
                            return
                        
                        object_ranged2 = bpy.data.objects.get("Ranged-Node2_1") # origin
                        object_ranged1 = bpy.data.objects.get("Ranged-Node1_1") # Z
                        object_ranged4 = bpy.data.objects.get("Ranged-Node4_1") #  Y
                        object_ranged3 = bpy.data.objects.get("Ranged-Node3_1") # X
                        
                        required_objects = [
                            object_ranged2,
                            object_ranged1,
                            object_ranged4,
                            object_ranged3
                        ]

                        # Check if all are not None
                        if not all(required_objects):
                            self.report({'ERROR'}, "Ranged skeleton isn't found or some nodes is invalid in the scene.\n Please make sure the Rig is correct.")
                            return {'CANCELLED'}
                        
                        align_origin()
                        
                        target_z = object_ranged1
                        target_y = object_ranged4

                        # Build orthonormal basis
                        z_dir = (target_z.location - selected_object.location).normalized()
                        y_dir = (target_y.location - selected_object.location).normalized()
                        x_dir = y_dir.cross(z_dir).normalized()
                        y_dir = z_dir.cross(x_dir).normalized()

                        rot_matrix = mathutils.Matrix((x_dir, y_dir, z_dir)).transposed()
                        new_quat = rot_matrix.to_quaternion()

                        # Store old rotation and compute delta
                        old_quat = selected_object.rotation_quaternion.copy()
                        delta_quat = new_quat @ old_quat.inverted()

                        # Set new origin rotation
                        selected_object.rotation_mode = 'QUATERNION'
                        selected_object.rotation_quaternion = new_quat

                        # Apply inverse delta to mesh vertices to visually preserve mesh
                        if selected_object.type == 'MESH' and selected_object.data:
                            mesh = selected_object.data
                            for vert in mesh.vertices:
                                vert.co.rotate(delta_quat.inverted())
                            mesh.update()

                        self.report({'INFO'}, "Origin orientation updated.")
                        return
                    
                    else:
                        if not obj_orientation:
                            self.report({'ERROR'}, "No object selected to set orientation.")
                            return

                        selected = [o for o in context.selected_objects if o != obj_orientation]
                        if len(selected) != 2:
                            self.report({'ERROR'}, "Select exactly two other objects to define orientation.")
                            return

                        target_z = selected[0]
                        target_y = selected[1]

                        # Build orthonormal basis
                        z_dir = (target_z.location - obj_orientation.location).normalized()
                        y_dir = (target_y.location - obj_orientation.location).normalized()
                        x_dir = y_dir.cross(z_dir).normalized()
                        y_dir = z_dir.cross(x_dir).normalized()

                        rot_matrix = mathutils.Matrix((x_dir, y_dir, z_dir)).transposed()
                        new_quat = rot_matrix.to_quaternion()

                        # Store old rotation and compute delta
                        old_quat = obj_orientation.rotation_quaternion.copy()
                        delta_quat = new_quat @ old_quat.inverted()

                        # Set new origin rotation
                        obj_orientation.rotation_mode = 'QUATERNION'
                        obj_orientation.rotation_quaternion = new_quat

                        # Apply inverse delta to mesh vertices to visually preserve mesh
                        if obj_orientation.type == 'MESH' and obj_orientation.data:
                            mesh = obj_orientation.data
                            for vert in mesh.vertices:
                                vert.co.rotate(delta_quat.inverted())
                            mesh.update()

                        self.report({'INFO'}, "Origin orientation updated.")
                        return
                    
                else:
                    if not obj_orientation:
                        self.report({'ERROR'}, "No object selected to set orientation.")
                        return

                    selected = [o for o in context.selected_objects if o != obj_orientation]
                    if len(selected) != 2:
                        self.report({'ERROR'}, "Select exactly two other objects to define orientation.")
                        return

                    target_z = selected[0]
                    target_y = selected[1]

                    # Build orthonormal basis
                    z_dir = (target_z.location - obj_orientation.location).normalized()
                    y_dir = (target_y.location - obj_orientation.location).normalized()
                    x_dir = y_dir.cross(z_dir).normalized()
                    y_dir = z_dir.cross(x_dir).normalized()

                    rot_matrix = mathutils.Matrix((x_dir, y_dir, z_dir)).transposed()
                    new_quat = rot_matrix.to_quaternion()

                    # Store old rotation and compute delta
                    old_quat = obj_orientation.rotation_quaternion.copy()
                    delta_quat = new_quat @ old_quat.inverted()

                    # Set new origin rotation
                    obj_orientation.rotation_mode = 'QUATERNION'
                    obj_orientation.rotation_quaternion = new_quat

                    # Apply inverse delta to mesh vertices to visually preserve mesh
                    if obj_orientation.type == 'MESH' and obj_orientation.data:
                        mesh = obj_orientation.data
                        for vert in mesh.vertices:
                            vert.co.rotate(delta_quat.inverted())
                        mesh.update()

                    self.report({'INFO'}, "Origin orientation updated.")
                    return
            
            else:
                if not obj_orientation:
                    self.report({'ERROR'}, "No object selected to set orientation.")
                    return

                selected = [o for o in context.selected_objects if o != obj_orientation]
                if len(selected) != 2:
                    self.report({'ERROR'}, "Select exactly two other objects to define orientation.")
                    return

                target_z = selected[0]
                target_y = selected[1]

                # Build orthonormal basis
                z_dir = (target_z.location - obj_orientation.location).normalized()
                y_dir = (target_y.location - obj_orientation.location).normalized()
                x_dir = y_dir.cross(z_dir).normalized()
                y_dir = z_dir.cross(x_dir).normalized()

                rot_matrix = mathutils.Matrix((x_dir, y_dir, z_dir)).transposed()
                new_quat = rot_matrix.to_quaternion()

                # Store old rotation and compute delta
                old_quat = obj_orientation.rotation_quaternion.copy()
                delta_quat = new_quat @ old_quat.inverted()

                # Set new origin rotation
                obj_orientation.rotation_mode = 'QUATERNION'
                obj_orientation.rotation_quaternion = new_quat

                # Apply inverse delta to mesh vertices to visually preserve mesh
                if obj_orientation.type == 'MESH' and obj_orientation.data:
                    mesh = obj_orientation.data
                    for vert in mesh.vertices:
                        vert.co.rotate(delta_quat.inverted())
                    mesh.update()

                self.report({'INFO'}, "Origin orientation updated.")
                return
            
        def align_not_use_existing_object():
            if not advanced_options and model_type != 'MODEL':
                if model_type == 'WEAPON':
                    if not weapon_left_obj and not weapon_right_obj:
                            self.report({'ERROR'}, "At least one weapon must be selected.")
                            return
                        
                    object_weapon_node2_1 = bpy.data.objects.get("Weapon-Node2_1") # Left Hand Origin
                    object_weapon_node1_1 = bpy.data.objects.get("Weapon-Node1_1") # Left Hand Z
                    object_weapon_node3_1 = bpy.data.objects.get("Weapon-Node3_1") # Left Hand Y
                    
                    object_weapon_node2_2 = bpy.data.objects.get("Weapon-Node2_2") # Right Hand Origin
                    object_weapon_node1_2 = bpy.data.objects.get("Weapon-Node1_2") # Right Hand Z
                    object_weapon_node3_2 = bpy.data.objects.get("Weapon-Node3_2") # Right Hand Y
                    
                    required_objects = [
                        object_weapon_node2_1,
                        object_weapon_node1_1,
                        object_weapon_node3_1,
                        object_weapon_node2_2,
                        object_weapon_node1_2,
                        object_weapon_node3_2
                    ]

                    # Check if all are not None
                    if not all(required_objects):
                        self.report({'ERROR'}, "One or more required Weapon-Node objects were not found in the scene.\n Please make sure SF2's Rig is correct.")
                        return {'CANCELLED'}
                    if weapon_left_obj:
                        origin_point = object_weapon_node2_1
                        target_z = object_weapon_node1_1
                        target_y = object_weapon_node3_1
                        
                        weapon_left_obj.matrix_world.translation = mathutils.Vector((0, 0, 0))
                        weapon_left_obj.constraints.clear()
                        
                        copy_loc = weapon_left_obj.constraints.new(type='COPY_LOCATION')
                        copy_loc.target = object_weapon_node2_1
                        copy_loc.use_offset = True
                        
                        z_direction = (target_z.location - origin_point.location).normalized()
                        y_direction = (target_y.location - origin_point.location).normalized()
                        x_direction = y_direction.cross(z_direction).normalized()
                        y_direction = z_direction.cross(x_direction).normalized()
                        
                        rotation_matrix = mathutils.Matrix((
                            x_direction.to_3d(),
                            y_direction.to_3d(),
                            z_direction.to_3d()
                        )).transposed()
                        
                        current_scale = weapon_left_obj.matrix_basis.to_scale()
                        new_basis = mathutils.Matrix.LocRotScale(weapon_left_obj.location, rotation_matrix.to_quaternion(), current_scale)
                        weapon_left_obj.matrix_basis = new_basis
                        context.view_layer.update()
                        
                        damped_z = weapon_left_obj.constraints.new(type='DAMPED_TRACK')
                        damped_z.target = object_weapon_node1_1
                        damped_z.track_axis = 'TRACK_Z'

                        damped_y = weapon_left_obj.constraints.new(type='DAMPED_TRACK')
                        damped_y.target = object_weapon_node3_1
                        damped_y.track_axis = 'TRACK_Y'
                        
                    if weapon_right_obj:
                        origin_point = object_weapon_node2_2
                        target_z = object_weapon_node1_2
                        target_y = object_weapon_node3_2
                        
                        weapon_right_obj.matrix_world.translation = mathutils.Vector((0, 0, 0))
                        weapon_right_obj.constraints.clear()
                        
                        copy_loc = weapon_right_obj.constraints.new(type='COPY_LOCATION')
                        copy_loc.target = object_weapon_node2_2
                        copy_loc.use_offset = True
                        
                        z_direction = (target_z.location - origin_point.location).normalized()
                        y_direction = (target_y.location - origin_point.location).normalized()
                        x_direction = y_direction.cross(z_direction).normalized()
                        y_direction = z_direction.cross(x_direction).normalized()
                        
                        rotation_matrix = mathutils.Matrix((
                            x_direction.to_3d(),
                            y_direction.to_3d(),
                            z_direction.to_3d()
                        )).transposed()
                        
                        current_scale = weapon_right_obj.matrix_basis.to_scale()
                        new_basis = mathutils.Matrix.LocRotScale(weapon_right_obj.location, rotation_matrix.to_quaternion(), current_scale)
                        weapon_right_obj.matrix_basis = new_basis
                        context.view_layer.update()
                        
                        damped_z = weapon_right_obj.constraints.new(type='DAMPED_TRACK')
                        damped_z.target = object_weapon_node1_2
                        damped_z.track_axis = 'TRACK_Z'

                        damped_y = weapon_right_obj.constraints.new(type='DAMPED_TRACK')
                        damped_y.target = object_weapon_node3_2
                        damped_y.track_axis = 'TRACK_Y'
                
                elif model_type == 'FOOT_GEAR':
                    if not foot_1_obj and not foot_2_obj:
                        self.report({'ERROR'}, "At least one footgear must be specified.")
                        return
                    
                    object_ntoe_1 = bpy.data.objects.get("NToe_1") # foot 1 origin
                    object_ntoes_1 = bpy.data.objects.get("NToeS_1") # foot 1 Y
                    object_nheel_1 = bpy.data.objects.get("NHeel_1") # foot 1 Z
                    
                    object_ntoe_2 = bpy.data.objects.get("NToe_2") # foot 2 origin
                    object_ntoes_2 = bpy.data.objects.get("NToeS_2") # foot 2 Y
                    object_nheel_2 = bpy.data.objects.get("NHeel_2") # foot 2 Z
                    
                    required_objects = [
                        object_ntoe_1,
                        object_ntoes_1,
                        object_nheel_1,
                        object_ntoe_2,
                        object_ntoes_2,
                        object_nheel_2
                    ]

                    # Check if all are not None
                    if not all(required_objects):
                        self.report({'ERROR'}, "NToe, NToeS or NHeel isn't found in the scene.\n Please make sure the Rig is correct.")
                        return {'CANCELLED'}
                    
                    if foot_1_obj:
                        origin_point = object_ntoe_1
                        target_z = object_nheel_1
                        target_y = object_ntoes_1
                        
                        foot_1_obj.matrix_world.translation = mathutils.Vector((0, 0, 0))
                        foot_1_obj.constraints.clear()
                        
                        copy_loc = foot_1_obj.constraints.new(type='COPY_LOCATION')
                        copy_loc.target = origin_point
                        copy_loc.use_offset = True
                        
                        z_direction = (target_z.location - origin_point.location).normalized()
                        y_direction = (target_y.location - origin_point.location).normalized()
                        x_direction = y_direction.cross(z_direction).normalized()
                        y_direction = z_direction.cross(x_direction).normalized()
                        
                        rotation_matrix = mathutils.Matrix((
                            x_direction.to_3d(),
                            y_direction.to_3d(),
                            z_direction.to_3d()
                        )).transposed()
                        
                        current_scale = foot_1_obj.matrix_basis.to_scale()
                        new_basis = mathutils.Matrix.LocRotScale(foot_1_obj.location, rotation_matrix.to_quaternion(), current_scale)
                        foot_1_obj.matrix_basis = new_basis
                        context.view_layer.update()
                        
                        damped_z = foot_1_obj.constraints.new(type='DAMPED_TRACK')
                        damped_z.target = target_z
                        damped_z.track_axis = 'TRACK_Z'

                        damped_y = foot_1_obj.constraints.new(type='DAMPED_TRACK')
                        damped_y.target = target_y
                        damped_y.track_axis = 'TRACK_Y'
                        
                    if foot_2_obj:
                        origin_point = object_ntoe_2
                        target_z = object_nheel_2
                        target_y = object_ntoes_2
                        
                        foot_2_obj.matrix_world.translation = mathutils.Vector((0, 0, 0))
                        foot_2_obj.constraints.clear()
                        
                        copy_loc = foot_2_obj.constraints.new(type='COPY_LOCATION')
                        copy_loc.target = origin_point
                        copy_loc.use_offset = True
                        
                        z_direction = (target_z.location - origin_point.location).normalized()
                        y_direction = (target_y.location - origin_point.location).normalized()
                        x_direction = y_direction.cross(z_direction).normalized()
                        y_direction = z_direction.cross(x_direction).normalized()
                        
                        rotation_matrix = mathutils.Matrix((
                            x_direction.to_3d(),
                            y_direction.to_3d(),
                            z_direction.to_3d()
                        )).transposed()
                        
                        current_scale = foot_2_obj.matrix_basis.to_scale()
                        new_basis = mathutils.Matrix.LocRotScale(foot_2_obj.location, rotation_matrix.to_quaternion(), current_scale)
                        foot_2_obj.matrix_basis = new_basis
                        context.view_layer.update()
                        
                        damped_z = foot_2_obj.constraints.new(type='DAMPED_TRACK')
                        damped_z.target = target_z
                        damped_z.track_axis = 'TRACK_Z'

                        damped_y = foot_2_obj.constraints.new(type='DAMPED_TRACK')
                        damped_y.target = target_y
                        damped_y.track_axis = 'TRACK_Y'
                    
                elif model_type == 'HEAD_GEAR':
                    if not selected_object:
                        self.report({'ERROR'}, "No Head Gear selected for orientation.")
                        return
                    
                    object_nhead = bpy.data.objects.get("NHead") # head origin
                    object_ntop = bpy.data.objects.get("NTop") # head Z
                    object_nheadf = bpy.data.objects.get("NHeadF") # head Y
                    
                    required_objects = [
                        object_nhead,
                        object_ntop,
                        object_nheadf
                    ]

                    # Check if all are not None
                    if not all(required_objects):
                        self.report({'ERROR'}, "NHead, NTop or NHeadF isn't found in the scene.\n Please make sure the Rig is correct.")
                        return {'CANCELLED'}
                    
                    origin_point = object_nhead
                    target_z = object_ntop
                    target_y = object_nheadf
                    
                    selected_object.matrix_world.translation = mathutils.Vector((0, 0, 0))
                    selected_object.constraints.clear()
                    
                    copy_loc = selected_object.constraints.new(type='COPY_LOCATION')
                    copy_loc.target = origin_point
                    copy_loc.use_offset = True
                    
                    z_direction = (target_z.location - origin_point.location).normalized()
                    y_direction = (target_y.location - origin_point.location).normalized()
                    x_direction = y_direction.cross(z_direction).normalized()
                    y_direction = z_direction.cross(x_direction).normalized()
                    
                    rotation_matrix = mathutils.Matrix((
                        x_direction.to_3d(),
                        y_direction.to_3d(),
                        z_direction.to_3d()
                    )).transposed()
                    
                    current_scale = selected_object.matrix_basis.to_scale()
                    new_basis = mathutils.Matrix.LocRotScale(selected_object.location, rotation_matrix.to_quaternion(), current_scale)
                    selected_object.matrix_basis = new_basis
                    context.view_layer.update()
                    
                    damped_z = selected_object.constraints.new(type='DAMPED_TRACK')
                    damped_z.target = target_z
                    damped_z.track_axis = 'TRACK_Z'

                    damped_y = selected_object.constraints.new(type='DAMPED_TRACK')
                    damped_y.target = target_y
                    damped_y.track_axis = 'TRACK_Y'
                
                elif model_type == 'RANGED':
                    if not selected_object:
                        self.report({'ERROR'}, "No Ranged selected for orientation.")
                        return
                    
                    object_ranged2 = bpy.data.objects.get("Ranged-Node2_1") # origin
                    object_ranged1 = bpy.data.objects.get("Ranged-Node1_1") # Z
                    object_ranged4 = bpy.data.objects.get("Ranged-Node4_1") #  Y
                    object_ranged3 = bpy.data.objects.get("Ranged-Node3_1") # X
                    
                    required_objects = [
                        object_ranged2,
                        object_ranged1,
                        object_ranged4,
                        object_ranged3
                    ]

                    # Check if all are not None
                    if not all(required_objects):
                        self.report({'ERROR'}, "Ranged skeleton isn't found or some nodes is invalid in the scene.\n Please make sure the Rig is correct.")
                        return {'CANCELLED'}
                    
                    origin_point = object_ranged2
                    target_z = object_ranged1
                    target_y = object_ranged4
                    
                    selected_object.matrix_world.translation = mathutils.Vector((0, 0, 0))
                    selected_object.constraints.clear()
                    
                    copy_loc = selected_object.constraints.new(type='COPY_LOCATION')
                    copy_loc.target = origin_point
                    copy_loc.use_offset = True
                    
                    z_direction = (target_z.location - origin_point.location).normalized()
                    y_direction = (target_y.location - origin_point.location).normalized()
                    x_direction = y_direction.cross(z_direction).normalized()
                    y_direction = z_direction.cross(x_direction).normalized()
                    
                    rotation_matrix = mathutils.Matrix((
                        x_direction.to_3d(),
                        y_direction.to_3d(),
                        z_direction.to_3d()
                    )).transposed()
                    
                    current_scale = selected_object.matrix_basis.to_scale()
                    new_basis = mathutils.Matrix.LocRotScale(selected_object.location, rotation_matrix.to_quaternion(), current_scale)
                    selected_object.matrix_basis = new_basis
                    context.view_layer.update()
                    
                    damped_z = selected_object.constraints.new(type='DAMPED_TRACK')
                    damped_z.target = target_z
                    damped_z.track_axis = 'TRACK_Z'

                    damped_y = selected_object.constraints.new(type='DAMPED_TRACK')
                    damped_y.target = target_y
                    damped_y.track_axis = 'TRACK_Y'
                
        def align_bodygear():
            if not model_path:
                self.report({'ERROR'}, "No model XML file selected")
                return {'CANCELLED'}
                
            model_collection = bpy.data.collections.get("Model")
            if not model_collection:
                model_collection = bpy.data.collections.new("Model")
                context.scene.collection.children.link(model_collection)
                
            model_name = os.path.basename(model_path).split('.')[0]
            child_collection = bpy.data.collections.get(model_name)
            if not child_collection:
                child_collection = bpy.data.collections.new(model_name)
                model_collection.children.link(child_collection)
                
            hook_collection_name = f"Hook_{model_name}"
            hook_collection = bpy.data.collections.get(hook_collection_name)
            if not hook_collection:
                hook_collection = bpy.data.collections.new(hook_collection_name)
                child_collection.children.link(hook_collection)
                
            # Mapping of alignment profiles
            alignment_profiles = {
                'CHEST': {
                    'copy_location': "NChest",
                    'track_1': "NNeck",
                    'track_2': "NChestF",
                    'track_3': "NChestS_2",
                },
                'STOMACH': {
                    'copy_location': "NStomach",
                    'track_1': "NChest",
                    'track_2': "NStomachF",
                    'track_3': "NStomachS_2",
                },
                'HIP': {
                    'copy_location': "NPivot",
                    'track_1': "NStomach",
                    'track_2': "NPelvisF",
                    'track_3': "NHip_2",
                }
            }

            def create_hook(vgroup_name, hook_suffix, alignment_type):
                if vgroup_name not in [vg.name for vg in selected_object.vertex_groups]:
                    return

                profile = alignment_profiles.get(alignment_type)
                if not profile:
                    return

                hook_name = f"Hook_{hook_suffix}_{model_name}"
                empty = bpy.data.objects.new(hook_name, None)
                empty.empty_display_type = 'PLAIN_AXES'
                hook_collection.objects.link(empty)

                # Copy Location Constraint
                if profile['copy_location']:
                    target = bpy.data.objects.get(profile['copy_location'])
                    if target:
                        constraint = empty.constraints.new(type='COPY_LOCATION')
                        constraint.target = target

                # Damped Track Constraints
                for axis, key in zip(['TRACK_Z', 'TRACK_Y', 'TRACK_X'], ['track_1', 'track_2', 'track_3']):
                    if flipped and axis == 'TRACK_X':
                        axis = 'TRACK_NEGATIVE_X'
                        
                    target_name = profile[key]
                    target_obj = bpy.data.objects.get(target_name)
                    if target_obj:
                        constraint = empty.constraints.new(type='DAMPED_TRACK')
                        constraint.track_axis = axis
                        constraint.target = target_obj
                
                context.view_layer.update()
                
                # Hook Modifier
                mod = selected_object.modifiers.new(name=f"Hook_{vgroup_name}", type='HOOK')
                mod.object = empty
                mod.vertex_group = vgroup_name
                
                if selected_object.type == 'MESH':
                    mesh = selected_object.data
                    bm = bmesh.new()
                    bm.from_mesh(mesh)

                    group_index = selected_object.vertex_groups[vgroup_name].index

                    # Collect vertex indices in the vertex group
                    verts_in_group = [
                        v.index for v in selected_object.data.vertices
                        if any(g.group == group_index for g in v.groups)
                    ]

                    if verts_in_group:
                        mod = selected_object.modifiers.get(f"Hook_{vgroup_name}")
                        if mod:
                            # Assign the hook modifier to those vertices
                            mod.vertex_indices_set(verts_in_group)

                    bm.free()

            create_hook("Armor_Top", "Top", model_body_top)
            create_hook("Armor_Middle", "Middle", model_body_middle)
            create_hook("Armor_Bottom", "Bottom", model_body_bottom)
        
        if advanced_options or model_type == 'MODEL':
            if settings.model_use_origin:
               align_origin()
            align_origin_orientation()
            add_constraint()
        
        elif not advanced_options and model_type != 'MODEL' and model_type != 'BODY_GEAR':
            if use_existing_object:
                align_origin_orientation()
                add_constraint()
            else:
                align_not_use_existing_object()
        
        elif not advanced_options and model_type == 'BODY_GEAR':
            align_bodygear()
            
        return {'FINISHED'}

class AddRuleOperator(bpy.types.Operator):
    bl_idname = "macro_rules.add_rule"
    bl_label = "Add Rule"
    bl_description = "Add a new group rule."

    def execute(self, context):
        context.scene.macro_rules.add()
        context.scene.macro_rules_index = len(context.scene.macro_rules) - 1
        return {'FINISHED'}

class RemoveRuleOperator(bpy.types.Operator):
    bl_idname = "macro_rules.remove_rule"
    bl_label = "Remove Rule"
    bl_description = "Remove a group rule."

    def execute(self, context):
        index = context.scene.macro_rules_index
        if index >= 0:
            context.scene.macro_rules.remove(index)
            context.scene.macro_rules_index = min(index, len(context.scene.macro_rules) - 1)
        return {'FINISHED'}

class AddTemplateGroupsOperator(bpy.types.Operator):
    bl_idname = "macro_rules.add_templates"
    bl_label = "Preset Groups"
    bl_description = "Add selected preset groups to the rule."

    group_type: bpy.props.EnumProperty(
        name="Group Type",
        description="Choose which preset groups to add",
        items=[
            ('ARMOR', "Armor", "Add only armor groups"),
            ('WEAPON', "Weapon", "Add only weapon groups"),
            ('ALL', "All", "Add all template groups"),
        ],
        default='ALL'
    )

    def execute(self, context):
        scene = context.scene
        existing_groups = {item.group for item in scene.macro_rules}

        templates = []

        if self.group_type in {'ARMOR', 'ALL'}:
            templates += [
                {"group": "Armor_Top", "names": "NChestS_2,NChestF,NChestS_1,NNeck"},
                {"group": "Armor_Middle", "names": "NStomachS_2,NStomachF,NStomachS_1,NChest"},
                {"group": "Armor_Bottom", "names": "NHip_1,NPelvisF,NHip_2,NStomach"},
            ]

        if self.group_type in {'WEAPON', 'ALL'}:
            templates += [
                {"group": "Weapon_1", "names": "Weapon-Node4_1,Weapon-Node3_1,Weapon-Node2_1,Weapon-Node1_1"},
                {"group": "Weapon_2", "names": "Weapon-Node4_2,Weapon-Node3_2,Weapon-Node2_2,Weapon-Node1_2"},
            ]

        added = 0
        for entry in templates:
            if entry["group"] not in existing_groups:
                rule = scene.macro_rules.add()
                rule.group = entry["group"]
                rule.names = entry["names"]
                added += 1

        self.report({'INFO'}, f"Added {added} template group(s)")
        
        # Force UI refresh
        for window in context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()

        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

class ClearMacroRulesOperator(bpy.types.Operator):
    bl_idname = "macro_rules.clear_rules"
    bl_label = "Clear All Rules"
    bl_description = "Remove all entries from the list"

    def execute(self, context):
        scene = context.scene
        scene.macro_rules.clear()
        scene.macro_rules_index = 0

        for window in context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()

        return {'FINISHED'}

# Settings
class GymnastToolModelSettings(bpy.types.PropertyGroup):
    selected_object: bpy.props.PointerProperty(
        name="Object",
        description="Select the object to convert into XML",
        type=bpy.types.Object,
        update=refresh_enum
    )
    model_string_name: bpy.props.StringProperty(
        name="Prefix",
        description="The name to add into each element's name in the XML such as Nodes, Edges and Figures.\nEx. 'Cloth-', 'CoolStaff-'",
    )
    weapon_object_1: bpy.props.PointerProperty(
        name="Weapon 1",
        description="Select the weapon that will be attach to the left hand",
        type=bpy.types.Object
    )
    weapon_object_2: bpy.props.PointerProperty(
        name="Weapon 2",
        description="Select the weapon that will be attach to the right hand",
        type=bpy.types.Object
    )
    foot_object_1: bpy.props.PointerProperty(
        name="Footwear 1",
        description="Select the footwear that will be attach to the right foot (Vector) or left foot (SF2)",
        type=bpy.types.Object
    )
    foot_object_2: bpy.props.PointerProperty(
        name="Footwear 2",
        description="Select the weapon that will be attach to the left foot (Vector) or right foot (SF2)",
        type=bpy.types.Object
    )
    model_type_export: bpy.props.EnumProperty(
        name="Type",
        description="Choose the type of model\nDefault: MODEL",
        items=[
            ('MODEL', "Model", "Normal model. (Mostly Used in Vector)"),
            ('HEAD_GEAR', "Head Gear", "Helm or Head accessory model."),
            ('BODY_GEAR', "Body Gear", "Armor or Body accessory model."),
            ('FOOT_GEAR', "Foot Gear", "Shoes or Footwear accessory model."),
            ('WEAPON', "Weapon", "Weapon Model. (SF2 Only)"),
            ('RANGED', "Ranged", "Ranged Weapon. (SF2 Only)")
        ],
        default='MODEL',
        update=refresh_enum
    )
    model_node_mass: bpy.props.FloatProperty(
        name="Node's Mass", 
        description="Mass for every node", 
        default=1.0,
        min=0.0,
        max=10000.0,
        precision=2
    )
    model_node_collisible: bpy.props.BoolProperty(
        name="Node's Collisible", 
        description="Every node is collisible\nDefault: False", 
        default=False
    )
    model_node_fixed: bpy.props.BoolProperty(
        name="Node's Fixed", 
        description="Every node is fixed and will not move (Unless it's played by model animation)\nDefault: False", 
        default=False
    )
    model_edge_collisible: bpy.props.BoolProperty(
        name="Edge's Collisible", 
        description="Every edge is collisible\nDefault: False", 
        default=False
    )
    model_node_offset: bpy.props.IntProperty(
        name="Start Node",
        description="Starting number for node numbering\nDefault: 1",
        default=1,
        min=1
    )
    model_edge_offset: bpy.props.IntProperty(
        name="Start Edge",
        description="Starting number for edge numbering\nDefault: 1",
        default=1,
        min=1
    )
    model_tri_offset: bpy.props.IntProperty(
        name="Start Tri",
        description="Starting number for triangle numbering\nDefault: 1",
        default=1,
        min=1
    )
    model_orientation: bpy.props.PointerProperty(
        name="Object",
        description="Select the object to set orientation (Must select two object in the scene to indicate the orientation.)",
        type=bpy.types.Object
    )
    model_use_origin: bpy.props.BoolProperty(
        name="Set Origin",
        description="Change the origin's location of the selected object and apply a ChildOf Constraint.\nDefault: False",
        default=False
    )
    model_origin_object: bpy.props.PointerProperty(
        name="Origin",
        description="The Object position to set to the selected object's origin.",
        type=bpy.types.Object
    )
    model_body_top: bpy.props.EnumProperty(
        name="Top",
        description="Select the body area that the body's gear will be attached to.\nDefault: CHEST",
        items=[
            ('CHEST', "Chest", "Chest area or the upper torso part to the neck."),
            ('STOMACH', "Stomach", "Stomach area or the middle torso, between the chest and the hip."),
            ('HIP', "Hip", "Hip area or the part below the middle torso.")
        ],
        default='CHEST'
    )
    model_body_middle: bpy.props.EnumProperty(
        name="Middle",
        description="Select the body area that the body's gear will be attached to.\nDefault: STOMACH",
        items=[
            ('CHEST', "Chest", "Chest area or the upper torso part to the neck."),
            ('STOMACH', "Stomach", "Stomach area or the middle torso, between the chest and the hip."),
            ('HIP', "Hip", "Hip area or the part below the middle torso.")
        ],
        default='STOMACH'
    )
    model_body_bottom: bpy.props.EnumProperty(
        name="Bottom",
        description="Select the body area that the body's gear will be attached to.\nDefault: HIP",
        items=[
            ('CHEST', "Chest", "Chest area or the upper torso part to the neck."),
            ('STOMACH', "Stomach", "Stomach area or the middle torso, between the chest and the hip."),
            ('HIP', "Hip", "Hip area or the part below the middle torso.")
        ],
        default='HIP'
    )
    model_export_capsules: bpy.props.BoolProperty(
        name="Export Capsules", 
        description="Includes capsules during the model exporting.\nDefault: False", 
        default=False
    )
    model_export_capsules_predefined: bpy.props.BoolProperty(
        name="Use Predefined Edge.", 
        description="Instead of finding suitable edge automatically during the export, it will use the name of the edge under the socket input.\nDefault: False", 
        default=False
    )
    model_export_capsules_folder: bpy.props.PointerProperty(
        name="Capsules Collection",
        description="The collection containing the Capsules ready to export.",
        type=bpy.types.Collection
    )
    model_export_cloth: bpy.props.BoolProperty(
        name="Export Cloth", 
        description="Specify node-cloth based on the assigned vertices in object's Vertex Group\nDefault: False", 
        default=False
    )
    model_export_cloth_attenuation: bpy.props.FloatProperty(
        name="Attenuation", 
        description="Controls how much a cloth node resists deformation.\n0 = Soft\n 1 = Stiff", 
        default=0,
        min=0.0,
        max=2.0,
        precision=2
    )
    model_export_cloth_mass: bpy.props.FloatProperty(
        name="Mass", 
        description="Mass for every cloth nodes", 
        default=0.1,
        min=0.0,
        max=10000.0,
        precision=2
    )
    model_export_cloth_general_folder: bpy.props.EnumProperty(
        name="Cloth Group",
        description="The Vertex Group containing the Object's Vertices marked as a cloth node.",
        items=get_general_vertex_groups
    )
    model_export_cloth_weapon1_folder: bpy.props.EnumProperty(
        name="Cloth Group 1",
        description="The Vertex Group containing the Weapon 1's Vertices marked as a cloth node.",
        items=get_weapon1_vertex_groups
    )
    model_export_cloth_weapon2_folder: bpy.props.EnumProperty(
        name="Cloth Group 2",
        description="The Vertex Group containing the Weapon 2's Vertices marked as a cloth node.",
        items=get_weapon2_vertex_groups
    )
    model_export_cloth_foot1_folder: bpy.props.EnumProperty(
        name="Cloth Group 1",
        description="The Vertex Group containing the Foot 1's Vertices marked as a cloth node.",
        items=get_foot1_vertex_groups
    )
    model_export_cloth_foot2_folder: bpy.props.EnumProperty(
        name="Cloth Group 2",
        description="The Vertex Group containing the Foot 2's Vertices marked as a cloth node.",
        items=get_foot2_vertex_groups
    )
    model_apply_constraint: bpy.props.BoolProperty(
        name="Add Constraint", 
        description="Add a Damped Track and Copy Location Constraint to the Object.\nThe first selected Object will be Z and second will be Y\nDefault: False", 
        default=False
    )
    model_is_advanced: bpy.props.BoolProperty(
        name="Advanced Options", 
        description="Allows for a manual set-up with complicated models.", 
        default=False
    )
    model_use_existing_object: bpy.props.BoolProperty(
        name="Use Existing OBJ", 
        description="When importing Nekki's Model, the LCCs will already be applied to the MacroNode. This make it so that when:\n Enabled - Set Origin Alignment and Constraint to the Model will not change its position visually.\n Disabled - Set Model's alignment and constraint will change its position and orientation (Used for Model that's not attached originally).\nDefault: True", 
        default=True
    )
    calculate_macronode: bpy.props.BoolProperty(
        name="Apply LCCs", 
        description="Whether or not to apply LCC to MacroNode while importing.\nDefault: True", 
        default=True
    )
    model_include_attack_edges: bpy.props.BoolProperty(
        name="Add Attack Edges", 
        description="Edges for defining the damage part.\nDefault: True", 
        default=True
    )
    model_attack_edges_object_1: bpy.props.PointerProperty(
        name="Edges 1",
        description="Select the object to be referenced as attack edges for weapon 1.",
        type=bpy.types.Object
    )
    model_attack_edges_object_2: bpy.props.PointerProperty(
        name="Edges 2",
        description="Select the object to be referenced as attack edges for weapon 2.",
        type=bpy.types.Object
    )
    model_use_pivot: bpy.props.BoolProperty(
        name="Use Pivot",
        description="Whether or not to specify which vertex should be a Pivot Node.\nIf you disable this and try to load the model in, the game may crash.\nDefault: True",
        default=True
    )
    model_pivot: bpy.props.EnumProperty(
        name="Pivot",
        description="The Vertex Group containing the Object's Vertex that will be referenced as a Pivot Node\nUsually consisting of just 1 Vertex.",
        items=get_general_vertex_groups
    )
    model_include_necessary_tri_body: bpy.props.BoolProperty(
        name="Include Foot Triangle (SF2)", 
        description="Normally, there's a visible hole on the side of the foot for SF2's rig. We can hide this with a triangle.\nDefault: False", 
        default=False
    )
    model_use_dependencies: bpy.props.BoolProperty(
        name="Use Dependencies", 
        description="While exporting model, it will also search for the nodes inside the Dependencies XML.\nIf this is disabled, then it will only use the node inside the Model XML.\nDefault: True", 
        default=True
    )
    import_node_as_vertex: bpy.props.BoolProperty(
        name="Import Node as Vertex", 
        description="Importing node will add nodes as a vertices, instead of UV Sphere.\nNote: For Import Nodes.\nDefault: False", 
        default=False
    )
    add_vertex_group: bpy.props.BoolProperty(
        name="Add Vertex Group", 
        description="While importing XML to OBJ, it will also add an appropriate Vertex Group based on the Node and MacroNode's attributes.\nEx. Cloth Node and Armor Top, Middle, Bottom section.\nDefault: True", 
        default=True
    )
    add_vertex_group_include_cloth: bpy.props.BoolProperty(
        name="Include Cloth", 
        description="Add a Cloth Vertex Group during the conversion.\nDefault: True", 
        default=True
    )
    model_align_flipped: bpy.props.BoolProperty(
        name="Flipped",
        description="Whether or not the damped track should be flipped.\nNormally, Vector and SF2 rig has swapped side, 1 will be swapped with 2 (Ex. NAnkle_1 --> NAnkle_2)\nVector = True, SF2 = False\nDefault: False",
        default=False
    )
    model_custom_childnode: bpy.props.BoolProperty(
        name="Custom ChildNodes", 
        description="**WORK IN PROGRESS: CURRENTLY FIXED AT ONLY 4 CHILDNODE\nDefine a custom childnodes.\nDefault: False", 
        default=False
    )
    childnode_1_object: bpy.props.PointerProperty(
        name="Childnode 1",
        description="Select the object to be referenced as childnode 1 for Macronode.",
        type=bpy.types.Object
    )
    childnode_2_object: bpy.props.PointerProperty(
        name="Childnode 2",
        description="Select the object to be referenced as childnode 2 for Macronode.",
        type=bpy.types.Object
    )
    childnode_3_object: bpy.props.PointerProperty(
        name="Childnode 3",
        description="Select the object to be referenced as childnode 3 for Macronode.",
        type=bpy.types.Object
    )
    childnode_4_object: bpy.props.PointerProperty(
        name="Childnode 4",
        description="Select the object to be referenced as childnode 4 for Macronode.",
        type=bpy.types.Object
    )
    macronode_vertex_group: bpy.props.EnumProperty(
        name="Macronode",
        description="The Vertex Group containing the Object's Vertices that will be referenced as a Macronode.",
        items=get_general_vertex_groups
    )
    macronode_vertex_group_weapon_1: bpy.props.EnumProperty(
        name="Macronode 1",
        description="The Vertex Group containing the Object's Vertices that will be referenced as a Macronode for the Weapon 1.",
        items=get_weapon1_vertex_groups
    )
    macronode_vertex_group_weapon_2: bpy.props.EnumProperty(
        name="Macronode 2",
        description="The Vertex Group containing the Object's Vertices that will be referenced as a Macronode for the Weapon 2.",
        items=get_weapon2_vertex_groups
    )
    macronode_vertex_group_foot_1: bpy.props.EnumProperty(
        name="Macronode 1",
        description="The Vertex Group containing the Object's Vertices that will be referenced as a Macronode for the Foot 1.",
        items=get_foot1_vertex_groups
    )
    macronode_vertex_group_foot_2: bpy.props.EnumProperty(
        name="Macronode 2",
        description="The Vertex Group containing the Object's Vertices that will be referenced as a Macronode for the Foot 2.",
        items=get_foot2_vertex_groups
    )
    
class MacroRuleItem(bpy.types.PropertyGroup):
    group: bpy.props.StringProperty(name="Group", description="Name of the Vertex Group.")
    names: bpy.props.StringProperty(name="Names", description="Names of the 4 ChildNode separated by commas with no space.\nEx. NChestS_2,NChestF,NChestS_1,NNeck")
    
    
# #################### #
# Sideview Panel Menu  #
# #################### #


class VIEW3D_PT_gymnast_model_panel(bpy.types.Panel):
    bl_label = "Model Tools"
    bl_idname = "VIEW3D_PT_gymnast_model_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Gymnast Tool Suite"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        layout.prop(context.scene, "gymnast_dependencies_xml")
        layout.prop(context.scene, "gymnast_normal_xml")
        box = layout.box()
        box.label(text="Model Options", icon='OBJECT_DATA')
        box.operator(ConvertXMLOperator.bl_idname, text="Convert XML to OBJ")
        box.operator(ExportModelToXML.bl_idname, text="Convert OBJ to XML")
        box.operator(AddNodesOperator.bl_idname, text="Import Nodes")
        box.operator(AddEdgesOperator.bl_idname, text="Import Edges")
        box.operator(AddCapsulesOperator.bl_idname, text="Import Capsules")

class VIEW3D_PT_gymnast_model_settings(bpy.types.Panel):
    bl_label = "Settings"
    bl_idname = "VIEW3D_PT_gymnast_model_settings"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Gymnast Tool Suite'
    bl_parent_id = "VIEW3D_PT_gymnast_model_panel"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout

class VIEW3D_PT_gymnast_model_settings_import(bpy.types.Panel):
    bl_label = "Import Settings"
    bl_idname = "VIEW3D_PT_gymnast_model_settings_import"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Gymnast Tool Suite'
    bl_parent_id = "VIEW3D_PT_gymnast_model_settings"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        props = context.scene.gymnast_tool_model_props
        layout = self.layout
        box = layout.box()
        scene = context.scene
        rules = scene.macro_rules
        
        box.label(text="Import Settings")
        box.prop(context.scene.gymnast_tool_model_props, "calculate_macronode")
        box.prop(context.scene.gymnast_tool_model_props, "model_use_dependencies")
        box.prop(context.scene.gymnast_tool_model_props, "import_node_as_vertex")
        
        box.prop(context.scene.gymnast_tool_model_props, "add_vertex_group")
        if props.add_vertex_group:
            row = layout.row()
            row.template_list("MACRO_UL_rules", "", scene, "macro_rules", scene, "macro_rules_index")
            
            col = row.column(align=True)
            col.operator("macro_rules.add_rule", icon='ADD', text="")
            col.operator("macro_rules.remove_rule", icon='REMOVE', text="")
            col.operator("macro_rules.add_templates", icon='PRESET', text="")
            col.operator("macro_rules.clear_rules", icon='TRASH', text="")
            layout.prop(context.scene.gymnast_tool_model_props, "add_vertex_group_include_cloth")
            
            if scene.macro_rules_index >= 0 and len(rules) > 0:
                item = rules[scene.macro_rules_index]
                layout.prop(item, "group")
                layout.prop(item, "names")

class MACRO_UL_rules(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        layout.label(text=item.group)

class VIEW3D_PT_gymnast_model_settings_export(bpy.types.Panel):
    bl_label = "Export Settings"
    bl_idname = "VIEW3D_PT_gymnast_model_settings_export"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Gymnast Tool Suite'
    bl_parent_id = "VIEW3D_PT_gymnast_model_settings"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        props = context.scene.gymnast_tool_model_props
        model_type = props.model_type_export
        layout = self.layout
        box = layout.box()
        box.label(text="Export Settings")
        box.prop(context.scene.gymnast_tool_model_props, "model_string_name")
        box.prop(context.scene.gymnast_tool_model_props, "model_type_export")
        if model_type == 'MODEL':
            box.prop(props, "selected_object")
            box.prop(context.scene.gymnast_tool_model_props, "model_node_mass")
            box.prop(context.scene.gymnast_tool_model_props, "model_node_fixed")
            box.prop(context.scene.gymnast_tool_model_props, "model_node_collisible")
            box.prop(context.scene.gymnast_tool_model_props, "model_edge_collisible")
            box.prop(context.scene.gymnast_tool_model_props, "model_use_pivot")
            if props.model_use_pivot:
                box.prop(context.scene.gymnast_tool_model_props, "model_pivot")
        elif model_type == 'HEAD_GEAR':
            box.prop(props, "selected_object")
            box.prop(context.scene.gymnast_tool_model_props, "model_node_mass")
            box.prop(context.scene.gymnast_tool_model_props, "model_edge_collisible")
        elif model_type == 'BODY_GEAR':
            box.prop(props, "selected_object")
            box.prop(context.scene.gymnast_tool_model_props, "model_node_mass")
            box.prop(context.scene.gymnast_tool_model_props, "model_body_top")
            box.prop(context.scene.gymnast_tool_model_props, "model_body_middle")
            box.prop(context.scene.gymnast_tool_model_props, "model_body_bottom")
            box.prop(context.scene.gymnast_tool_model_props, "model_edge_collisible")            
        elif model_type == 'WEAPON':
            box.prop(props, "weapon_object_1")
            box.prop(props, "weapon_object_2")
            box.prop(context.scene.gymnast_tool_model_props, "model_node_mass")
            box.prop(context.scene.gymnast_tool_model_props, "model_node_fixed")
            box.prop(context.scene.gymnast_tool_model_props, "model_edge_collisible")
        elif model_type == 'FOOT_GEAR':
            box.prop(props, "foot_object_1")
            box.prop(props, "foot_object_2")
            box.prop(context.scene.gymnast_tool_model_props, "model_node_mass")
            box.prop(context.scene.gymnast_tool_model_props, "model_edge_collisible")
        elif model_type == 'RANGED':
            box.prop(props, "selected_object")
            box.prop(context.scene.gymnast_tool_model_props, "model_node_mass")
            box.prop(context.scene.gymnast_tool_model_props, "model_node_fixed")
            box.prop(context.scene.gymnast_tool_model_props, "model_edge_collisible")
        
        
        if model_type == 'WEAPON':
            box3 = layout.box()
            box3.label(text="Attack Edges")
            box3.prop(context.scene.gymnast_tool_model_props, "model_include_attack_edges")
            if props.model_include_attack_edges:
                box3.prop(context.scene.gymnast_tool_model_props, "model_attack_edges_object_1")
                box3.prop(context.scene.gymnast_tool_model_props, "model_attack_edges_object_2")
        elif model_type == 'RANGED':
            box3 = layout.box()
            box3.label(text="Attack Edges")
            box3.prop(context.scene.gymnast_tool_model_props, "model_include_attack_edges")
            if props.model_include_attack_edges:
                box3.prop(context.scene.gymnast_tool_model_props, "model_attack_edges_object_1")
        
        box2 = layout.box()
        
        box2.label(text="Additional Settings")
        
        if model_type == 'BODY_GEAR':
            box2.prop(context.scene.gymnast_tool_model_props, "model_include_necessary_tri_body")
        
        box2.prop(context.scene.gymnast_tool_model_props, "model_export_capsules")
        if props.model_export_capsules:
            box2.prop(context.scene.gymnast_tool_model_props, "model_export_capsules_predefined")
            box2.prop(context.scene.gymnast_tool_model_props, "model_export_capsules_folder")
            
        box2.prop(context.scene.gymnast_tool_model_props, "model_export_cloth")
        if props.model_export_cloth:
            box2.prop(context.scene.gymnast_tool_model_props, "model_export_cloth_attenuation")
            box2.prop(context.scene.gymnast_tool_model_props, "model_export_cloth_mass")
            if model_type == 'MODEL' or model_type == 'HEAD_GEAR' or model_type == 'BODY_GEAR':
                box2.prop(context.scene.gymnast_tool_model_props, "model_export_cloth_general_folder")
            elif model_type == 'WEAPON':
                box2.prop(context.scene.gymnast_tool_model_props, "model_export_cloth_weapon1_folder")
                box2.prop(context.scene.gymnast_tool_model_props, "model_export_cloth_weapon2_folder")
            elif model_type == 'FOOT_GEAR':
                box2.prop(context.scene.gymnast_tool_model_props, "model_export_cloth_foot1_folder")
                box2.prop(context.scene.gymnast_tool_model_props, "model_export_cloth_foot2_folder")
        
        box3 = layout.box()
        box3.label(text="Childnode (WIP)")
        
        
        
class VIEW3D_PT_gymnast_settings_object_settings(bpy.types.Panel):
    bl_label = "Object Settings"
    bl_idname = "VIEW3D_PT_gymnast_settings_object_settings"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Gymnast Tool Suite'
    bl_parent_id = "VIEW3D_PT_gymnast_model_settings"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        props = context.scene.gymnast_tool_model_props
        layout = self.layout
        layout.prop(context.scene.gymnast_tool_model_props, "model_is_advanced")
        if not props.model_is_advanced:
            layout.prop(context.scene.gymnast_tool_model_props, "model_type_export")
        
        if props.model_is_advanced:
            box = layout.box()
            box.label(text="Alignment")
            box.prop(context.scene.gymnast_tool_model_props, "model_orientation")
            box.prop(context.scene.gymnast_tool_model_props, "model_use_origin")
            if props.model_use_origin:
                box.prop(context.scene.gymnast_tool_model_props, "model_origin_object")
            box.prop(context.scene.gymnast_tool_model_props, "model_apply_constraint")
            box.operator(SetOrientation.bl_idname, text="Set Alignment")
        else:
            if props.model_type_export == 'WEAPON':
                box = layout.box()
                box.label(text="Weapon Alignment")
                box.prop(context.scene.gymnast_tool_model_props, "weapon_object_1")
                box.prop(context.scene.gymnast_tool_model_props, "weapon_object_2")
                box.prop(context.scene.gymnast_tool_model_props, "model_use_existing_object")
                box.operator(SetOrientation.bl_idname, text="Set Alignment")
            elif props.model_type_export == 'FOOT_GEAR':
                box = layout.box()
                box.label(text="Footwear Alignment")
                box.prop(context.scene.gymnast_tool_model_props, "foot_object_1")
                box.prop(context.scene.gymnast_tool_model_props, "foot_object_2")
                box.prop(context.scene.gymnast_tool_model_props, "model_use_existing_object")
                box.operator(SetOrientation.bl_idname, text="Set Alignment")
            elif props.model_type_export == 'HEAD_GEAR':
                box = layout.box()
                box.label(text="Head Gear Alignment")
                box.prop(context.scene.gymnast_tool_model_props, "selected_object")
                box.prop(context.scene.gymnast_tool_model_props, "model_use_existing_object")
                box.prop(context.scene.gymnast_tool_model_props, "model_align_flipped")
                box.operator(SetOrientation.bl_idname, text="Set Alignment")
            elif props.model_type_export == 'BODY_GEAR':
                box = layout.box()
                box.label(text="Body Gear Alignment")
                box.prop(context.scene.gymnast_tool_model_props, "selected_object")
                box.prop(context.scene.gymnast_tool_model_props, "model_body_top")
                box.prop(context.scene.gymnast_tool_model_props, "model_body_middle")
                box.prop(context.scene.gymnast_tool_model_props, "model_body_bottom")
                box.prop(context.scene.gymnast_tool_model_props, "model_align_flipped")                
                box.operator(SetOrientation.bl_idname, text="Set Alignment")
            elif props.model_type_export == 'MODEL':
                box = layout.box()
                box.label(text="Alignment")
                box.prop(context.scene.gymnast_tool_model_props, "model_orientation")
                box.prop(context.scene.gymnast_tool_model_props, "model_use_origin")
                if props.model_use_origin:
                    box.prop(context.scene.gymnast_tool_model_props, "model_origin_object")
                box.prop(context.scene.gymnast_tool_model_props, "model_apply_constraint")
                box.operator(SetOrientation.bl_idname, text="Set Alignment")
            elif props.model_type_export == 'RANGED':
                box = layout.box()
                box.label(text="Ranged Alignment")
                box.prop(context.scene.gymnast_tool_model_props, "selected_object")
                box.prop(context.scene.gymnast_tool_model_props, "model_use_existing_object")
                box.operator(SetOrientation.bl_idname, text="Set Alignment")
            
class VIEW3D_PT_gymnast_model_settings_misc(bpy.types.Panel):
    bl_label = "Miscellaneous"
    bl_idname = "VIEW3D_PT_gymnast_model_settings_misc"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Gymnast Tool Suite'
    bl_parent_id = "VIEW3D_PT_gymnast_model_settings"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text="Offset")
        box.prop(context.scene.gymnast_tool_model_props, "model_node_offset")
        box.prop(context.scene.gymnast_tool_model_props, "model_edge_offset")
        box.prop(context.scene.gymnast_tool_model_props, "model_tri_offset")

#register
classes = [
    ConvertXMLOperator,
    ExportModelToXML,
    AddNodesOperator,
    AddEdgesOperator,
    AddCapsulesOperator,
    SetOrientation,
    MACRO_UL_rules,
    AddRuleOperator,
    RemoveRuleOperator,
    AddTemplateGroupsOperator,
    ClearMacroRulesOperator,
    GymnastToolModelSettings,
    MacroRuleItem,
    VIEW3D_PT_gymnast_model_panel,
    VIEW3D_PT_gymnast_model_settings,
    VIEW3D_PT_gymnast_model_settings_import,
    VIEW3D_PT_gymnast_model_settings_export,
    VIEW3D_PT_gymnast_settings_object_settings,
    VIEW3D_PT_gymnast_model_settings_misc,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.gymnast_dependencies_xml = bpy.props.StringProperty(
        name="Dependencies XML",
        description="Select the dependencies/skeleton XML file",
        subtype="FILE_PATH"
    )
    bpy.types.Scene.gymnast_normal_xml = bpy.props.StringProperty(
        name="Model XML",
        description="Select the normal model XML file",
        subtype="FILE_PATH"
    )
    bpy.types.Scene.gymnast_tool_model_props = bpy.props.PointerProperty(type=GymnastToolModelSettings)
    bpy.types.Scene.macro_rules = bpy.props.CollectionProperty(type=MacroRuleItem)
    bpy.types.Scene.macro_rules_index = bpy.props.IntProperty()

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