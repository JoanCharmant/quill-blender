import bpy
from mathutils import Matrix, Vector, Quaternion, Euler

# Functions to convert from Blender coordinate system to Quill’s.
# Some functions taken from the glTF addon.

def swizzle_yup_location(loc: Vector) -> Vector:
    return Vector((loc[0], loc[2], -loc[1]))


def swizzle_yup_rotation(rot: Quaternion) -> Quaternion:
    return Quaternion((rot[0], rot[1], rot[3], -rot[2]))


def swizzle_yup_scale(scale: Vector) -> Vector:
    return Vector((scale[0], scale[2], scale[1]))


def swizzle_quaternion(rot: Quaternion) -> Quaternion:
    # Blender quaternions is stored as WXYZ, Quill uses XYZW.
    return Quaternion((rot[1], rot[2], rot[3], rot[0]))


def convert_transform(m: Matrix):
    """Convert a Blender matrix to a Quill transform."""
    translation, rotation, scale = m.decompose()

    translation = swizzle_yup_location(translation)
    rotation = swizzle_quaternion(swizzle_yup_rotation(rotation))
    scale = swizzle_yup_scale(scale)
    flip = "N"

    return translation, rotation, scale, flip


def transform_equals(m1: Matrix, m2: Matrix, epsilon=1e-6):
    """Compare two matrices for equality, with a tolerance."""
    if m1 == m2:
        return True

    # Check for equality with a tolerance.
    for i in range(4):
        for j in range(4):
            if abs(m1[i][j] - m2[i][j]) > epsilon:
                return False

    return True
