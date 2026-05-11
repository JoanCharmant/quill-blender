
import bpy
import mathutils
import random

from ..model import paint, quill_utils, sequence
from . import utils

def convert(obj, config):
    """Converts a Blender armature object to a hierarchy of groups and layers.
    Create a sub-group for each bone, and add a paint layer with a stroke representing the bone."""

    armature_group_layer = quill_utils.create_group_layer(obj.name)
    
    # We work everything out in Blender's coordinate system and then apply a single transform at the end
    # to convert to Quill's coordinate system. This is easier to debug.
    # The extra transform is done upstream in export_quill.py.
    bone_groups = {}
    for pose_bone in obj.pose.bones:
        
        # Create a group for this bone.
        bone_group_layer = quill_utils.create_group_layer(pose_bone.name)
        bone_group_layer.animation.timeline = False
        bone_groups[pose_bone.name] = bone_group_layer
        
        # Add a paint layer for the bone stick.
        bone_paint_layer = quill_utils .create_paint_layer(pose_bone.name)
        drawing = quill_utils.create_drawing()
        bone_paint_layer.implementation.drawings.append(drawing)
        bone_group_layer.implementation.children.append(bone_paint_layer)
       
        # Parenting.
        # Normally the hierarchy is traversed depth first so the parent should already be created.
        if (pose_bone.parent is None):
            armature_group_layer.implementation.children.append(bone_group_layer)
        else:
            if pose_bone.parent.name not in bone_groups:
                print(f"Error: bone {pose_bone.name} has parent {pose_bone.parent.name} which was not found.")
            else:
                bone_groups[pose_bone.parent.name].implementation.children.append(bone_group_layer)
       
        # Draw the bone, this happens in the space of the bone basis itself.
        # Since the paint layer is a child of the bone group onto which we'll apply the transform, 
        # we draw the bone in its own local space.
        # matrix_local and tail_local are both in armature space.
        # TODO: check if this holds true for disconnected bones.
        head = mathutils.Vector((0, 0, 0))
        tail = pose_bone.bone.matrix_local.inverted() @ pose_bone.bone.tail_local
       
        # Random color for the bone.
        bone_color = list([random.random() for i in range(3)])
        
        stroke = make_bone_stroke(head, tail, bone_color, config)
        if stroke is None:
            continue

        drawing.data.strokes.append(stroke)
        drawing.bounding_box = quill_utils.bbox_add(drawing.bounding_box, stroke.bounding_box)
        
        
    # Now go through the timeline and apply the correct transform to each bone group at each frame.
    scn = bpy.context.scene
    frame_start = max(scn.frame_start, 0)
    frame_end = max(scn.frame_end, 0)
    ticks_per_second = 12600
    ticks_per_frame = int(ticks_per_second / scn.render.fps)
    memo_current_frame = scn.frame_current
    
    frame_range = range(frame_start, frame_end + 1)
    if not config["armature_animation"]:
        frame_range = [memo_current_frame]
    
    for frame in frame_range:
        scn.frame_set(frame)
        time = frame * ticks_per_frame
    
        for pose_bone in obj.pose.bones:
            
            if pose_bone.name not in bone_groups:
                print(f"Error: bone {pose_bone.name} not found in bone groups.")
                continue
            
            bone_group_layer = bone_groups[pose_bone.name]
        
            # Find the rest pose of the bone in the space of the rest pose of its parent.
            if pose_bone.parent is not None:
                rest_pose_in_armature = pose_bone.bone.matrix_local
                parent_rest_pose_in_armature = pose_bone.parent.bone.matrix_local
                rest_pose_in_parent = parent_rest_pose_in_armature.inverted() @ rest_pose_in_armature

            else:
                rest_pose_in_parent = pose_bone.bone.matrix_local
                
            # Apply the current pose to the rest pose to get the final pose.
            # Ommiting this step exports the rest pose for the whole armature.
            pose_in_parent = rest_pose_in_parent @ pose_bone.matrix_basis

            # Convert the transform and apply to the group layer.
            translation, rotation, scale, flip = utils.convert_transform_raw(pose_in_parent)
            transform = sequence.Transform(flip, list(rotation), scale[0], list(translation))
            
            if config["armature_animation"]:
                keyframe = sequence.Keyframe("None", time, transform)
                kktt = bone_group_layer.animation.keys.transform
                kktt.append(keyframe)
            else:
                bone_group_layer.transform = transform
            
            # The pivot should be at the bone head which is the origin so we don't need to set it explicitly.
            # TODO: still true for disconnected nodes? 
            # TODO: should it be set from the rest pose?
            #bone_group_layer.implementation.pivot = head
        
    # Restore the active frame
    scn.frame_set(memo_current_frame)

    # TODO: go through the armature children, find objects that are parented to bones,
    # convert them and put them in the correct group.

    return armature_group_layer


def make_bone_stroke(head, tail, color, config):
    """Make a stroke representing a bone, from head to tail.
    Head and tail already converted to the correct coordinate system."""
    
    brush_type = paint.BrushType.CYLINDER
    disable_rotational_opacity = True
    length = (tail - head).length
    vertices = []

    # Location of the blender camera, used to get a normal.
    camera_position = mathutils.Vector((0, 0, 0))
    camera = bpy.context.scene.camera
    if camera is not None:
        camera_position = bpy.context.scene.camera.matrix_world.to_translation()
        camera_position = utils.swizzle_yup_location(camera_position)

    # The stroke is straight so all points have the same tangent.
    tangent = (tail - head).normalized()

    def add_vertex(p, width):

        # Set the normal to be in the direction of the camera.
        normal = (camera_position - p).normalized()

        opacity = 1.0
        vertex = paint.Vertex(p, normal, tangent, color, opacity, width)
        vertices.append(vertex)

    if config["armature_bone_shape"] == "OCTAHEDRAL":
        # Make a stroke that resembles the Blender octahedral bone.
        # We need a minimum of 4 points to make a quill stroke.
        # p1 is the main driver of the shape and p2 is just a support point.
        add_vertex(head, 0)
        p1 = head.lerp(tail, 0.1)
        p1_width = length / 8
        add_vertex(p1, p1_width)
        p2 = head.lerp(tail, 0.9)
        p2_width = ((length * 0.1) * p1_width) / length
        add_vertex(p2, p2_width)
        add_vertex(tail, 0)
    elif config["armature_bone_shape"] == "STICK":
        add_vertex(head, 0)
        segments = 10
        for i in range(segments-1):
            add_vertex(head.lerp(tail, (i + 1) / segments), length / 10)
        add_vertex(tail, 0)

    bounding_box = quill_utils.bbox_from_points(head, tail)

    id = 0
    stroke = paint.Stroke(id, bounding_box, brush_type, disable_rotational_opacity, vertices)
    return stroke
