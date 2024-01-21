
import struct

# Core data used by Drawings and read/write functions.
# These do not depend on any Blender data types.

class DrawingData:
    def __init__(self):
        self.strokes = []


class Stroke:
    def __init__(self, id, u2, bounding_box, brush_type, disable_rotational_opacity, u3, vertices):
        self.id = id
        self.u2 = u2
        self.bounding_box = bounding_box
        self.brush_type = brush_type
        self.disable_rotational_opacity = disable_rotational_opacity
        self.u3 = u3
        self.vertices = vertices


class Vertex:
    def __init__(self, position, normal, tangent, color, opacity, width):
        self.position = position
        self.normal = normal
        self.tangent = tangent
        self.color = color
        self.opacity = opacity
        self.width = width


def read_drawing(qbin):
    data = DrawingData()
    stroke_count = struct.unpack("<I", qbin.read(4))[0]
    for i in range(stroke_count):
        data.strokes.append(read_stroke(qbin))

    return data


def read_stroke(qbin):
    id = struct.unpack("<I", qbin.read(4))[0]
    u2 = struct.unpack("<I", qbin.read(4))[0]
    bounding_box = struct.unpack("<ffffff", qbin.read(4*6))
    brush_type = struct.unpack("<h", qbin.read(2))[0]
    disable_rotational_opacity = struct.unpack("<?", qbin.read(1))[0]
    u3 = struct.unpack("<c", qbin.read(1))[0]
    count = struct.unpack("<I", qbin.read(4))[0]
    vertices = []
    for i in range(count):
        vertices.append(read_vertex(qbin))

    return Stroke(id, u2, bounding_box, brush_type, disable_rotational_opacity, u3, vertices)


def read_vertex(qbin):
    position = struct.unpack("<fff", qbin.read(4*3))
    normal = struct.unpack("<fff", qbin.read(4*3))
    tangent = struct.unpack("<fff", qbin.read(4*3))
    color = struct.unpack("<fff", qbin.read(4*3))
    opacity = struct.unpack("<f", qbin.read(4))[0]
    width = struct.unpack("<f", qbin.read(4))[0]

    return Vertex(position, normal, tangent, color, opacity, width)


