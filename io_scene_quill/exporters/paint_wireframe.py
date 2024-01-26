
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
    # https://docs.blender.org/api/current/bpy.types.Mesh.html
    mesh = obj.data
    for (v1, v2) in mesh.edge_keys:
        p1 = utils.swizzle_yup_location(mesh.vertices[v1].co)
        p2 = utils.swizzle_yup_location(mesh.vertices[v2].co)
        stroke = make_edge_stroke(p1, p2, config)
        if stroke is None:
            continue
        drawing.data.strokes.append(stroke)
        drawing.bounding_box = utils.bbox_add(drawing.bounding_box, stroke.bounding_box)

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

        p = points[i]

        # Fake normal and tangent as if the painter was at the origin.
        # `normal` controls the orientation of ribbon strokes.
        # `tangent` controls the incident ray for rotational opacity.
        normal = p.normalized()
        tangent = normal
        color = (0, 0, 0)
        opacity = 1.0
        width = min_size if (i == 0 or i == segments) else brush_size
        vertex = paint.Vertex(p, normal, tangent, color, opacity, width)
        vertices.append(vertex)

    bounding_box = utils.bbox_from_points(start, end)

    id = 0
    stroke = paint.Stroke(id, bounding_box, brush_type, disable_rotational_opacity, vertices)
    return stroke




