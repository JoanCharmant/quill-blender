import os
import bpy
import logging
import mathutils
import numpy as np
from math import floor, radians
from .importers import animation, curve_paint, gpencil_paint, image_picture, mesh_material, mesh_paint, sound_sound
from .model import quill_utils
from .utils import timeline

class QuillImporter:

    def __init__(self, path, kwargs, operator):
        self.path = os.path.dirname(path)
        self.config = kwargs

        self.material = None
        self.next_empty_channel = -1
        self.lipsync_data = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        pass

    def import_scene(self):

        # Import the Quill scene to memory, including scene graph and drawing data.
        quill_scene = quill_utils.import_scene(self.path, self.config["layer_types"], self.config["only_visible"], self.config["only_non_empty"])

        # Copy lipsync data.
        if quill_scene.lipsync_data is not None and len(quill_scene.lipsync_data) > 0:
            logging.info("Found lipsync data for %d layers.", len(quill_scene.lipsync_data))
            self.lipsync_data = quill_scene.lipsync_data
        
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

        # Transform key frames are converted using the scene frame rate and frame range,
        # so these must match Quill before any layer is imported.
        # Paint layer importers would otherwise only change them after their parent groups are animated.
        scn = bpy.context.scene
        framerate = quill_scene.sequence.framerate
        if framerate:
            scn.render.fps = int(framerate)
            scn.render.fps_base = 1.0
        if self.config["transform_keys"] != "NONE":
            timeline.setup_frame_range(scn)

        # Create the shared material.
        self.material = None
        if self.config["convert_paint"] == "MESH":
            self.material = mesh_material.create_principled("vertex.colors")

        # Import/convert layers to Blender objects.
        root_layer = quill_scene.sequence.root_layer
        self.import_layer(root_layer, 0)
        bpy.context.view_layer.update()

        # Configure 3D viewport solid shading to match Quill.
        self.configure_viewport_shading(quill_scene)


    def import_layer(self, layer, offset, parent_layer=None, parent_obj=None, layer_path=""):

        logging.info("Importing Quill layer: %s (%s).", layer.name, layer.type)

        if layer.type == "Group":

            if layer.is_model_top_layer:
                # Special case for Model layers with multiple meshes (FBX).
                # The group itself doesn't have the path of the file but each 
                # children layer should have it.
                if layer.implementation.children and len(layer.implementation.children) > 0:
                    # Get the file path from the first child.
                    model_file_path = layer.implementation.children[0].implementation.import_file_path
                    self.import_model_layer_group(layer, model_file_path, offset, parent_obj, layer_path)
                else:
                    logging.warning("Model layer has no children: %s", layer.name)
                    self.import_model_layer_fallback(layer, offset, parent_obj, layer_path)
                    
                return

            # Group layers are converted to empty objects.
            obj = bpy.data.objects.new(layer.name, None)
            self.setup_obj(obj, layer, parent_obj, layer_path)

            # Rotate the root object by 90° to match the Blender coordinate system.
            # If the root is animated the rotation is baked into its key frames.
            correction = None
            if parent_layer is None:
                correction = mathutils.Matrix.Rotation(radians(90.0), 4, 'X')
            animated = self.setup_animation(obj, layer, offset, correction=correction)

            # If we are a sequence the times of children are relative to our start point.
            # FIXME: it's more complicated than that. Clips and loops in parent sequence layers
            # are restarting the timeline for children and the key frames should be duplicated
            # and adjusted accordingly.
            # It's not actually possible to handle everything with sparse key frames since a clip
            # may end in the middle of two key frames and the next clip restart before the next.
            # The following only handles the case where the first clip doesn't start at time 0.
            if layer.animation.timeline:
                kkvv = layer.animation.keys.visibility
                if kkvv and len(kkvv) > 0:
                    offset += kkvv[0].time

            for child in layer.implementation.children:
                child_layer_path = layer_path + "/" + layer.name
                self.import_layer(child, offset, layer, obj, child_layer_path)

            if correction is not None and not animated:
                obj.matrix_local = correction @ obj.matrix_local

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
                mesh_paint.convert(self.config, obj, layer, self.material, use_keymesh, self.lipsync_data)

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
                if layer.implementation.data:
                    quill_utils.export_sound_data(layer.implementation.data, file_path)

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

            # This is for handling Quill model layers that are imported from OBJ or 
            # from FBX with the option "Single Layer" checked in the importer dialog.
            # In this case the model is imported as a single layer with "IsModelTopLayer" : true property.
            # The other case is for FBX files with multiple meshes, these are imported as a group layer,
            # and are handled in the import_model_layer_group() function.
            
            # As for other asset types we have both the original file and the QBIN data to work with.
            # We give priority to the original file.
            # Note: Quill importer only supports FBX and OBJ files.
            file_path = layer.implementation.import_file_path
            model_data = None

            if file_path and os.path.isfile(file_path):
                ext = os.path.splitext(file_path)[1].lower()
    
                if ext == ".fbx":
                    bpy.ops.import_scene.fbx(filepath=file_path)
                    
                    # It's possible that the FBX file contains multiple meshes but was imported 
                    # in Quill as a single layer.
                    # In that case we revert to importing as a group.
                    if len(bpy.context.selected_objects) > 1:
                        logging.warning("FBX file contains multiple meshes but was imported as a single layer: %s", file_path)
                        self.import_model_layer_group(layer, file_path, offset, parent_obj, layer_path)
                        return
                    else:
                        obj = bpy.context.selected_objects[0]
                        self.setup_obj(obj, layer, parent_obj, layer_path)
                        self.setup_animation(obj, layer, offset)
                        return
                    
                elif ext == ".obj":

                    # Import an OBJ file as a single mesh.
                    bpy.ops.wm.obj_import(filepath=file_path)
                    
                    obj = bpy.context.selected_objects[0]
                    self.setup_obj(obj, layer, parent_obj, layer_path)
                    self.setup_animation(obj, layer, offset)
                    return
                else:
                    logging.warning("Unsupported model file format: %s", ext)
                    self.import_model_layer_fallback(layer, offset, parent_obj, layer_path)
                    return
                    
            
            # TODO: handle model data in Qbin if the original file is not available.
            logging.warning("Model file not found: %s", file_path)
            self.import_model_layer_fallback(layer, offset, parent_obj, layer_path)

        elif layer.type == "Picture":

            # Start by creating an empty, we'll load image data into it if possible.
            obj = bpy.data.objects.new(layer.name, None)
            obj.empty_display_type = 'IMAGE'
            self.setup_obj(obj, layer, parent_obj, layer_path)
            self.setup_animation(obj, layer, offset, False)

            # Prefer the original file, but fall back to the pixels in Qbin.
            file_path = layer.implementation.import_file_path or ""
            image_data = None

            if file_path and os.path.isfile(file_path):
                try:
                    image_data = bpy.data.images.load(file_path, check_existing=False)
                except (OSError, RuntimeError) as e:
                    logging.warning("Cannot load picture %s from disk: %s", file_path, e)

            # Bail out if loading from disk succeeded with a zero-sized image buffer.
            if image_data is not None and (image_data.size[0] == 0 or image_data.size[1] == 0):
                bpy.data.images.remove(image_data)
                image_data = None

            # If the original file is not available, try to recover the picture from the Qbin data.
            if image_data is None and layer.implementation.data is not None:
                try:
                    image_data = image_picture.convert(layer.name, layer.implementation.data)
                except (ValueError, RuntimeError, TypeError, MemoryError) as e:
                    logging.warning("Cannot decode Qbin picture %s: %s", layer.name, e)

            if image_data is None:
                logging.warning("Picture unavailable: %s (original: %s)", layer.name, file_path)
                obj.show_name = True
                return

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

        # Verify if the object already exists in the collection,
        # this can happen when importing model layers.
        if obj.name not in bpy.context.collection.objects:
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

    def setup_animation(self, obj, layer, offset, do_scale=True, correction=None):
        """
        Setup the animation of the object.
        Returns True if transform key frames were created.
        """

        # Quill has several types of key frames.
        # Visibility and Offset key frames are used for clips and spans.
        # Opacity key frames are used for fading layers in and out, not supported.
        # Transform key frames are imported as sparse key frames or baked on every frame.
        kktt = layer.animation.keys.transform
        if kktt is None or len(kktt) == 0:
            return False

        mode = self.config["transform_keys"]
        if mode == "KEYFRAMES":
            self.animate_transform(obj, layer, kktt, offset, do_scale, correction)
            return True
        elif mode == "BAKE":
            self.bake_transform(obj, layer, kktt, do_scale, correction)
            return True

        return False

    def animate_transform(self, obj, layer, kktt, offset=0, do_scale=True, correction=None):
        """
        Convert Quill transform key frames to Blender key frames, one for one.
        If a parent sequence loops the animation, one iteration is keyed and repeated with a Cycles modifier.
        Clips, offsets and nested loops can't be expressed with sparse key frames, these layers are baked.
        """

        mapping, duration = self.get_time_mapping(layer)

        keys = None
        if mapping == "LINEAR":
            keys = [(key.time, self.get_key_transform(key.value, do_scale, correction), key.interpolation) for key in kktt]
        elif mapping == "LOOP":
            keys = self.get_loop_keys(kktt, duration, do_scale, correction)

        if keys is None:
            logging.info("Baking transform key frames of %s, parent sequences use clips or offsets.", layer.name)
            self.bake_transform(obj, layer, kktt, do_scale, correction)
            return

        # Quill stores rotations as quaternions. Keying them directly avoids
        # the flips we get when converting each key to Euler angles independently.
        obj.rotation_mode = 'QUATERNION'

        fps = bpy.context.scene.render.fps
        time_base = 1/12600

        # First pass, create the key frames with default interpolation.
        # The following dict stores the Blender interpolation type for the Blender frame, to be applied in a second pass.
        # It keeps the last value in case multiple Quill keys land on the same Blender frame.
        frame_interpolation = {}
        previous_rot = None
        for time, (loc, rot, scale), interpolation in keys:
            frame = (time + offset) * time_base * fps
            if mapping == "LINEAR":
                frame = floor(frame + 0.5)

            if previous_rot is not None and rot.dot(previous_rot) < 0:
                rot = -rot
            previous_rot = rot

            self.insert_transform_key(obj, frame, loc, rot, scale, do_scale)
            frame_interpolation[round(frame, 3)] = self.get_interpolation(interpolation)

        # Second pass, set the interpolation.
        # Match Blender key frames to Quill keys by frame.
        for fcurve in timeline.get_fcurves(obj):
            if fcurve.data_path not in ("location", "rotation_quaternion", "scale"):
                continue
            for kp in fcurve.keyframe_points:
                interp = frame_interpolation.get(round(kp.co.x, 3))
                if interp is not None:
                    kp.interpolation, kp.easing = interp

            if mapping == "LOOP":
                cycles = fcurve.modifiers.new('CYCLES')
                cycles.mode_before = 'NONE'
                cycles.mode_after = 'REPEAT'

    def get_time_mapping(self, layer):
        """
        Find how the parent sequences remap the time of the layer transform key frames.
        Returns ("LINEAR", None) if time is only shifted, ("LOOP", duration) if a single
        parent sequence loops it, or ("COMPLEX", None) for clips, offsets and nested loops.
        Loops longer than the Blender timeline are ignored as they never wrap.
        This includes the root layer which loops every hour by default.
        """

        scn = bpy.context.scene
        timeline_ticks = (scn.frame_end - scn.frame_start + 1) * 12600 / scn.render.fps

        loop_duration = None
        shifted_inside_loop = False
        parent = layer.parent
        while parent is not None:
            anim = parent.animation
            kkvv = anim.keys.visibility
            if len(kkvv) > 1 or any(key.value != 0 for key in anim.keys.offset):
                return "COMPLEX", None

            if anim.timeline:
                looping = anim.max_repeat_count == 0 and 0 < anim.duration < timeline_ticks
                if looping:
                    if loop_duration is not None or shifted_inside_loop:
                        return "COMPLEX", None
                    loop_duration = anim.duration
                elif len(kkvv) == 1 and kkvv[0].time != 0 and loop_duration is None:
                    # A sequence starting late, below a potential loop.
                    shifted_inside_loop = True

            parent = parent.parent

        if loop_duration is None:
            return "LINEAR", None

        return "LOOP", loop_duration

    def get_loop_keys(self, kktt, duration, do_scale, correction):
        """
        Build the key frames of one iteration of a loop, from 0 to `duration`, closed with
        a copy of the first key. Returns None if the iteration can't be represented exactly,
        when the loop cuts a segment that is interpolating toward a key beyond the loop end.
        """

        if kktt[0].time < 0:
            return None

        inside = [key for key in kktt if key.time < duration]
        if len(inside) == 0:
            return None

        keys = []
        if inside[0].time > 0:
            # Quill holds the first key value from the start.
            keys.append((0, self.get_key_transform(inside[0].value, do_scale, correction), "None"))

        for key in inside:
            keys.append((key.time, self.get_key_transform(key.value, do_scale, correction), key.interpolation))

        # Check the last segment, it gets cut by the loop and restarts at the first value.
        first_value = keys[0][1]
        last = inside[-1]
        following = kktt[len(inside)] if len(inside) < len(kktt) else None
        if following is None:
            # Quill holds the last value until the loop restarts.
            keys[-1] = (keys[-1][0], keys[-1][1], "None")
        elif last.interpolation != "None":
            following_value = self.get_key_transform(following.value, do_scale, correction)
            if following.time != duration or not self.transform_equals(following_value, first_value):
                return None

        keys.append((duration, first_value, "None"))
        return keys

    def transform_equals(self, a, b, epsilon=1e-6):
        """Compare two (location, rotation, scale) tuples. Opposite quaternions are the same rotation."""
        loc_a, rot_a, scale_a = a
        loc_b, rot_b, scale_b = b
        if rot_a.dot(rot_b) < 0:
            rot_b = -rot_b
        return all(abs(x - y) < epsilon for va, vb in ((loc_a, loc_b), (rot_a, rot_b), (scale_a, scale_b)) for x, y in zip(va, vb))

    def bake_transform(self, obj, layer, kktt, do_scale=True, correction=None):
        """
        Sample the Quill transform animation on every frame of the Blender timeline.
        The transform key frames of a layer live in the timeline of its parent,
        so we resolve looping, clips and offsets of all the ancestors at each frame.
        Frame holds are collapsed to their first and last frames.
        """

        obj.rotation_mode = 'QUATERNION'

        scn = bpy.context.scene
        ticks_per_frame = int(12600 / scn.render.fps)

        # Lineage of ancestors, from the parent up to the root.
        stack = []
        parent = layer.parent
        while parent is not None:
            stack.append(parent)
            parent = parent.parent

        pivot = layer.pivot.translation if layer.pivot is not None else (0.0, 0.0, 0.0)
        pivot_loc = mathutils.Vector(pivot)
        
        # Sample the transform at every frame.
        # When a parent is hidden (between clips) hold the last value.
        samples = []
        current = None
        for frame in range(scn.frame_start, scn.frame_end + 1):
            visible, local_time = animation.get_local_time(stack, frame * ticks_per_frame, ticks_per_frame)
            if visible or current is None:
                time = local_time if visible else kktt[0].time
                loc, rot, scale = self.evaluate_transform(kktt, time, do_scale, pivot_loc, correction)
                if current is not None and rot.dot(current[1]) < 0:
                    rot.negate()
                current = (loc, rot, scale)
            samples.append((frame, current))

        def same(a, b):
            return all(abs(x - y) < 1e-6 for va, vb in zip(a, b) for x, y in zip(va, vb))

        last = len(samples) - 1
        for i, (frame, value) in enumerate(samples):
            if 0 < i < last and same(samples[i - 1][1], value) and same(value, samples[i + 1][1]):
                continue
            loc, rot, scale = value
            self.insert_transform_key(obj, frame, loc, rot, scale, do_scale)

        for fcurve in timeline.get_fcurves(obj):
            if fcurve.data_path in ("location", "rotation_quaternion", "scale"):
                for kp in fcurve.keyframe_points:
                    kp.interpolation = 'LINEAR'

    def evaluate_transform(self, kktt, time, do_scale, pivot, correction):
        """Evaluate Quill transform key frames at `time` (in ticks)."""

        if time <= kktt[0].time:
            return self.get_key_transform(kktt[0].value, do_scale, correction)

        # Note: the static transform at the layer level is always the same as the first key frame,
        # we can safely ignore it.
        
        for i in range(len(kktt) - 1):
            a = kktt[i]
            b = kktt[i + 1]
            if a.time <= time < b.time:
                
                # The interpolation of a key applies to the segment leaving it (same in Quill and Blender).
                u = self.ease(a.interpolation, (time - a.time) / (b.time - a.time))
                loc_a, rot_a, scale_a = self.get_key_transform(a.value, do_scale, correction)
                loc_b, rot_b, scale_b = self.get_key_transform(b.value, do_scale, correction)

                # Quill already accounts for the pivot in each key's translation.
                # However, interpolating these translations directly would cause
                # the layer to drift away from its pivot during rotation or scaling.
                # Instead, interpolate the transformed pivot position and reconstruct
                # the translation from the interpolated rotation and scale.
                # The pivot moves through space as the layer translation is animated.
                pivot_a = self.transformed_pivot(loc_a, rot_a, scale_a, pivot)
                pivot_b = self.transformed_pivot(loc_b, rot_b, scale_b, pivot)

                pivot_loc = pivot_a.lerp(pivot_b, u)
                rot = rot_a.slerp(rot_b, u)
                scale = scale_a.lerp(scale_b, u)

                # pivot is the static pivot position in the layer's local coordinates. It never changes.
                # pivot_loc is the interpolated position of that pivot in the parent's coordinate system, after applying the animated transform.
                # Find a translation loc that places the original pivot at pivot_loc, given the interpolated rotation and scale.
                loc = pivot_loc - rot @ (scale * pivot)
                
                return loc, rot, scale

        return self.get_key_transform(kktt[-1].value, do_scale, correction)

    def transformed_pivot(self, loc, rot, scale, pivot):
        return loc + rot @ (scale * pivot)

    def ease(self, interpolation, u):
        """Remap the normalized time `u` according to the Quill interpolation."""
        if interpolation == "None":
            return 0.0
        elif interpolation == "EaseIn":
            return u * u * u
        elif interpolation == "EaseOut":
            return 1.0 - (1.0 - u) ** 3
        elif interpolation == "Smoothstep":
            return u * u * (3.0 - 2.0 * u)
        else:
            return u

    def get_key_transform(self, transform, do_scale, correction):
        """Convert a Quill key frame transform to Blender location, rotation and scale."""
        mat = self.get_transform(transform)
        if correction is not None:
            mat = correction @ mat
        loc, rot, scale = mat.decompose()
        if not do_scale:
            scale = mathutils.Vector((1.0, 1.0, 1.0))
        return loc, rot, scale

    def insert_transform_key(self, obj, frame, loc, rot, scale, do_scale):
        # Name of the channels is from the F-Curve panel in the Graph Editor.
        obj.location = loc
        obj.rotation_quaternion = rot
        obj.keyframe_insert(data_path="location", frame=frame)
        obj.keyframe_insert(data_path="rotation_quaternion", frame=frame)
        if do_scale:
            obj.scale = scale
            obj.keyframe_insert(data_path="scale", frame=frame)
        else:
            obj.scale = (1.0, 1.0, 1.0)

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
        elif interpolation == "Smoothstep":
            return 'CUBIC', 'EASE_IN_OUT'
        else:
            return 'LINEAR', 'AUTO'

    def configure_viewport_shading(self, quill_scene):
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

    def import_model_layer_fallback(self, layer, offset, parent_obj, layer_path):

        # Fallback function when importing a model layer for which we couldn't reload the original file.
        obj = bpy.data.objects.new(layer.name, None)
        obj.empty_display_type = 'CUBE'
        self.setup_obj(obj, layer, parent_obj, layer_path)
        self.setup_animation(obj, layer, offset)

    def import_model_layer_group(self, layer, model_file_path, offset, parent_obj, layer_path):

        # Import a group layer that is the root of a multi-mesh model.
        # We also come here for multi-mesh FBX files that were imported as a single layer in Quill,
        # so the `layer` variable can be either a group or a model layer.
        
        if not os.path.isfile(model_file_path):
            logging.warning("Model file not found: %s", model_file_path)
            self.import_model_layer_fallback(layer, offset, parent_obj, layer_path)
            return
        
        # Quill model importer only supports FBX and OBJ files, and only FBX can have multiple meshes.
        ext = os.path.splitext(model_file_path)[1].lower()
        if ext != ".fbx":
            logging.warning("Unsupported model file format: %s", ext)
            self.import_model_layer_fallback(layer, offset, parent_obj, layer_path)
            return

        # Import the FBX file to Blender.
        # This will import it in the collection and select all the sub-objects.
        # Note that the import scale from the Quill importer dialog is simply stored as 
        # a scale factor in the transform of the top layer, so we don't need to set it here.
        bpy.ops.import_scene.fbx(filepath=model_file_path)

        # The Quill importer doesn't support armatures or animations, and the user can also
        # manually delete sub-meshes inside Quill after import.
        # Find the mapping between the imported objects and the Quill layers, based on names.
        mapping = {}
        for obj in bpy.context.selected_objects:
            if obj.type == 'MESH':
                for child in layer.implementation.children:
                    if child.name == obj.name:
                        mapping[child] = obj
                        break

        # Remove anything that doesn't have a corresponding Quill layer.
        for obj in bpy.context.selected_objects:
            if obj not in mapping.values():
                logging.warning("Imported object %s has no corresponding Quill layer, removing it.", obj.name)
                bpy.data.objects.remove(obj, do_unlink=True)
        
        # Create the group object that will be the parent of all the imported meshes.
        group_obj = bpy.data.objects.new(layer.name, None)
        self.setup_obj(group_obj, layer, parent_obj, layer_path)
        self.setup_animation(group_obj, layer, offset)
        
        # Set up the imported meshes and their animation.
        for child_layer, obj in mapping.items():
            self.setup_obj(obj, child_layer, group_obj, layer_path + "/" + layer.name)
            self.setup_animation(obj, child_layer, offset)

        return


def load(operator, filepath="", **kwargs):

    with QuillImporter(filepath, kwargs, operator) as importer:
        try:
            importer.import_scene()
        except Exception as e:
            operator.report({'ERROR'}, f"Failed to import Quill scene: {str(e)}")
            return {'CANCELLED'}

    return {'FINISHED'}