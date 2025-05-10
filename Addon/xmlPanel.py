# #################### #
# XML Panel
# #################### #

import bpy
import xml.etree.ElementTree as ET
import xml.dom.minidom
from bpy.props import StringProperty, CollectionProperty, PointerProperty


# #################### #
# Property Groups      #
# #################### #


class XMLAttribute(bpy.types.PropertyGroup):
    key: StringProperty(name="Key")
    value: StringProperty(name="Value")

class XMLItem(bpy.types.PropertyGroup):
    name: StringProperty(name="Element Name")
    attributes: CollectionProperty(type=XMLAttribute)
    attribute_index: bpy.props.IntProperty()
    
    
# #################### #
# Operator             #
# #################### #


class LoadXMLSceneOperator(bpy.types.Operator):
    bl_idname = "xmlscene.load"
    bl_label = "Import XML"
    bl_description = "Load and parse an XML file into categorized panels"

    def execute(self, context):
        scene = context.scene
        scene.xml_nodes.clear()
        scene.xml_edges.clear()
        scene.xml_figures.clear()

        try:
            path = bpy.path.abspath(scene.xml_file_path)
            tree = ET.parse(path)
            root = tree.getroot()

            def process_section(tag, collection):
                section = root.find(tag)
                if section:
                    for elem in section:
                        item = collection.add()
                        item.name = elem.tag
                        for k, v in elem.attrib.items():
                            attr = item.attributes.add()
                            attr.key = k
                            attr.value = v

            process_section("Nodes", scene.xml_nodes)
            process_section("Edges", scene.xml_edges)
            process_section("Figures", scene.xml_figures)

            self.report({'INFO'}, "XML loaded successfully.")
        except Exception as e:
            self.report({'ERROR'}, f"Failed: {e}")

        return {'FINISHED'}

class XML_OT_AddElement(bpy.types.Operator):
    bl_idname = "xmlscene.add_element"
    bl_label = "Add Element"
    bl_description = "Add a new element to the list"

    type: StringProperty()  # "nodes", "edges", "figures"

    def execute(self, context):
        scene = context.scene
        collection = getattr(scene, f"xml_{self.type}")
        item = collection.add()
        item.name = "NewElement"
        setattr(scene, f"xml_{self.type}_index", len(collection) - 1)
        return {'FINISHED'}

class XML_OT_RemoveElement(bpy.types.Operator):
    bl_idname = "xmlscene.remove_element"
    bl_label = "Remove Element"
    bl_description = "Remove the selected element from the list"

    type: StringProperty()  # "nodes", "edges", "figures"

    def execute(self, context):
        scene = context.scene
        collection = getattr(scene, f"xml_{self.type}")
        index = getattr(scene, f"xml_{self.type}_index")
        if 0 <= index < len(collection):
            collection.remove(index)
            setattr(scene, f"xml_{self.type}_index", min(index, len(collection) - 1))
        return {'FINISHED'}

class XML_OT_AddAttribute(bpy.types.Operator):
    bl_idname = "xmlscene.add_attribute"
    bl_label = "Add Attribute"
    bl_description = "Add a new attribute to the selected element"

    type: StringProperty()  # "nodes", "edges", "figures"

    def execute(self, context):
        scene = context.scene
        index = getattr(scene, f"xml_{self.type}_index")
        collection = getattr(scene, f"xml_{self.type}")
        if 0 <= index < len(collection):
            item = collection[index]
            attr = item.attributes.add()
            attr.key = "Key"
            attr.value = "Value"
        return {'FINISHED'}

class RemoveXMLAttributeOperator(bpy.types.Operator):
    bl_idname = "xmlscene.remove_attribute"
    bl_label = "Remove Attribute"
    type: StringProperty()

    def execute(self, context):
        scene = context.scene
        collection = getattr(scene, f"xml_{self.type}")
        index = getattr(scene, f"xml_{self.type}_index")

        if 0 <= index < len(collection):
            item = collection[index]
            attr_index = item.attribute_index
            if 0 <= attr_index < len(item.attributes):
                item.attributes.remove(attr_index)
                item.attribute_index = max(0, attr_index - 1)

        return {'FINISHED'}

class XML_OT_ClearElements(bpy.types.Operator):
    bl_idname = "xmlscene.clear_elements"
    bl_label = "Clear All Elements"
    bl_description = "Clear the entire list of elements"

    type: StringProperty()

    def execute(self, context):
        scene = context.scene
        getattr(scene, f"xml_{self.type}").clear()
        setattr(scene, f"xml_{self.type}_index", 0)
        return {'FINISHED'}

class MoveXMLAttributeOperator(bpy.types.Operator):
    bl_idname = "xmlscene.move_attribute"
    bl_label = "Move Attribute"
    type: StringProperty()
    direction: StringProperty()

    def execute(self, context):
        scene = context.scene
        collection = getattr(scene, f"xml_{self.type}")
        index = getattr(scene, f"xml_{self.type}_index")

        if 0 <= index < len(collection):
            item = collection[index]
            attr_index = item.attribute_index
            new_index = attr_index + (-1 if self.direction == 'UP' else 1)

            if 0 <= new_index < len(item.attributes):
                item.attributes.move(attr_index, new_index)
                item.attribute_index = new_index

        return {'FINISHED'}

