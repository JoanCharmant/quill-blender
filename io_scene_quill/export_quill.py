
import os
import bpy
import json
import logging
from .model import sequence, state, paint
from .exporters import paint_wireframe, paint_armature, paint_gpencil, utils

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

        # Create a folder at the target location instead of using the provided filename.
        file_dir = os.path.dirname(self.path)
        file_name = os.path.splitext(os.path.basename(self.path))[0]
        folder_path = os.path.join(file_dir, file_name)
        os.makedirs(folder_path, exist_ok=True)

        # Write qbin file.
        # This will also update the data_file_offset fields in the drawing data.
        qbin_path = os.path.join(folder_path, "Quill.qbin")
        self.qbin = open(qbin_path, 'wb')
        paint.write_header(self.qbin)
        self.write_drawing_data(root_layer)
        self.qbin.close()

        # Write the scene graph and application state files.
        self.write_json(self.quill_sequence.to_dict(), folder_path, "Quill.json")
        self.write_json(self.quill_state.to_dict(), folder_path, "State.json")

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

        if obj.type not in self.config["object_types"]:
            return False

        if self.config["use_selection"] and not obj.select_get():
            return False

        if self.config["use_visible"]:
            view_layer = bpy.context.view_layer
            if obj.name not in view_layer.objects:
                return False
            if not obj.visible_get():
                return False

        return True

    def export_object(self, obj, parent_layer):

        if obj not in self.exporting_objects:
            return

        logging.info("Exporting Blender object: %s", obj.name)

        memo_active = bpy.context.view_layer.objects.active
        bpy.context.view_layer.objects.active = obj

        # Note: Quill only supports uniform scaling.
        # If the object has non-uniform scaling the user should have manually applied scale
        # before export or checked the "Apply transforms" option.
        # The rest of the code will assume the scale is uniform and use scale[0] as a proxy.
        if (obj.scale.x != obj.scale.y or obj.scale.y != obj.scale.z):
            logging.warning("Non-uniform scaling not supported. Please apply scale on %s.", obj.name)

        if obj.type == "EMPTY":
            layer = sequence.Layer.create_group_layer(obj.name)
            self.setup_layer(layer, obj, parent_layer)

            for child in obj.children:
                self.export_object(child, layer)

        elif obj.type == "MESH":
            layer = paint_wireframe.convert(obj, self.config)
            self.setup_layer(layer, obj, parent_layer)

        elif obj.type == "CAMERA":
            layer = sequence.Layer.create_viewpoint_layer(obj.name)
            self.setup_layer(layer, obj, parent_layer)

        elif obj.type == "GPENCIL":
            layer = paint_gpencil.convert(obj, self.config)
            self.setup_layer(layer, obj, parent_layer)

        elif obj.type == "ARMATURE":
            layer = paint_armature.convert(obj, self.config)
            self.setup_layer(layer, obj, parent_layer)

        bpy.context.view_layer.objects.active = memo_active

    def setup_layer(self, layer, obj, parent_layer):
        """Common setup for all layers."""
        layer.transform = self.get_transform(obj.matrix_local)
        parent_layer.implementation.children.append(layer)


    def write_drawing_data(self, layer):

        if layer.type == "Group":
            for child in layer.implementation.children:
                self.write_drawing_data(child)

        elif layer.type == "Paint":
            for drawing in layer.implementation.drawings:
                offset = hex(self.qbin.tell())[2:].upper().zfill(8)
                drawing.data_file_offset = offset
                paint.write_drawing_data(drawing.data, self.qbin)

    def write_json(self, obj, folder_path, file_name):
        encoded = json.dumps(obj, indent=4, separators=(',', ': '))
        file_path = os.path.join(folder_path, file_name)
        file = open(file_path, "w", encoding="utf8", newline="\n")
        file.write(encoded)
        file.write("\n")
        file.close()

    def get_transform(self, m):
        """Convert a Blender matrix to a Quill transform."""
        translation, rotation, scale = m.decompose()

        # Move from Blender to Quill coordinate system.
        translation = utils.swizzle_yup_location(translation)
        rotation = utils.swizzle_quaternion(utils.swizzle_yup_rotation(rotation))
        scale = utils.swizzle_yup_scale(scale)

        flip = "N"
        return sequence.Transform(flip, list(rotation), scale[0], list(translation))


def save(operator, filepath="", **kwargs):
    """Begin the export"""

    with QuillExporter(filepath, kwargs, operator) as exp:
        exp.export()

    return {'FINISHED'}




