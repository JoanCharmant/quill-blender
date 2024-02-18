import bpy
import math
import mathutils

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

    tau = 2 * math.pi

    # self.normal = normal
    # self.tangent = tangent
    # self.color = color
    # self.opacity = opacity

    base_vertex = 0

    # Stroke conversion.
    # At each quill vertex, generate a cross section based on the brush type,
    # then connect the cross section vertices into quad faces.
    # We do this manually instead of using a curve and bevel object to have maximum control
    # over the resulting shape and match the Quill brush types as closely as possible.
    for stroke in drawing.data.strokes:

        #stroke.brush_type
        # CYLINDER cross section is an heptagon.
        resolution = 7
        sector = tau / resolution

        for i in range(len(stroke.vertices)):

            vertex = stroke.vertices[i]
            center = mathutils.Vector(vertex.position)
            radius = vertex.width

            # Rotation basis to match the stroke orientation.
            # TODO: lerp between the orientations based on the previous and next vertex.
            yaxis = mathutils.Vector((0, 1, 0))
            if i < len(stroke.vertices) - 1:
                next = mathutils.Vector(stroke.vertices[i + 1].position)
                yaxis = (next - center).normalized()
            temp = mathutils.Vector((0, 0, 1))
            xaxis = temp.cross(-yaxis)
            zaxis = xaxis.cross(yaxis)
            basis = mathutils.Matrix((
                [xaxis.x, yaxis.x, zaxis.x, 0],
                [xaxis.y, yaxis.y, zaxis.y, 0],
                [xaxis.z, yaxis.z, zaxis.z, 0],
                [0, 0, 0, 1]))

            # Generate the cross section vertices.
            for u in range(resolution):
                # Define the cross section on the XZ plane and then transform
                # it to the drawing space.
                theta = u * sector
                x = radius * math.cos(theta)
                y = 0
                z = radius * math.sin(theta)
                p = mathutils.Vector((x, y, z))

                p = basis @ p
                p = center + p

                vertices.append(p)
                vertex_colors.append((vertex.color[0], vertex.color[1], vertex.color[2], 1.0))

            # Connect the vertices into quad faces.
            if i == 0:
                continue

            for u in range(resolution):
                # Clockwise winding.
                v0 = (i - 1) * resolution + u
                v1 = i * resolution + u
                v2 = i * resolution + (u + 1) % resolution
                v3 = (i - 1) * resolution + (u + 1) % resolution
                face = [v0 + base_vertex, v1 + base_vertex, v2 + base_vertex, v3 + base_vertex]
                faces.append(face)

        base_vertex += resolution * len(stroke.vertices)

    mesh.from_pydata(vertices, edges, faces)

    # Vertex colors and smooth shading
    mesh.vertex_colors.new(name="rgb")
    for poly in mesh.polygons:
        poly.use_smooth = True
        for vert_i_poly, vert_i_mesh in enumerate(poly.vertices):
            vert_i_loop = poly.loop_indices[vert_i_poly]
            mesh.vertex_colors["rgb"].data[vert_i_loop].color = vertex_colors[vert_i_mesh]

    # Create a material node tree for vertex colors.
    mat = bpy.data.materials.new(name=layer.name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()

    node_vc = nodes.new(type="ShaderNodeVertexColor")
    node_vc.layer_name = "rgb"
    node_vc.location = 0, 0

    node_bsdf = nodes.new(type="ShaderNodeBsdfDiffuse")
    node_bsdf.location = 200, 0

    node_output = nodes.new(type="ShaderNodeOutputMaterial")
    node_output.location = 400, 0

    mat.node_tree.links.new(node_vc.outputs[0], node_bsdf.inputs[0])
    mat.node_tree.links.new(node_bsdf.outputs[0], node_output.inputs[0])

    mesh.materials.append(mat)