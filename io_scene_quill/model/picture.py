# Qbin data used by images.
# These do not depend on any Blender data types.

from enum import Enum
import struct
import numpy as np

class AssetFormat(Enum):
    NONE     = 0
    PNG      = 1
    JPG      = 2
    WAV      = 3
    OGG      = 4
    OPUS     = 5


class ImageType(Enum):
    TYPE_1D     = 1
    TYPE_2D     = 2
    TYPE_3D     = 3
    TYPE_CUBE   = 4


class ImageFormat(Enum):
    UNUSED1         = 0
    UNUSED2         = 1
    FORMAT_I_GREY   = 2
    FORMAT_I_15BIT  = 3
    FORMAT_I_16BIT  = 4
    FORMAT_I_RG     = 5
    FORMAT_I_RGB    = 6
    FORMAT_I_RGBA   = 7
    FORMAT_F_GREY   = 8
    FORMAT_F_RG     = 9
    FORMAT_F_RGB    = 10
    FORMAT_F_RGBA   = 11


class PictureData:
    def __init__(self):
        self.hasAlpha = False
        self.width = 16
        self.height = 16
        self.pixels = None


def read_picture_data(qbin):

    data = PictureData()    
    
    # Unknown.
    _ = struct.unpack("<B", qbin.read(1))[0]
    _ = struct.unpack("<B", qbin.read(1))[0]
    _ = struct.unpack("<B", qbin.read(1))[0]
    
    
    asset_format = AssetFormat(struct.unpack("<B", qbin.read(1))[0])
    if (asset_format != AssetFormat.PNG):
        return None

    # ImageType?
    image_type = ImageType(struct.unpack("<B", qbin.read(1))[0])
    if (image_type != ImageType.TYPE_2D):
        return None
    
    image_format = ImageFormat(struct.unpack("<B", qbin.read(1))[0])
    if image_format == ImageFormat.FORMAT_I_RGBA or image_format == ImageFormat.FORMAT_F_RGBA:
        data.hasAlpha = True
    else:
        data.hasAlpha = False
    
    # Only support 8-bit per channel RGB(A) images for now.
    if image_format != ImageFormat.FORMAT_I_RGB and image_format != ImageFormat.FORMAT_I_RGBA:
        return None
    
    _ = struct.unpack("<B", qbin.read(1))[0]
    _ = struct.unpack("<B", qbin.read(1))[0]
    
    data.width = struct.unpack("<I", qbin.read(4))[0]
    data.height = struct.unpack("<I", qbin.read(4))[0]
    _ = struct.unpack("<I", qbin.read(4))[0]
    
    # The pixel data is expected to be an array of RGB(A) values in [0..255].
    num_channels = 4 if data.hasAlpha else 3
    total_bytes = data.width * data.height * num_channels
    pixel_data = qbin.read(total_bytes)
    pixels = np.frombuffer(pixel_data, dtype=np.uint8)
    pixels = pixels.astype(np.float32)
    pixels = pixels / 255.0
    data.pixels = pixels.reshape((data.height, data.width, num_channels)).tolist()
    
    return data
    
    

def write_picture_data(data:PictureData, qbin):

    # A lot of the file format is unknown but we have enough to create a valid layer.
    # The viewer-locked flag and projection type are in the JSON.

    # TODO: Revisit this based on IMM piImage.cpp.
    # https://github.com/Immersive-Foundation/IMM/blob/main/code/libImmCore/src/libBasics/piImage.h

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

    # Unknown, likely the depth in pixels for dense 3D images.
    qbin.write(struct.pack("<I", 1))

    # Input pixel data is expected to be an array of RGB(A) values in [0..1].
    # Convert to [0..255].
    pixels = np.array(data.pixels)
    pixels = pixels * 255
    pixels = pixels.astype(np.int8)

    pixels.tofile(qbin)
