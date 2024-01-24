import bpy
from mathutils import Matrix, Vector, Quaternion, Euler

# Functions to convert from Blender coordinate system to Quill’s.
# Functions taken from the glTF addon.

def swizzle_yup_location(loc: Vector) -> Vector:
    return Vector((loc[0], loc[2], -loc[1]))


def swizzle_yup_rotation(rot: Quaternion) -> Quaternion:
    return Quaternion((rot[0], rot[1], rot[3], -rot[2]))


def swizzle_yup_scale(scale: Vector) -> Vector:
    return Vector((scale[0], scale[2], scale[1]))


def swizzle_quaternion(rot: Quaternion) -> Quaternion:
    # Blender quaternions is stored as WXYZ, Quill uses XYZW.
    return Quaternion((rot[1], rot[2], rot[3], rot[0]))

# Functions to work with bounding boxes.

def make_bounding_box(p1: Vector, p2: Vector):
    """Make a bounding box from two points."""
    return [
        min(p1.x, p2.x),
        min(p1.y, p2.y),
        min(p1.z, p2.z),
        max(p1.x, p2.x),
        max(p1.y, p2.y),
        max(p1.z, p2.z),
    ]


def update_bounding_box(a, b):
    """Augment bounding box a with bounding box b and return a."""
    a[0] = min(a[0], b[0])
    a[1] = min(a[1], b[1])
    a[2] = min(a[2], b[2])
    a[3] = max(a[3], b[3])
    a[4] = max(a[4], b[4])
    a[5] = max(a[5], b[5])
    return a