
import os
import bpy
import logging
import mathutils
from math import degrees, radians
from .model import quill_utils, sequence
from .exporters import paint_armature, paint_gpencil, paint_wireframe, picture, utils

class QuillExporter:
    """Handles picking what nodes to export and kicks off the export process"""

    def __init__(self, path, kwargs, operator):
        self.path = path
        self.operator = operator
        self.scene = bpy.context.scene
        self.config = kwargs

        self.original_quill_scenes = {}
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

        # Loop through the Blender objects and decide which objects to export.
        for obj in self.scene.objects:
            if obj in self.exporting_objects:
                continue
            if self.should_export_object(obj):
                self.exporting_objects.add(obj)

        logging.info("Exporting %d objects", len(self.exporting_objects))

        # Loop through the Blender objects and export them.
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

        # Always include pure empties as they are used for grouping.
        # We then have a second pass at the end to remove empty groups if needed.
        if obj.type != "EMPTY" and obj.type not in self.config["object_types"]:
            return False

        if obj.type == "EMPTY" and obj.empty_display_type == "IMAGE" and "IMAGE" not in self.config["object_types"]:
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

        # Note: Quill only supports uniform scaling.
        # If the object has non-uniform scaling the user should have manually applied scale before export.
        # The rest of the code will assume the scale is uniform and use scale[0] as a proxy.
        if (obj.scale.x != obj.scale.y or obj.scale.y != obj.scale.z):
            logging.warning("Non-uniform scaling not supported. Please apply scale on %s.", obj.name)

        memo_active = bpy.context.view_layer.objects.active
        bpy.context.view_layer.objects.active = obj

        if obj.type == "EMPTY":

            if obj.empty_display_type == "IMAGE":
                # Special case for Image empties.

                # Bail out if the image is not loaded or invalid.
                if obj.data == None or obj.data.size[1] == 0:
                    return

                layer = picture.convert(obj, self.config)
                self.setup_layer(layer, obj, parent_layer)

            else:
                # Bail out if it's going to create an empty group and the user doesn't want that.
                if len(obj.children) == 0 and self.config["use_non_empty"]:
                    return

                if obj.quill.active and obj.quill.paint_layer:
                    # This empty represents a Quill paint layer that was imported as a group of objects.
                    # Rebuild the paint layer from the contained objects.
                    paint_layer = quill_utils.create_paint_layer(obj.name)
                    self.setup_layer(paint_layer, obj, parent_layer)
                    self.animate_layer(paint_layer, obj)

                    # Get the original Quill layer.
                    original_quill_scene = self.get_quill_scene(obj)
                    original_layer = quill_utils.get_layer(original_quill_scene, obj.quill.layer_path)

                    # Loop through contained objects and add their drawings to the paint layer.
                    # Keep track of which Blender objects were actually added in case there are extra ones.
                    blender_object_indices = []
                    for i, child in enumerate(obj.children):

                        # Bail out if the child is not a mesh or not imported from Quill.
                        if child.type != "MESH" or not child.quill.active:
                            logging.warning("Skipping non-mesh or non-Quill child %s in paint layer %s", child.name, obj.name)
                            continue

                        # Bail out if it wasn't part of the original paint layer (we might handle this in the future).
                        if child.quill.scene_path != obj.quill.scene_path or child.quill.layer_path != obj.quill.layer_path:
                            logging.warning("Skipping Quill drawing %s not part of original paint layer %s", child.name, obj.name)
                            continue

                        blender_object_indices.append(i)

                        # Add the drawing to the paint layer.
                        original_drawing = original_layer.implementation.drawings[child.quill.drawing_index]
                        paint_layer.implementation.drawings.append(original_drawing)

                    drawing_count = len(paint_layer.implementation.drawings)
                    if drawing_count == 0:
                        logging.warning("Paint layer %s has no drawings after export.", obj.name)
                        return

                    if drawing_count == 1:
                        # If there is a single frame don't create an animation.
                        paint_layer.implementation.frames = [0]

                    else:
                        # Create the animation for the paint layer.
                        # Note that this isn't a non-descructive round trip, the looping flag and clips
                        # have been collapsed into a single frame list during import.
                        scn = bpy.context.scene
                        frame_start = scn.frame_start
                        frame_end = scn.frame_end
                        paint_layer.implementation.frames = []
                        for frame in range(frame_start, frame_end + 1):
                            scn.frame_set(frame)

                            # Determine which drawing is visible at this frame.
                            # We assume at most one drawing is visible at a time and stop at the first one we find.
                            blender_drawing_index = -1
                            for i, child in enumerate(obj.children):
                                if child.visible_get() and i in blender_object_indices:
                                    blender_drawing_index = i
                                    break

                            # If no suitable drawing is visible, use the special empty drawing.
                            # This may happen when the original Quill layer or parents have clips that
                            # start after frame 0 or there are gaps between the clips.
                            # Normally we can't rebuild a base animation with gaps, but we can
                            # create a special empty drawing to represent those gaps.
                            quill_drawing_index = -1
                            if blender_drawing_index == -1:
                                # TODO: check if we already added the empty drawing to the paint layer.
                                # add it if not, and set the visible_drawing_index to it.
                                # empty_drawing = quill_utils.create_empty_drawing()
                                # paint_layer.implementation.drawings.append(empty_drawing)
                                # visible_drawing_index = drawing_count
                                # drawing_count += 1
                                pass
                            else:
                                # We found a visible drawing on this frame.
                                # Map from blender child index to Quill drawing index.
                                quill_drawing_index = obj.children[blender_drawing_index].quill.drawing_index

                            # Set the drawing index for this frame.
                            paint_layer.implementation.frames.append(quill_drawing_index)

                else:
                    # Otherwise it's a normal Empty, representing a group or sequence.
                    # Either imported from Quill or created in Blender.
                    # Make a group layer and process the children recursively.
                    layer = quill_utils.create_group_layer(obj.name)
                    self.setup_layer(layer, obj, parent_layer)
                    self.animate_layer(layer, obj)
                    for child in obj.children:
                        self.export_object(child, layer)

        elif obj.type == "MESH":

            if obj.quill.active:

                # Since we are on an individual mesh object this should result in a single drawing.
                # This could be a mesh extracted or duplicated out of a paint layer container,
                # or could be a multi-frame Keymesh object (TODO).
                # Mark the object as "paint layer", this is used later to adjust the transform.
                obj.quill.paint_layer = True

                # Create a new paint layer.
                layer = quill_utils.create_paint_layer(obj.name)

                # Get the original Quill layer.
                original_quill_scene = self.get_quill_scene(obj)
                original_layer = quill_utils.get_layer(original_quill_scene, obj.quill.layer_path)

                # TODO: Check if it's a Keymesh object and export all blocks as drawings,
                # then recreate the base animation.
                #if hasattr(obj, "keymesh") and obj.keymesh.active:
                # otherwise  create a layer with a single drawing in it.
                original_drawing = original_layer.implementation.drawings[obj.quill.drawing_index]
                layer.implementation.drawings.append(original_drawing)
            else:
                # If not imported from Quill convert the mesh to a wireframe.
                # TODO: if this is a keymesh object we could also export an animated wireframe.
                layer = paint_wireframe.convert(obj, self.config)

            if layer is not None:
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
            self.setup_layer(layer, obj, parent_layer)
            self.animate_layer(layer, obj)

        elif obj.type == "GPENCIL" or obj.type == "GREASEPENCIL":
            layer = paint_gpencil.convert(obj, self.config)
            self.setup_layer(layer, obj, parent_layer)
            self.animate_layer(layer, obj)

        elif obj.type == "ARMATURE":
            layer = paint_armature.convert(obj, self.config)
            self.setup_layer(layer, obj, parent_layer)

        bpy.context.view_layer.objects.active = memo_active

    def setup_layer(self, layer, obj, parent_layer):
        """Common setup for all layers."""

        if layer is None:
            return

        layer.transform = self.get_transform(obj)
        parent_layer.add_child(layer)

    def animate_layer(self, layer, obj):
        """Layer level animation with transform key frames."""

        if layer is None:
            return

        # Approach: loop through blender frames and create a key frame at each frame.
        # This way we get all the drivers, modifiers and interpolation baked in
        # without having to drill down the F-curves channels and interpret everything.
        scn = bpy.context.scene

        frame_start = max(scn.frame_start, 0)
        frame_end = max(scn.frame_end, 0)
        ticks_per_second = 12600
        ticks_per_frame = int(ticks_per_second / scn.render.fps)

        memo_current_frame = scn.frame_current

        # At this point we don't know if there will be any key frames to create.
        # We always create the first one to make sure we initialize it correctly in case there are others.
        # We'll remove it at the end if it turns out it's the only one and the layer-level transform is enough.
        previous_matrix_local = None

        # Transform key frames.
        kktt = layer.animation.keys.transform
        for frame in range(frame_start, frame_end + 1):

            scn.frame_set(frame)

            # Only create a kf if we have moved.
            # Perform the check on the Blender transform to minimize precision issues.
            # It's not clear what the epsilon of matrix equality is in Blender, but it doesn't work for the local
            # matrix of an object parented to a moving empty. The local matrix keeps changing when it shouldn't.
            # Using 1e-5 seems to work.
            epsilon = 1e-5
            if previous_matrix_local == None or not utils.transform_equals(obj.matrix_local, previous_matrix_local, epsilon):

                transform = self.get_transform(obj)

                # If we do create it, create it with constant interpolation.
                # Any interpolation style on Blender side is already accounted for from the
                # fact that we get the transform at every frame. The only remaning case is a frame-hold.
                time = frame * ticks_per_frame
                keyframe = sequence.Keyframe("None", time, transform)
                kktt.append(keyframe)

                previous_matrix_local = obj.matrix_local.copy()

        # Cleanup unecessary keyframe.
        # If there is a single key frame we don't need it.
        # The layer-level transform has already been set.
        if len(kktt) == 1:
            kktt.clear()

        # Restore the active frame
        scn.frame_set(memo_current_frame)

    def get_transform(self, obj):
        """Get the object's transform at the current frame, in Quill space."""

        if obj.type == "EMPTY" and obj.empty_display_type == "IMAGE":

            # Blender identity pose for images is on the front plane.
            mat = obj.matrix_local @ mathutils.Matrix.Rotation(radians(90), 4, 'X')
            translation, rotation, scale, flip = utils.convert_transform(mat)

            # On Blender side, images have a display size independent of the scale.
            # For landscape the unit quad is mapped to the width, for portrait to the height.
            # On Quill side, images are mapped to quads of size 2x2 and it's always
            # the height that drives the aspect ratio.
            # Heuristic
            # - if the image is square or portrait, it's the same model as Quill,
            # so we just have to scale by the display size and divide by 2.
            # - if the image is landscape, we also need to scale by 1/aspect.

            scale_factor = obj.empty_display_size

            aspect = float(obj.data.size[0] / obj.data.size[1])
            if aspect > 1.0:
                 scale_factor /= aspect

            scale_factor *= 0.5

            scale *= scale_factor
            transform = sequence.Transform(flip, list(rotation), scale[0], list(translation))

        elif obj.type == "CAMERA":

            # Blender identity pose for cameras looks down.
            # Rotate by 90° around X axis to match Quill.
            mat = obj.matrix_local @ mathutils.Matrix.Rotation(- radians(90), 4, 'X')
            translation, rotation, scale, flip = utils.convert_transform(mat)

            # Apply extra scale based on the "display size" of the camera
            # Camera > Viewport Display > Size (cm).
            scale *= obj.data.display_size
            transform = sequence.Transform(flip, list(rotation), scale[0], list(translation))

        elif obj.quill.active and obj.quill.paint_layer:
            # We want to use any custom transform applied at the layer level in Blender,
            # but at the same time the drawings inside will be coming from the original Quill layer
            # without the modification we normally apply during import (90° rotation around X).
            # To achieve this we apply an extra -90° rotation around X to the transform.
            # This is applied to layer paint containers and to isolated meshes converted to their own paint layer.
            # This approach means that every time we import and export we accumulate rotations around X.
            # The other approach would be to modify the original drawing data on the fly at the vertex level
            # just to counter the rotation done in `convert_transform`.
            mat = obj.matrix_local @ mathutils.Matrix.Rotation(- radians(90), 4, 'X')
            translation, rotation, scale, flip = utils.convert_transform(mat)
            transform = sequence.Transform(flip, list(rotation), scale[0], list(translation))

        else:
            # Normal case for groups and leaf objects created in Blender.
            # This does the normal conversion from Blender to Quill space.
            translation, rotation, scale, flip = utils.convert_transform(obj.matrix_local)
            transform = sequence.Transform(flip, list(rotation), scale[0], list(translation))

        return transform

    def get_quill_scene(self, obj):
        """Get the original Quill scene for an object imported from Quill."""

        # Check if we already have it in our little cache, otherwise load it.
        scene_path = obj.quill.scene_path
        if scene_path in self.original_quill_scenes:
            return self.original_quill_scenes[scene_path]

        original_quill_scene = quill_utils.import_scene(scene_path)
        if original_quill_scene is None:
            logging.warning("Could not load original Quill scene at %s for object %s", scene_path, obj.name)
            return None

        self.original_quill_scenes[scene_path] = original_quill_scene
        return original_quill_scene


def save(operator, filepath="", **kwargs):
    """Begin the export"""

    with QuillExporter(filepath, kwargs, operator) as exp:
        exp.export()

    return {'FINISHED'}




