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

    # Animate visibility
    # Quill requires a fully expanded frame list.
    # Ex: "Frames" : [ "0", "1", "2", "3", "4", "5", "6", "6", "6", "6", "7", "8", "9"]

    # Special case for single frame.
    # Nothing more to do.
    if len(drawings) == 1 and len(layer.implementation.frames) == 1 and layer.implementation.max_repeat_count <= 1:
        return

    # Hide all drawings within the blender scene range.
    scn = bpy.context.scene
    for _, obj in drawing_to_obj.items():
        obj.hide_viewport = True
        obj.keyframe_insert(data_path="hide_viewport", frame=scn.frame_start)
        obj.keyframe_insert(data_path="hide_viewport", frame=scn.frame_end)
        obj.hide_render = True
        obj.keyframe_insert(data_path="hide_render", frame=scn.frame_start)
        obj.keyframe_insert(data_path="hide_render", frame=scn.frame_end)

    # Loop through the Blender output frames and show the corresponding drawing.
    # Blender default range starts at 1, Quill at 0, so we need to adjust the frame index.
    # frame_start: first frame in Blender timeline, used as an offset to map to Quill timeline.
    # frame_target: the index of the frame in the blender timeline we are showing the drawing on.
    # frame_source: the index of the frame in the Quill timeline we are copying the drawing from.
    # drawing_index: the actual index of the drawing in the list of drawings (the drawings are in
    # order but they might be duplicated on the quill timeline so don't map with frames.)
    prev_drawing_index = -1
    frame_start = scn.frame_start
    for frame_target in range(scn.frame_start, scn.frame_end + 1):
        frame_source = frame_target - frame_start
        if layer.implementation.framerate != scn.render.fps:
            time = frame_source / scn.render.fps
            frame_source = math.floor(time * layer.implementation.framerate + 0.5)

        looping = layer.implementation.max_repeat_count == 0
        if not looping and frame_source >= len(layer.implementation.frames):
            break

        # Get the source frame index and the drawing index.
        frame_source = frame_source % len(layer.implementation.frames)
        drawing_index = int(layer.implementation.frames[frame_source])

        # If it's the same drawing we keep it visible so nothing more to do.
        if drawing_index == prev_drawing_index:
            continue

        # Changing drawing: hide the previous one if any.
        if prev_drawing_index != -1:
            obj = drawing_to_obj[prev_drawing_index]
            obj.hide_viewport = True
            obj.keyframe_insert(data_path="hide_viewport", frame=frame_target)
            obj.hide_render = True
            obj.keyframe_insert(data_path="hide_render", frame=frame_target)

        # Show current drawing.
        obj = drawing_to_obj[drawing_index]
        obj.hide_viewport = False
        obj.keyframe_insert(data_path="hide_viewport", frame=frame_target)
        obj.hide_render = False
        obj.keyframe_insert(data_path="hide_render", frame=frame_target)

        prev_drawing_index = drawing_index


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
            v1 = i * resolution + u
            v2 = i * resolution + (u + 1) % resolution
            v3 = (i - 1) * resolution + (u + 1) % resolution
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
    yaxis = (last - first + mathutils.Vector(0.000001, 0.000002, 0.000003)).normalized()
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




def linear_to_srgb(v):
    if (v > 0.0031308):
        return 1.055 * v ** (1./2.4) - 0.055
    else:
        return 12.92 * v