
import bpy
import logging
import random
from ..model import sequence, paint
from . import utils

def convert(obj, config):
    """Convert from Grease pencil to Quill paint strokes."""

    gpencil_data = obj.data

    count_layers = len(gpencil_data.layers)
    if count_layers == 0:
        return None

    # We only support depth order = "3D" and thickness space = "WORLDSPACE"
    # as that’s what Quill will be using.
    if gpencil_data.stroke_depth_order != '3D' or gpencil_data.stroke_thickness_space != 'WORLDSPACE':
        logging.warning("Unsupported stroke depth order or thickness space will be ignored.")

    gpencil_layers = gpencil_data.layers
    gpencil_materials = gpencil_data.materials

    # If the grease pencil object has several layers create a group with multiple
    # paint layers inside, otherwise create a single paint layer.
    if count_layers == 1:
        return make_paint_layer(gpencil_layers[0], gpencil_materials, config)
    else:
        group_layer = sequence.Layer.create_group_layer(obj.name)
        for gpencil_layer in gpencil_layers:
            paint_layer = make_paint_layer(gpencil_layer, gpencil_materials, config)
            if paint_layer is None:
                continue
            group_layer.implementation.children.append(paint_layer)

        return group_layer


def make_paint_layer(gpencil_layer, gpencil_materials, config):

    if gpencil_layer.frames == 0 or gpencil_layer.is_ruler:
        return None

    # Convert Grease pencil to Quill.
    # The data models are not an exact match.
    #
    # 1. In Grease pencil but not in Quill:
    # - fills
    # - textured brushes, more complex color model.
    # - masking.
    # - display mode (screen, 3D space, 2D space)
    # - stroke thickness model (world space v screen space), depth order.
    #
    # 2. In Quill but not in Grease pencil:
    # - brush type defines the shape of the stroke cross section (round, square, flat).
    # - strokes on a given layer can have a different brush type.
    # - orientation-dependent opacity.
    #
    # References
    # https://docs.blender.org/api/current/bpy.types.GreasePencil.html
    # https://docs.blender.org/api/current/bpy.types.GPencilLayer.html
    # https://docs.blender.org/api/current/bpy.types.GPencilStroke.html
    # https://docs.blender.org/api/current/bpy.types.MaterialGPencilStyle.html

    # Create a default paint layer and drawing.
    paint_layer = sequence.Layer.create_paint_layer(gpencil_layer.info)

    # Blend (gpencil_layer.blend_mode): Ignore. We only support "Regular".
    # Opacity: supported.
    paint_layer.opacity = gpencil_layer.opacity

    # Ajustments > Stroke thickness
    # Thickness change to apply to current strokes.
    thickness_offset = gpencil_layer.line_change

    # Set all layers to the Blender frame rate.
    paint_layer.implementation.frame_rate = bpy.context.scene.render.fps
    paint_layer.implementation.max_repeat_count = 1

    # (?)
    #gpencil_layer.tint_color
    #gpencil_layer.tint_factor
    #gpencil_layer.vertex_paint_opacity

    # Frame by frame animation:
    # Grease pencil "frames" corresponds to Quill drawings aka key frames.
    # Blender timeline frames corresponds to Quill frames.

    # Drawing list
    for gpencil_frame in gpencil_layer.frames:
        drawing = sequence.Drawing.from_default()
        drawing.data = paint.DrawingData()
        paint_layer.implementation.drawings.append(drawing)

        # Convert all Grease Pencil strokes to Quill ones.
        for gpencil_stroke in gpencil_frame.strokes:

            # Surface component (Stroke, Fill or both).
            # If neither are enabled or the drawing has no strokes, it is still
            # a valid drawing, just empty.
            material = gpencil_materials[gpencil_stroke.material_index].grease_pencil

            if material.show_stroke:
                # This can be represented by a normal Quill stroke.
                stroke = make_normal_stroke(gpencil_stroke, material, thickness_offset)
                if stroke is None:
                    continue
                drawing.data.strokes.append(stroke)
                drawing.bounding_box = utils.bbox_add(drawing.bounding_box, stroke.bounding_box)

            if material.show_fill:
                # This requires special handling.
                stroke = make_fill_stroke(gpencil_stroke, material)
                if stroke is None:
                    continue
                drawing.data.strokes.append(stroke)
                drawing.bounding_box = utils.bbox_add(drawing.bounding_box, stroke.bounding_box)

    # Frame list.
    # Quill stores a fully expanded frame list.
    # e.g: [0, 1, 1, 1, 2, 2, 3, 3, 3]
    # Blender stores a map of key frames to frame numbers.
    # e.g: {0:0, 1:1, 2:4, 3:6]
    # Unlike Quill, Blender keeps the list ordered.
    scn = bpy.context.scene
    frame_start = scn.frame_start
    frame_end = scn.frame_end

    # Loop through the blender frames and assign the correct drawing.
    # We know the frame rates are matching at this point.
    paint_layer.implementation.frames = []
    current_gp_drawing = 0
    for blender_frame in range(frame_start, frame_end + 1):

        # Check if we should switch to the next drawing.
        if current_gp_drawing < len(gpencil_layer.frames) - 1:
            next_gp_frame_number = gpencil_layer.frames[current_gp_drawing + 1].frame_number
            if blender_frame >= next_gp_frame_number:
                current_gp_drawing += 1

        paint_layer.implementation.frames.append(current_gp_drawing)

    return paint_layer

