import bpy


class OBJECT_PG_quill(bpy.types.PropertyGroup):

    # True if the object was created from a Quill layer.
    active: bpy.props.BoolProperty(
        name = "Quill Object",
        options = set(),
        default = False,
    )

    # File system path to the Quill scene project folder this layer comes from.
    scene_path: bpy.props.StringProperty(
        name = "Path to Quill Scene",
        subtype = 'FILE_PATH',
        options = {'PATH_SUPPORTS_BLEND_RELATIVE'},
    )

    # Internal path to the layer this object was imported from.
    layer_path: bpy.props.StringProperty(
        name = "Path to Layer",
    )

    # True for objects created from Quill paint layers.
    paint_layer: bpy.props.BoolProperty(
        name = "Paint Layer",
        options = set(),
        default = False,
    )

    # Set on mesh objects created from individual drawings.
    drawing_index: bpy.props.IntProperty(
        name = "Drawing Index",
        options = set(),
        default = 0,
    )


def register():
    bpy.utils.register_class(OBJECT_PG_quill)
    bpy.types.Object.quill = bpy.props.PointerProperty(type=OBJECT_PG_quill, name="Quill")

def unregister():
    bpy.utils.unregister_class(OBJECT_PG_quill)
    del bpy.types.Object.quill