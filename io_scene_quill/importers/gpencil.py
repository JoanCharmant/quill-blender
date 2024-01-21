import bpy

def convert(obj, layer):
    """Convert a Quill paint layer to a Blender grease pencil object."""

    gpencil_data = obj.data

    # When using World space the line width seems to be expressed in millimeters.
    # We’ll lock the line width to 1 meter and use the pressure property to scale it.
    # The pressure property is limited to 0..1 range, this means we cannot
    # express strokes wider than 1 meter.
    gpencil_data.stroke_thickness_space = 'WORLDSPACE'
    gpencil_data.stroke_depth_order = '3D'
    gpencil_layer = gpencil_data.layers[0]

    drawings = layer.implementation.drawings
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
                gp_point.pressure = vertex.width
                gp_point.strength = vertex.opacity
                gp_point.vertex_color = (vertex.color[0], vertex.color[1], vertex.color[2], 1)
