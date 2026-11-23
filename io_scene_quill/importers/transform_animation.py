import bpy
import logging
import mathutils
from math import floor
from .animation import get_local_time
from . import timeline, transforms
from ..utils import fcurves

#-------------------------------
# Functions related to importing the transform keys
#-------------------------------

def setup(obj, layer, offset, mode, do_scale=True, correction=None):
    """
    Setup the animation of the object.
    Returns True if transform key frames were created.
    """

    # Quill has several types of key frames.
    # Visibility and Offset key frames are used for clips and spans.
    # Opacity key frames are used for fading layers in and out.
    # Transform key frames are imported as sparse key frames or baked on every frame.
    kktt = layer.animation.keys.transform
    if kktt is None or len(kktt) == 0:
        return False

    if mode == "KEYFRAMES":
        animate_transform(obj, layer, kktt, offset, do_scale, correction)
        return True
    elif mode == "BAKE":
        bake_transform(obj, layer, kktt, do_scale, correction)
        return True

    return False


def animate_transform(obj, layer, kktt, offset=0, do_scale=True, correction=None):
    """
    Convert Quill transform key frames to Blender key frames, one for one.
    Used for import mode "Keyframes", to keep sparse key frames.
    
    If a parent sequence loops the animation, one iteration is keyed and repeated with a Cycles modifier.
    Clips, offsets and nested loops can't be expressed with sparse key frames, these layers are baked.
    """

    mapping, duration = get_time_mapping(layer)

    keys = None
    if mapping == "LINEAR":
        keys = [(key.time, get_key_transform(key.value, do_scale, correction), key.interpolation) for key in kktt]
    elif mapping == "LOOP":
        keys = get_loop_keys(kktt, duration, do_scale, correction)

    if keys is None:
        logging.info("Baking transform key frames of %s, parent sequences use clips or offsets.", layer.name)
        bake_transform(obj, layer, kktt, do_scale, correction)
        return

    # Quill stores rotations as quaternions. Keying them directly avoids
    # the flips we get when converting each key to Euler angles independently.
    obj.rotation_mode = 'QUATERNION'

    fps = bpy.context.scene.render.fps
    time_base = 1/12600

    # First pass, create the key frames with default interpolation.
    # Loops keep fractional frames so the period of the cycle is exact.
    # The following dict stores the Blender interpolation type for the Blender frame, 
    # to be applied in a second pass.
    # It keeps the last value in case multiple Quill keys land on the same Blender frame.
    frame_interpolation = {}
    previous_rot = None
    for time, (loc, rot, scale), interpolation in keys:
        frame = (time + offset) * time_base * fps
        if mapping == "LINEAR":
            frame = floor(frame + 0.5)

        if previous_rot is not None and rot.dot(previous_rot) < 0:
            rot = -rot
        previous_rot = rot

        insert_transform_key(obj, frame, loc, rot, scale, do_scale)
        frame_interpolation[round(frame, 3)] = get_interpolation(interpolation)

    # Second pass, set the interpolation.
    # Match Blender key frames to Quill keys by frame.
    for fcurve in fcurves.get_fcurves(obj):
        if fcurve.data_path not in ("location", "rotation_quaternion", "scale"):
            continue
        for kp in fcurve.keyframe_points:
            interp = frame_interpolation.get(round(kp.co.x, 3))
            if interp is not None:
                kp.interpolation, kp.easing = interp

        if mapping == "LOOP":
            cycles = fcurve.modifiers.new('CYCLES')
            cycles.mode_before = 'NONE'
            cycles.mode_after = 'REPEAT'


