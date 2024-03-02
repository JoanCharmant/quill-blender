
import struct
from enum import Enum

# Core data used by Drawings and read/write functions.
# These do not depend on any Blender data types.


class BrushType(Enum):
    UNKNOWN = 0
    RIBBON = 1
    CYLINDER = 2
    ELLIPSE = 3
    CUBE = 4


class DrawingData:
    def __init__(self):
        self.strokes = []


class Stroke:
    def __init__(self, id, bounding_box, brush_type, disable_rotational_opacity, vertices):
        self.id = id
        self.bounding_box = bounding_box
        self.brush_type = brush_type
        self.disable_rotational_opacity = disable_rotational_opacity
        self.vertices = vertices


class Vertex:
    def __init__(self, position, normal, tangent, color, opacity, width):
        self.position = position
        self.normal = normal
        self.tangent = tangent
        self.color = color
        self.opacity = opacity
        self.width = width


def read_drawing_data(qbin):
    data = DrawingData()
    stroke_count = struct.unpack("<I", qbin.read(4))[0]
    for _ in range(stroke_count):
        data.strokes.append(read_stroke(qbin))

    return data


def read_stroke(qbin):
    id = struct.unpack("<I", qbin.read(4))[0]
    _ = struct.unpack("<I", qbin.read(4))[0]
    bounding_box = struct.unpack("<ffffff", qbin.read(4*6))
    brush_type = BrushType(struct.unpack("<h", qbin.read(2))[0])
    disable_rotational_opacity = struct.unpack("<?", qbin.read(1))[0]
    _ = struct.unpack("<c", qbin.read(1))[0]
    count = struct.unpack("<I", qbin.read(4))[0]
    vertices = []
    for _ in range(count):
        vertices.append(read_vertex(qbin))

    return Stroke(id, bounding_box, brush_type, disable_rotational_opacity, vertices)


def read_vertex(qbin):
    position = struct.unpack("<fff", qbin.read(4*3))
    normal = struct.unpack("<fff", qbin.read(4*3))
    tangent = struct.unpack("<fff", qbin.read(4*3))
    color = struct.unpack("<fff", qbin.read(4*3))
    opacity = struct.unpack("<f", qbin.read(4))[0]
    width = struct.unpack("<f", qbin.read(4))[0]

    return Vertex(position, normal, tangent, color, opacity, width)


def write_header(qbin):
    # 8-byte header.
    qbin.write(struct.pack("<I", 0))
    qbin.write(struct.pack("<I", 0))


def write_drawing_data(data, qbin):
    qbin.write(struct.pack("<I", len(data.strokes)))
    for stroke in data.strokes:
        write_stroke(stroke, qbin)


def write_stroke(stroke, qbin):

    # We don’t know what these two fields are but they are always 0 in files produced by Quill.
    u2 = 0
    u3 = b'\x00'

    qbin.write(struct.pack("<I", stroke.id))
    qbin.write(struct.pack("<I", u2))
    qbin.write(struct.pack("<ffffff", *stroke.bounding_box))
    qbin.write(struct.pack("<h", stroke.brush_type.value))
    qbin.write(struct.pack("<?", stroke.disable_rotational_opacity))
    qbin.write(struct.pack("<c", u3))
    qbin.write(struct.pack("<I", len(stroke.vertices)))
    for vertex in stroke.vertices:
        write_vertex(vertex, qbin)


def write_vertex(vertex, qbin):
    qbin.write(struct.pack("<fff", *vertex.position))
    qbin.write(struct.pack("<fff", *vertex.normal))
    qbin.write(struct.pack("<fff", *vertex.tangent))
    qbin.write(struct.pack("<fff", *vertex.color))
    qbin.write(struct.pack("<f", vertex.opacity))
    qbin.write(struct.pack("<f", vertex.width))


