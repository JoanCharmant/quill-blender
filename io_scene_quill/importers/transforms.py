from mathutils import Matrix, Vector, Quaternion

def convert_transform(t):
    """Convert a Quill transform to a Blender matrix."""

    if isinstance(t, list):
        # Old-style transform from before Quill 1.7 (circa 2018).
        return Matrix((t[0:4], t[4:8], t[8:12], t[12:16]))
    
    else:
        loc = Vector((t.translation[0], t.translation[1], t.translation[2]))
        quat = Quaternion((t.rotation[3], t.rotation[0], t.rotation[1], t.rotation[2]))
        scale = Vector((t.scale, t.scale, t.scale))
        mat = Matrix.LocRotScale(loc, quat, scale)
        if t.flip == "X":
            return mat @ Matrix.Scale(-1, 4, (1, 0, 0))
        elif t.flip == "Y":
            return mat @ Matrix.Scale(-1, 4, (0, 1, 0))
        elif t.flip == "Z":
            return mat @ Matrix.Scale(-1, 4, (0, 0, 1))
        else:
            return mat


def transform_equals(a, b, epsilon=1e-6):
    """Compare two (location, rotation, scale) tuples."""
    
    loc_a, rot_a, scale_a = a
    loc_b, rot_b, scale_b = b

    # Opposite quaternions are the same rotation.
    if rot_a.dot(rot_b) < 0:
        rot_b = -rot_b

    for va, vb in ((loc_a, loc_b), (rot_a, rot_b), (scale_a, scale_b)):
        for x, y in zip(va, vb):
            if abs(x - y) >= epsilon:
                return False

    return True