class MoveXMLElementOperator(bpy.types.Operator):
    bl_idname = "xmlscene.move_element"
    bl_label = "Move Element"
    bl_description = "Move the selected element up or down in the list"

    type: StringProperty()
    direction: StringProperty()

    def execute(self, context):
        scene = context.scene
        collection = getattr(scene, f"xml_{self.type}")
        index = getattr(scene, f"xml_{self.type}_index")

        new_index = index + (-1 if self.direction == 'UP' else 1)

        if 0 <= index < len(collection) and 0 <= new_index < len(collection):
            collection.move(index, new_index)
            setattr(scene, f"xml_{self.type}_index", new_index)

        return {'FINISHED'}

class XMLSceneSaveOperator(bpy.types.Operator):
    bl_idname = "xmlscene.save"
    bl_label = "Export XML"
    bl_description = "Save into an XML file."

    filepath: StringProperty(subtype="FILE_PATH")

    def execute(self, context):
        scene = context.scene

        root = ET.Element("Scene")
        for section_name in ["nodes", "edges", "figures"]:
            section_tag = section_name.capitalize()
            section_elem = ET.SubElement(root, section_tag)

            collection = getattr(scene, f"xml_{section_name}")
            for item in collection:
                element = ET.SubElement(section_elem, item.name)
                for attr in item.attributes:
                    element.set(attr.key, attr.value)

        rough_string = ET.tostring(root, 'utf-8')
        reparsed = xml.dom.minidom.parseString(rough_string)
        pretty_xml = reparsed.toprettyxml(indent="  ")  # 2 spaces

        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                f.write(pretty_xml)
            self.report({'INFO'}, f"XML saved to {self.filepath}")
        except Exception as e:
            self.report({'ERROR'}, f"Failed to save: {e}")
            return {'CANCELLED'}

        return {'FINISHED'}

    def invoke(self, context, event):
        if not self.filepath.lower().endswith(".xml"):
            self.filepath = bpy.path.ensure_ext(self.filepath, "exported_xml.xml")
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


# #################### #
# Panel Menu           #
# #################### #


class XMLScenePanel(bpy.types.Panel):
    bl_label = "XML Tools"
    bl_idname = "VIEW3D_PT_xml_scene"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Gymnast Tool Suite'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        layout.prop(scene, "xml_file_path")
        layout.operator("xmlscene.load", icon="FILE_FOLDER")
        layout.operator("xmlscene.save", icon="FILE_TICK")
  
def draw_items(layout, items):
    for item in items:
        box = layout.box()
        box.label(text=f"{item.name}")
        for attr in item.attributes:
            row = box.row(align=True)
            row.prop(attr, "key", text="")
            row.prop(attr, "value", text="")

class XMLNodePanel(bpy.types.Panel):
    bl_label = "Nodes"
    bl_idname = "VIEW3D_PT_xml_nodes"
    bl_parent_id = "VIEW3D_PT_xml_scene"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'XMLScene'

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        row = layout.row()
        row.template_list("XML_UL_ElementList", "", scene, "xml_nodes", scene, "xml_nodes_index")
        
        col = row.column(align=True)
        col.operator("xmlscene.add_element", text="", icon="ADD").type = "nodes"
        col.operator("xmlscene.remove_element", text="", icon="REMOVE").type = "nodes"
        col.operator("xmlscene.clear_elements", text="", icon="TRASH").type = "nodes"
        
        op = col.operator("xmlscene.move_element", text="", icon="TRIA_UP")
        op.type = "nodes"
        op.direction = "UP"

        op = col.operator("xmlscene.move_element", text="", icon="TRIA_DOWN")
        op.type = "nodes"
        op.direction = "DOWN"

        if len(scene.xml_nodes) > 0 and scene.xml_nodes_index < len(scene.xml_nodes):
            item = scene.xml_nodes[scene.xml_nodes_index]

            box = layout.box()
            box.label(text=f"Attributes of {item.name}")

            row = box.row()
            row.template_list("XML_UL_AttributeList", "", item, "attributes", item, "attribute_index")

            col = row.column(align=True)
            col.operator("xmlscene.add_attribute", text="", icon="ADD").type = "nodes"
            col.operator("xmlscene.remove_attribute", text="", icon="REMOVE").type = "nodes"
            col.separator()
            op = col.operator("xmlscene.move_attribute", text="", icon="TRIA_UP")
            op.direction = 'UP'
            op.type = 'nodes'

            op = col.operator("xmlscene.move_attribute", text="", icon="TRIA_DOWN")
            op.direction = 'DOWN'
            op.type = 'nodes'

