# Qbin data used by images.
# These do not depend on any Blender data types.

import struct
import numpy as np

class PictureData:
    def __init__(self):
        self.hasAlpha = False
        self.width = 16
        self.height = 16
        self.pixels = None


def write_picture_data(data:PictureData, qbin):
    
    # A lot of the file format is unknown but we have enough to create a valid layer.
    # The viewer-locked flag and projection type are in the JSON.
    
    # Unknown
    qbin.write(struct.pack("<B", 0x00))
    qbin.write(struct.pack("<B", 0x00))
    qbin.write(struct.pack("<B", 0x00))
    qbin.write(struct.pack("<B", 0x01))
    qbin.write(struct.pack("<B", 0x02))
    
    # 07 for RGBA.
    # 06 for RGB.
    if data.hasAlpha:
        qbin.write(struct.pack("<B", 0x07))
    else:
        qbin.write(struct.pack("<B", 0x06))

    # Unknown
    qbin.write(struct.pack("<B", 0x00))
    qbin.write(struct.pack("<B", 0x00))

    # Image size.
    qbin.write(struct.pack("<I", data.width))
    qbin.write(struct.pack("<I", data.height))

    # Unknown
    qbin.write(struct.pack("<I", 1))
    
    # The pixel data is expected to be an array of RGB(A) values in [0..1].
    # Convert to [0..255].
    pixels = np.array(data.pixels)
    pixels = pixels * 255
    pixels = pixels.astype(np.int8)

    pixels.tofile(qbin)
