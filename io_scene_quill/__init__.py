import bpy
from bpy.props import StringProperty, BoolProperty, FloatProperty, EnumProperty
from bpy_extras.io_utils import ExportHelper
from . import export_quill


bl_info = {
    'name': 'Quill',
    'author': 'Joan Charmant',
    'version': (0, 0, 1),
    'blender': (2, 80, 0),
    'location': 'File > Import-Export',
    'description': 'Import-Export Quill scenes',
    'warning': '',
    'category': 'Import-Export',
}


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
            ("ARMATURE", "Armature", ""),
        ),
        default={
            "EMPTY",
            "MESH",
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
        """Begin the export"""

        keywords = self.as_keywords(ignore=(
            "axis_forward",
            "axis_up",
            "global_scale",
            "check_existing",
            "filter_glob",
            "xna_validate",
        ))

        return export_quill.save(self, **keywords)


def menu_func(self, context):
    """Add to the menu"""
    self.layout.operator(ExportQuill.bl_idname, text="Quill scene")


def register():
    """Add addon to blender"""
    bpy.utils.register_class(ExportQuill)
    bpy.types.TOPBAR_MT_file_export.append(menu_func)


def unregister():
    """Remove addon from blender"""
    bpy.utils.unregister_class(ExportQuill)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func)


if __name__ == "__main__":
    register()
