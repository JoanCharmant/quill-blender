from ..model import picture, quill_utils

def convert(obj, config):
    """Convert from Blender Image reference to Quill picture layer."""
    
    # TODO: handle sequences.
    #obj.data.source = "SEQUENCE"
    
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
