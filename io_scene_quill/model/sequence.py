# Serialization functions for the Quill scene file (the file named "Quill.json").
# This file was initially generated by Quicktype using a JSON schema,
# it has since then been manually updated to match the Quill file format,
# add default initializers and better implement the layer hierarchy.

import logging

def from_list(f, x):
    assert isinstance(x, list)
    return [f(y) for y in x]


def from_str(x):
    assert isinstance(x, str)
    return x


def to_class(c, x):
    assert isinstance(x, c)
    return x.to_dict()


def from_float(x):
    assert isinstance(x, (float, int)) and not isinstance(x, bool)
    return float(x)


def to_float(x):
    assert isinstance(x, float)
    return x


def from_int(x):
    assert isinstance(x, int) and not isinstance(x, bool)
    return x


def from_bool(x):
    assert isinstance(x, bool)
    return x


def from_none(x):
    assert x is None
    return x


def from_union(fs, x):
    for f in fs:
        try:
            return f(x)
        except:
            pass
    assert False

def is_type(t, x):
    assert isinstance(x, t)
    return x


class Thumbnails:
    def __init__(self, ):
        pass

    @staticmethod
    def from_dict(obj):
        assert isinstance(obj, dict)
        return Thumbnails()

    def to_dict(self):
        result = {}
        return result

    @staticmethod
    def from_default():
        return Thumbnails()


class PictureMetadata:
    def __init__(self, ):
        pass

    @staticmethod
    def from_dict(obj):
        assert isinstance(obj, dict)
        return PictureMetadata()

    def to_dict(self):
        result = {}
        return result


class Picture:
    def __init__(self, type, data_file_offset, metadata):
        self.type = type
        self.data_file_offset = data_file_offset
        self.metadata = metadata

    @staticmethod
    def from_dict(obj):
        assert isinstance(obj, dict)
        type = from_str(obj.get("Type"))
        data_file_offset = from_str(obj.get("DataFileOffset"))
        metadata = PictureMetadata.from_dict(obj.get("Metadata"))
        return Picture(type, data_file_offset, metadata)

    def to_dict(self):
        result = {}
        result["Type"] = from_str(self.type)
        result["DataFileOffset"] = from_str(self.data_file_offset)
        result["Metadata"] = to_class(PictureMetadata, self.metadata)
        return result


class Gallery:
    def __init__(self, pictures, thumbnails):
        self.pictures = pictures
        self.thumbnails = thumbnails

    @staticmethod
    def from_dict(obj):
        assert isinstance(obj, dict)
        pictures = from_union([lambda x: from_list(Picture.from_dict, x), from_none], obj.get("Pictures"))
        thumbnails = Thumbnails.from_dict(obj.get("Thumbnails"))
        return Gallery(pictures, thumbnails)

    def to_dict(self):
        result = {}
        if self.pictures is not None:
            result["Pictures"] = from_union([lambda x: from_list(lambda x: to_class(Picture, x), x), from_none], self.pictures)
        result["Thumbnails"] = to_class(Thumbnails, self.thumbnails)
        return result

    @staticmethod
    def from_default():
        pictures = []
        thumbnails = Thumbnails.from_default()
        return Gallery(pictures, thumbnails)


class Metadata:
    def __init__(self, description, thumbnail_crop_position, title):
        self.description = description
        self.thumbnail_crop_position = thumbnail_crop_position
        self.title = title

    @staticmethod
    def from_dict(obj):
        assert isinstance(obj, dict)
        description = from_str(obj.get("Description"))
        thumbnail_crop_position = from_union([from_float, from_none], obj.get("ThumbnailCropPosition"))
        title = from_str(obj.get("Title"))
        return Metadata(description, thumbnail_crop_position, title)

    def to_dict(self):
        result = {}
        result["Description"] = from_str(self.description)
        result["ThumbnailCropPosition"] = from_union([from_float, from_none], self.thumbnail_crop_position)
        result["Title"] = from_str(self.title)
        return result

    @staticmethod
    def from_default():
        description = ""
        thumbnail_crop_position = 0.0
        title = "Untitled"
        return Metadata(description, thumbnail_crop_position, title)


