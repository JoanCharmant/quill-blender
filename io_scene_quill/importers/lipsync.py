import bpy
from ..utils.keymesh import keymesh_keyframe, keymesh_get_blank, keymesh_delete_all_keyframes


def apply_lipsync(drawing_to_obj, layer, parent_obj, lipsync_data):
    """Animate one keymesh object according to lipsync data.
    
    :param drawing_to_obj: maps the index of the drawing in Quill to the corresponding Blender object.
    :param layer: the Quill paint layer.
    :param parent_obj: the Blender object representing the paint layer.
    :param lipsync_data: the lipsync data for this specific layer.
    """
    
    if not lipsync_data or len(lipsync_data) == 0:
        return
    
    if len(parent_obj.keymesh.blocks) == 0:
        return
    
    # Lipsync data is a mapping from frame index to mouth shape name.
    # The keymesh object has one sub-mesh per mouth shape, in a standardized order.
    #mouth_shapes = ["AI", "E", "O", "U", "WQ", "L", "FV", "MBP", "etc", "rest"]
    mouth_shapes = ["AI", "O", "E", "U", "etc", "L", "WQ", "MBP", "FV", "rest"]
    
    # Remove all the existing keyframes on the keymesh layer.
    # These would have been created from the initial list of mouth shapes drawings.
    keymesh_delete_all_keyframes(parent_obj)
    
    # Create keyframes for each entry in the lipsync data.
    for frame_index, mouth_shape in lipsync_data:
        if mouth_shape not in mouth_shapes:
            continue
        
        shape_index = mouth_shapes.index(mouth_shape)
        
        # A frame value of -1 means we start at whatever Blender timeline starts.
        if frame_index == -1:
            frame_index = bpy.context.scene.frame_start
        
        keymesh_keyframe(parent_obj, frame_index, shape_index)
    