def bake_transform(obj, layer, kktt, do_scale=True, correction=None):
    """
    Sample the Quill transform animation on every frame of the Blender timeline.
    Used for the "Bake" import mode.
    
    The transform key frames of a layer live in the timeline of its parent,
    so we resolve looping, clips and offsets of all the ancestors at each frame.
    Frame holds are collapsed to their first and last frames.
    """

    obj.rotation_mode = 'QUATERNION'

    scn = bpy.context.scene
    ticks_per_frame = int(12600 / scn.render.fps)

    # Lineage of ancestors, from the parent up to the root.
    stack = []
    parent = layer.parent
    while parent is not None:
        stack.append(parent)
        parent = parent.parent

    pivot = layer.pivot.translation if layer.pivot is not None else (0.0, 0.0, 0.0)
    pivot_loc = mathutils.Vector(pivot)

    import_start, import_end = timeline.setup_frame_range(scn)
    
    # Sample the transform at every frame.
    # When a parent is hidden (between clips) hold the last value.
    samples = []
    current = None
    for frame in range(import_start, import_end + 1):
        visible, local_time = get_local_time(stack, frame * ticks_per_frame, ticks_per_frame)
        if visible or current is None:
            time = local_time if visible else kktt[0].time
            loc, rot, scale = evaluate_transform(kktt, time, do_scale, pivot_loc, correction)
            if current is not None and rot.dot(current[1]) < 0:
                rot.negate()
            current = (loc, rot, scale)
        samples.append((frame, current))

    last = len(samples) - 1
    
    for i, (frame, value) in enumerate(samples):
        
        if 0 < i < last:
            prev = samples[i - 1][1]
            next = samples[i + 1][1]
            if (transforms.transform_equals(value, prev) and 
                transforms.transform_equals(value, next)):
                continue
        
        loc, rot, scale = value
        insert_transform_key(obj, frame, loc, rot, scale, do_scale)

    for fcurve in fcurves.get_fcurves(obj):
        if fcurve.data_path in ("location", "rotation_quaternion", "scale"):
            for kp in fcurve.keyframe_points:
                kp.interpolation = 'LINEAR'


#-------------------------------
#Time mapping and loop analysis
#-------------------------------

def get_time_mapping(layer):
    """
    Find how the parent sequences remap the time of the layer transform key frames.
    Returns ("LINEAR", None) if time is only shifted, ("LOOP", duration) if a single
    parent sequence loops it, or ("COMPLEX", None) for clips, offsets and nested loops.
    Loops longer than the Blender timeline are ignored as they never wrap.
    This includes the root layer which loops every hour by default.
    """

    scn = bpy.context.scene
    timeline_ticks = (scn.frame_end - scn.frame_start + 1) * 12600 / scn.render.fps

    loop_duration = None
    shifted_inside_loop = False
    parent = layer.parent
    while parent is not None:
        anim = parent.animation
        kkvv = anim.keys.visibility
        if len(kkvv) > 1 or any(key.value != 0 for key in anim.keys.offset):
            return "COMPLEX", None

        if anim.timeline:
            looping = anim.max_repeat_count == 0 and 0 < anim.duration < timeline_ticks
            if looping:
                if loop_duration is not None or shifted_inside_loop:
                    return "COMPLEX", None
                loop_duration = anim.duration
            elif len(kkvv) == 1 and kkvv[0].time != 0 and loop_duration is None:
                # A sequence starting late, below a potential loop.
                shifted_inside_loop = True

        parent = parent.parent

    if loop_duration is None:
        return "LINEAR", None

    return "LOOP", loop_duration


def get_loop_keys(kktt, duration, do_scale, correction):
    """
    Build the key frames of one iteration of a loop, from 0 to `duration`, closed with
    a copy of the first key. Returns None if the iteration can't be represented exactly,
    when the loop cuts a segment that is interpolating toward a key beyond the loop end.
    """

    if kktt[0].time < 0:
        return None

    inside = [key for key in kktt if key.time < duration]
    if len(inside) == 0:
        return None

    keys = []
    if inside[0].time > 0:
        # Quill holds the first key value from the start.
        keys.append((0, get_key_transform(inside[0].value, do_scale, correction), "None"))

    for key in inside:
        keys.append((key.time, get_key_transform(key.value, do_scale, correction), key.interpolation))

    # Check the last segment, it gets cut by the loop and restarts at the first value.
    first_value = keys[0][1]
    last = inside[-1]
    following = kktt[len(inside)] if len(inside) < len(kktt) else None
    if following is None:
        # Quill holds the last value until the loop restarts.
        keys[-1] = (keys[-1][0], keys[-1][1], "None")
    elif last.interpolation != "None":
        following_value = get_key_transform(following.value, do_scale, correction)
        if following.time != duration or not transforms.transform_equals(following_value, first_value):
            return None

    keys.append((duration, first_value, "None"))
    return keys


