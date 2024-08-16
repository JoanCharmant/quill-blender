import os
import bpy
import json
import logging
import mathutils
from math import radians, floor
from .model import sequence, sequence_utils, paint
from .importers import gpencil_paint, mesh_paint, mesh_material

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

        # Filter out unwanted layers.
        if not self.config["load_hidden_layers"]:
            sequence_utils.delete_hidden(root_layer)

        if not self.config["load_cameras"]:
            sequence_utils.delete_type(root_layer, "Viewpoint")
            sequence_utils.delete_type(root_layer, "Camera")

        # Load the drawing data.
        self.qbin = open(qbin_path, "rb")
        self.load_drawing_data(root_layer)
        self.qbin.close()

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
        self.import_layer(root_layer, 0)
        bpy.context.view_layer.update()

    def load_drawing_data(self, layer):

        if layer.type == "Group":
            for child in layer.implementation.children:
                self.load_drawing_data(child)

        elif layer.type == "Paint":
            drawings = layer.implementation.drawings
            if drawings is None or len(drawings) == 0:
                return

            # Only load the first drawing for now.
            #for drawing in layer.implementation.drawings:
            drawing = layer.implementation.drawings[0]
            self.qbin.seek(int(drawing.data_file_offset, 16))
            drawing.data = paint.read_drawing_data(self.qbin)

    def import_layer(self, layer, offset, parent_layer=None, parent_obj=None):

        logging.info("Importing Quill layer: %s (%s).", layer.name, layer.type)

        if layer.type == "Group":
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
            if self.config["convert_paint"] == "MESH":
                mesh = bpy.data.meshes.new(layer.name)
                obj = bpy.data.objects.new(mesh.name, mesh)
                bpy.context.collection.objects.link(obj)
                bpy.context.view_layer.objects.active = obj
                self.setup_obj(layer, parent_layer, parent_obj)
                self.setup_animation(layer, offset)

                mesh_paint.convert(mesh, layer)
                mesh.materials.append(self.material)

            elif self.config["convert_paint"] == "GPENCIL":
                bpy.ops.object.gpencil_add()
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
            obj.data.lens_unit = 'FOV'
            obj.data.angle = radians(layer.implementation.fov)

        elif layer.type == "Sound":
            bpy.ops.object.speaker_add()
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

        else:
            logging.warning("Unsupported Quill layer type: %s", layer.type)

    def setup_obj(self, layer, parent_layer=None, parent_obj=None):
        """Basic configuration of the resulting Blender object, common to all layer types."""
        obj = bpy.context.object
        obj.name = layer.name
        obj.parent = parent_obj
        obj.matrix_local = self.get_transform(layer.transform)
        # TODO: pivot.

        # Visibility: in Quill if the parent is hidden the whole subtree is hidden,
        # even if the individual layers are marked as visible.
        # In Blender each object has its own visibility independent of the parent.
        # In order to match Quill behavior we force the visibility of the object
        # to match that of its parent.
        # However this must use the flag in the parent Quill layer, not the Blender object which 
        # current visibility value may depend on animation.
        visible = layer.visible and (parent_layer is None or parent_layer.visible)
        hidden = not visible
        obj.hide_viewport = hidden
        obj.hide_render = hidden

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
        obj = bpy.context.object
        fps = bpy.context.scene.render.fps

        # Key frame times are stored relative to the parent Sequence.
        # Bare groups do not alter the time of their children.
        # Quill uses a time base of 1/12600 (nicely divisible).
        time_base = 1/12600
        
        # Visibility key frames.
        kkvv = layer.animation.keys.visibility
        if kkvv and len(kkvv) > 0:
            # Quill layers are invisible by default and have a first key frame turning visibility on. 
            # Blender objects are visible by default.
            # -> If the first key frame is not at time 0 we need to create one to hide the object before it is visible.
            if kkvv[0].time + offset > 0:
                obj.hide_viewport = True
                obj.hide_render = True
                obj.keyframe_insert(data_path="hide_render", frame=0)
                obj.keyframe_insert(data_path="hide_viewport", frame=0)
                
            for key in kkvv:
                time = key.time + offset
                frame = floor(time * time_base * fps + 0.5)
                hidden = not key.value
                obj.hide_viewport = hidden
                obj.hide_render = hidden
                obj.keyframe_insert(data_path="hide_render", frame=frame)
                obj.keyframe_insert(data_path="hide_viewport", frame=frame)
        
        # Transform key frames.
        kktt = layer.animation.keys.transform
        if kktt:
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