
import os
import bpy
import json
import logging
from .model.state import quill_state_from_default
from .model.sequence import quill_sequence_from_default

class QuillExporter:
    """Handles picking what nodes to export and kicks off the export process"""

    def __init__(self, path, kwargs, operator):
        self.path = path
        self.operator = operator
        self.scene = bpy.context.scene
        self.config = kwargs
        self.config["path"] = path

        self.quill_sequence = None
        self.quill_state = None
        self.quill_qbin = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        pass

    def export(self):
        """Begin the export"""

        # Create a default scene with a viewpoint and no paint layer.
        seq = quill_sequence_from_default()
        root_layer = seq.sequence.root_layer
        viewpoint_layer = root_layer.implementation.children[0]
        viewpoint_layer.visible = False
        self.quill_sequence = seq

        # Create a default application state.
        self.quill_state = quill_state_from_default()

        # Convert from Blender model to Quill.
        #self.export_scene()
        # TODO: create qbin, create paint layers, etc.

        # Write the Quill scene to disk.
        # Create a folder at the target location instead of using the provided filename.
        file_dir = os.path.dirname(self.path)
        file_name = os.path.splitext(os.path.basename(self.path))[0]
        folder_path = os.path.join(file_dir, file_name)
        os.makedirs(folder_path, exist_ok=True)

        self.write_sequence(folder_path)
        self.write_state(folder_path)
        self.write_qbin(folder_path)

    def write_sequence(self, folder_path):
        sequence = self.quill_sequence.to_dict()
        encoded = json.dumps(sequence, indent=4, separators=(',', ': '))

        file_name = "Quill.json"
        file_path = os.path.join(folder_path, file_name)
        file = open(file_path, "w", encoding="utf8", newline="\n")
        file.write(encoded)
        file.write("\n")
        file.close()

    def write_state(self, folder_path):
        state = self.quill_state.to_dict()
        encoded = json.dumps(state, indent=4, separators=(',', ': '))

        file_name = "State.json"
        file_path = os.path.join(folder_path, file_name)
        file = open(file_path, "w", encoding="utf8", newline="\n")
        file.write(encoded)
        file.write("\n")
        file.close()

    def write_qbin(self, folder_path):
        pass

    def should_export_object(self, obj):
        """Checks if a node should be exported:"""
        if obj.type not in self.config["object_types"]:
            return False
        if self.config["use_included_in_render"] and obj.hide_render:
            return False
        if self.config["use_visible_objects"]:
            view_layer = bpy.context.view_layer
            if obj.name not in view_layer.objects:
                return False
            if not obj.visible_get():
                return False

        if self.config["use_export_selected"] and not obj.select_get():
            return False

        return True

    def export_object(self, obj, parent_node):

        logging.info("Exporting Blender object: %s", obj.name)


def save(operator, filepath="", **kwargs):
    """Begin the export"""

    with QuillExporter(filepath, kwargs, operator) as exp:
        exp.export()

    return {'FINISHED'}




