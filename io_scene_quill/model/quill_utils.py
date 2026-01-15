import json
import os
import re
import struct
from . import paint, picture, sound, sequence, state


def create_scene():
    """Create a default Quill scene with a root layer and an initial viewpoint."""
    # Create the minimal layer hierarchy.
    root_layer = create_group_layer("Root")
    viewpoint_layer = create_viewpoint_layer("InitialSpawnArea")
    root_layer.add_child(viewpoint_layer)
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


def create_drawing():
    """Create a new drawing with an empty stroke list."""
    drawing = sequence.Drawing.from_default()
    drawing.data = paint.DrawingData()
    drawing.data.strokes = []
    return drawing


def create_picture_layer(name):
    """Create a new picture layer."""
    type = "Picture"
    implementation = sequence.PictureLayerImplementation.from_dict({
        "DataFileOffset": "0",
        "ImportFilePath": "",
        "Type": "2D",
        "ViewerLocked": False
    })

    name = sanitize_name(name)
    return sequence.Layer.from_default(type, implementation, name)


def delete_hidden(layer):
    """Delete all hidden layers recursively."""
    if layer.type == "Group":
        for child in layer.implementation.children:
            if child.type == "Group" and child.visible:
                delete_hidden(child)

        # In Quill hiding a sound layer just makes the speaker gizmo invisible but the audio still plays,
        # so we don't remove hidden sound layers here.
        layer.implementation.children = [child for child in layer.implementation.children if child.visible or child.type == "Sound"]


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


def read_sound_data(qbin, data_file_offset):
    """Load sound data at the passed QBin file offset."""
    qbin.seek(int(data_file_offset, 16))
    sound_data = sound.read_sound_data(qbin)
    return sound_data


def export_sound_data(data, path):
    """Write sound data to an external file (.wav)."""
    return sound.export_sound_data(data, path)


def write_qbin_data(layer, qbin):
    """Write Qbin data for the layer and its children. Update data_file_offset fields."""

    if layer.type == "Group":
        for child in layer.implementation.children:
            write_qbin_data(child, qbin)

    elif layer.type == "Paint":
        for drawing in layer.implementation.drawings:
            offset = hex(qbin.tell())[2:].upper().zfill(8)
            drawing.data_file_offset = offset
            paint.write_drawing_data(drawing.data, qbin)

    elif layer.type == "Picture" and layer.implementation.data != None:
        offset = hex(qbin.tell())[2:].upper().zfill(8)
        layer.implementation.data_file_offset = offset
        picture.write_picture_data(layer.implementation.data, qbin)


def write_json(json_obj, folder_path, file_name):
    encoded = json.dumps(json_obj, indent=4, separators=(',', ': '))
    file_path = os.path.join(folder_path, file_name)
    file = open(file_path, "w", encoding="utf8", newline="\n")
    file.write(encoded)
    file.write("\n")
    file.close()


def import_scene(path, layer_types, only_visible=False, only_non_empty=False):
    """Load a Quill scene graph and its data."""

    scene_path = os.path.join(path, "Quill.json")
    qbin_path = os.path.join(path, "Quill.qbin")

    # Check if the expected files exist.
    if not os.path.exists(scene_path) or not os.path.exists(qbin_path):
        raise FileNotFoundError(f"File not found.")

    scene = None
    try:
        with open(scene_path) as f:
            d = json.load(f)
            scene = sequence.QuillScene.from_dict(d)
            connect_parents(scene.sequence.root_layer)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to load JSON: {e}")
    except:
        raise ValueError(f"Failed to load Quill sequence: {scene_path}")

    # Filter out unwanted layers.
    if only_visible:
        delete_hidden(scene.sequence.root_layer)

    if 'PAINT' not in layer_types:
        delete_type(scene.sequence.root_layer, "Paint")
    if 'VIEWPOINT' not in layer_types:
        delete_type(scene.sequence.root_layer, "Viewpoint")
    if 'CAMERA' not in layer_types:
        delete_type(scene.sequence.root_layer, "Camera")
    if 'PICTURE' not in layer_types:
        delete_type(scene.sequence.root_layer, "Picture")
    if 'SOUND' not in layer_types:
        delete_type(scene.sequence.root_layer, "Sound")

    if only_non_empty:
        delete_empty_groups(scene.sequence.root_layer)

    # Load the drawing data.
    qbin = open(qbin_path, "rb")
    load_drawing_data(scene.sequence.root_layer, qbin)
    qbin.close()

    return scene


