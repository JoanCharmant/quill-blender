import bpy
import math
import mathutils
from ..model.paint import BrushType

def convert(mesh, layer):
    """Convert a Quill paint layer to a Blender mesh object."""

    drawings = layer.implementation.drawings
    if drawings is None or len(drawings) == 0:
        return

    # Only support the first drawing for now.
    drawing = drawings[0]
    if drawing.data is None:
        return

    vertices = []
    edges = []
    faces = []
    vertex_colors = []

    # Stroke conversion.
    # At each quill vertex, generate a cross section based on the brush type,
    # then connect the cross section vertices into quad faces.
    # We do this manually instead of using a curve and bevel object to have maximum control
    # over the resulting shape and match the Quill brush types as closely as possible.
    base_vertex = 0
    for stroke in drawing.data.strokes:
        count = convert_stroke(stroke, vertices, edges, faces, vertex_colors, base_vertex)
        base_vertex += count

    mesh.from_pydata(vertices, edges, faces)
    assign_vertex_colors(mesh, vertex_colors)


def convert_stroke(stroke, vertices, edges, faces, vertex_colors, base_vertex):
    """Convert a Quill stroke to connected polygons."""

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
            vertex_colors.append(color_linear)

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

    yaxis = compute_tangent(stroke, i, center, normal)
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


def compute_tangent(stroke, i, point, normal):

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


def assign_vertex_colors(mesh, vertex_colors):
    # Vertex colors and smooth shading
    mesh.vertex_colors.new(name="rgba")
    for poly in mesh.polygons:
        poly.use_smooth = True
        for vert_i_poly, vert_i_mesh in enumerate(poly.vertices):
            vert_i_loop = poly.loop_indices[vert_i_poly]
            mesh.vertex_colors["rgba"].data[vert_i_loop].color = vertex_colors[vert_i_mesh]


def linear_to_srgb(v):
    if (v > 0.0031308):
        return 1.055 * v ** (1./2.4) - 0.055
    else:
        return 12.92 * v