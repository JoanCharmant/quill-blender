import bpy

def convert(layer, channel):
    """Convert a Quill Sound layer to Blender sound strips."""

    scn = bpy.context.scene
    if scn.frame_start == 1:
        scn.frame_start = 0

    ticks_per_second = 12600
    ticks_per_frame = int(ticks_per_second / scn.render.fps)

    filepath = layer.implementation.import_file_path
    name = layer.name

    #----------------------------------------------------------
    # Every clip is guaranteed to have an offset key at its start time, so we use that
    # to find the start of clips.
    # A basic sound layer with no clips will have one visibility key turning it "on" at time 0,
    # and one offset key at time 0 with offset 0, but no end key.
    # Clicking the "[" button in between two clips will create a new clip
    # starting at the current time and ending right before the next clip.
    #
    # We don't support clips nested in sequences for now, only the clips on the sound layer itself.
    # Looping doesn't appear to be supported in Blender sound strips.
    # The Mute and Solo flags from Quill don't seem to be saved in the JSON file.
    #----------------------------------------------------------

    kkvv = layer.animation.keys.visibility
    kkoo = layer.animation.keys.offset
    for i in range(len(kkoo)):
        time_start = kkoo[i].time
        time_offset = kkoo[i].value

        # Find the next "visibility=off" key after this one, if any.
        time_end = None
        for j in range(len(kkvv)):
            if kkvv[j].time > time_start and kkvv[j].value == False:
                time_end = kkvv[j].time
                break

        frame_offset_start = int(time_offset / ticks_per_frame)
        # The frame start must be adjusted by the offset.
        # Applying the offset is like trimming the start of the clip.
        frame_start = int(time_start / ticks_per_frame) - frame_offset_start
        max_frame = frame_start

        if time_end is not None:
            frame_end = int(time_end / ticks_per_frame)
            max_frame = frame_end

        # Extends Blender timeline if needed.
        if scn.frame_end < max_frame:
            scn.frame_end = max_frame

        # Create the sound strip.
        sound_strip = scn.sequence_editor.sequences.new_sound(name=name, filepath=filepath, channel=channel, frame_start=frame_start)
        sound_strip.frame_offset_start = frame_offset_start
        if time_end is not None:
            sound_strip.frame_final_end = frame_end
