import bpy
from ..utils.keymesh import keymesh_keyframe, keymesh_get_blank


def animate(drawing_to_obj, layer, use_keymesh, parent_obj):
    """
    Animates the paint layer by keyframing the visibility of the drawings.

    :param drawing_to_obj: maps the index of the drawing in Quill to the corresponding Blender object.
    :param layer: the Quill paint layer.
    :param use_keymesh: whether we are using Keymesh for this paint layer.
    :param parent_obj: the Blender object representing the paint layer.
    """

    #--------------------------------------------------------------
    # Animation of the paint layer.
    # We treat everything here because Blender empty objects aren't a good match for Quill groups
    # as they don't inherit visibility and there is no concept of offsetting.
    # All the visibility information from parent groups is baked into the leaf objects.
    # For non-keymesh we animate the visibility of the child objects directly.
    # For Keymesh we animate the blocks visibility inside the parent keymesh object.
    #--------------------------------------------------------------

    #--------------------------------------------------------------
    # Blender frame range vs Quill animation range.
    # We will loop through Blender frames and show the corresponding drawing.
    # Heuristic:
    # - if the Blender scene starts before 0, we import from 0 until the end.
    # - if the Blender scene starts at 0, we import from 0 until the end.
    # - if the Blender scene starts at 1 (blender default), we change it to start at 0, then import from 0 to the end.
    # - if the Blender scene starts after 1, we change it to start at 0, import from 0 to how many frames the original range was,
    # and change the end to match the number of frames.
    # We do this to cope with Blender scenes set up between say 1000 and 1249, which is done to create a buffer for simulations.
    # Instead of importing from 0 to 1249 we import from 0 to 249. We don't try to import from 1000 to 1249.
    # Bottom line: if a buffer is needed for simulation, start the frame range in the negative instead of 1000.
    #--------------------------------------------------------------
    scn = bpy.context.scene
    import_end = scn.frame_end
    if scn.frame_start <= 0:
        import_start = 0
    elif scn.frame_start == 1:
        scn.frame_start = 0
        import_start = 0
    else:
        count_frames = scn.frame_end - scn.frame_start
        scn.frame_start = 0
        import_start = 0
        import_end = count_frames
        scn.frame_end = count_frames

    # Force frame rate to match Quill scene.
    # Normally all layers should have the same framerate.
    if layer.implementation.framerate != scn.render.fps:
        scn.render.fps = int(layer.implementation.framerate)

    # Start by hiding all drawings from the very beginning.
    # We revisit this at the end to remove that keyframe if not really necessary
    # in case of a single, always visible drawing.
    # For keymesh this is already the default state.
    if not use_keymesh:
        for i in range(len(drawing_to_obj)):
            hide_drawing(i, min(scn.frame_start, import_start), drawing_to_obj)

    #--------------------------------------------------------------
    # Quill animation mechanics.
    #
    # 0. Drawing collection.
    # The lowest level is the unordered collection of drawings.
    # Quill UI doesn't really expose this list.
    # These are stored in order of creation, not in timeline order.
    # A new drawing is created when the user creates a keyframe.
    #
    # 1. Base frame by frame animation.
    # The first animation level is the basic sequence of drawings.
    # Quill format uses a dense frame list pointing to indices in the drawing collection.
    # Example frame list: [2, 2, 2, 0, 3, 3, 3, 4, 1, 1]
    # This basic animated sequence is what gets exported by Quill's Alembic exporter.
    # From the Quill UI it's not possible to duplicate a drawing after another one, but the format allows it.
    # Ex: [0, 1, 0, 1, 0] is a valid frame list.
    #
    # 2. The base animation can either be looping or open-ended (repeat the last drawing).
    # In both cases it is unbounded in time, to close it off we need to use clips.
    #
    # 3. Clips.
    # Each clip is like an independent window over an infinite series of the base animation.
    # These let us stop and restart the base animation.
    # The length of a clip may be a fractional number of iterations of the base animation.
    # This is controlled by in and out points, the [ and ] icons in Quill.
    # https://www.youtube.com/watch?v=1w0wk2Sjih0
    # In the file format each in and out point becomes a visibility key frame.
    # By default a clip restarts at the first drawing of the basic sequence.
    # It's possible to remove the out-point of the last clip.
    # Grabbing the clip by the middle moves it as a whole.
    # Grabbing it by the in-point changes the start point and also sets the offset (= left trim).
    # Because of this it's not possible to move the in-point of a clip leftward beyond 0.
    # Using the [ button between two clips doesn't pull the next clip leftward,
    # instead it creates a new small clip starting at the current time and going to the next clip's in-point.
    #
    # 3.1. Offsetting.
    # To control the first drawing shown in a clip, we can left-trim it by grabbing the in-point.
    # In the format this results in an offset key frame at the same time as a visibility one.
    # In theory there should be one offset key frame for each in-point.
    # The value of the offset key frame is a time, not a frame index.
    #
    # 4. Group layers can be marked as "sequences" (timelines).
    # These define their own base animation via a loop-point.
    # This base animation can be looping or open-ended.
    # Then we can create clips of that base animation, with offsets.
    #
    # 5. For normal groups (not sequences), the in and out points define visibility spans only.
    # They do not restart the underlying animation.
    # It looks like the UI still treats them as pseudo-clips, you can select, delete and trim them.
    # Grabbing and moving a clip on a normal group does weird things.
    #
    # 6. The base animation (on paint layers or sequences) can also have transform key frames.
    # When we loop it or create clips out of it, the transform should respect the clipping logic.
    # In particular this means we can have a clip ending before the next transform key frame.
    #
    # None of these concepts exist in Blender.
    # We bake all the visibility information into the drawings themselves.
    # This is done by keyframing the hide_viewport and hide_render properties.
    # Transforms are not handled here.
    #
    # Points unclear:
    # - StartOffset property. This seems redundant with the first offset key frame.
    #--------------------------------------------------------------

    # Source-lookup approach.
    # We can either loop through the frames of the Blender timeline and look up the
    # corresponding drawing to show, or loop through Quill key frames and set things up similarly in Blender.
    # The first option is simpler and more robust. We can have nested timelines and groups,
    # with optional looping, clips that restart at an offset, etc.
    #
    # For any target frame in the Blender timeline, we do:
    # blender frame -> global time -> local time -> quill frame -> quill drawing -> blender obj.
    # - local time is the time within the low level, base animation sequence, taking offset and looping into account.


    # Create a stack of the lineage for this layer all the way up to the root.
    # We will compute the local time by walking down the tree.
    stack = [layer]
    parent = layer.parent
    while parent is not None:
        stack.append(parent)
        parent = parent.parent

    # Loop through the Blender frames and show the corresponding drawing.
    was_visible = True
    ticks_per_second = 12600
    ticks_per_frame = int(ticks_per_second / scn.render.fps)
    active_drawing_index = -1
    last_frame = len(layer.implementation.frames) - 1
    for frame_target in range(import_start, import_end + 1):

        #print("----------------------------------------")
        #print("Blender frame:", frame_target)

        # Convert Blender frame to Quill ticks.
        global_time = frame_target * ticks_per_frame
        visible, local_time = get_local_time(stack, global_time, ticks_per_frame)

        if visible:

            # We are within an active iteration of the fundamental paint level animation.
            # Convert the time to a frame index
            frame_source = min(int(local_time / ticks_per_frame), last_frame)

            # Get the actual drawing that should be visible.
            drawing_index = int(layer.implementation.frames[frame_source])

            # Bail out if we are still on the same drawing (frame hold).
            # We have already set a key frame to show it during a previous iteration.
            if drawing_index == active_drawing_index:
                continue

            # Swap the active drawing.
            if use_keymesh:
                keymesh_keyframe(parent_obj, frame_target, drawing_index)
            else:
                hide_drawing(active_drawing_index, frame_target, drawing_to_obj)
                show_drawing(drawing_index, frame_target, drawing_to_obj)

            active_drawing_index = drawing_index
            was_visible = True

        else:
            # We are between clips, all drawings must be hidden.
            if not was_visible:
                 continue

            if use_keymesh:
                # For Keymesh we would need to hide all blocks which is not possible.
                # Create a blank block if it doesn't exist and activate it.
                blank_index = keymesh_get_blank(parent_obj)
                keymesh_keyframe(parent_obj, frame_target, blank_index)
            else:
                hide_drawing(active_drawing_index, frame_target, drawing_to_obj)

            active_drawing_index = -1
            was_visible = False

    # Cleanup unecessary keyframes.
    # If it's a single, always visible drawing, we don't actually need the keyframe so
    # clear up the animation data. It's simpler to do it this way than to try to predict
    # if a keyframe is needed or not due to parent sequences or groups.
    if not use_keymesh and len(drawing_to_obj) == 1 and len(layer.animation.keys.visibility) == 1:
        obj = drawing_to_obj[0]
        if obj.animation_data.action.frame_start == 0 and obj.animation_data.action.frame_end == 0:
            obj.animation_data_clear()

    # Return to start of animation.
    scn.frame_set(import_start)


