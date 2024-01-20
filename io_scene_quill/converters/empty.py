
import bpy
from ..model import sequence

def convert(obj):
    """Convert an empty object to a group layer."""

    group_layer = sequence.Layer.create_group_layer(obj.name)

    # TODO: Assign the transform.

    return group_layer