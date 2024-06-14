
import bpy
import random
from ..model import sequence, paint
from . import utils

def convert(obj, config):
    """Convert an armature to a series of paint strokes"""

    # Create a default paint layer and drawing.
    paint_layer = sequence.Layer.create_paint_layer(obj.name)
    drawing = sequence.Drawing.from_default()
    drawing.data = paint.DrawingData()
    paint_layer.implementation.drawings.append(drawing)

    # Produce a paint stroke for each bone.
    # https://docs.blender.org/api/current/bpy.types.Armature.html
    # https://docs.blender.org/api/current/bpy.types.Bone.html
    armature = obj.data

    # For the flattened armature case we don’t care about the hierarchy, naming, etc.
    # Just create one stroke per bone.
    for bone in armature.bones:
        deforming = bone.use_deform
        if not deforming:
            continue

        # bone.head_local is relative to the armature (bone.head is relative to the parent bone).
        head = utils.swizzle_yup_location(bone.head_local)
        tail = utils.swizzle_yup_location(bone.tail_local)

        # FIXME: How do we go from bone.color.palette (ex: "THEME01") to the actual color?
        #bone_color = bone.color.palette
        #bone_color_sets = bpy.context.preferences.themes["Default"].bone_color_sets
        bone_color = list([random.random() for i in range(3)])

        stroke = make_bone_stroke(head, tail, bone_color, config)
        if stroke is None:
            continue

        drawing.data.strokes.append(stroke)
        drawing.bounding_box = utils.bbox_add(drawing.bounding_box, stroke.bounding_box)

    return paint_layer


def make_bone_stroke(head, tail, color, config):

    brush_type = paint.BrushType.CYLINDER
    disable_rotational_opacity = True
    length = (tail - head).length
    vertices = []

    def add_vertex(p, width):
        # Fake normal and tangent as if the painter was at the origin.
        # `normal` controls the orientation of ribbon strokes.
        # `tangent` controls the incident ray for rotational opacity.
        normal = p.normalized()
        tangent = normal
        opacity = 1.0
        vertex = paint.Vertex(p, normal, tangent, color, opacity, width)
        vertices.append(vertex)

    # Make a stroke that resembles the Blender octahedral bone.
    # We need a minimum of 4 points to make a quill stroke. 
    # p1 is the main driver of the shape and p2 is just a support point.
    add_vertex(head, 0)
    p1 = head.lerp(tail, 0.1)
    p1_width = length / 4
    add_vertex(p1, p1_width)
    p2 = head.lerp(tail, 0.9)
    p2_width = ((length * 0.1) * p1_width) / length
    add_vertex(p2, p2_width)
    add_vertex(tail, 0)

    bounding_box = utils.bbox_from_points(head, tail)

    id = 0
    stroke = paint.Stroke(id, bounding_box, brush_type, disable_rotational_opacity, vertices)
    return stroke
