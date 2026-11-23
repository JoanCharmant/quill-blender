import bpy

#------------------------------
# Functions related to the Blender timeline.
#------------------------------


def setup_frame_range(scn):
    """
    Remap the Blender frame range so the Quill timeline starts at frame 0.
    Returns (import_start, import_end). 
    Calling this more than once is harmless.
    """

    #--------------------------------------------------------------
    # Blender frame range vs Quill animation range.
    # We will loop through Blender frames and pull the corresponding Quill data.
    #
    # Heuristic:
    # - if the Blender scene starts before 0, we import from 0 until the end.
    # - if the Blender scene starts at 0, we import from 0 until the end.
    # - if the Blender scene starts at 1 (blender default), we change it to start at 0, then import from 0 to the end.
    # - if the Blender scene starts after 1, we change it to start at 0, import from 0 to how many frames the original range was,
    # and change the end to match the number of frames.
    #
    # We do this to cope with Blender scenes set up between say 1000 and 1249, which is done to create a buffer for simulations.
    # Instead of importing from 0 to 1249 we import from 0 to 249. We don't try to import from 1000 to 1249.
    # Bottom line: if a buffer is needed for simulation, start the frame range in the negative instead of 1000.
    #--------------------------------------------------------------

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

    return import_start, import_end


