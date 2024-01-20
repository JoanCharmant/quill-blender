

import bpy
from ..model import sequence

def convert(obj, config):
    """Convert a single mesh into a series of paint strokes"""
    paint_layer = sequence.Layer.create_paint_layer(obj.name)
    # create an empty drawing.
    # keep track of the visited edges.
    # for each edge of each polygon.
    # find start and end of edge.
    # if not visited, make a paint stroke for the edge.
    # add the stroke to the drawing.
    # update bounding box of the drawing.
    # update the qbin offset in the paint layer.
    return paint_layer

def make_edge_stroke(start, end, config):
    pass
    # convert length unit.
    # create an empty paint stroke.
    # set brush type, rotational opacity.
    # compute number of segments based on paint speed.
    # build list of segments.
    # convert segments to quill vertices.
    # update the bounding box of the stroke.
    # return the stroke.