def make_normal_stroke(gpencil_stroke, material, thickness_offset):

    # TODO:
    # Check if we made a backup of the Quill brush type in the material property
    # for round tripping Quill -> Blender -> Quill.
    brush_type = paint.BrushType.CYLINDER
    disable_rotational_opacity = True

    line_width = (gpencil_stroke.line_width + thickness_offset) / 1000
    #gpencil_stroke.start_cap_mode
    #gpencil_stroke.end_cap_mode

    # Line type (material.mode): we only support "Line", not "Dots" or "Box"
    # Line style (material.stroke_style): we only support "Solid", not "Texture".

    # Line color (material.color).
    # Color model: in Grease pencil the final color of the point is a mix between
    # the vertex color and the material color, in Quill there is only one color.
    # We compute the rendered color and bake it in the Quill stroke point.
    base_color = material.color

    bbox = utils.bbox_empty()
    vertices = []
    for gpencil_point in gpencil_stroke.points:

        p = utils.swizzle_yup_location(gpencil_point.co)

        # Fake normal and tangent as if the painter was at the origin.
        normal = p.normalized()
        tangent = normal

        # Mix between the vertex color and the base color.
        alpha = gpencil_point.vertex_color[3]
        beta = 1.0 - alpha
        color = (
            gpencil_point.vertex_color[0] * alpha + base_color[0] * beta,
            gpencil_point.vertex_color[1] * alpha + base_color[1] * beta,
            gpencil_point.vertex_color[2] * alpha + base_color[2] * beta)
        opacity = gpencil_point.strength
        width = line_width * gpencil_point.pressure
        vertex = paint.Vertex(p, normal, tangent, color, opacity, width)
        vertices.append(vertex)
        bbox = utils.bbox_add_point(bbox, p)

    id = 0
    return paint.Stroke(id, bbox, brush_type, disable_rotational_opacity, vertices)


def make_fill_stroke(gpencil_stroke, material):

    # TODO: make some sort of Quill stroke that emulates the fill.
    # Store some metadata somewhere (in the layer title?) to be able to round trip.
    brush_type = paint.BrushType.RIBBON
    disable_rotational_opacity = True

    triangles = gpencil_stroke.triangles
    #is_nofill_stroke = gpencil_stroke.is_nofill_stroke
    #vertex_color_fill = gpencil_stroke.vertex_color_fill

    return None