class Drawing:
    def __init__(self, bounding_box, data_file_offset):
        self.bounding_box = bounding_box
        self.data_file_offset = data_file_offset
        self.data = None

    @staticmethod
    def from_dict(obj):
        assert isinstance(obj, dict)
        bounding_box = from_list(from_float, obj.get("BoundingBox"))
        data_file_offset = from_str(obj.get("DataFileOffset"))
        return Drawing(bounding_box, data_file_offset)

    def to_dict(self):
        result = {}
        result["BoundingBox"] = from_list(to_float, self.bounding_box)
        result["DataFileOffset"] = from_str(self.data_file_offset)
        return result

    @staticmethod
    def from_default():
        bounding_box = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        data_file_offset = "0"
        return Drawing(bounding_box, data_file_offset)


class Keyframe:
    def __init__(self, interpolation, time, value):
        self.interpolation = interpolation
        self.time = time
        self.value = value

    @staticmethod
    def from_dict(obj):
        assert isinstance(obj, dict)
        interpolation = from_str(obj.get("Interpolation"))
        time = from_union([from_int, lambda x: int(from_str(x))], obj.get("Time"))
        value = from_union([from_int, from_float, from_bool, Transform.from_dict], obj.get("Value"))
        return Keyframe(interpolation, time, value)

    def to_dict(self):
        result = {}
        result["Interpolation"] = from_str(self.interpolation)
        result["Time"] = from_str(str(self.time))
        result["Value"] = from_union([from_int, to_float, from_bool, lambda x: to_class(Transform, x)], self.value)
        return result

    @staticmethod
    def from_default():
        interpolation = "Linear"
        time = 0
        value = 0

        return Keyframe(interpolation, time, value)


class Keys:
    def __init__(self, offset, opacity, transform, visibility):
        self.offset = offset
        self.opacity = opacity
        self.transform = transform
        self.visibility = visibility

    @staticmethod
    def from_dict(obj):
        assert isinstance(obj, dict)
        offset = from_union([lambda x: from_list(Keyframe.from_dict, x), from_none], obj.get("Offset"))
        opacity = from_union([lambda x: from_list(Keyframe.from_dict, x), from_none], obj.get("Opacity"))
        transform = from_union([lambda x: from_list(Keyframe.from_dict, x), from_none], obj.get("Transform"))
        visibility = from_union([lambda x: from_list(Keyframe.from_dict, x), from_none], obj.get("Visibility"))
        return Keys(offset, opacity, transform, visibility)

    def to_dict(self):
        result = {}
        if self.offset is not None:
            result["Offset"] = from_union([lambda x: from_list(lambda x: to_class(Keyframe, x), x), from_none], self.offset)
        if self.opacity is not None:
            result["Opacity"] = from_union([lambda x: from_list(lambda x: to_class(Keyframe, x), x), from_none], self.opacity)
        if self.transform is not None:
            result["Transform"] = from_union([lambda x: from_list(lambda x: to_class(Keyframe, x), x), from_none], self.transform)
        if self.visibility is not None:
            result["Visibility"] = from_union([lambda x: from_list(lambda x: to_class(Keyframe, x), x), from_none], self.visibility)
        return result

    @staticmethod
    def from_default():
        offset = []
        opacity = []
        transform = []
        visibility = []
        offset.append(Keyframe("None", 0, 0))
        visibility.append(Keyframe("None", 0, True))
        return Keys(offset, opacity, transform, visibility)


