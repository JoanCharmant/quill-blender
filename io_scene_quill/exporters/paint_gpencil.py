
import bpy
import random
from ..model import sequence, paint
from . import utils

def convert(obj, config):
    """Convert from Grease pencil to Quill paint strokes."""

    gpencil_data = obj.data
    gpencil_layers = gpencil_data.layers

    # If the grease pencil object has several layers create a group with multiple
    # paint layers inside, otherwise create a single paint layer.
    if len(gpencil_layers) > 1:
        group_layer = sequence.Layer.create_group_layer(obj.name)

        for gpencil_layer in gpencil_layers:
            paint_layer = make_paint_layer(gpencil_layer, config)
            group_layer.implementation.children.append(paint_layer)

        return group_layer

    else:
        gpencil_layer = gpencil_layers[0]
        paint_layer = make_paint_layer(gpencil_layer, config)

        return paint_layer


def make_paint_layer(gpencil_layer, config):

    # Create a default paint layer and drawing.
    paint_layer = sequence.Layer.create_paint_layer(gpencil_layer.info)
    drawing = sequence.Drawing.from_default()
    drawing.data = paint.DrawingData()
    paint_layer.implementation.drawings.append(drawing)

    # Common paint stroke parameters.
    brush_type = paint.BrushType.CYLINDER
    disable_rotational_opacity = True

    # Convert grease pencil.
    # The data model between grease pencil and Quill is not an exact match.
    # There are two main aspects of grease pencil we cannot export: fills and textured brushes.
    # Furthermore stroke_thickness_space should be set to "WORLDSPACE" and depth_order to "3D"
    # to match Quill spatial model.
    # Colors should use vertex colors not material.

    #for gpencil_frame in gpencil_layer.frames:
    # Only support the first frame for now.
    gpencil_frame = gpencil_layer.frames[0]

    for gpencil_stroke in gpencil_frame.strokes:

        line_width = gpencil_stroke.line_width / 1000
        #start_cap_mode = gpencil_stroke.start_cap_mode
        #end_cap_mode = gpencil_stroke.end_cap_mode

        bbox = utils.bbox_empty()
        vertices = []
        for gpencil_point in gpencil_stroke.points:

            p = utils.swizzle_yup_location(gpencil_point.co)

            # Fake normal and tangent as if the painter was at the origin.
            # `normal` controls the orientation of ribbon strokes.
            # `tangent` controls the incident ray for rotational opacity.
            normal = p.normalized()
            tangent = normal
            color = (gpencil_point.vertex_color[0],
                     gpencil_point.vertex_color[1],
                     gpencil_point.vertex_color[2])
            opacity = gpencil_point.strength
            width = line_width * gpencil_point.pressure
            vertex = paint.Vertex(p, normal, tangent, color, opacity, width)
            vertices.append(vertex)
            bbox = utils.bbox_add_point(bbox, p)

        id = 0
        stroke = paint.Stroke(id, bbox, brush_type, disable_rotational_opacity, vertices)
        drawing.data.strokes.append(stroke)
        drawing.bounding_box = utils.bbox_add(drawing.bounding_box, stroke.bounding_box)

    return paint_layer
