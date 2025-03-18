import json
import os
import re
from . import paint, sequence, state


def create_scene():
    """Create a default Quill scene with a root layer and an initial viewpoint."""
    # Create the minimal layer hierarchy.
    root_layer = create_group_layer("Root")
    viewpoint_layer = create_viewpoint_layer("InitialSpawnArea")
    root_layer.implementation.children.append(viewpoint_layer)
    seq = sequence.Sequence.from_default(root_layer)
    version = 1
    return sequence.QuillScene(seq, version)


def create_state():
    """Create a default Quill state"""
    return state.quill_state_from_default()


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
        # Technically the format supports arbitrary strings but some functions
        # like the camera preview don't work with names that have spaces for example.
        return re.sub(r'[^A-Za-z0-9-_]+', '-', name)


def load_drawing_data(layer, qbin):
    """Load drawing data for the layer and its children."""

    if layer.type == "Group":
        for child in layer.implementation.children:
            load_drawing_data(child, qbin)

    elif layer.type == "Paint":
        drawings = layer.implementation.drawings
        if drawings is None or len(drawings) == 0:
            return

        for drawing in layer.implementation.drawings:
            qbin.seek(int(drawing.data_file_offset, 16))
            drawing.data = paint.read_drawing_data(qbin)


def write_drawing_data(layer, qbin):
    """Write drawing data for the layer and its children."""

    if layer.type == "Group":
        for child in layer.implementation.children:
            write_drawing_data(child, qbin)

    elif layer.type == "Paint":
        for drawing in layer.implementation.drawings:
            offset = hex(qbin.tell())[2:].upper().zfill(8)
            drawing.data_file_offset = offset
            paint.write_drawing_data(drawing.data, qbin)


def write_json(json_obj, folder_path, file_name):
    encoded = json.dumps(json_obj, indent=4, separators=(',', ': '))
    file_path = os.path.join(folder_path, file_name)
    file = open(file_path, "w", encoding="utf8", newline="\n")
    file.write(encoded)
    file.write("\n")
    file.close()


def import_scene(scene_path, qbin_path, include_hidden=True, include_cameras=True):
    """Load a Quill scene graph and drawing data."""

    scene = None
    try:
        with open(scene_path) as f:
            d = json.load(f)
            scene = sequence.QuillScene.from_dict(d)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to load JSON: {e}")
    except:
        raise ValueError(f"Failed to load Quill sequence: {scene_path}")

    # Filter out unwanted layers.
    if not include_hidden:
        delete_hidden(scene.sequence.root_layer)

    if not include_cameras:
        delete_type(scene.sequence.root_layer, "Viewpoint")
        delete_type(scene.sequence.root_layer, "Camera")

    # Load the drawing data.
    qbin = open(qbin_path, "rb")
    load_drawing_data(scene.sequence.root_layer, qbin)
    qbin.close()

    return scene


def export_scene(folder_path, scene, state):
    """Write a Quill scene to a folder with a Quill.json, Quill.qbin, and State.json file."""

    # Write qbin file.
    # This will also update the data_file_offset fields in the drawing data.
    qbin_path = os.path.join(folder_path, "Quill.qbin")
    qbin = open(qbin_path, 'wb')
    paint.write_header(qbin)
    write_drawing_data(scene.sequence.root_layer, qbin)
    qbin.close()

    # Write the scene graph and application state files.
    write_json(scene.to_dict(), folder_path, "Quill.json")
    write_json(state.to_dict(), folder_path, "State.json")


def bbox_empty():
    # Makes a bounding box initialized to reversed inifinity values
    # so the first added point will always update the bounding box.
    return [float('inf'), float('inf'), float('inf'), float('-inf'), float('-inf'), float('-inf')]


def bbox_add(a, b):
    """Augment bounding box a with bounding box b and return a."""
    a[0] = min(a[0], b[0])
    a[1] = min(a[1], b[1])
    a[2] = min(a[2], b[2])
    a[3] = max(a[3], b[3])
    a[4] = max(a[4], b[4])
    a[5] = max(a[5], b[5])
    return a


def bbox_add_point(a, p):
    """Expand bounding box a with point p and return a."""
    a[0] = min(a[0], p[0])
    a[1] = min(a[1], p[1])
    a[2] = min(a[2], p[2])
    a[3] = max(a[3], p[0])
    a[4] = max(a[4], p[1])
    a[5] = max(a[5], p[2])
    return a
