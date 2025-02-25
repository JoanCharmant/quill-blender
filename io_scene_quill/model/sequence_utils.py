import re
from . import sequence


def create_scene():
    """Create a new Quill scene with a root layer and an initial viewpoint."""
    # Create the minimal layer hierarchy.
    root_layer = create_group_layer("Root")
    viewpoint_layer = create_viewpoint_layer("InitialSpawnArea")
    root_layer.implementation.children.append(viewpoint_layer)
    seq = sequence.Sequence.from_default(root_layer)
    version = 1
    return sequence.QuillScene(seq, version)


def create_group_layer(name):
    """Create a new group layer."""
    type = "Group"
    implementation = sequence.GroupLayerImplementation.from_dict({
        "Children": []
    })

    name = sanitize_name(name)
    return sequence.Layer.from_default(type, implementation, name)


def create_viewpoint_layer(name):
    """Create a new viewpoint layer."""
    type = "Viewpoint"
    implementation = sequence.ViewpointLayerImplementation.from_dict({
        "AllowTranslationX": True,
        "AllowTranslationY": True,
        "AllowTranslationZ": True,
        "Color": [0.392336,0.942602,0.580318],
        "Exporting": True,
        "ShowingVolume": False,
        "Sphere": [0, 1, 0, 2],
        "TypeStr": "FloorLevel",
        "Version": 1,
    })

    name = sanitize_name(name)
    return sequence.Layer.from_default(type, implementation, name)


def create_camera_layer(name):
    """Create a new camera layer."""
    type = "Camera"
    implementation = sequence.CameraLayerImplementation.from_dict({
        "FOV": 45,
    })

    name = sanitize_name(name)
    return sequence.Layer.from_default(type, implementation, name)


def create_paint_layer(name):
    """Create a new paint layer."""
    type = "Paint"
    implementation = sequence.PaintLayerImplementation.from_dict({
        "Drawings": [],
        "Frames": ["0"],
        "Framerate": 24.0,
        "MaxRepeatCount": 1,
    })

    name = sanitize_name(name)
    return sequence.Layer.from_default(type, implementation, name)


def delete_hidden(layer):
    """Delete all hidden layers recursively."""
    if layer.type == "Group":
        for child in layer.implementation.children:
            if child.type == "Group" and child.visible:
                delete_hidden(child)

        layer.implementation.children = [child for child in layer.implementation.children if child.visible]


def delete_type(layer, type):
    """Delete all layers of a given type, recursively."""
    if layer.type == "Group":
        for child in layer.implementation.children:
            if child.type == "Group":
                delete_type(child, type)

        layer.implementation.children = [child for child in layer.implementation.children if child.type != type]


def is_empty_group(layer):
        """Returns true if a layer is a group with no children."""
        return layer.type == "Group" and len(layer.implementation.children) == 0


def delete_empty_groups(layer):
    """Delete empty groups recursively."""

    if layer.type != "Group":
        return

    # Traverse depth first.
    for child in layer.implementation.children:
        delete_empty_groups(child)

    # Remove empty groups from children.
    layer.implementation.children = list(filter(lambda x: not is_empty_group(x), layer.implementation.children))


def sanitize_name(name):
        """Sanitize a layer name for Quill."""
        # Replace anything that's not on the Quill keyboard with a dash.
        # Technically the format support arbitrary strings but some functions
        # like the camera preview don't work with names that have spaces for example.
        return re.sub(r'[^A-Za-z0-9-_]+', '-', name)

