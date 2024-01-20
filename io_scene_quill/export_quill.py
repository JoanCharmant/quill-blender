
import os
import bpy
import json
import logging
from .model import sequence
from .model import state
from .exporters import group, paint_wireframe

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

        self.exporting_objects = set()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        pass

    def export(self):
        """Begin the export"""

        # Create a default scene with a viewpoint and no paint layer.
        seq = sequence.quill_sequence_from_default()
        root_layer = seq.sequence.root_layer
        viewpoint_layer = root_layer.implementation.children[0]
        viewpoint_layer.visible = False
        self.quill_sequence = seq

        # Create a default application state.
        # Note: this references a "Root/Paint" layer that doesn't exist yet.
        self.quill_state = state.quill_state_from_default()

        # Convert from Blender model to Quill’s.
        self.export_scene()

        # TODO: create qbin, create paint layers, etc.
        # TESTING
        # paint_layer = sequence.Layer.create_paint_layer("Paint")
        # root_layer.implementation.children.append(paint_layer)
        # # Create a simple drawing.
        # # Reference the drawing from the paint layer.
        # bbox = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        # file_offset = "08"
        # drawing = sequence.Drawing.from_dict({
        #     "BoundingBox": bbox,
        #     "FileOffset": file_offset
        # })
        # paint_layer.implementation.drawings.append(drawing)
        # frame = "0"
        # paint_layer.implementation.frames.append(frame)


        # Write the Quill scene to disk.
        # Create a folder at the target location instead of using the provided filename.
        file_dir = os.path.dirname(self.path)
        file_name = os.path.splitext(os.path.basename(self.path))[0]
        folder_path = os.path.join(file_dir, file_name)
        os.makedirs(folder_path, exist_ok=True)
        self.write_sequence(folder_path)
        self.write_state(folder_path)
        self.write_qbin(folder_path)

    def export_scene(self):
        logging.info("Exporting scene: %s", self.scene.name)

        # Temporary toggle off edit mode if necessary.
        memo_edit_mode = False
        if bpy.context.object and bpy.context.object.mode == "EDIT":
            memo_edit_mode = True
            bpy.ops.object.editmode_toggle()

        # Decide which objects to export.
        for obj in self.scene.objects:
            if obj in self.exporting_objects:
                continue
            if self.should_export_object(obj):
                self.exporting_objects.add(obj)

        logging.info("Exporting %d objects", len(self.exporting_objects))

        # Loop over all objects in the scene and export them.
        root_layer = self.quill_sequence.sequence.root_layer
        for obj in self.scene.objects:
            if obj in self.exporting_objects and obj.parent is None:
                self.export_object(obj, root_layer)

        if memo_edit_mode:
            bpy.ops.object.editmode_toggle()

    def should_export_object(self, obj):
        """Checks if a node should be exported:"""

        if obj.type not in self.config["object_types"]:
            logging.info("Skipping object: %s (%s).", obj.name, obj.type)
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

    def export_object(self, obj, parent_layer):

        logging.info("Exporting Blender object: %s", obj.name)

        memo_active = bpy.context.view_layer.objects.active
        bpy.context.view_layer.objects.active = obj

        if obj not in self.exporting_objects:
            pass

        elif obj.type == "EMPTY":

            group_layer = group.convert(obj)
            parent_layer.implementation.children.append(group_layer)

            for child in obj.children:
                self.export_object(child, group_layer)

        elif obj.type == "MESH":

            paint_layer = paint_wireframe.convert(obj, self.config)
            parent_layer.implementation.children.append(paint_layer)


        elif obj.type == "ARMATURE":
            logging.warning("Armature object not yet supported.")

        bpy.context.view_layer.objects.active = memo_active

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


def save(operator, filepath="", **kwargs):
    """Begin the export"""

    with QuillExporter(filepath, kwargs, operator) as exp:
        exp.export()

    return {'FINISHED'}




