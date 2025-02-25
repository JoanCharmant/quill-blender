import bpy
import math
import mathutils
from ..model.paint import BrushType

def convert(config, parent_obj, layer, material):
    """Convert a Quill paint layer to a Blender mesh object."""

    drawings = layer.implementation.drawings
    if drawings is None or len(drawings) == 0:
        return

    # Load all drawings into mesh objects.
    # Note: empty frames still have a drawing pointer, just no strokes.
    index = 0
    drawing_to_obj = {}
    for drawing in drawings:

        # Create a new mesh object for this drawing.
        mesh = bpy.data.meshes.new(layer.name + f"_{index}")
        obj = bpy.data.objects.new(mesh.name, mesh)
        obj.parent = parent_obj
        drawing_to_obj[index] = obj
        bpy.context.collection.objects.link(obj)
        bpy.context.view_layer.objects.active = obj

        # Load the drawing data into the mesh.
        # The extra attributes besides rgba are only added if the option is enabled.
        vertices = []
        edges = []
        faces = []
        attributes = {
            "rgba": [],
            "stroke": [],   # Quill Stroke ID.
            "brush": [],    # Quill Brush type.
            "index": [],    # Index of the vertex within the stroke.
            "p": [],        # Position of the vertex in Quill.
            "n": [],        # Normal of the vertex in Quill.
            "t": [],        # Tangent of the vertex in Quill.
            "w": [],        # Width of the vertex in Quill.
        }

        base_vertex = 0
        for stroke in drawing.data.strokes:
            count = convert_stroke(stroke, vertices, edges, faces, attributes, base_vertex)
            base_vertex += count

        mesh.from_pydata(vertices, edges, faces)
        assign_attributes(config, mesh, attributes)
        mesh.materials.append(material)

        index += 1

    animate(drawing_to_obj, layer)


def convert_stroke(stroke, vertices, edges, faces, attributes, base_vertex):
    """Convert a Quill stroke to connected polygons."""

    # Stroke conversion.
    # One paint stroke becomes an island of connected polygons.
    # At each quill vertex, generate a cross section based on the brush type,
    # then connect the cross section vertices into quad faces.
    # We do this manually instead of using a curve and bevel object to have maximum control
    # over the resulting shape and match the Quill brush types as closely as possible.

    # base_vertex is the index of the next vertex to add,
    # this is used to index vertices from face corners.

    # Brush to mesh conversion parameters
    # resolution is the number of vertices in the cross section.
    offset = 0
    aspect = 1.0
    brush = stroke.brush_type
    if brush == BrushType.CYLINDER:
        # Cylinder brush: regular heptagon.
        resolution = 7
        face_count = resolution
    elif brush == BrushType.ELLIPSE:
        # Ellipse brush: flattened heptagon.
        resolution = 7
        face_count = resolution
        aspect = 0.3
    elif brush == BrushType.CUBE:
        # Cube brush: square.
        resolution = 4
        offset = - 0.75 * math.pi
        face_count = resolution
    else:
        # Ribbon brush: single face, no wrap around.
        resolution = 2
        face_count = 1

    sector = 2 * math.pi / resolution

    # Loop through quill vertices.
    for i in range(len(stroke.vertices)):

        quill_vertex = stroke.vertices[i]
        center = mathutils.Vector(quill_vertex.position)
        radius = quill_vertex.width

        # Cubic brush has a wider cross-section corresponding to the
        # circumscribed square around the idealized stroke circle.
        if brush == BrushType.CUBE:
            radius = math.sqrt(2*radius*radius)

        basis = compute_basis(stroke, i, center, quill_vertex.normal)

        # Generate the cross section vertices.
        for u in range(resolution):
            # Define the cross section on the XZ plane and then transform it to the drawing space.
            theta = u * sector + offset
            x = radius * math.cos(theta)
            y = 0
            z = radius * math.sin(theta) * aspect

            p = basis @ mathutils.Vector((x, y, z))
            p = center + p
            vertices.append(p)
            color = (quill_vertex.color[0], quill_vertex.color[1], quill_vertex.color[2], 1.0)

            # It appears that Blender assumes the incoming vertex colors are in sRGB instead
            # of linear, so we apply a conversion here.
            # TODO: should alpha be converted as well?
            color_linear = [linear_to_srgb(c) for c in color]
            color_linear[3] = quill_vertex.opacity

            # Duplicate the Quill vertex data at each vertex of the cross section.
            # The extra attributes may be used to export back the data to Quill.
            attributes["rgba"].append(color_linear)
            attributes["stroke"].append(stroke.id)
            attributes["brush"].append(brush.value)
            attributes["index"].append(i)
            attributes["p"].append(quill_vertex.position)
            attributes["n"].append(quill_vertex.normal)
            attributes["t"].append(quill_vertex.tangent)
            attributes["w"].append(quill_vertex.width)

        # Connect the vertices into quad faces.
        if i == 0:
            continue

        for u in range(face_count):
            # Clockwise winding starting bottom left.
            v0 = (i - 1) * resolution + u
            v1 = (i - 1) * resolution + (u + 1) % resolution
            v2 = i * resolution + (u + 1) % resolution
            v3 = i * resolution + u
            face = [v0 + base_vertex, v1 + base_vertex, v2 + base_vertex, v3 + base_vertex]
            faces.append(face)

    # Return the number of vertices generated.
    return resolution * len(stroke.vertices)


