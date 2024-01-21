import os
import bpy
import json
import logging
from .model import sequence, paint

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

        # Load the drawing data.
        self.qbin = open(qbin_path, "rb")
        self.load_drawing_data(root_layer)
        self.qbin.close()

        # Import layers and convert to Blender objects.
        bpy.ops.object.select_all(action='DESELECT')
        self.import_layer(root_layer)
        bpy.context.view_layer.update()

    def load_drawing_data(self, layer):

        if layer.type == "Group":
            for child in layer.implementation.children:
                self.load_drawing_data(child)

        elif layer.type == "Paint":
            for drawing in layer.implementation.drawings:
                self.qbin.seek(int(drawing.data_file_offset))
                drawing.data = paint.read_drawing(self.qbin)

    def import_layer(self, layer, parent=None):

        logging.info("Importing Quill layer: %s (%s).", layer.name, layer.type)

        # Basic configuration of the resulting Blender object, common to all layer types.
        def setup_obj():
            obj = bpy.context.object
            obj.name = layer.name
            obj.parent = parent
            obj.hide_set(not layer.visible) # disable in viewport.
            obj.hide_render = not layer.visible

            # TODO: setup transform, provision for old type transform.

        if layer.type == "Viewpoint":
            bpy.ops.object.camera_add()
            setup_obj()

        elif layer.type == "Sound":
            bpy.ops.object.speaker_add()
            setup_obj()

        elif layer.type == "Model":
            bpy.ops.object.empty_add(type='CUBE')
            setup_obj()

        elif layer.type == "Picture":
            bpy.ops.object.empty_add(type='IMAGE')
            setup_obj()

        elif layer.type == "Paint":
            bpy.ops.object.gpencil_add()
            setup_obj()

            # TODO: Convert quill paint strokes to grease pencil strokes.



        elif layer.type == "Group":

            # Create an empty to represent the group layer.
            bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0, 0, 0))
            setup_obj()

            obj = bpy.context.object
            for child in layer.implementation.children:
                self.import_layer(child, obj)

        else:
            raise logging.warning("Unsupported Quill layer type: %s", layer.type)


def load(operator, context, filepath="", **kwargs):
    """Load a Quill scene"""

    with QuillImporter(filepath, kwargs, operator) as importer:
        importer.import_scene(context)

    return {'FINISHED'}