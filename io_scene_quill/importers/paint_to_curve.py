
def convert(obj, layer):
    """Convert a Quill paint layer to a Blender curve object with polyline splines."""
    
    drawings = layer.implementation.drawings
    if drawings is None or len(drawings) == 0:
        return
    
    curve_data = obj.data
    curve_data.dimensions = '3D'
    curve_data.resolution_u = 2
    
    # Only import the first drawing for now.
    import_drawing(drawings[0], curve_data)


def import_drawing(drawing, curve_data):
    
    if drawing.data is None:
        return
    
    for stroke in drawing.data.strokes:
        polyline = curve_data.splines.new('POLY')
        # There is already one point by default so we only need to add count-1.
        polyline.points.add(len(stroke.vertices) - 1)
        for i in range(len(stroke.vertices)):
            vertex = stroke.vertices[i]
            polyline.points[i].co = (vertex.position[0], vertex.position[1], vertex.position[2], 1)
            polyline.points[i].radius = vertex.width
