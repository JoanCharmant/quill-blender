import os
import bpy
import logging
import mathutils
from math import floor, radians
from .importers import gpencil_paint, mesh_material, mesh_paint, curve_paint, sound_sound
from .model import quill_utils
from .utils import timeline

class QuillImporter:

    def __init__(self, path, kwargs, operator):
        self.path = os.path.dirname(path)
        self.config = kwargs

        self.material = None
        self.next_empty_channel = -1

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        pass

    def import_scene(self):

        # Import the Quill scene to memory, including scene graph and drawing data.
        quill_scene = quill_utils.import_scene(self.path, self.config["layer_types"], self.config["only_visible"], self.config["only_non_empty"])

        # Deselect everything.
        for obj in bpy.context.view_layer.objects:
            obj.select_set(False)

        #bpy.context.scene.frame_set(1)

        # Find the last visible frame to extend the Blender timeline.
        # This is commented out for now since it may result in very long loading times.
        # ticks_per_second = 12600
        # ticks_per_frame = int(ticks_per_second / quill_scene.sequence.framerate)
        # frame_end = quill_utils.find_last_visible_frame(quill_scene.sequence.root_layer, ticks_per_frame)
        # if (frame_end > 0 and frame_end > bpy.context.scene.frame_end):
        #     logging.info("Extending Blender timeline to frame %d.", frame_end)
        #     bpy.context.scene.frame_end = frame_end

        # Create the shared material.
        self.material = None
        if self.config["convert_paint"] == "MESH":
            self.material = mesh_material.create_principled("vertex.colors")

        # Import/convert layers to Blender objects.
        root_layer = quill_scene.sequence.root_layer
        self.import_layer(root_layer, 0)
        bpy.context.view_layer.update()

        # Configure 3D viewport solid shading to match Quill.
        if self.config["configure_shading"]:
            # Solid shading
            for area in bpy.context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.spaces[0].shading.light = 'FLAT'
                    area.spaces[0].shading.color_type = 'VERTEX'
                    area.spaces[0].shading.background_type = 'VIEWPORT'
                    area.spaces[0].shading.background_color = quill_scene.sequence.background_color
                    area.spaces[0].shading.show_object_outline = False

            # View transform to standard.
            bpy.context.scene.view_settings.view_transform = 'Standard'


    def import_layer(self, layer, offset, parent_layer=None, parent_obj=None, layer_path=""):

        logging.info("Importing Quill layer: %s (%s).", layer.name, layer.type)

        if layer.type == "Group":

            # Group layers are converted to empty objects.
            obj = bpy.data.objects.new(layer.name, None)
            self.setup_obj(obj, layer, parent_obj, layer_path)
            self.setup_animation(obj, layer, offset)

            # If we are a sequence the times of children are relative to our start point.
            if layer.animation.timeline:
                kkvv = layer.animation.keys.visibility
                if kkvv and len(kkvv) > 0:
                    offset += kkvv[0].time

            for child in layer.implementation.children:
                layer_path = layer_path + "/" + layer.name
                self.import_layer(child, offset, layer, obj, layer_path)

            # Apply a 90° rotation on the root object to match Blender coordinate system.
            if parent_layer is None:
                mat_rot = mathutils.Matrix.Rotation(radians(90.0), 4, 'X')
                obj.matrix_local = mat_rot @ obj.matrix_local

        elif layer.type == "Paint":

            # Quill paint layers are converted to Mesh, Grease Pencil or Curves.

            if self.config["convert_paint"] == "MESH":

                use_keymesh = hasattr(parent_obj, "keymesh")

                # For Keymesh, create a mesh object that will become the Keymesh mesh.
                # Otherwise create an Empty that will become the parent of the individual drawings.
                data = None
                if use_keymesh:
                    data = bpy.data.meshes.new(layer.name)

                obj = bpy.data.objects.new(layer.name, data)
                self.setup_obj(obj, layer, parent_obj, layer_path)
                self.setup_animation(obj, layer, offset)

                # Import the drawings and animate them.
                mesh_paint.convert(self.config, obj, layer, self.material, use_keymesh)

            elif self.config["convert_paint"] == "GPENCIL" or self.config["convert_paint"] == "GREASEPENCIL":

                data = None
                if bpy.app.version < (4, 3, 0):
                    data = bpy.data.grease_pencils.new(layer.name)
                elif bpy.app.version < (5, 0, 0):
                    data = bpy.data.grease_pencils_v3.new(layer.name)
                else:
                    data = bpy.data.grease_pencils.new(layer.name)

                obj = bpy.data.objects.new(layer.name, data)
                self.setup_obj(obj, layer, parent_obj, layer_path)
                self.setup_animation(obj, layer, offset)

                gpencil_paint.convert(obj, layer)

            elif self.config["convert_paint"] == "CURVE":

                data = bpy.data.curves.new(layer.name, type='CURVE')
                obj = bpy.data.objects.new(layer.name, data)
                self.setup_obj(obj, layer, parent_obj, layer_path)
                self.setup_animation(obj, layer, offset)

                curve_paint.convert(obj, layer)

        elif layer.type == "Viewpoint":

            layer.transform.scale = 1.0

            data = bpy.data.cameras.new(name=layer.name)
            obj = bpy.data.objects.new(layer.name, data)
            self.setup_obj(obj, layer, parent_obj, layer_path)
            self.setup_animation(obj, layer, offset, False)

            # There is no FOV info in viewpoint layers as they are for VR viewing.
            # Set the FOV to a relatively large value to simulate a wide angle lens.
            data.lens_unit = 'FOV'
            data.angle = radians(90.0)

        elif layer.type == "Camera":

            layer.transform.scale = 1.0

            data = bpy.data.cameras.new(name=layer.name)
            obj = bpy.data.objects.new(layer.name, data)
            self.setup_obj(obj, layer, parent_obj, layer_path)
            self.setup_animation(obj, layer, offset, False)

            # FIXME FOV isn't an exact match between Quill and Blender.
            data.lens_unit = 'FOV'
            data.angle = radians(layer.implementation.fov)

        elif layer.type == "Sound":


            # TODO: handle hidden sound layers properly.
            # TODO: handle scaling in a way that reproduce the Quill gizmo size.
            # TODO: link sound strip to speaker object.
            #layer.transform.scale = 1.0

            # For now it's not clear if it's possible to link the sound strip to the speaker object.
            # The speaker object lets us see where the sound is in space and how it is animated.
            # The sound strip lets us start the sound at the correct time.
            # For this first implementation we favor the sound strip to work on lip sync.

            # Create the speaker object.
            data = bpy.data.speakers.new(name=layer.name)
            obj = bpy.data.objects.new(layer.name, data)
            self.setup_obj(obj, layer, parent_obj, layer_path)
            self.setup_animation(obj, layer, offset, False)

            # Quill stores both the data in Qbin and the file path in JSON.
            # If we don't find the file on disk try to extract it from the QBin data.
            file_path = layer.implementation.import_file_path

            if not os.path.exists(file_path):
                # Look for the .wav file in the Quill project folder
                # in case we extracted it earlier.
                file_name = os.path.basename(layer.implementation.import_file_path)
                file_name = os.path.splitext(file_name)[0] + ".wav"
                file_path = os.path.join(self.path, file_name)

            if not os.path.exists(file_path):
                # Still not found, extract the data from the Qbin.
                qbin_path = os.path.join(self.path, "Quill.qbin")
                qbin = open(qbin_path, "rb")
                data_file_offset = layer.implementation.data_file_offset
                sound_data = quill_utils.read_sound_data(qbin, data_file_offset)
                qbin.close()
                if sound_data:
                    quill_utils.export_sound_data(sound_data, file_path)

            if not os.path.exists(file_path):
                # Still not found, bail out.
                logging.warning("Audio file not found: %s", file_path)
                obj.show_name = True
                return

            # We don't actually set the sound on the speaker data.
            # Everything is handled through the sound strip in the Video Sequence Editor.
            #sound = bpy.data.sounds.load(filepath, check_existing=False)
            #obj.data.sound = sound

            # Create a sound strip in the Video Sequence Editor on a new channel.
            # Find the next empty channel.
            sequencer_scene = None
            strips = None
            if bpy.app.version < (5, 0, 0):
                sequencer_scene = bpy.context.scene
                strips = sequencer_scene.sequence_editor.sequences_all
            else:
                if bpy.context.workspace.sequencer_scene is None:
                    bpy.context.workspace.sequencer_scene = bpy.context.scene

                sequencer_scene = bpy.context.workspace.sequencer_scene
                strips = sequencer_scene.sequence_editor.strips_all

            if len(strips) == 0:
                self.next_empty_channel = 1
            elif self.next_empty_channel == -1:
                max_channel = max((strip.channel for strip in strips))
                self.next_empty_channel = max_channel + 1
            else:
                self.next_empty_channel += 1

            sound_sound.convert(layer, file_path, sequencer_scene, self.next_empty_channel)

        elif layer.type == "Model":

            obj = bpy.data.objects.new(layer.name, None)
            obj.empty_display_type = 'CUBE'
            self.setup_obj(obj, layer, parent_obj, layer_path)
            self.setup_animation(obj, layer, obj, offset, False)

        elif layer.type == "Picture":

            # Start by creating an empty, we'll load image data into it if possible.
            obj = bpy.data.objects.new(layer.name, None)
            obj.empty_display_type = 'IMAGE'
            self.setup_obj(obj, layer, parent_obj, layer_path)
            self.setup_animation(obj, layer, offset, False)

            # Load the image data.
            # Quill stores both the data in Qbin and the file path in JSON.
            # We just support the path for now, so the file has to be on disk.
            # Note: some characters in the file path may be unsupported like em dash.
            file_path = layer.implementation.import_file_path
            if not os.path.exists(file_path):
                logging.warning("Image file not found: %s", file_path)
                obj.show_name = True
                return

            image_data = bpy.data.images.load(file_path, check_existing=False)
            obj.data = image_data

            # To get the correct size we need to do some shenanigans.
            # This was found by trial and error with images of various aspect ratio.
            # The correct size is twice the aspect ratio for landscape images,
            # and for portrait images the aspect ratio is aliased to 1.0.
            aspect_ratio = image_data.size[0] / image_data.size[1]
            aspect_ratio = max(1.0, aspect_ratio)
            obj.empty_display_size = aspect_ratio * 2.0

        else:
            logging.warning("Unsupported Quill layer type: %s", layer.type)

    def setup_obj(self, obj, layer, parent_obj=None, layer_path=""):
        """
        Configure the Blender object representing the Quill layer, common to all layer types.
        """

        bpy.context.collection.objects.link(obj)
        obj.parent = parent_obj
        obj.matrix_local = self.get_transform(layer.transform)
        # TODO: pivot.

        # Store a reference to the original Quill project and layer.
        # This is used during export, to swap back the original Quill data.
        obj.quill.active = True
        obj.quill.scene_path = self.path
        obj.quill.layer_path = layer_path + "/" + layer.name

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

    def setup_animation(self, obj, layer, offset, do_scale=True):
        """Setup the animation of the object."""

        # Quill has several types of key frames.
        # Visibility and Offset key frames are used for clips and spans.
        # Opacity key frames are used for fading layers in and out, not supported.
        # Transform key frames are supported.
        self.animate_transform(obj, layer, offset, do_scale)

    def animate_transform(self, obj, layer, offset=0, do_scale=True):

        # Transform key frames.
        # This is set up on all layer types, including groups.
        # This only handles the base animation for now, not looping and clips.
        kktt = layer.animation.keys.transform
        if kktt == None or len(kktt) == 0:
            return

        fps = bpy.context.scene.render.fps
        time_base = 1/12600

        # First pass, create the key frames with default interpolation.
        for key in kktt:
            time = key.time + offset
            frame = floor(time * time_base * fps + 0.5)

            # Set the object transform for this key frame.
            obj.matrix_local = self.get_transform(key.value)

            # Insert the key frame.
            # Name of the channels is from the F-Curve panel in the Graph Editor.
            obj.keyframe_insert(data_path="location", frame=frame)
            obj.keyframe_insert(data_path="rotation_euler", frame=frame)
            if do_scale:
                obj.keyframe_insert(data_path="scale", frame=frame)

        # Second pass, set the interpolation.
        # Note that we change the interpolation of every f-curve on the object.
        # This will work as long as these are the first key frames set on the object.
        # This approach makes it simpler to find all the axes at once and avoid
        # scanning all the previous key frame for each key frame.
        fcurves = None
        if bpy.app.version < (5, 0, 0):
            fcurves = obj.animation_data.action.fcurves
        else:
            channelbag = timeline.ensure_channelbag(obj)
            fcurves = channelbag.fcurves

        for fcurve in fcurves:
            for i in range(len(fcurve.keyframe_points)):
                kp = fcurve.keyframe_points[i]
                interp, easing = self.get_interpolation(kktt[i].interpolation)
                kp.interpolation = interp
                kp.easing = easing

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


def load(operator, filepath="", **kwargs):

    with QuillImporter(filepath, kwargs, operator) as importer:
        try:
            importer.import_scene()
        except Exception as e:
            operator.report({'ERROR'}, f"Failed to import Quill scene: {str(e)}")
            return {'CANCELLED'}

    return {'FINISHED'}