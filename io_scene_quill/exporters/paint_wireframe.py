
import bpy
import math
import mathutils
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
    stroke_id = 0
    for (v1, v2) in mesh.edge_keys:
        p1 = utils.swizzle_yup_location(mesh.vertices[v1].co)
        p2 = utils.swizzle_yup_location(mesh.vertices[v2].co)
        stroke = make_edge_stroke(p1, p2, stroke_id, config)
        if stroke is None:
            continue
        drawing.data.strokes.append(stroke)
        drawing.bounding_box = utils.bbox_add(drawing.bounding_box, stroke.bounding_box)
        stroke_id += 1

    return paint_layer

def make_edge_stroke(start, end, id, config):

    brush_type = paint.BrushType.CYLINDER
    disable_rotational_opacity = True

    dist = (end - start).length
    min_size = 0.001
    max_size = dist / 4
    if dist < 0.004:
        return None

    brush_size = max(min(config["wireframe_stroke_width"], max_size), min_size)
    segments = math.ceil(dist * config["wireframe_segments_per_unit"])
    segments = max(segments, 3)

    points = []
    for i in range(segments):
        points.append(start.lerp(end, i / segments))
    points.append(end)

    # Location of the blender camera, used to get a normal.
    camera_position = mathutils.Vector((0, 0, 0))
    camera = bpy.context.scene.camera
    if camera is not None:
        camera_position = bpy.context.scene.camera.matrix_world.to_translation()
        camera_position = utils.swizzle_yup_location(camera_position)

    # The stroke is straight so all points have the same tangent.
    tangent = (end - start).normalized()

    vertices = []
    for i in range(len(points)):

        p = points[i]

        # Set the normal to be in the direction of the camera.
        normal = (camera_position - p).normalized()
        color = (0, 0, 0)
        opacity = 1.0
        width = min_size if (i == 0 or i == segments) else brush_size
        vertex = paint.Vertex(p, normal, tangent, color, opacity, width)
        vertices.append(vertex)

    bounding_box = utils.bbox_from_points(start, end)

    stroke = paint.Stroke(id, bounding_box, brush_type, disable_rotational_opacity, vertices)
    return stroke




