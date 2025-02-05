import bpy

def convert(obj, layer):
    """Convert a Quill paint layer to a Blender grease pencil object."""

    drawings = layer.implementation.drawings
    if drawings is None or len(drawings) == 0:
        return

    gpencil_data = obj.data

    # GPencil data tab > Strokes group.
    # Stroke depth order: '3D' may create an undesirable self overlap effect on strokes,
    # but it's the only way to get the correct stroke order, if we set to 2D the strokes
    # will be drawn in the order they were created ignoring 3D location.
    gpencil_data.stroke_depth_order = '3D'

    if bpy.app.version < (4, 3, 0):
        # Grease Pencil v2
        # Stroke thickness space: when using World space the line width seems to be expressed in millimeters.
        # We’ll lock the line width to 1 meter and use the pressure property to scale it.
        gpencil_data.stroke_thickness_space = 'WORLDSPACE'

    # Put everything on a single GPencil layer.
    gpencil_layer = gpencil_data.layers[0]
    gpencil_layer.opacity = layer.opacity

    for drawing in drawings:

        # Convert a Quill drawing to a GP frame.
        if drawing.data is None:
            continue

        gp_frame = gpencil_layer.frames[0]

        if bpy.app.version < (4, 3, 0):

            # Grease Pencil v2

            for stroke in drawing.data.strokes:

                gp_stroke = gp_frame.strokes.new()

                gp_stroke.display_mode = '3DSPACE'
                gp_stroke.line_width = 1000
                gp_stroke.start_cap_mode = 'ROUND'
                gp_stroke.end_cap_mode = 'ROUND'

                for vertex in stroke.vertices:
                    index = len(gp_stroke.points)
                    gp_stroke.points.add(1)
                    gp_point = gp_stroke.points[index]

                    gp_point.co = (vertex.position[0], vertex.position[1], vertex.position[2])
                    gp_point.pressure = vertex.width * 2
                    gp_point.strength = vertex.opacity
                    gp_point.vertex_color = (vertex.color[0],
                                            vertex.color[1],
                                            vertex.color[2],
                                            1)

        else:

            # Grease Pencil v3
            # https://developer.blender.org/docs/features/grease_pencil/architecture/
            # Layer > Frame > Drawing > Stroke > Point.
            # https://docs.blender.org/api/current/bpy.types.GPencilLayer.html
            # https://docs.blender.org/api/current/bpy.types.GPencilFrame.html
            # https://docs.blender.org/api/current/bpy.types.GreasePencilDrawing.html
            # https://docs.blender.org/api/current/bpy.types.GPencilStroke.html
            # https://docs.blender.org/api/current/bpy.types.GPencilStrokePoint.html

            gp_drawing = gp_frame.drawing

            for stroke in drawing.data.strokes:

                gp_drawing.add_strokes([len(stroke.vertices)])
                stroke_index = len(gp_drawing.strokes) - 1

                gp_stroke = gp_drawing.strokes[stroke_index]
                gp_stroke.cyclic = False
                gp_stroke.start_cap = 0 # Round
                gp_stroke.end_cap = 0

                vertex_index = 0
                for vertex in stroke.vertices:

                    gp_point = gp_stroke.points[vertex_index]
                    gp_point.position = (vertex.position[0], vertex.position[1], vertex.position[2])
                    gp_point.radius = vertex.width
                    gp_point.opacity = vertex.opacity
                    gp_point.vertex_color = (vertex.color[0],
                                             vertex.color[1],
                                             vertex.color[2],
                                             1)

                    vertex_index += 1


def linear_to_srgb(v):
    if (v > 0.0031308):
        return 1.055 * v ** (1./2.4) - 0.055
    else:
        return 12.92 * v


def srgb_to_linear(v):
    if v < 0.04045:
        return 0.0 if v < 0.0 else v * (1.0 / 12.92)
    else:
        return pow((v + 0.055) * (1.0 / 1.055), 2.4)