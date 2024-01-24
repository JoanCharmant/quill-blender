
bl_info = {
    'name': 'Quill',
    'author': 'Joan Charmant',
    'version': (0, 0, 2),
    'blender': (2, 80, 0),
    'location': 'File > Import-Export',
    'description': 'Import-Export Quill scenes',
    'warning': '',
    'tracker_url': "https://github.com/JoanCharmant/quill-blender/issues/",
    'category': 'Import-Export',
}

# To support reload properly, try to access a package var, if it's there, reload everything
if "bpy" in locals():
    import importlib
    if "export_quill" in locals():
        importlib.reload(export_quill)
    if "import_quill" in locals():
        importlib.reload(import_quill)


import bpy
from bpy.props import StringProperty, BoolProperty, FloatProperty, EnumProperty
from bpy_extras.io_utils import ExportHelper, ImportHelper, orientation_helper, axis_conversion


class ImportQuill(bpy.types.Operator, ImportHelper):
    """Load a Quill scene"""
    bl_idname = "import_quill.json"
    bl_label = "Import Quill"
    bl_options = {'UNDO', 'PRESET'}

    filename_ext = ".json"
    filter_glob: StringProperty(default="*.json", options={"HIDDEN"})

    load_hidden_layers: BoolProperty(
            name="Load hidden layers",
            description="Load hidden layers from the Quill scene.",
            default=True,
            )

    load_viewpoints: BoolProperty(
            name="Load viewpoints",
            description="Load viewpoints as cameras.",
            default=False,
            )

    def execute(self, context):

        from . import import_quill

        keywords = self.as_keywords(ignore=("filter_glob", "filepath"))

        return import_quill.load(self, context, filepath=self.filepath, **keywords)

class ExportQuill(bpy.types.Operator, ExportHelper):
    """Save a Quill scene"""
    bl_idname = "export_scene.quill"
    bl_label = "Export Quill scene"
    bl_options = {'PRESET'}

    filename_ext = ".zip"
    filter_glob: StringProperty(default="*.zip", options={"HIDDEN"})

    # List of operator properties.

    use_selection: BoolProperty(
        name="Selected Objects",
        description="Export selected and visible objects only",
        default=False,
    )

    use_visible: BoolProperty(
        name="Visible Objects",
        description="Export visible objects only",
        default=False,
    )

    object_types: EnumProperty(
        name="Object Types",
        options={'ENUM_FLAG'},
        items=(('EMPTY', "Empty", ""),
                ('CAMERA', "Camera", ""),
                ('GPENCIL', "Grease Pencil", ""),
                ('MESH', "Mesh", ""),
                ('ARMATURE', "Armature", ""),
                ),
        description="Which kind of object to export",
        default={'EMPTY', 'CAMERA', 'GPENCIL', 'MESH', 'ARMATURE'},
    )

    bake_space_transform: BoolProperty(
        name="Apply Transform",
        description="Bake object transforms into paint strokes",
        default=False,
    )

    use_mesh_modifiers: BoolProperty(
        name="Apply Modifiers",
        description="Apply modifiers to mesh objects.",
        default=True,
    )

    def draw(self, context):
        pass

    def execute(self, context):
        from . import export_quill

        if not self.filepath:
            raise Exception("filepath not set")

        keywords = self.as_keywords(ignore=(
            "axis_forward",
            "axis_up",
            "global_scale",
            "check_existing",
            "filter_glob",
            "xna_validate",
        ))

        return export_quill.save(self, **keywords)


class QUILL_PT_export_include(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Include"
    bl_parent_id = "FILE_PT_operator"

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator

        return operator.bl_idname == "EXPORT_SCENE_OT_quill"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        sfile = context.space_data
        operator = sfile.active_operator

        sublayout = layout.column(heading="Limit to")
        sublayout.prop(operator, "use_selection")
        sublayout.prop(operator, "use_visible")
        layout.column().prop(operator, "object_types")


class QUILL_PT_export_transform(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Transform"
    bl_parent_id = "FILE_PT_operator"

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator

        return operator.bl_idname == "EXPORT_SCENE_OT_quill"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        sfile = context.space_data
        operator = sfile.active_operator

        layout.prop(operator, "bake_space_transform")


def menu_func_import(self, context):
    self.layout.operator(ImportQuill.bl_idname, text="Quill scene")


def menu_func_export(self, context):
    self.layout.operator(ExportQuill.bl_idname, text="Quill scene")

classes = (
    ImportQuill,
    ExportQuill,
    QUILL_PT_export_include,
    QUILL_PT_export_transform,
)

def register():

    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