#-------------------------------
# Transform evaluation and keying
#-------------------------------


def evaluate_transform(kktt, time, do_scale, pivot, correction):
    """Evaluate Quill transform key frames at `time` (in ticks)."""

    if time <= kktt[0].time:
        return get_key_transform(kktt[0].value, do_scale, correction)

    # Note: We can safely ignore the static transform at the layer level.
    
    for i in range(len(kktt) - 1):
        a = kktt[i]
        b = kktt[i + 1]
        if a.time <= time < b.time:
            
            # The interpolation of a key applies to the segment leaving it (same in Quill and Blender).
            u = ease(a.interpolation, (time - a.time) / (b.time - a.time))
            loc_a, rot_a, scale_a = get_key_transform(a.value, do_scale, correction)
            loc_b, rot_b, scale_b = get_key_transform(b.value, do_scale, correction)

            # Quill already accounts for the pivot in each key's translation.
            # However, interpolating these translations directly would cause
            # the layer to drift away from its pivot during rotation or scaling.
            # Instead, interpolate the transformed pivot position and reconstruct
            # the translation from the interpolated rotation and scale.
            # The pivot moves through space as the layer translation is animated.
            pivot_a = transformed_pivot(loc_a, rot_a, scale_a, pivot)
            pivot_b = transformed_pivot(loc_b, rot_b, scale_b, pivot)

            pivot_loc = pivot_a.lerp(pivot_b, u)
            rot = rot_a.slerp(rot_b, u)
            scale = scale_a.lerp(scale_b, u)

            # `pivot` is the static pivot position in the layer's local coordinates. It never changes.
            # `pivot_loc` is the interpolated position of that pivot in the parent's coordinate system, 
            # after applying the animated transform.
            # Find a translation loc that places the original pivot at pivot_loc, 
            # given the interpolated rotation and scale.
            loc = pivot_loc - rot @ (scale * pivot)
            
            return loc, rot, scale

    return get_key_transform(kktt[-1].value, do_scale, correction)


def transformed_pivot(loc, rot, scale, pivot):
    return loc + rot @ (scale * pivot)


def get_key_transform(transform, do_scale, correction):
    """Convert a Quill key frame transform to Blender location, rotation and scale."""
    
    mat = transforms.convert_transform(transform)
    
    if correction is not None:
        mat = correction @ mat
        
    loc, rot, scale = mat.decompose()
    
    if not do_scale:
        scale = mathutils.Vector((1.0, 1.0, 1.0))
    
    return loc, rot, scale


def insert_transform_key(obj, frame, loc, rot, scale, do_scale):
    """Insert a key frame for the Blender object at the given frame."""
    
    # The names of the channels are from the F-Curve panel in the Graph Editor.
    obj.location = loc
    obj.rotation_quaternion = rot
    obj.keyframe_insert(data_path="location", frame=frame)
    obj.keyframe_insert(data_path="rotation_quaternion", frame=frame)
    
    if do_scale:
        obj.scale = scale
        obj.keyframe_insert(data_path="scale", frame=frame)
    else:
        obj.scale = (1.0, 1.0, 1.0)


def get_interpolation(interpolation):
    """Convert Quill interpolation to Blender f-curve interpolation"""
    # Note that these do not exactly match the Quill interpolation,
    # the one in ease() function for the "bake" path does match Quill.
    if interpolation == "None":
        return 'CONSTANT', 'AUTO'
    elif interpolation == "Linear":
        return 'LINEAR', 'AUTO'
    elif interpolation == "EaseIn":
        return 'CUBIC', 'EASE_IN'
    elif interpolation == "EaseOut":
        return 'CUBIC', 'EASE_OUT'
    elif interpolation == "Smoothstep":
        return 'CUBIC', 'EASE_IN_OUT'
    else:
        return 'LINEAR', 'AUTO'


def ease(interpolation, u):
    """Remap the normalized time `u` according to the Quill interpolation mode."""
    if interpolation == "None":
        return 0.0
    elif interpolation == "EaseIn":
        return u * u * u
    elif interpolation == "EaseOut":
        return 1.0 - (1.0 - u) ** 3
    elif interpolation == "Smoothstep":
        return u * u * (3.0 - 2.0 * u)
    else:
        # Linear
        return u

        