class Animation:
    def __init__(self, duration, keys, max_repeat_count, start_offset, timeline):
        self.duration = duration
        self.keys = keys
        self.max_repeat_count = max_repeat_count
        self.start_offset = start_offset
        self.timeline = timeline

    @staticmethod
    def from_dict(obj):
        assert isinstance(obj, dict)

        # Animation JSON changed quite a lot.
        # Pipe everything into the latest representation.
        if "Frames" in obj or "Spans" in obj:
            return Animation.from_default()

        duration = from_union([from_float, from_int, lambda x: int(from_str(x))], obj.get("Duration"))
        keys = Keys.from_dict(obj.get("Keys"))
        max_repeat_count = from_union([from_float, from_int, lambda x: int(from_str(x))], obj.get("MaxRepeatCount"))
        start_offset = from_union([from_none, from_float, from_int, lambda x: int(from_str(x))], obj.get("StartOffset"))
        timeline = from_bool(obj.get("Timeline"))
        return Animation(duration, keys, max_repeat_count, start_offset, timeline)

    def to_dict(self):
        result = {}
        result["Duration"] = from_int(self.duration)
        result["Timeline"] = from_bool(self.timeline)
        result["StartOffset"] = from_union([lambda x: from_none((lambda x: is_type(type(None), x))(x)), lambda x: from_int((lambda x: is_type(int, x))(x))], self.start_offset)
        result["MaxRepeatCount"] = from_int(self.max_repeat_count)
        result["Keys"] = to_class(Keys, self.keys)
        return result

    @staticmethod
    def from_default():
        duration = 45360000
        keys = Keys.from_default()
        max_repeat_count = 0
        start_offset = 0
        timeline = True
        return Animation(duration, keys, max_repeat_count, start_offset, timeline)


class KeepAlive:
    def __init__(self, type):
        self.type = type

    @staticmethod
    def from_dict(obj):
        assert isinstance(obj, dict)
        type = from_str(obj.get("Type"))
        return KeepAlive(type)

    def to_dict(self):
        result = {}
        result["Type"] = from_str(self.type)
        return result

    @staticmethod
    def from_default():
        type = "None"
        return KeepAlive(type)


class Transform:
    def __init__(self, flip, rotation, scale, translation):
        self.flip = flip
        self.rotation = rotation
        self.scale = scale
        self.translation = translation

    def __eq__(self, other):
        if not isinstance(other, Transform):
            return NotImplemented

        return self.flip == other.flip and self.rotation == other.rotation and self.scale == other.scale and self.translation == other.translation



    @staticmethod
    def from_dict(obj):
        assert isinstance(obj, dict)
        flip = from_str(obj.get("Flip"))
        rotation = from_list(from_float, obj.get("Rotation"))
        scale = from_float(obj.get("Scale"))
        translation = from_list(from_float, obj.get("Translation"))
        return Transform(flip, rotation, scale, translation)

    def to_dict(self):
        result = {}
        result["Flip"] = from_str(self.flip)
        result["Rotation"] = from_list(to_float, self.rotation)
        result["Scale"] = to_float(self.scale)
        result["Translation"] = from_list(to_float, self.translation)
        return result

    @staticmethod
    def identity():
        flip = "N"
        rotation = [0.0, 0.0, 0.0, 1.0]
        scale = 1.0
        translation = [0.0, 0.0, 0.0]
        return Transform(flip, rotation, scale, translation)


class GroupLayerImplementation:
    def __init__(self, children):
        self.children = children

    @staticmethod
    def from_dict(obj):
        assert isinstance(obj, dict)
        children = from_list(lambda x: Layer.from_dict(x), obj.get("Children"))
        return GroupLayerImplementation(children)

    def to_dict(self):
        result = {}
        result["Children"] = from_list(lambda x: to_class(Layer, x), self.children)
        return result


