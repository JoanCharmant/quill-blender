# Qbin data used by sounds.
# These do not depend on any Blender data types.

import struct
import wave

class SoundData:
    def __init__(self):
        self.num_channels = 0
        self.bits = 0
        self.rate = 0
        self.num_samples = 0
        self.samples = []


def read_sound_data(qbin):
    """Read sound data from the passed QBin file object."""

    data = SoundData()

    # Based on piWave.cpp.
    # https://github.com/Immersive-Foundation/IMM/blob/main/code/libImmCore/src/libWave/piWave.cpp
    version = struct.unpack("<I", qbin.read(4))[0]
    if version != 0:
        return None

    _ = struct.unpack("<h", qbin.read(2))[0]

    data.num_channels = struct.unpack("<B", qbin.read(1))[0]
    data.bits = struct.unpack("<B", qbin.read(1))[0]
    data.rate = struct.unpack("<I", qbin.read(4))[0]
    data.num_samples = struct.unpack("<Q", qbin.read(8))[0]

    # Read samples in a bytearray.
    bytes_per_sample = int(data.num_channels * data.bits / 8)
    total_bytes = data.num_samples * bytes_per_sample
    data.samples = qbin.read(total_bytes)

    return data


def write_sound_data(data:SoundData, qbin):
    """Write sound data to the passed QBin file object."""

    # version (4 bytes), unknown (2 bytes), num_channels (1 byte), bits (1 byte),
    # rate (4 bytes), num_samples (8 bytes), samples (num_samples * num_channels * bits/8 bytes).
    # version.
    qbin.write(struct.pack("<I", 0))
    
    # unused.
    qbin.write(struct.pack("<h", 0))
    
    # fields.
    qbin.write(struct.pack("<B", data.num_channels))
    qbin.write(struct.pack("<B", data.bits))
    qbin.write(struct.pack("<I", data.rate))
    qbin.write(struct.pack("<Q", data.num_samples))
    qbin.write(data.samples)


def export_sound_data(data:SoundData, path):
    """Write sound data to an external file (.wav)."""
    # https://docs.python.org/3/library/wave.html
    with wave.open(path, "wb") as wave_write:
        wave_write.setnchannels(data.num_channels)
        wave_write.setsampwidth(int(data.bits / 8))
        wave_write.setframerate(data.rate)
        wave_write.writeframes(data.samples)
    return True


