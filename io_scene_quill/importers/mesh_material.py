import bpy
import math
import mathutils

def create_diffuse(name):
    """Creates a basic Diffuse BSDF and bind vertex colors"""

    material = bpy.data.materials.new(name=name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    nodes.clear()

    node_vc = nodes.new(type="ShaderNodeVertexColor")
    node_vc.layer_name = "rgba"
    node_vc.location = 0, 0

    node_bsdf = nodes.new(type="ShaderNodeBsdfDiffuse")
    node_bsdf.location = 200, 0

    node_output = nodes.new(type="ShaderNodeOutputMaterial")
    node_output.location = 400, 0

    material.node_tree.links.new(node_vc.outputs["Color"], node_bsdf.inputs["Color"])
    material.node_tree.links.new(node_bsdf.outputs["BSDF"], node_output.inputs["Surface"])

    return material


def create_principled(name):
    """Creates a Principled BSDF and bind vertex colors"""

    material = bpy.data.materials.new(name=name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    nodes.clear()

    node_vc = nodes.new(type="ShaderNodeVertexColor")
    node_vc.layer_name = "rgba"
    node_vc.location = 0, 0

    node_bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")
    node_bsdf.location = 200, 0
    node_bsdf.inputs["IOR"].default_value = 1.0

    node_output = nodes.new(type="ShaderNodeOutputMaterial")
    node_output.location = 500, 0

    # Force all normals to be fixed to a single direction to "flatten" the paint strokes.
    node_normal = nodes.new(type="ShaderNodeNormal")
    node_normal.location = 0, -200
    node_normal.outputs[0].default_value = (0, 0, 1)

    # Noodles connecting everything.
    material.node_tree.links.new(node_vc.outputs["Color"], node_bsdf.inputs["Base Color"])
    material.node_tree.links.new(node_vc.outputs["Alpha"], node_bsdf.inputs["Alpha"])
    material.node_tree.links.new(node_bsdf.outputs["BSDF"], node_output.inputs["Surface"])
    material.node_tree.links.new(node_normal.outputs["Normal"], node_bsdf.inputs["Normal"])

    # Set Alpha Blend mode to "Alpha Hashed" instead of "Opaque".
    material.blend_method = "HASHED"
    material.shadow_method = "HASHED"

    return material