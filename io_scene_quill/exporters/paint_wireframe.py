

import bpy
import math
from ..model import sequence, paint
from . import utils

def convert(obj, config):
    """Convert a mesh wireframe into a series of paint strokes"""

    # Create a default paint layer and drawing.
    paint_layer = sequence.Layer.create_paint_layer(obj.name)
    drawing = sequence.Drawing.from_default()
    drawing.data = paint.DrawingData()
    paint_layer.implementation.drawings.append(drawing)

    # Produce a paint stroke for each edge.
    mesh = obj.data
    for (v1, v2) in mesh.edge_keys:
        p1 = utils.swizzle_yup_location(mesh.vertices[v1].co)
        p2 = utils.swizzle_yup_location(mesh.vertices[v2].co)
        stroke = make_edge_stroke(p1, p2, config)
        if stroke is None:
            continue
        drawing.data.strokes.append(stroke)
        drawing.bounding_box = update_bounding_box(drawing.bounding_box, stroke.bounding_box)

    return paint_layer

def make_edge_stroke(start, end, config):

    brush_type = paint.BrushType.CYLINDER
    disable_rotational_opacity = True

    dist = (end - start).length
    min_size = 0.001
    max_size = dist / 4
    if dist < 0.004:
        return None

    brush_size = max(min(config["wireframe_stroke_width"], max_size), min_size)
    segments = math.ceil(dist * config["segments_per_unit"])
    segments = max(segments, 3)

    points = []
    for i in range(segments):
        points.append(start.lerp(end, i / segments))
    points.append(end)

    vertices = []
    for i in range(len(points)):

        # `normal` controls the orientation of ribbon strokes.
        # `tangent` controls the incident ray for rotational opacity.
        # Make up values assuming the virtual painter is at the world origin.
        normal = points[i].normalized()
        tangent = normal

        color = (0, 0, 0)
        opacity = 1.0
        width = min_size if (i == 0 or i == segments) else brush_size
        vertex = paint.Vertex(points[i], normal, tangent, color, opacity, width)
        vertices.append(vertex)

    bounding_box = make_bounding_box(start, end)

    id = 0
    stroke = paint.Stroke(id, bounding_box, brush_type, disable_rotational_opacity, vertices)
    return stroke


def make_bounding_box(p1, p2):
    """Make a bounding box from two points."""
    return [
        min(p1[0], p2[0]),
        min(p1[1], p2[1]),
        min(p1[2], p2[2]),
        max(p1[0], p2[0]),
        max(p1[1], p2[1]),
        max(p1[2], p2[2]),
    ]


def update_bounding_box(a, b):
    """Augment bounding box a with bounding box b and return a."""
    a[0] = min(a[0], b[0])
    a[1] = min(a[1], b[1])
    a[2] = min(a[2], b[2])
    a[3] = max(a[3], b[3])
    a[4] = max(a[4], b[4])
    a[5] = max(a[5], b[5])
    return a



