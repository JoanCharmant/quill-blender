
bl_info = {
    'name': 'Quill',
    'author': 'Joan Charmant',
    'version': (1, 2, 0),
    'blender': (3, 6, 0),
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
from bpy.props import StringProperty, BoolProperty, FloatProperty, IntProperty, EnumProperty
from bpy_extras.io_utils import ExportHelper, ImportHelper, orientation_helper, axis_conversion

gp = 'GPENCIL' if bpy.app.version < (4, 3, 0) else 'GREASEPENCIL'

class ImportQuill(bpy.types.Operator, ImportHelper):
    """Load a Quill scene"""
    bl_idname = "import_scene.quill"
    bl_label = "Import Quill"
    bl_options = {'UNDO', 'PRESET'}

    filename_ext = ".json"
    filter_glob: StringProperty(default="*.json", options={"HIDDEN"})

    load_hidden_layers: BoolProperty(
            name="Hidden Layers",
            description="Load hidden layers from the Quill scene",
            default=False,
            )

    load_cameras: BoolProperty(
            name="Cameras",
            description="Load Quill cameras and viewpoints as Blender cameras",
            default=True,
            )

    convert_paint: EnumProperty(
        name="Convert to",
        items=(("MESH", "Mesh", ""),
            (gp, "Grease Pencil", ""),
            ("CURVE", "Curve", "")),
        description="How paint layers are converted during import",
        default="MESH")

    extra_attributes: BoolProperty(
            name="Extra attributes",
            description="Create attributes for Quill stroke data",
            default=False,
            )

    def draw(self, context):
        pass

    def execute(self, context):

        from . import import_quill

        keywords = self.as_keywords(ignore=("filter_glob", "filepath"))

        return import_quill.load(self, context, filepath=self.filepath, **keywords)


class QUILL_PT_import_include(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Include"
    bl_parent_id = "FILE_PT_operator"

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator
        return operator.bl_idname == "IMPORT_SCENE_OT_quill"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        sfile = context.space_data
        operator = sfile.active_operator

        layout.prop(operator, "load_hidden_layers")
        layout.prop(operator, "load_cameras")


class QUILL_PT_import_paint(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Paint Layers"
    bl_parent_id = "FILE_PT_operator"

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator
        return operator.bl_idname == "IMPORT_SCENE_OT_quill"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        sfile = context.space_data
        operator = sfile.active_operator

        layout.prop(operator, "convert_paint")
        
        # Hide the extra attributes option for now.
        # It will only make sense when we can actually round trip the data.
        #layout.prop(operator, "extra_attributes")


class ExportQuill(bpy.types.Operator, ExportHelper):
    """Save a Quill scene"""
    bl_idname = "export_scene.quill"
    bl_label = "Export Quill scene"
    bl_options = {'PRESET'}

    filename_ext = ".zip"
    filter_glob: StringProperty(default="*.zip", options={"HIDDEN"})

    # List of operator properties.
    object_types: EnumProperty(
        name="Object Types",
        options={'ENUM_FLAG'},
        items=((gp, "Grease Pencil", ""),
               ('CAMERA', "Camera", ""),
               ('MESH', "Mesh", ""),
               ('ARMATURE', "Armature", ""),
               ('IMAGE', "Image", ""),
        ),
        description="Which kind of object to export",
        default={gp, 'CAMERA', 'MESH', 'ARMATURE', 'IMAGE'},
    )

    use_selection: BoolProperty(
        name="Selected Objects",
        description="Export selected and visible objects only",
        default=False,
    )

    use_visible: BoolProperty(
        name="Visible Objects",
        description="Export visible objects only",
        default=True,
    )

    use_non_empty: BoolProperty(
        name="Non-empty",
        description="Do not create groups without children",
        default=True,
    )
    
    greasepencil_brush_type: EnumProperty(
        name="Brush type",
        items=(("CYLINDER", "Cylinder", ""),
               ("RIBBON", "Ribbon", "")),
        description="Brush type of exported strokes. When using 'Ribbon' the flat side will be facing up.",
        default="CYLINDER",
    )
    
    match_round_caps: BoolProperty(
        name="Match round caps",
        description="Add extra vertices to the end of strokes to match Blender caps. This is only used if the strokes are created with Round caps in the first place.",
        default=True,
    )

    wireframe_stroke_width: FloatProperty(
        name="Width",
        description="Size of paint strokes",
        min=0.0001, max=1000.0,
        soft_min=0.001, soft_max=100.0,
        default=0.01,
    )

    wireframe_segments_per_unit: IntProperty(
        name="Resolution",
        description="Number of segments per unit",
        min=1, max=1000,
        soft_min=1, soft_max=100,
        default=10,
    )

    armature_bone_shape: EnumProperty(
        name="Bone shape",
        items=(("OCTAHEDRAL", "Octahedral", ""),
                ("STICK", "Stick", "")),
        description="Shape of paint strokes used to represent bones",
        default="STICK",
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

        layout.column().prop(operator, "object_types")
        sublayout = layout.column(heading="Limit to")
        sublayout.prop(operator, "use_selection")
        sublayout.prop(operator, "use_visible")
        sublayout.prop(operator, "use_non_empty")


class QUILL_PT_export_greasepencil(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Grease Pencil"
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

        layout.prop(operator, "greasepencil_brush_type")
        layout.prop(operator, "match_round_caps")


class QUILL_PT_export_wireframe(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Mesh Wireframe"
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

        layout.prop(operator, "wireframe_stroke_width")
        layout.prop(operator, "wireframe_segments_per_unit")


class QUILL_PT_export_armature(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Armature"
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

        layout.prop(operator, "armature_bone_shape")


def menu_func_import(self, context):
    self.layout.operator(ImportQuill.bl_idname, text="Quill scene")


def menu_func_export(self, context):
    self.layout.operator(ExportQuill.bl_idname, text="Quill scene")

classes = (
    ImportQuill,
    QUILL_PT_import_include,
    QUILL_PT_import_paint,
    ExportQuill,
    QUILL_PT_export_include,
    QUILL_PT_export_greasepencil,
    QUILL_PT_export_wireframe,
    QUILL_PT_export_armature,
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
