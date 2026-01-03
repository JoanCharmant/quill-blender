import bpy

def convert(obj, layer):
    """
    Converts a Quill paint layer to a Blender grease pencil object.

    Imports the base frame-by-frame animation with optional looping. Not clips.

    :param obj: Blender object to populate with grease pencil data.
    :param layer: Quill paint layer to convert.
    """

    drawings = layer.implementation.drawings
    if drawings is None or len(drawings) == 0:
        return

    gpencil_data = obj.data

    # GPencil data tab > Strokes group.
    # Stroke depth order: '3D' may create an undesirable effect for self overlaping
    # and partially transparent strokes, but it's the only way to get the correct stroke order,
    # if we set to 2D the strokes will be drawn in the order they were created, ignoring 3D location.
    gpencil_data.stroke_depth_order = '3D'

    if bpy.app.version < (4, 3, 0):
        # Grease Pencil v2
        # Stroke thickness space: when using World space the line width seems to be expressed in millimeters.
        # We’ll lock the line width to 1 meter and use the pressure property to scale it.
        gpencil_data.stroke_thickness_space = 'WORLDSPACE'

    # Put everything on a single GPencil layer.
    gpencil_layer = gpencil_data.layers[0]
    gpencil_layer.opacity = layer.opacity

    # Delete the default frame, we'll create our own.
    if bpy.app.version < (4, 3, 0):
        gpencil_layer.frames.remove(gpencil_layer.frames[0])
    else:
        gpencil_layer.frames.remove(gpencil_layer.frames[0].frame_number)


    # Blender frame range vs Quill animation range.
    # We will loop through Blender frames and show the corresponding drawing.
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

    # Loop through the Blender frames and show the corresponding drawing.
    # We only support the base frame-by-frame animation + optional looping.
    active_drawing_index = -1
    for frame_target in range(import_start, import_end + 1):
        #print("processing:", frame_target)

        frame_source = frame_target

        # Take layer-level looping into account.
        looping = layer.implementation.max_repeat_count == 0
        if looping:
            frame_source = frame_source % len(layer.implementation.frames)
        else:
            frame_source = min(frame_source, len(layer.implementation.frames) - 1)

        # Get the actual drawing that should be visible.
        drawing_index = int(layer.implementation.frames[frame_source])

        # Bail out if we are still on the same drawing (frame hold).
        if drawing_index == active_drawing_index:
            continue

        active_drawing_index = drawing_index

        # Add a frame and import the drawing.
        gpencil_layer.frames.new(frame_target)

        # Inside Quill UI it's not possible to duplicate a drawing past another one,
        # the only duplication that can happen is frame-hold.
        # We don't need to keep track of previously imported drawings.
        import_drawing(drawings[drawing_index], gpencil_layer.frames[-1])


def import_drawing(drawing, gp_frame):
    """
    Convert a Quill drawing to a GP frame (v2) or GP drawing (v3).

    :param drawing: Quill drawing to convert.
    :param gp_frame: Blender GP frame to populate.
    """

    # https://developer.blender.org/docs/features/grease_pencil/architecture/
    # https://docs.blender.org/api/current/bpy.types.GPencilLayer.html
    # https://docs.blender.org/api/current/bpy.types.GPencilFrame.html
    # https://docs.blender.org/api/current/bpy.types.GreasePencilDrawing.html
    # https://docs.blender.org/api/current/bpy.types.GPencilStroke.html
    # https://docs.blender.org/api/current/bpy.types.GPencilStrokePoint.html

    if drawing.data is None:
        return

    if bpy.app.version < (4, 3, 0):

        # Grease Pencil v2
        # Layer > Frame > Stroke > Point.

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
                gp_point.vertex_color = (vertex.color[0], vertex.color[1], vertex.color[2], 1)

    else:

        # Grease Pencil v3
        # Layer > Frame > Drawing > Stroke > Point.

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
                gp_point.vertex_color = (vertex.color[0], vertex.color[1], vertex.color[2], 1)

                vertex_index += 1
