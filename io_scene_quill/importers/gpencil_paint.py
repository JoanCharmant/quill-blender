import bpy

def convert(obj, layer):
    """Convert a Quill paint layer to a Blender grease pencil object."""

    drawings = layer.implementation.drawings
    if drawings is None or len(drawings) == 0:
        return

    gpencil_data = obj.data

    # Note: when using World space the line width seems to be expressed in millimeters.
    # We’ll lock the line width to 1 meter and use the pressure property to scale it.
    gpencil_data.stroke_thickness_space = 'WORLDSPACE'
    gpencil_data.stroke_depth_order = '3D'
    gpencil_layer = gpencil_data.layers[0]
    gpencil_layer.opacity = layer.opacity

    for drawing in drawings:
        if drawing.data is None:
            continue

        # TODO: create a frame per drawing.
        gp_frame = gpencil_layer.frames[0]

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