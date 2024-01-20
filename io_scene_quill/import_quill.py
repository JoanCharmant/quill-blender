import os
import bpy
import json
import logging
from .model import sequence
from .importers import curves

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
        # TODO: support selecting any of: quill.json, state.json, .qbin or .zip.
        # For now assume the user selected quill.json.

        # Check if the file exists.
        if not os.path.exists(self.path):
            raise FileNotFoundError(f"File not found: {self.path}")

        # Load the scene graph.
        try:
            with open(self.path) as f:
                d = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to load JSON: {e}")

        quill_sequence = sequence.QuillSequence.from_dict(d)

        # Convert recursively from the root layer.
        self.import_layer(quill_sequence.sequence.root_layer)

    def import_layer(self, layer, parent=None):

        logging.info("Importing Quill layer: %s (%s).", layer.name, layer.type)

        # Basic configuration of the resulting Blender object, common to all layer types.
        def setup_obj():
            obj = bpy.context.object
            obj.name = layer.name
            obj.parent = parent
            obj.hide_set(not layer.visible) # disable in viewport.
            obj.hide_render = not layer.visible

            # TODO: transform.

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

        elif layer.type == "Group":

            # Create an empty to represent the group layer.
            bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0, 0, 0))
            setup_obj()

            obj = bpy.context.object
            for child in layer.implementation.children:
                self.import_layer(child, obj)


def load(operator, context, filepath="", **kwargs):
    """Load a Quill scene"""

    with QuillImporter(filepath, kwargs, operator) as importer:
        importer.import_scene(context)

    return {'FINISHED'}