def export_scene(folder_path, scene, state):
    """Write a Quill scene to a folder with a Quill.json, Quill.qbin, and State.json file."""

    # Write qbin file.
    qbin_path = os.path.join(folder_path, "Quill.qbin")
    qbin = open(qbin_path, 'wb')

    # Write the 8-byte header.
    qbin.write(struct.pack("<I", 0))
    qbin.write(struct.pack("<I", 0))

    # Write the data.
    # This will also update the data_file_offset fields in the drawing data.
    write_qbin_data(scene.sequence.root_layer, qbin)
    qbin.close()

    # Write the scene graph and application state files.
    write_json(scene.to_dict(), folder_path, "Quill.json")
    write_json(state.to_dict(), folder_path, "State.json")


def get_layer(scene, layer_path):
    """Get a layer by its path in the scene graph."""

    parts = layer_path.split("/")

    # Remove empty and root parts.
    parts = parts[2:]

    current_layer = scene.sequence.root_layer
    for part in parts:
        found = False
        if current_layer.type != "Group":
            return None
        for child in current_layer.implementation.children:
            if child.name == part:
                current_layer = child
                found = True
                break
        if not found:
            return None

    return current_layer


def connect_parents(layer_group):
    """Recursively assign the parent."""
    for child in layer_group.implementation.children:
        if child.type == "Group":
            connect_parents(child)
        child.parent = layer_group


def find_last_visible_frame(layer, ticks_per_frame):
    """
    Recursively find the last visible frame in the layer and its children.

    This is based on visibility keyframes (clips), not transform keyframes.
    """

    # Find the last "visibility off" keyframe on this layer, if any.
    kkvv = layer.animation.keys.visibility
    last_kv_off = 0
    if len(kkvv) > 0 and kkvv[-1].value == False:
        last_kv_off = kkvv[-1].time

    last_frame_layer = int(last_kv_off / ticks_per_frame)

    # If we are not a group we are done.
    if layer.type != "Group":
        return last_frame_layer

    # If we are a group it's more subtle.
    # None of the children are visible after the parent is hidden,
    # but it's possible that all the children are hidden before the parent is hidden.
    # In that case we need to find the last visible frame among the children.
    last_frame_children = 0
    for child in layer.implementation.children:
        last_frame = find_last_visible_frame(child, ticks_per_frame)
        if last_frame > last_frame_children:
            last_frame_children = last_frame

    if last_frame_layer == 0:
        return last_frame_children
    elif last_frame_children == 0:
        return last_frame_layer
    else:
        return min(last_frame_layer, last_frame_children)


def bbox_empty():
   """ Returns a bounding box initialized to reversed inifinity values so the first point added will always update it."""
   return [float('inf'), float('inf'), float('inf'), float('-inf'), float('-inf'), float('-inf')]


def bbox_add(a, b):
    """Augments bounding box `a` with bounding box `b` and returns `a`."""
    a[0] = min(a[0], b[0])
    a[1] = min(a[1], b[1])
    a[2] = min(a[2], b[2])
    a[3] = max(a[3], b[3])
    a[4] = max(a[4], b[4])
    a[5] = max(a[5], b[5])
    return a


def bbox_add_point(a, p):
    """Expands bounding box `a` with point `p` and returns `a`."""
    a[0] = min(a[0], p[0])
    a[1] = min(a[1], p[1])
    a[2] = min(a[2], p[2])
    a[3] = max(a[3], p[0])
    a[4] = max(a[4], p[1])
    a[5] = max(a[5], p[2])
    return a


def bbox_from_points(p1, p2):
    """Makes a bounding box from two points."""
    return [
        min(p1[0], p2[0]),
        min(p1[1], p2[1]),
        min(p1[2], p2[2]),
        max(p1[0], p2[0]),
        max(p1[1], p2[1]),
        max(p1[2], p2[2]),
    ]