def get_local_time(stack, global_time, ticks_per_frame):

    """
    Compute the local time relatively to the fundamental base frame sequence,
    taking into account clips, offsets, and looping at each level of the scene graph.

    :param stack: the stack of layers from the paint layer up to the root.
    :param global_time: the global time in ticks.
    :param ticks_per_frame: number of ticks per frame.
    :return (visible, local_time)
    """

    # The stack starts at the paint layer and goes up to the root.

    local_time = int(global_time)

    # Walk from the root down to the layer and update the local time at each level,
    # based on clips, offsets, and looping of the fundamental animation.
    # At each level we calculate the time within the fundamental animation sequence, not the clip.
    # A clip may cover multiple iterations of the fundamental animation, and may start at an offset.
    # A single layer can have multiple clips each with its own duration and offset.
    # If we are invisible at a given level we bail out early since no drawing will be visible underneath.
    for i in range(len(stack) - 1, -1, -1):

        layer = stack[i]


        # Find the key at or before the current time.
        kkvv = layer.animation.keys.visibility
        kkoo = layer.animation.keys.offset
        last_key = None
        for i in range(len(kkvv)):
            if kkvv[i].time > local_time:
                break

            last_key = kkvv[i]

        # Bail out if we are before the first key.
        if last_key is None:
            return False, local_time

        if last_key.value:
            # We are inside a clip or a visibility span.

            # Check if there is an offset key matching the in-point.
            start_offset = 0
            for i in range(len(kkoo)):
                if kkoo[i].time == int(last_key.time):
                    start_offset = int(kkoo[i].value)
                    break

            # Sequences define clips while groups define visibility spans.
            # Update the time to be relative to the start of the clip, taking offset into account.
            if layer.type == "Paint" or layer.animation.timeline:
                local_time = local_time - int(last_key.time) + start_offset

            # Handle base animation looping.
            # For sequence layers the base animation is defined by the loop point.
            # For paint layers the base animation is the drawing sequence.
            # TODO: handle max repeat count that's not 0 or 1, does Quill support this?
            looping = False
            duration = 0
            if layer.type == "Paint":
                looping = layer.implementation.max_repeat_count == 0
                duration = len(layer.implementation.frames) * ticks_per_frame
            else:
                looping = layer.animation.max_repeat_count == 0
                duration = int(layer.animation.duration)

            if looping and duration > 0:
                local_time = int(local_time % duration)

            #print("layer:", layer.name, "local frame:", int(local_time / ticks_per_frame))

        else:
            # We are between clips or after the last.
            #print("layer:", layer.name, "local frame: X")
            return False, local_time

    return True, local_time


def show_drawing(drawing_index, frame, drawing_to_obj):
    keyframe_drawing_visibility(drawing_index, frame, drawing_to_obj, False)


def hide_drawing(drawing_index, frame, drawing_to_obj):
    keyframe_drawing_visibility(drawing_index, frame, drawing_to_obj, True)


def keyframe_drawing_visibility(drawing_index, frame, drawing_to_obj, hide=True):
    """Hide or show the drawing on `frame`."""

    if drawing_index == -1:
        return

    obj = drawing_to_obj[drawing_index]
    obj.hide_viewport = hide
    obj.keyframe_insert(data_path="hide_viewport", frame=frame)
    obj.hide_render = hide
    obj.keyframe_insert(data_path="hide_render", frame=frame)


