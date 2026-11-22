import bpy

#------------------------------
# Functions related to the Blender timeline.
#------------------------------

def ensure_channelbag(data_block):
    """
    Returns the channelbag of f-curves for a given ID, or `None` if the ID doesn't
    have an animation data, an action, or a slot.
    """

    anim_data = data_block.animation_data
    if anim_data is None:
        return None

    action = anim_data.action
    if action is None:
        return None
    if action.is_empty:
        return None

    if anim_data.action_slot is None:
        return None

    from bpy_extras.anim_utils import action_ensure_channelbag_for_slot
    channelbag = action_ensure_channelbag_for_slot(action, anim_data.action_slot)

    return channelbag


def get_fcurve(obj, path: str):
    """Returns the f-curve with a given data-path from objects action, or `None` if it doesn't exists."""

    if not obj.animation_data or not obj.animation_data.action:
        return None

    if bpy.app.version >= (5, 0, 0):
        # Slotted actions check.
        channelbag = ensure_channelbag(obj)
        for fcurve in channelbag.fcurves:
            if fcurve.data_path == path:
                return fcurve
    else:
        # Blender 4.5 LTS or older check.
        for fcurve in obj.animation_data.action.fcurves:
            if fcurve.data_path == path:
                return fcurve


def get_fcurves(obj):
    """Returns all the f-curves of the object's action, or an empty list."""

    if not obj.animation_data or not obj.animation_data.action:
        return []

    if bpy.app.version >= (5, 0, 0):
        channelbag = ensure_channelbag(obj)
        return list(channelbag.fcurves) if channelbag else []
    else:
        return list(obj.animation_data.action.fcurves)


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


