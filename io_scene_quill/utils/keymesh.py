import bpy
import random
from .fcurves import get_fcurve


# Helper functions for Keymesh objects.
# These only rely on the data structures used by Keymesh and not on its operators.


def new_object_id() -> int:
    """Returns random unused number between 1-1000 to be used as Keymesh ID."""
    id = random.randint(1, 1000)
    used_ids = {o.keymesh.get("ID") for o in bpy.data.objects if o.keymesh.get("ID") is not None}
    while id in used_ids:
        id = random.randint(1, 1000)

    return id


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
    index = 0
    for obj in drawing_objs:
        # Give the block Keymesh properties.
        block = obj.data
        block.keymesh["ID"] = parent_obj.keymesh["ID"]
        block.keymesh["Data"] = index
        block.use_fake_user = True

        # Assign the block to the parent object.
        block_registry = parent_obj.keymesh.blocks.add()
        block_registry.block = block
        block_registry.name = obj.name

        index += 1

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


def keymesh_get_frame_sequence(obj):
    """
    Returns a list of (frame, drawing_index) tuples for each keyframe in the Keymesh object `obj`.
    """

    frame_sequence = []

    data_path = 'keymesh["Keymesh Data"]'
    fcurve = get_fcurve(obj, data_path)
    if fcurve:
        for kf in fcurve.keyframe_points:
            frame = int(kf.co.x)
            drawing_index = int(kf.co.y)
            frame_sequence.append((frame, drawing_index))

    return frame_sequence