class XMLEdgePanel(bpy.types.Panel):
    bl_label = "Edges"
    bl_idname = "VIEW3D_PT_xml_edges"
    bl_parent_id = "VIEW3D_PT_xml_scene"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'XMLScene'

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        row = layout.row()
        row.template_list("XML_UL_ElementList", "", scene, "xml_edges", scene, "xml_edges_index")
        
        col = row.column(align=True)
        col.operator("xmlscene.add_element", text="", icon="ADD").type = "edges"
        col.operator("xmlscene.remove_element", text="", icon="REMOVE").type = "edges"
        col.operator("xmlscene.clear_elements", text="", icon="TRASH").type = "edges"
        
        op = col.operator("xmlscene.move_element", text="", icon="TRIA_UP")
        op.type = "edges"
        op.direction = "UP"

        op = col.operator("xmlscene.move_element", text="", icon="TRIA_DOWN")
        op.type = "edges"
        op.direction = "DOWN"

        if len(scene.xml_edges) > 0 and scene.xml_edges_index < len(scene.xml_edges):
            item = scene.xml_edges[scene.xml_edges_index]

            box = layout.box()
            box.label(text=f"Attributes of {item.name}")

            row = box.row()
            row.template_list("XML_UL_AttributeList", "", item, "attributes", item, "attribute_index")

            col = row.column(align=True)
            col.operator("xmlscene.add_attribute", text="", icon="ADD").type = "edges"
            col.operator("xmlscene.remove_attribute", text="", icon="REMOVE").type = "edges"
            col.separator()
            op = col.operator("xmlscene.move_attribute", text="", icon="TRIA_UP")
            op.direction = 'UP'
            op.type = 'edges'

            op = col.operator("xmlscene.move_attribute", text="", icon="TRIA_DOWN")
            op.direction = 'DOWN'
            op.type = 'edges'

class XMLFigurePanel(bpy.types.Panel):
    bl_label = "Figures"
    bl_idname = "VIEW3D_PT_xml_figures"
    bl_parent_id = "VIEW3D_PT_xml_scene"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'XMLScene'

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        row = layout.row()
        row.template_list("XML_UL_ElementList", "", scene, "xml_figures", scene, "xml_figures_index")
        
        col = row.column(align=True)
        col.operator("xmlscene.add_element", text="", icon="ADD").type = "figures"
        col.operator("xmlscene.remove_element", text="", icon="REMOVE").type = "figures"
        col.operator("xmlscene.clear_elements", text="", icon="TRASH").type = "figures"
        
        op = col.operator("xmlscene.move_element", text="", icon="TRIA_UP")
        op.type = "figures"
        op.direction = "UP"

        op = col.operator("xmlscene.move_element", text="", icon="TRIA_DOWN")
        op.type = "figures"
        op.direction = "DOWN"

        if len(scene.xml_figures) > 0 and scene.xml_figures_index < len(scene.xml_figures):
            item = scene.xml_figures[scene.xml_figures_index]

            box = layout.box()
            box.label(text=f"Attributes of {item.name}")

            row = box.row()
            row.template_list("XML_UL_AttributeList", "", item, "attributes", item, "attribute_index")

            col = row.column(align=True)
            col.operator("xmlscene.add_attribute", text="", icon="ADD").type = "figures"
            col.operator("xmlscene.remove_attribute", text="", icon="REMOVE").type = "figures"
            col.separator()
            op = col.operator("xmlscene.move_attribute", text="", icon="TRIA_UP")
            op.direction = 'UP'
            op.type = 'figures'

            op = col.operator("xmlscene.move_attribute", text="", icon="TRIA_DOWN")
            op.direction = 'DOWN'
            op.type = 'figures'

class XML_UL_ElementList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        layout.prop(item, "name", text="", emboss=False)
  
class XML_UL_AttributeList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        layout.prop(item, "key", text="", emboss=False)
        layout.prop(item, "value", text="")


#register
classes = [
    XMLAttribute,
    XMLItem,
    LoadXMLSceneOperator,
    XML_OT_AddElement,
    XML_OT_RemoveElement,
    XML_OT_AddAttribute,
    RemoveXMLAttributeOperator,
    XML_OT_ClearElements,
    MoveXMLAttributeOperator,
    MoveXMLElementOperator,
    XMLSceneSaveOperator,
    XMLScenePanel,
    XMLNodePanel,
    XMLEdgePanel,
    XMLFigurePanel,
    XML_UL_ElementList,
    XML_UL_AttributeList,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.xml_nodes = CollectionProperty(type=XMLItem)
    bpy.types.Scene.xml_edges = CollectionProperty(type=XMLItem)
    bpy.types.Scene.xml_figures = CollectionProperty(type=XMLItem)
    bpy.types.Scene.xml_nodes_index = bpy.props.IntProperty()
    bpy.types.Scene.xml_edges_index = bpy.props.IntProperty()
    bpy.types.Scene.xml_figures_index = bpy.props.IntProperty()
    bpy.types.Scene.xml_file_path = StringProperty(
        name="XML File Path",
        subtype='FILE_PATH'
    )

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.xml_nodes
    del bpy.types.Scene.xml_edges
    del bpy.types.Scene.xml_figures
    del bpy.types.Scene.xml_nodes_index
    del bpy.types.Scene.xml_edges_index
    del bpy.types.Scene.xml_figures_index
    del bpy.types.Scene.xml_file_path

if __name__ == "__main__":
    register()