import os
import bpy
import json
import logging
import mathutils
from math import floor, radians
from .importers import gpencil_paint, mesh_material, mesh_paint
from .model import paint, quill_utils, sequence

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
        scene_path = os.path.join(file_dir, "Quill.json")
        qbin_path = os.path.join(file_dir, "Quill.qbin")

        # Check if the files exist.
        if not os.path.exists(scene_path) or not os.path.exists(qbin_path):
            raise FileNotFoundError(f"File not found.")

        include_hidden = self.config["load_hidden_layers"]
        include_cameras = self.config["load_cameras"]
        quill_scene = quill_utils.import_scene(scene_path, qbin_path, include_hidden, include_cameras)

        # Reset the context.
        # Should we backup and restore afterwards?
        if bpy.context.object:
            bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

        bpy.ops.object.select_all(action='DESELECT')
        bpy.context.scene.frame_set(1)

        # Create the shared material.
        self.material = None
        if self.config["convert_paint"] == "MESH":
            self.material = mesh_material.create_principled("vertex.colors")

        # Import/convert layers to Blender objects.
        root_layer = quill_scene.sequence.root_layer
        self.import_layer(root_layer, 0)
        bpy.context.view_layer.update()

    def import_layer(self, layer, offset, parent_layer=None, parent_obj=None):

        logging.info("Importing Quill layer: %s (%s).", layer.name, layer.type)

        if layer.type == "Group":

            # Group layers are converted to empty objects.
            # Since Blender doesn't inherit visibility, hidden layers will be visible.
            # The user can choose to not import these layers at all from the importer configuration.
            bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0, 0, 0))
            self.setup_obj(layer, parent_layer, parent_obj)
            self.setup_animation(layer, offset)

            # If we are a sequence the times of children are relative to our start point.
            if layer.animation.timeline:
                kkvv = layer.animation.keys.visibility
                if kkvv and len(kkvv) > 0:
                    offset += kkvv[0].time

            obj = bpy.context.object
            for child in layer.implementation.children:
                self.import_layer(child, offset, layer, obj)

            # Apply a 90° rotation on the root object to match Blender coordinate system.
            if parent_layer is None:
                mat_rot = mathutils.Matrix.Rotation(radians(90.0), 4, 'X')
                obj.matrix_local = mat_rot @ obj.matrix_local

        elif layer.type == "Paint":
            # Quill paint layers are converted to Mesh objects or Grease Pencil objects.

            if self.config["convert_paint"] == "MESH":
                # Create a container obj and add the drawings to it.
                bpy.ops.object.empty_add(type='PLAIN_AXES')
                self.setup_obj(layer, parent_layer, parent_obj)
                self.setup_animation(layer, offset)
                obj = bpy.context.object
                mesh_paint.convert(self.config, obj, layer, self.material)

            elif self.config["convert_paint"] == "GPENCIL" or self.config["convert_paint"] == "GREASEPENCIL":

                if bpy.app.version < (4, 3, 0):
                    bpy.ops.object.gpencil_add()
                else:
                    bpy.ops.object.grease_pencil_add()

                self.setup_obj(layer, parent_layer, parent_obj)
                self.setup_animation(layer, offset)
                gpencil_paint.convert(bpy.context.object, layer)

        elif layer.type == "Viewpoint":
            bpy.ops.object.camera_add()
            self.setup_obj(layer, parent_layer, parent_obj)
            self.setup_animation(layer, offset, False)

        elif layer.type == "Camera":
            bpy.ops.object.camera_add()
            layer.transform.scale = 1.0
            self.setup_obj(layer, parent_layer, parent_obj)
            self.setup_animation(layer, offset, False)
            obj = bpy.context.object
            # FIXME FOV isn't an exact match between Quill and Blender.
            obj.data.lens_unit = 'FOV'
            obj.data.angle = radians(layer.implementation.fov)

        elif layer.type == "Sound":
            bpy.ops.object.speaker_add()
            layer.transform.scale = 1.0
            self.setup_obj(layer, parent_layer, parent_obj)
            self.setup_animation(layer, offset, False)

        elif layer.type == "Model":
            bpy.ops.object.empty_add(type='CUBE')
            self.setup_obj(layer, parent_layer, parent_obj)
            self.setup_animation(layer, offset, False)

        elif layer.type == "Picture":
            bpy.ops.object.empty_add(type='IMAGE')
            self.setup_obj(layer, parent_layer, parent_obj)
            self.setup_animation(layer, offset, False)
            obj = bpy.context.object
            
            # Quill stores both the image data and the original path.
            # We just support the path for now, so the image has to be on disk.
            # Note: some characters in the file path may be unsupported like em dash.
            filepath = layer.implementation.import_file_path
            if not os.path.exists(filepath):
                logging.warning("Image file not found: %s", filepath)
                obj.show_name = True
                return

            # Load the image.
            img = bpy.data.images.load(filepath, check_existing=False)
            obj.data = img
            
            # To get the correct size we need to do some shenanigans.
            # This was found by trial and error with images of various aspect ratio.
            # The correct size is twice the aspect ratio for landscape images,
            # and for portrait images the aspect ratio is aliased to 1.0.
            aspect_ratio = img.size[0] / img.size[1]
            aspect_ratio = max(1.0, aspect_ratio)
            obj.empty_display_size = aspect_ratio * 2.0

        else:
            logging.warning("Unsupported Quill layer type: %s", layer.type)

    def setup_obj(self, layer, parent_layer=None, parent_obj=None):
        """Basic configuration of the resulting Blender object, common to all layer types."""
        obj = bpy.context.object
        obj.name = layer.name
        obj.parent = parent_obj
        obj.matrix_local = self.get_transform(layer.transform)
        # TODO: pivot.

        # Visibility inheritance.
        # In Quill if the parent group is hidden the whole subtree is hidden,
        # even if the individual layers are marked as visible.
        # In Blender each object has its own visibility independent of the parent.
        # At the moment we don't have a satisfying way to handle this so we just
        # ignore visibility for hidden groups and let the user manually fix it.

    def get_transform(self, t):
        """Convert a Quill transform to a Blender matrix."""

        if isinstance(t, list):
            # Old-style transform from before Quill 1.7 (circa 2018).
            return mathutils.Matrix((t[0:4], t[4:8], t[8:12], t[12:16]))
        else:
            loc = mathutils.Vector((t.translation[0], t.translation[1], t.translation[2]))
            quat = mathutils.Quaternion((t.rotation[3], t.rotation[0], t.rotation[1], t.rotation[2]))
            scale = mathutils.Vector((t.scale, t.scale, t.scale))
            mat = mathutils.Matrix.LocRotScale(loc, quat, scale)
            if t.flip == "X":
                return mat @ mathutils.Matrix.Scale(-1, 4, (1, 0, 0))
            elif t.flip == "Y":
                return mat @ mathutils.Matrix.Scale(-1, 4, (0, 1, 0))
            elif t.flip == "Z":
                return mat @ mathutils.Matrix.Scale(-1, 4, (0, 0, 1))
            else:
                return mat

    def setup_animation(self, layer, offset, do_scale=True):
        """Setup the animation of the object."""

        # Key frame times are stored relative to the parent Sequence.
        # Bare groups do not alter the time of their children.
        # Quill uses a time base of 1/12600 (nicely divisible).
        # Never animate visibility since Blender doesn't inherit visibility.
        # We will handle it while importing the leaf layers.
        self.animate_transform(layer, offset, do_scale)

    def animate_transform(self, layer, offset=0, do_scale=True):

        # Transform key frames.
        # This is set up on all layer types, including groups.
        kktt = layer.animation.keys.transform
        if kktt == None or len(kktt) == 0:
            return

        obj = bpy.context.object
        fps = bpy.context.scene.render.fps
        time_base = 1/12600

        # Create the key frames.
        for key in kktt:
            time = key.time + offset
            frame = floor(time * time_base * fps + 0.5)

            # Name of the channels is from the F-Curve panel in the Graph Editor.
            obj.matrix_local = self.get_transform(key.value)
            obj.keyframe_insert(data_path="location", frame=frame)
            obj.keyframe_insert(data_path="rotation_euler", frame=frame)
            if do_scale:
                obj.keyframe_insert(data_path="scale", frame=frame)

        # Go through the key frames we just created and set the interpolation type.
        # https://docs.blender.org/api/current/bpy.types.Keyframe.html
        for fcurve in obj.animation_data.action.fcurves:
            for i in range(len(fcurve.keyframe_points)):
                keyframe = fcurve.keyframe_points[i]
                interp, easing = self.get_interpolation(kktt[i].interpolation)
                keyframe.interpolation = interp
                keyframe.easing = easing

    def get_interpolation(self, interpolation):
        """Convert Quill interpolation to Blender f-curve interpolation"""
        if interpolation == "None":
            return 'CONSTANT', 'AUTO'
        elif interpolation == "Linear":
            return 'LINEAR', 'AUTO'
        elif interpolation == "EaseIn":
            return 'CUBIC', 'EASE_IN'
        elif interpolation == "EaseOut":
            return 'CUBIC', 'EASE_OUT'
        elif interpolation == "EeaseInOut":
            return 'CUBIC', 'EASE_IN_OUT'
        else:
            return 'LINEAR', 'AUTO'


def load(operator, context, filepath="", **kwargs):
    """Load a Quill scene"""

    with QuillImporter(filepath, kwargs, operator) as importer:
        importer.import_scene(context)

    return {'FINISHED'}