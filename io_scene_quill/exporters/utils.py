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