def compute_basis(stroke, i, center, normal):
    # Basis to match the stroke rotation along its longitudinal axis.
    # This must reproduce exactly what Quill does as the brushes
    # are not isotropic (ribbon, ellipse, cube).
    #
    # This code is adapted from Element::ComputeBasis at
    # https://github.com/Immersive-Foundation/IMM/blob/main/code/libImmImporter/src/document/layerPaint/element.cpp

    yaxis = compute_tangent(stroke, i, center)
    epsilon = 0.0000001

    zaxis = mathutils.Vector(normal)
    xaxis = zaxis.cross(yaxis)
    if xaxis.length >= epsilon:
        xaxis = xaxis.normalized()
    elif abs(yaxis.x) < 0.9:
         xaxis = mathutils.Vector((0, yaxis.z, yaxis.y))
    elif abs(yaxis.y) < 0.9:
         xaxis = mathutils.Vector((-yaxis.z, 0, yaxis.x))
    else:
         xaxis = mathutils.Vector((yaxis.y, -yaxis.x, 0))

    zaxis = yaxis.cross(xaxis).normalized()

    basis = mathutils.Matrix((
        [xaxis.x, yaxis.x, zaxis.x, 0],
        [xaxis.y, yaxis.y, zaxis.y, 0],
        [xaxis.z, yaxis.z, zaxis.z, 0],
        [0, 0, 0, 1]))

    return basis


def compute_tangent(stroke, i, point):

    # Compute direction of the stroke at a given point.
    # This code is adapted from Element::ComputeTangent at
    # https://github.com/Immersive-Foundation/IMM/blob/main/code/libImmImporter/src/document/layerPaint/element.cpp

    epsilon = 0.0000001

    # Find first valid forward difference.
    forward = mathutils.Vector((0, 0, 0))
    for j in range(i + 1, len(stroke.vertices)):
        delta = mathutils.Vector(stroke.vertices[j].position) - point
        if delta.length >= epsilon:
            forward = delta.normalized()
            break

    # Find first valid backward difference.
    backward = mathutils.Vector((0, 0, 0))
    for j in range(i - 1, -1, -1):
        delta = point - mathutils.Vector(stroke.vertices[j].position)
        if delta.length >= epsilon:
            backward = delta.normalized()
            break

    # Average
    yaxis = forward + backward
    if yaxis.length >= epsilon:
        return yaxis.normalized()

    # If that's still zero, go for a desperate solution - overal stroke direction + noise.
    last = mathutils.Vector(stroke.vertices[-1].position)
    first = mathutils.Vector(stroke.vertices[0].position)
    yaxis = (last - first + mathutils.Vector((0.000001, 0.000002, 0.000003))).normalized()
    return yaxis


def assign_attributes(config, mesh, attributes):

    # Go back through all the created polygons and assign attributes.
    # The original Quill vertex data is spread over all the vertices making up the cross section.
    # RGBA color is stored in the corner domain, the extra attributes are stored on points directly.

    # Vertex colors ( + set smooth shading)
    mesh.color_attributes.new(name="rgba", type="BYTE_COLOR", domain="CORNER")
    for poly in mesh.polygons:
        poly.use_smooth = True
        for vert_i_poly, vert_i_mesh in enumerate(poly.vertices):
            vert_i_loop = poly.loop_indices[vert_i_poly]
            mesh.attributes["rgba"].data[vert_i_loop].color_srgb = attributes["rgba"][vert_i_mesh]

    # Extra attributes
    if config["extra_attributes"]:
        mesh.attributes.new(name="q_stroke", type="INT", domain="POINT")
        mesh.attributes.new(name="q_brush", type="INT", domain="POINT")
        mesh.attributes.new(name="q_index", type="INT", domain="POINT")
        mesh.attributes.new(name="q_p", type="FLOAT_VECTOR", domain="POINT")
        mesh.attributes.new(name="q_n", type="FLOAT_VECTOR", domain="POINT")
        mesh.attributes.new(name="q_t", type="FLOAT_VECTOR", domain="POINT")
        mesh.attributes.new(name="q_w", type="FLOAT", domain="POINT")
        for vert in mesh.vertices:
            vert_i = vert.index
            mesh.attributes["q_stroke"].data[vert_i].value = attributes["stroke"][vert_i]
            mesh.attributes["q_brush"].data[vert_i].value = attributes["brush"][vert_i]
            mesh.attributes["q_index"].data[vert_i].value = attributes["index"][vert_i]
            mesh.attributes["q_p"].data[vert_i].vector = attributes["p"][vert_i]
            mesh.attributes["q_n"].data[vert_i].vector = attributes["n"][vert_i]
            mesh.attributes["q_t"].data[vert_i].vector = attributes["t"][vert_i]
            mesh.attributes["q_w"].data[vert_i].value = attributes["w"][vert_i]