class ViewpointLayerImplementation:
    def __init__(self, allow_translation_x, allow_translation_y, allow_translation_z, color, exporting, showing_volume, sphere, type_str, version):
        self.allow_translation_x = allow_translation_x
        self.allow_translation_y = allow_translation_y
        self.allow_translation_z = allow_translation_z
        self.color = color
        self.exporting = exporting
        self.showing_volume = showing_volume
        self.sphere = sphere
        self.type_str = type_str
        self.version = version

    @staticmethod
    def from_dict(obj):
        assert isinstance(obj, dict)
        allow_translation_x = from_bool(obj.get("AllowTranslationX"))
        allow_translation_y = from_bool(obj.get("AllowTranslationY"))
        allow_translation_z = from_bool(obj.get("AllowTranslationZ"))
        color = from_list(from_float, obj.get("Color"))
        exporting = from_bool(obj.get("Exporting"))
        showing_volume = from_bool(obj.get("ShowingVolume"))
        sphere = from_list(from_float, obj.get("Sphere"))
        type_str = from_union([from_str, from_none], obj.get("TypeStr"))
        version = from_union([from_int, from_none], obj.get("Version"))
        return ViewpointLayerImplementation(allow_translation_x, allow_translation_y, allow_translation_z, color, exporting, showing_volume, sphere, type_str, version)

    def to_dict(self):
        result = {}
        result["AllowTranslationX"] = from_union([from_bool, from_none], self.allow_translation_x)
        result["AllowTranslationY"] = from_union([from_bool, from_none], self.allow_translation_y)
        result["AllowTranslationZ"] = from_union([from_bool, from_none], self.allow_translation_z)
        result["Color"] = from_union([lambda x: from_list(to_float, x), from_none], self.color)
        result["Exporting"] = from_union([from_bool, from_none], self.exporting)
        result["ShowingVolume"] = from_union([from_bool, from_none], self.showing_volume)
        result["Sphere"] = from_union([lambda x: from_list(to_float, x), from_none], self.sphere)
        result["TypeStr"] = from_union([from_str, from_none], self.type_str)
        result["Version"] = from_union([from_int, from_none], self.version)
        return result


class CameraLayerImplementation:
    def __init__(self, fov):
        self.fov = fov

    @staticmethod
    def from_dict(obj):
        assert isinstance(obj, dict)
        fov = from_float(obj.get("FOV"))
        return CameraLayerImplementation(fov)

    def to_dict(self):
        result = {}
        result["FOV"] = to_float(self.fov)
        return result


class PaintLayerImplementation:
    def __init__(self, drawings, framerate, frames, max_repeat_count):
        self.drawings = drawings
        self.framerate = framerate
        self.frames = frames
        self.max_repeat_count = max_repeat_count

    @staticmethod
    def from_dict(obj):
        assert isinstance(obj, dict)
        framerate = from_union([from_float, from_none], obj.get("Framerate"))
        max_repeat_count = from_union([from_int, from_none], obj.get("MaxRepeatCount"))
        drawings = from_union([lambda x: from_list(Drawing.from_dict, x), from_none], obj.get("Drawings"))
        frames = from_union([
            lambda x: from_list(lambda x: int(from_str(x)), x),
            lambda x: from_list(from_float, x),
            from_none],
            obj.get("Frames"))

        # Quill 1.3 and earlier did not have animated paint layers.
        if "DataFileOffset" in obj:
            framerate = 24.0
            max_repeat_count = 0
            drawings = []
            drawing = Drawing.from_dict({
                "BoundingBox": obj.get("BoundingBox"),
                "DataFileOffset": obj.get("DataFileOffset")
            })
            drawings.append(drawing)
            frames = ["0"]

        return PaintLayerImplementation(drawings, framerate, frames, max_repeat_count)

    def to_dict(self):
        result = {}
        result["Drawings"] = from_union([lambda x: from_list(lambda x: to_class(Drawing, x), x), from_none], self.drawings)
        result["Framerate"] = from_union([from_float, from_none], self.framerate)
        result["Frames"] = from_union([lambda x: from_list(lambda x: from_str((lambda x: str(x))(x)), x), from_none], self.frames)
        result["MaxRepeatCount"] = from_union([from_int, from_none], self.max_repeat_count)
        return result


class PictureLayerImplementation:
    def __init__(self, data_file_offset, import_file_path, type, viewer_locked):
        self.data_file_offset = data_file_offset
        self.import_file_path = import_file_path
        self.type = type
        self.viewer_locked = viewer_locked

    @staticmethod
    def from_dict(obj):
        assert isinstance(obj, dict)
        data_file_offset = from_str(obj.get("DataFileOffset"))
        import_file_path = from_str(obj.get("ImportFilePath"))
        type = from_str(obj.get("Type"))
        viewer_locked = from_bool(obj.get("ViewerLocked"))
        return PictureLayerImplementation(data_file_offset, import_file_path, type, viewer_locked)

    def to_dict(self):
        result = {}
        result["DataFileOffset"] = from_str(self.data_file_offset)
        result["ImportFilePath"] = from_str(self.import_file_path)
        result["Type"] = from_str(self.type)
        result["ViewerLocked"] = from_bool(self.viewer_locked)
        return result


