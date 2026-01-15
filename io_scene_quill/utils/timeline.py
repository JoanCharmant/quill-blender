import bpy


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
