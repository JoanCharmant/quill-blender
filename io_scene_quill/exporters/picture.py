import bpy
from ..model import picture, quill_utils

def convert(obj, config):
    """Convert from Blender Image reference to Quill picture layer."""
    
    # TODO: handle image sequences and movies.
    # Ideally we just want to grab the image data updated to the current frame.
    #obj.data.source = "SEQUENCE"
    # For now it doesn't seem possible to force an update of the obj.data.pixels.
    # We always get the data of the current frame at the moment of the export.
    # Tested to change the frame:
    # - scn.frame_set(frame)
    # - scn.frame_current = frame
    # - obj.image_user.frame_current = frame
    # Tested to force update pixel data:
    # - obj.data.update()
    # - obj.data.reload()
    # - bpy.context.view_layer.update()
    # - finding VIEW_3D area and doing area.tag_redraw()
    # - obj.hide_render = obj.hide_render
    
    picture_layer = quill_utils.create_picture_layer(obj.name)
    
    # JSON level properties.
    # data_file_offset is filled during export.
    picture_layer.implementation.type = "2D"
    picture_layer.implementation.viewer_locked = False
    picture_layer.implementation.import_file_path = obj.data.filepath
    
    # Qbin level properties.
    picture_data = picture.PictureData()
    picture_layer.implementation.data = picture_data
    
    picture_data.hasAlpha = True
    picture_data.width = obj.data.size[0]
    picture_data.height = obj.data.size[1]
    
    # Blender stores the data as [0..1] floats, RGB(A).
    # We convert to [0..255] bytes in the write function.
    picture_data.pixels = obj.data.pixels
    
    return picture_layer