class LayerImplementation:
    # This is a generic class for unsupported layer types.
    def __init__(self):
        pass

    @staticmethod
    def from_dict(obj):
        assert isinstance(obj, dict)
        return LayerImplementation()

    def to_dict(self):
        result = {}
        return result


class Layer:
    def __init__(self, animation, b_box_visible, collapsed, implementation, is_model_top_layer, keep_alive, locked, name, opacity, pivot, transform, type, visible):
        self.animation = animation
        self.b_box_visible = b_box_visible
        self.collapsed = collapsed
        self.implementation = implementation
        self.is_model_top_layer = is_model_top_layer
        self.keep_alive = keep_alive
        self.locked = locked
        self.name = name
        self.opacity = opacity
        self.pivot = pivot
        self.transform = transform
        self.type = type
        self.visible = visible

    @staticmethod
    def from_dict(obj):
        assert isinstance(obj, dict)
        animation = Animation.from_default() if "Animation" not in obj else Animation.from_dict(obj.get("Animation"))
        b_box_visible = from_bool(obj.get("BBoxVisible"))
        collapsed = from_bool(obj.get("Collapsed"))
        is_model_top_layer = from_union([from_bool, from_none], obj.get("IsModelTopLayer"))
        keep_alive = from_union([KeepAlive.from_dict, from_none], obj.get("KeepAlive"))
        locked = from_bool(obj.get("Locked"))
        name = from_str(obj.get("Name"))
        opacity = from_float(obj.get("Opacity"))
        pivot = from_union([
            Transform.from_dict,
            lambda x: from_list(from_float, x),
            from_none], obj.get("Pivot"))
        transform = from_union([Transform.from_dict, lambda x: from_list(from_float, x)], obj.get("Transform"))
        type = from_str(obj.get("Type"))
        visible = from_bool(obj.get("Visible"))

        if type == "Group":
            implementation = GroupLayerImplementation.from_dict(obj.get("Implementation"))
        elif type == "Viewpoint":
            implementation = ViewpointLayerImplementation.from_dict(obj.get("Implementation"))
        elif type == "Camera":
            implementation = CameraLayerImplementation.from_dict(obj.get("Implementation"))
        elif type == "Paint":
            implementation = PaintLayerImplementation.from_dict(obj.get("Implementation"))
        elif type == "Picture":
            implementation = PictureLayerImplementation.from_dict(obj.get("Implementation"))
        else:
            implementation = LayerImplementation.from_dict(obj.get("Implementation"))

        return Layer(animation, b_box_visible, collapsed, implementation, is_model_top_layer, keep_alive, locked, name, opacity, pivot, transform, type, visible)

    def to_dict(self):
        result = {}
        result["Animation"] = from_union([lambda x: to_class(Animation, x), from_none], self.animation)
        result["BBoxVisible"] = from_bool(self.b_box_visible)
        result["Collapsed"] = from_bool(self.collapsed)
        result["IsModelTopLayer"] = from_union([from_bool, from_none], self.is_model_top_layer)
        result["KeepAlive"] = from_union([lambda x: to_class(KeepAlive, x), from_none], self.keep_alive)
        result["Locked"] = from_bool(self.locked)
        result["Name"] = from_str(self.name)
        result["Opacity"] = to_float(self.opacity)
        result["Pivot"] = from_union([lambda x: to_class(Transform, x), lambda x: from_list(from_float, x)], self.pivot)
        result["Transform"] = from_union([lambda x: to_class(Transform, x), lambda x: from_list(from_float, x)], self.transform)
        result["Type"] = from_str(self.type)
        result["Visible"] = from_bool(self.visible)

        if self.type == "Group":
            logging.info("Exporting group layer: %s", self.name)
            result["Implementation"] = to_class(GroupLayerImplementation, self.implementation)
        elif self.type == "Viewpoint":
            logging.info("Exporting viewpoint layer: %s", self.name)
            result["Implementation"] = to_class(ViewpointLayerImplementation, self.implementation)
        elif self.type == "Camera":
            logging.info("Exporting camera layer: %s", self.name)
            result["Implementation"] = to_class(CameraLayerImplementation, self.implementation)
        elif self.type == "Paint":
            logging.info("Exporting paint layer: %s", self.name)
            result["Implementation"] = to_class(PaintLayerImplementation, self.implementation)
        else:
            logging.warning("Exporting unsupported layer type: %s", self.type)
            result["Implementation"] = to_class(LayerImplementation, self.implementation)

        return result

    @staticmethod
    def from_default(type, implementation, name = ""):
        animation = Animation.from_default()
        b_box_visible = False
        collapsed = False
        is_model_top_layer = False
        keep_alive = KeepAlive.from_default()
        locked = False
        opacity = 1.0
        pivot = Transform.identity()
        transform = Transform.identity()
        visible = True
        return Layer(animation, b_box_visible, collapsed, implementation, is_model_top_layer, keep_alive, locked, name, opacity, pivot, transform, type, visible)


