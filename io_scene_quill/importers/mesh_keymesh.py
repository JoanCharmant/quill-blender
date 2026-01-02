import bpy
import random


# Helper functions for Keymesh objects.
# These only rely on the data structures used by Keymesh and not on its operators.


def new_object_id() -> int:
    """Returns random unused number between 1-1000 to be used as Keymesh ID."""
    id = random.randint(1, 1000)
    used_ids = {o.keymesh.get("ID") for o in bpy.data.objects if o.keymesh.get("ID") is not None}
    while id in used_ids:
        id = random.randint(1, 1000)

    return id


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


def keymesh_init(obj):
    """
    Turns `obj` into a Keymesh object.
    """
    obj.keymesh.active = True
    obj.keymesh["ID"] = new_object_id()
    obj.keymesh.animated = True
    obj.keymesh["Keymesh Data"] = -1
    obj.keymesh.property_overridable_library_set('["Keymesh Data"]', True)


def keymesh_import(parent_obj, drawing_objs):
    """
    Inserts Keymesh blocks for each object in `drawing_objs` and delete the original objects afterwards.
    """
    block_index = 0
    for obj in drawing_objs:
        # Give the block Keymesh properties.
        block = obj.data
        block.keymesh["ID"] = parent_obj.keymesh["ID"]
        block.keymesh["Data"] = block_index
        block.use_fake_user = True

        # Assign the block to the parent object.
        block_registry = parent_obj.keymesh.blocks.add()
        block_registry.block = block
        block_registry.name = obj.name

        block_index += 1

    # Delete the individual drawing objects since their data is now in Keymesh blocks.
    bpy.ops.object.select_all(action='DESELECT')
    for obj in drawing_objs:
        obj.select_set(True)
        bpy.ops.object.delete()

    bpy.context.view_layer.objects.active = parent_obj


def keymesh_keyframe(parent_obj, frame, index):
    """
    Adds a keyframe to show the drawing at `index`.
    """
    # This implements the same logic as the insert_keymesh_keyframe function
    # of the Keymesh add-on.

    # Select the block corresponding to the drawing we want to show.
    # Since we are still in the setup phase we know the block index matches the drawing index.
    # After that drawings can be rearranged in the frame picker.
    parent_obj.keymesh["Keymesh Data"] = int(index)

    # Insert the keyframe.
    data_path = 'keymesh["Keymesh Data"]'
    parent_obj.keyframe_insert(data_path=data_path, frame=frame)

    # Set to constant Interpolation
    # Note: this is necessary for frame-holds so
    # the block doesn't change in the middle of the interval between keyframes.
    fcurve = get_fcurve(parent_obj, data_path)
    if fcurve:
        for kf in fcurve.keyframe_points:
            kf.interpolation = 'CONSTANT'


