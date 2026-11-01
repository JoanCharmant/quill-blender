# Qbin data used by images.
# These do not depend on any Blender data types.

from enum import Enum
import struct
import logging
import numpy as np

class AssetFormat(Enum):
    NONE     = 0
    PNG      = 1
    JPG      = 2
    WAV      = 3
    OGG      = 4
    OPUS     = 5


class ImageType(Enum):
    UNUSED1     = 0 
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

# The known record begins with a fixed 20-byte header followed by (width * height * channels) raw bytes. 
_PICTURE_HEADER = struct.Struct("<3sBBB2sIII")

# Safety limits for malformed/unknown input.
# 16384 pixels and 256 MB.
MAX_IMAGE_DIMENSION = 16384
MAX_IMAGE_BYTES = 256 * 1024 * 1024

_log = logging.getLogger(__name__)


class PictureData:
    def __init__(self):
        self.hasAlpha = False
        self.width = 16
        self.height = 16

        # numpy float32 array of shape (height, width, channels), values in [0..1].
        self.pixels = None


def read_picture_data(qbin):
    """Read a Quill RGB/RGBA image, return None if the format is unknown or unsupported."""


    header = qbin.read(_PICTURE_HEADER.size)
    if len(header) != _PICTURE_HEADER.size:
        return None

    (prefix, asset_format, image_type, image_format, extra, width, height, depth) = _PICTURE_HEADER.unpack(header)

    # These bytes have not been identified. The writer emits zeros. 
    # Until we understand them, reject nonzero values rather than risk mistaking an
    # extended image format for a raw image.
    if prefix != b"\x00" * 3 or extra != b"\x00" * 2:
        _log.warning("Qbin picture: unrecognized header bytes %s / %s", prefix.hex(), extra.hex())
        return None

    # Note: even when we import a JPG image in Quill the asset format is PNG and 
    # the file stores uncompressed bytes.
    if (asset_format != AssetFormat.PNG.value):
        return None
    
    if (image_type != ImageType.TYPE_2D.value):
        return None

    if image_format == ImageFormat.FORMAT_I_RGB.value:
        channels = 3
    elif image_format == ImageFormat.FORMAT_I_RGBA.value:
        channels = 4
    else:
        # Unsupported pixel format.
        return None

    if (not 1 <= width <= MAX_IMAGE_DIMENSION or 
        not 1 <= height <= MAX_IMAGE_DIMENSION or 
        depth != 1):
        _log.warning("Qbin picture: unsupported dimensions %dx%dx%d", width, height, depth)
        return None

    byte_count = width * height * channels
    if byte_count > MAX_IMAGE_BYTES:
        _log.warning("Qbin picture: image too large (%d raw bytes)", byte_count)
        return None

    raw = qbin.read(byte_count)
    if len(raw) != byte_count:
        _log.warning("Qbin picture: truncated pixels.")
        return None
        
    data = PictureData()
    data.width = width
    data.height = height
    data.hasAlpha = (channels == 4)
    data.pixels = (np.frombuffer(raw, dtype=np.uint8)
                   .reshape((height, width, channels))
                   .astype(np.float32) / 255.0)
    return data


def write_picture_data(data:PictureData, qbin):
    """Write the known (uncompressed, 8-bit RGB/RGBA) Quill image layout."""

    channels = 4 if data.hasAlpha else 3
    
    if (not 1 <= data.width <= MAX_IMAGE_DIMENSION or 
        not 1 <= data.height <= MAX_IMAGE_DIMENSION or
        data.width * data.height * channels > MAX_IMAGE_BYTES):
        
        raise ValueError("Picture size exceeds safe limits")
    
    pixels = np.asarray(data.pixels, dtype=np.float32)
    if pixels.shape != (data.height, data.width, channels):
        raise ValueError("Picture pixel shape does not match width/height/channels")
    if not np.isfinite(pixels).all():
        raise ValueError("Picture pixel data contains NaN or infinity")

    # Write the header.
    qbin.write(_PICTURE_HEADER.pack(
        b"\x00\x00\x00",
        AssetFormat.PNG.value,
        ImageType.TYPE_2D.value,
        ImageFormat.FORMAT_I_RGBA.value if data.hasAlpha else ImageFormat.FORMAT_I_RGB.value,
        b"\x00\x00",
        data.width, data.height, 1,
    ))

    # Write the pixel data.
    # Round before converting; uint8 represents the actual unsigned byte format.
    packed = np.rint(np.clip(pixels, 0, 1) * 255.0).astype(np.uint8)
    qbin.write(packed.tobytes(order="C"))