class Sequence:
    def __init__(self, background_color, camera_resolution, default_viewpoint, export_end, export_start, framerate, gallery, metadata, root_layer):
        self.background_color = background_color
        self.camera_resolution = camera_resolution
        self.default_viewpoint = default_viewpoint
        self.export_end = export_end
        self.export_start = export_start
        self.framerate = framerate
        self.gallery = gallery
        self.metadata = metadata
        self.root_layer = root_layer

    @staticmethod
    def from_dict(obj):
        assert isinstance(obj, dict)
        background_color = from_list(from_float, obj.get("BackgroundColor"))
        camera_resolution = from_union([lambda x: from_list(from_int, x), from_none], obj.get("CameraResolution"))
        default_viewpoint = from_union([from_str, from_none], obj.get("DefaultViewpoint"))
        export_end = from_union([from_int, from_none], obj.get("ExportEnd"))
        export_start = from_union([from_int, from_none], obj.get("ExportStart"))
        framerate = from_union([from_float, from_none], obj.get("Framerate"))
        gallery = from_union([Gallery.from_dict, from_none], obj.get("Gallery"))
        metadata = from_union([Metadata.from_dict, from_none], obj.get("Metadata"))
        root_layer = Layer.from_dict(obj.get("RootLayer"))
        return Sequence(background_color, camera_resolution, default_viewpoint, export_end, export_start, framerate, gallery, metadata, root_layer)

    def to_dict(self):
        result = {}
        result["BackgroundColor"] = from_list(to_float, self.background_color)
        result["CameraResolution"] = from_list(from_int, self.camera_resolution)
        result["DefaultViewpoint"] = from_union([from_str, from_none], self.default_viewpoint)
        result["ExportEnd"] = from_union([from_int, from_none], self.export_end)
        result["ExportStart"] = from_union([from_int, from_none], self.export_start)
        result["Framerate"] = from_union([from_float, from_none], self.framerate)
        result["Gallery"] = from_union([lambda x: to_class(Gallery, x), from_none], self.gallery)
        result["Metadata"] = from_union([lambda x: to_class(Metadata, x), from_none], self.metadata)
        result["RootLayer"] = to_class(Layer, self.root_layer)
        return result

    @staticmethod
    def from_default(root_layer):
        background_color = [0.8, 0.8, 0.8]
        camera_resolution = [1920, 1080]
        default_viewpoint = "Root/InitialSpawnArea"
        export_end = 126000
        export_start = 0
        framerate = 24.0
        gallery = Gallery.from_default()
        metadata = Metadata.from_default()

        return Sequence(background_color, camera_resolution, default_viewpoint, export_end, export_start, framerate, gallery, metadata, root_layer)


class QuillScene:
    def __init__(self, sequence, version):
        self.sequence = sequence
        self.version = version

    @staticmethod
    def from_dict(obj):
        assert isinstance(obj, dict)
        sequence = Sequence.from_dict(obj.get("Sequence"))
        version = from_int(obj.get("Version"))
        return QuillScene(sequence, version)

    def to_dict(self):
        result = {}
        result["Sequence"] = to_class(Sequence, self.sequence)
        result["Version"] = from_int(self.version)
        return result

