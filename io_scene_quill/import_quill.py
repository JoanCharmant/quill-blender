import os
import random
import bpy
import json
import logging
import mathutils
from math import radians
from .model import sequence, paint
from .importers import gpencil

class QuillImporter:

    def __init__(self, path, kwargs, operator):
        self.path = path
        self.config = kwargs
        self.config["path"] = path

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        pass

    def import_scene(self, context):

        file_dir = os.path.dirname(self.path)
        sequence_path = os.path.join(file_dir, "Quill.json")
        qbin_path = os.path.join(file_dir, "Quill.qbin")

        # Check if the files exist.
        if not os.path.exists(sequence_path) or not os.path.exists(qbin_path):
            raise FileNotFoundError(f"File not found.")

        # Load the scene graph.
        try:
            with open(sequence_path) as f:
                d = json.load(f)
                quill_sequence = sequence.QuillSequence.from_dict(d)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to load JSON: {e}")
        except:
            raise ValueError(f"Failed to load Quill sequence: {sequence_path}")

        root_layer = quill_sequence.sequence.root_layer

        if not self.config["load_hidden_layers"]:
            self.delete_hidden(root_layer)

        # Load the drawing data.
        self.qbin = open(qbin_path, "rb")
        self.load_drawing_data(root_layer)
        self.qbin.close()

        # Import layers and convert to Blender objects.
        bpy.ops.object.select_all(action='DESELECT')
        self.import_layer(root_layer)
        bpy.context.view_layer.update()

    def delete_hidden(self, layer):

        if layer.type == "Group":
            for child in layer.implementation.children:
                if child.type == "Group" and child.visible:
                    self.delete_hidden(child)

            layer.implementation.children = [child for child in layer.implementation.children if child.visible]

    def load_drawing_data(self, layer):

        if layer.type == "Group":
            for child in layer.implementation.children:
                self.load_drawing_data(child)

        elif layer.type == "Paint":
            # Only load the first drawing for now.
            #for drawing in layer.implementation.drawings:
            drawing = layer.implementation.drawings[0]
            self.qbin.seek(int(drawing.data_file_offset, 16))
            drawing.data = paint.read_drawing(self.qbin)

    def import_layer(self, layer, parent=None):

        logging.info("Importing Quill layer: %s (%s).", layer.name, layer.type)

        if layer.type == "Group":
            bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0, 0, 0))
            self.setup_obj(layer, parent)

            obj = bpy.context.object
            for child in layer.implementation.children:
                self.import_layer(child, obj)

            # Apply a 90° rotation on the root object to match Blender coordinate system.
            if parent is None:
                mat_rot = mathutils.Matrix.Rotation(radians(90.0), 4, 'X')
                obj.matrix_local = mat_rot @ obj.matrix_local

        elif layer.type == "Paint":
            bpy.ops.object.gpencil_add()
            self.setup_obj(layer, parent)
            gpencil.convert(bpy.context.object, layer)

        elif layer.type == "Viewpoint":
            bpy.ops.object.camera_add()
            self.setup_obj(layer, parent)

        elif layer.type == "Sound":
            bpy.ops.object.speaker_add()
            self.setup_obj(layer, parent)

        elif layer.type == "Model":
            bpy.ops.object.empty_add(type='CUBE')
            self.setup_obj(layer, parent)

        elif layer.type == "Picture":
            bpy.ops.object.empty_add(type='IMAGE')
            self.setup_obj(layer, parent)

        else:
            logging.warning("Unsupported Quill layer type: %s", layer.type)

    def setup_obj(self, layer, parent_obj=None):
        """Basic configuration of the resulting Blender object, common to all layer types."""
        obj = bpy.context.object
        obj.name = layer.name
        obj.parent = parent_obj
        obj.matrix_local = self.get_transform(layer.transform)
        # TODO: pivot.

        # Visibility: in Quill if the parent is hidden the whole subtree is not visible,
        # even if the individual layers are marked as visible.
        # In Blender each object has its own visibility flags independent of the parent.
        # Force the visibility of the object to match the parent to match Quill behavior.
        visible = layer.visible and (parent_obj is None or not parent_obj.hide_render)
        hidden = not visible
        obj.hide_set(hidden) # disable in viewport.
        obj.hide_render = hidden

    def get_transform(self, t):
        """Convert a Quill transform to a Blender matrix."""
        # TODO: support old-style transforms.
        loc = mathutils.Vector((t.translation[0], t.translation[1], t.translation[2]))
        quat = mathutils.Quaternion((t.rotation[3], t.rotation[0], t.rotation[1], t.rotation[2]))
        scale = mathutils.Vector((t.scale, t.scale, t.scale))
        return mathutils.Matrix.LocRotScale(loc, quat, scale)


def load(operator, context, filepath="", **kwargs):
    """Load a Quill scene"""

    with QuillImporter(filepath, kwargs, operator) as importer:
        importer.import_scene(context)

    return {'FINISHED'}