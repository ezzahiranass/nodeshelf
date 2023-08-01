import random
import bpy
import os

import addon_utils




class NODESHELF_AddonPrefs(bpy.types.AddonPreferences):
    # this must match the add-on name, use '__package__'
    # when defining this in a submodule of a python package.
    bl_idname = __package__

    for mod in addon_utils.modules():
        if mod.bl_info['name'] == "NodeShelf":
            filepath = mod.__file__
    folder = filepath.replace("__init__.py", "")
    blendpath = bpy.app.binary_path

    data_folder: bpy.props.StringProperty(
        name="Data Folder",
        description="Choose a folder where NodeShelf can store all of its data",
        subtype="DIR_PATH",
        default=folder,
    )
    blender_path: bpy.props.StringProperty(
        name="Blender Path",
        description="Locate your Blender Executable",
        subtype="FILE_PATH",
        default=blendpath,
    )
    confirmation: bpy.props.BoolProperty(
        name="Removal Confirmation",
        description="Popup Confirmation Dialog when removing a Node Pack",
        default=True,
    )
    tips: bpy.props.BoolProperty(
        name="Enable UI Tips",
        description="Enable UI Tips",
        default=True,
    )
    ###NOTES
    border_color: bpy.props.FloatVectorProperty(
        name="Note Border Color",
        description="Note Border Color",
        subtype="COLOR",
        default=(1.0, 1.0, 1.0),
        size=3,
        min=0.0, max=1.0,
    )
    font_size: bpy.props.FloatProperty(
        name="Note Font Size",
        description="Note Font Size",
        default=15,
        min=7, max=50,
    )
    alignment: bpy.props.EnumProperty(
        name="Alignment",
        description="Align Notes to Linked Nodes",
        items=[
            ("CENTER", "CENTER", "CENTER"),
            ("LEFT", "LEFT", "LEFT"),
            ("RIGHT", "RIGHT", "RIGHT"),
        ]
    )

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.label(text="Welcome to the NodeShelf Add-on!")

        box = layout.box()
        row = box.row()
        row.prop(self, "blender_path")
        row = box.row()
        row.prop(self, "data_folder")

        box = layout.box()
        row = box.row()
        row.label(text="UI Settings")
        row = box.row()
        row.prop(self, "confirmation")
        row.prop(self, "tips")

        box = layout.box()
        row = box.row()
        row.label(text="Notes Settings")
        row = box.row()
        row.operator("nodeshelf.open_json", icon="FILE")
        row = box.row()
        row.prop(self, "border_color")
        row = box.row()
        row.prop(self, "font_size")
        row = box.row()
        row.prop(self, "alignment")


def register():
    bpy.utils.register_class(NODESHELF_AddonPrefs)

def unregister():
    bpy.utils.unregister_class(NODESHELF_AddonPrefs)

