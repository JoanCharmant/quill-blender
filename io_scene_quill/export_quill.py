
import os
import bpy
import json
import logging
import mathutils
from math import degrees, radians
from .model import paint, quill_utils, state, sequence
from .exporters import paint_armature, paint_gpencil, paint_wireframe, utils

class QuillExporter:
    """Handles picking what nodes to export and kicks off the export process"""

    def __init__(self, path, kwargs, operator):
        self.path = path
        self.operator = operator
        self.scene = bpy.context.scene
        self.config = kwargs
        self.config["path"] = path

        self.quill_scene = None
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
        scene = quill_utils.create_scene()
        root_layer = scene.sequence.root_layer
        viewpoint_layer = root_layer.implementation.children[0]
        viewpoint_layer.visible = False
        self.quill_scene = scene

        # Create a default application state.
        # Note: this references a "Root/Paint" layer that doesn't exist yet.
        self.quill_state = quill_utils.create_state()

        # Convert from Blender model to Quill’s.
        self.export_scene()

        # Create a folder at the target location instead of using the provided filename.
        file_dir = os.path.dirname(self.path)
        file_name = os.path.splitext(os.path.basename(self.path))[0].strip()
        folder_path = os.path.join(file_dir, file_name)
        os.makedirs(folder_path, exist_ok=True)

        quill_utils.export_scene(folder_path, self.quill_scene, self.quill_state)

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
        root_layer = self.quill_scene.sequence.root_layer
        for obj in self.scene.objects:
            if obj in self.exporting_objects and obj.parent is None:
                self.export_object(obj, root_layer)

        # Remove empty hierarchies if needed.
        if self.config["use_non_empty"]:
            quill_utils.delete_empty_groups(root_layer)

        if memo_edit_mode:
            bpy.ops.object.editmode_toggle()

    def should_export_object(self, obj):

        # Always include empties as they are used for grouping.
        # We then have a second pass at the end to remove empty groups if needed.
        if obj.type != "EMPTY" and obj.type not in self.config["object_types"]:
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
        """Export one object and its children."""

        if obj not in self.exporting_objects:
            return

        logging.info("Exporting Blender object: %s", obj.name)

        memo_active = bpy.context.view_layer.objects.active
        bpy.context.view_layer.objects.active = obj

        # Note: Quill only supports uniform scaling.
        # If the object has non-uniform scaling the user should have manually applied scale before export.
        # The rest of the code will assume the scale is uniform and use scale[0] as a proxy.
        if (obj.scale.x != obj.scale.y or obj.scale.y != obj.scale.z):
            logging.warning("Non-uniform scaling not supported. Please apply scale on %s.", obj.name)

        if obj.type == "EMPTY":
            layer = quill_utils.create_group_layer(obj.name)
            self.setup_layer(layer, obj, parent_layer)
            self.animate_layer(layer, obj)

            for child in obj.children:
                self.export_object(child, layer)

        elif obj.type == "MESH":
            layer = paint_wireframe.convert(obj, self.config)
            self.setup_layer(layer, obj, parent_layer)
            self.animate_layer(layer, obj)

        elif obj.type == "CAMERA":
            layer = quill_utils.create_camera_layer(obj.name)

            # FOV.
            # FIXME: FOV is not quite right.
            # Blender uses a customisable sensor size and sensor fit system.
            # Quill is based on a fixed sensor size of 24mm and only stores the FOV (in degrees),
            # and is independent of the image aspect ratio.
            fov = obj.data.angle * (24/36)
            layer.implementation.fov = degrees(fov)
            self.setup_layer(layer, obj, parent_layer, is_camera=True)
            self.animate_layer(layer, obj, is_camera=True)

        elif obj.type == "GPENCIL" or obj.type == "GREASEPENCIL":
            layer = paint_gpencil.convert(obj, self.config)
            self.setup_layer(layer, obj, parent_layer)
            self.animate_layer(layer, obj)

        elif obj.type == "ARMATURE":
            layer = paint_armature.convert(obj, self.config)
            self.setup_layer(layer, obj, parent_layer)

        bpy.context.view_layer.objects.active = memo_active

    def setup_layer(self, layer, obj, parent_layer, is_camera=False):
        """Common setup for all layers."""

        if layer is None:
            return

        layer.transform = self.get_transform(obj, is_camera)
        parent_layer.implementation.children.append(layer)

    def animate_layer(self, layer, obj, is_camera=False):
        """Layer level animation with transform key frames."""

        if layer is None:
            return

        # Approach: loop through blender frames and create a key frame at each frame.
        # This way we get all the drivers, modifiers and interpolation baked in
        # without having to drill down the F-curves channels and interpret everything.
        scn = bpy.context.scene
        fps = scn.render.fps
        frame_start = max(scn.frame_start, 0)
        frame_end = max(scn.frame_end, 0)
        time_base = 12600

        memo_current_frame = scn.frame_current
        previous_transform = layer.transform

        # Transform key frames.
        kktt = layer.animation.keys.transform
        for frame in range(frame_start, frame_end + 1):

            scn.frame_set(frame)
            transform = self.get_transform(obj, is_camera)

            # Don't create a kf if we are still on the same tranform.
            if transform != previous_transform:
                # If we do create it, create it with constant interpolation:
                # any interpolation on blender side is already accounted for from the
                # fact that we test every frame for changes. The only remaning case is a frame-hold.
                time = int((frame / fps) * time_base)
                keyframe = sequence.Keyframe("None", time, transform)
                kktt.append(keyframe)
                previous_transform = transform

        # Restore the active frame
        scn.frame_set(memo_current_frame)

    def get_transform(self, obj, is_camera):
        """Get the object's transform at the current frame, in Quill space."""
        if is_camera:
            # Special setup.
            # Blender camera identity pose looks down (negative Z axis).
            # Rotate by 90° around X axis to match Quill.
            mat = obj.matrix_local @ mathutils.Matrix.Rotation(- radians(90), 4, 'X')
            translation, rotation, scale, flip = utils.convert_transform(mat)
            # Apply extra scale based on the "display size" of the camera
            # Camera > Viewport Display > Size (cm).
            scale *= obj.data.display_size
            transform = sequence.Transform(flip, list(rotation), scale[0], list(translation))
        else:
            translation, rotation, scale, flip = utils.convert_transform(obj.matrix_local)
            transform = sequence.Transform(flip, list(rotation), scale[0], list(translation))

        return transform



def save(operator, filepath="", **kwargs):
    """Begin the export"""

    with QuillExporter(filepath, kwargs, operator) as exp:
        exp.export()

    return {'FINISHED'}