def animate(drawing_to_obj, layer):
    # drawing_to_obj: maps the index of the drawing in Quill to the corresponding Blender object.
    # layer: the Quill paint layer.

    #--------------------------------------------------------------
    # Animation of the paint layer.
    # This covers multiple concepts:
    # - Frame by frame animation (multi-drawing layer)
    # - Looping (max_repeat_count)
    # - Spans (in and out points)
    # - Left-trimming a span (offset)
    # - Spans and offset of the parent groups, recursively all the way to the root.
    # - Sequences vs Groups, and sequence looping.
    # - Frame rate
    # - Frame range
    # We treat everything here because Blender empty objects aren't a good match for Quill groups,
    # as they don't inherit visibility and there is no concept of offsetting.
    # So all the visibility information from parent groups is baked into the children.
    #--------------------------------------------------------------

    #--------------------------------------------------------------
    # Blender frame range vs Quill animation range.
    # We will loop through Blender frames and show the corresponding drawing.
    # Heuristic:
    # - if the scene starts before 0, we import from 0 until the end.
    # - if the scene starts at 0, we import from 0 until the end.
    # - if the scene starts at 1 (blender default), we change it to start at 0, then import from 0 to the end.
    # - if the scene starts after 1, we change it to start at 0, import from 0 to how many frames the original range was,
    # and change the end to match the number of frames.
    # We do this to cope with Blender scenes set up between say 1000 and 1249, which is done to create a buffer for simulations.
    # Instead of importing from 0 to 1249 we import from 0 to 249. We don't try to import from 1000 to 1249.
    # Bottom line: if a buffer is needed for simulation, start the frame range in the negative instead of 1000.
    #--------------------------------------------------------------
    scn = bpy.context.scene
    import_end = scn.frame_end
    if scn.frame_start <= 0:
        import_start = 0
    elif scn.frame_start == 1:
        scn.frame_start = 0
        import_start = 0
    else:
        count_frames = scn.frame_end - scn.frame_start
        scn.frame_start = 0
        import_start = 0
        import_end = count_frames
        scn.frame_end = count_frames

    # Force frame rate to match Quill scene.
    if layer.implementation.framerate != scn.render.fps:
        scn.render.fps = int(layer.implementation.framerate)

    # Start by hiding all drawings from the very beginning.
    # We revisit this at the end to remove that keyframe if not really necessary
    # in case of a single, always visible drawing.
    for i in range(len(drawing_to_obj)):
        hide_drawing(i, min(scn.frame_start, import_start), drawing_to_obj)


    # Quill animation features.

    # 1. The lowest level is the basic sequence of drawings, for frame by frame animation. 
    # Quill format uses a fully expanded frame list pointing to the drawing indices.
    # The drawings are not necessarily stored in order of apparition in the timeline.
    # Framelist: [2, 2, 2, 0, 1, 2, 3, 3, 0]
    # This basic animated sequence is what gets exported by Quill Alembic/FBX exporter.
    # The sequence can be looped.

    # 2. The second level is a concept of "spans".
    # These let us stop and restart the animated sequence on the same layer.
    # The length of a span may be a fractional number of loops.
    # This is controlled by in and out points, the [ and ] icons in Quill.
    # https://www.youtube.com/watch?v=1w0wk2Sjih0
    # In the file format each in and out point becomes a visibility key frame.
    # Importantly, when we restart a visibility span it restarts at the first drawing
    # of the basic sequence, not where it would be from looping.

    # 3. The third concept is offsetting.
    # To control where in the basic sequence the span starts at, that is, which drawing is
    # shown on the first frame of a new span, we left-trim the block of frames.
    # In the format this results in an offset key frame.
    # In theory there should be one offset key frame for each in-point.
    # The value of the offset key frame is a time, not a frame index.

    # 4. The fourth concept is the visibility of the parent groups.
    # Normal groups can have spans.
    # Sequence groups can have spans, offsets, and looping.
    # Sequence groups have the "timeline" property to True, other than that the format is the same.
    # The parent groups can also have their "world visibility" on or off (the eye icon in Quill).

    # None of these concepts exist as such in Blender.
    # We must bake all the visibility information into the drawings themselves.
    # This is done by keyframing the hide_viewport and hide_render properties.
    # We also need to expand the Blender timeline to encompass the Quill timeline.

    # Points unclear:
    # - StartOffset property. This seems redundant with the first offset key frame.
    # - Layers with "Timeline" : false, and MaxRepeatCount: "0", and offsets.

    # There are three cases:
    # - single drawing layer: treated as an infinite loop.
    # - multi-drawing layer without loop.
    # - multi-drawing layer with loop.

    # Approaches.
    # We can either loop through the frames of the Blender timeline and show the
    # corresponding drawing, or loop through Quill key frames and set things up in Blender.
    # The first option seems simpler and more robust. Because we can have nested timelines
    # and groups, with optional looping, but with spans that restart at the beginning or at an offset,
    # it seems very complicated to handle this with keyframing in blender.
    # The drawback is that it's not clear how to find the last frame of the animation.

    # For any given frame in the Blender timeline, we do:
    # blender frame -> global time -> relative time -> local time -> quill frame -> quill drawing -> blender obj.
    # - relative time is the time since the start of the span.
    # - local time is the time within the drawing sequence taking offset and looping into account.

    # Loop through the Blender frames and show the corresponding drawing.
    is_visible = False
    kkvv = layer.animation.keys.visibility
    kkoo = layer.animation.keys.offset
    ticks_per_second = 12600
    fps = scn.render.fps
    active_drawing_index = -1
    for frame_target in range(import_start, import_end + 1):
        print("processing:", frame_target)

        # Convert time to Quill ticks for easier comparison with key frames.
        # Everything after this point is in Quill time.
        global_time = (frame_target / fps) * ticks_per_second
        print("global_time:", global_time)

        # TODO: find the current active key in the parent hierarchy,
        # update start time, update timeline time: the time relative
        # to the span start in the parent.
        # This must handle looping of any parent timeline here?
        timeline_time = global_time

        # Time relative to current span start.
        # Find the visibility key frame right before the current frame, at the layer level.
        last_key = None
        for i in range(len(kkvv)):
            if kkvv[i].time > timeline_time:
                break

            last_key = kkvv[i]

        # Bail out if we are before the first key frame.
        if last_key is None:
            continue

        if last_key.value == True:

            # We are within an active span.
            # A drawing must be visible, find which one.
            is_visible = True
            print("\twithin span")

            # Check if there is an offset key matching the in-point.
            local_start_offset = 0
            for i in range(len(kkoo)):
                if kkoo[i].time == last_key.time:
                    local_start_offset = kkoo[i].value
                    break

            # Time within the lower level frame animation sequence.
            local_time = timeline_time - last_key.time + local_start_offset

            # Convert back to a frame index
            frame_source = math.floor(local_time / ticks_per_second * fps + 0.5)

            # Take layer-level looping into account.
            looping = layer.implementation.max_repeat_count == 0
            if looping:
                frame_source = frame_source % len(layer.implementation.frames)
            else:
                frame_source = min(frame_source, len(layer.implementation.frames) - 1)

            # Get the actual drawing that should be visible.
            drawing_index = int(layer.implementation.frames[frame_source])

            # Bail out if we are still on the same drawing.
            # We have already set a key frame to show it during a previous iteration.
            # This happens for frame holds.
            if drawing_index == active_drawing_index:
                continue

            # Change active drawing.
            hide_drawing(active_drawing_index, frame_target, drawing_to_obj)
            print("\thidden drawing:", active_drawing_index)
            show_drawing(drawing_index, frame_target, drawing_to_obj)
            active_drawing_index = drawing_index
            print("\tshowing drawing:", active_drawing_index)

        else:
            print("\tbetween spans")
            # We are between spans, all drawings must be hidden.
            if not is_visible:
                continue

            hide_drawing(active_drawing_index, frame_target, drawing_to_obj, True)
            print("\thidden drawing:", active_drawing_index)
            active_drawing_index = -1
            is_visible = False


def hide_drawing(drawing_index, frame, drawing_to_obj, hide=True):

    if drawing_index == -1:
        return

    obj = drawing_to_obj[drawing_index]
    obj.hide_viewport = hide
    obj.keyframe_insert(data_path="hide_viewport", frame=frame)
    obj.hide_render = hide
    obj.keyframe_insert(data_path="hide_render", frame=frame)


def show_drawing(drawing_index, frame, drawing_to_obj):
    hide_drawing(drawing_index, frame, drawing_to_obj, False)


def linear_to_srgb(v):
    if (v > 0.0031308):
        return 1.055 * v ** (1./2.4) - 0.055
    else:
        return 12.92 * v