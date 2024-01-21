
bl_info = {
    'name': 'Quill',
    'author': 'Joan Charmant',
    'version': (0, 0, 1),
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
from bpy_extras.io_utils import ExportHelper
from bpy_extras.io_utils import ImportHelper


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
    bl_idname = "export_quill.zip"
    bl_label = "Export to Quill"

    filename_ext = ".zip"
    filter_glob: StringProperty(default="*.zip", options={"HIDDEN"})

    # List of operator properties
    object_types: EnumProperty(
        name="Object Types",
        options={"ENUM_FLAG"},
        items=(
            ("EMPTY", "Empty", ""),
            ("MESH", "Mesh", ""),
            ("GPENCIL", "Grease Pencil", ""),
            ("ARMATURE", "Armature", ""),
        ),
        default={
            "EMPTY",
            "MESH",
            "GPENCIL",
            "ARMATURE"
        },
    )

    use_visible_objects: BoolProperty(
        name="Only Visible Objects",
        description="Export only objects that are visible.",
        default=True,
    )

    use_export_selected: BoolProperty(
        name="Only Selected Objects",
        description="Export only selected objects.",
        default=False,
    )

    use_mesh_modifiers: BoolProperty(
        name="Apply Modifiers",
        description="Apply modifiers to mesh objects.",
        default=True,
    )

    def execute(self, context):
        from . import export_quill

        keywords = self.as_keywords(ignore=(
            "axis_forward",
            "axis_up",
            "global_scale",
            "check_existing",
            "filter_glob",
            "xna_validate",
        ))

        return export_quill.save(self, **keywords)


def menu_func_import(self, context):
    self.layout.operator(ImportQuill.bl_idname, text="Quill scene")


def menu_func_export(self, context):
    self.layout.operator(ExportQuill.bl_idname, text="Quill scene")

classes = (
    ExportQuill,
    ImportQuill,
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
