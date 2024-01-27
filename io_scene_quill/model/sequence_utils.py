

def delete_hidden(layer):
    """Delete all hidden layers recursively."""
    if layer.type == "Group":
        for child in layer.implementation.children:
            if child.type == "Group" and child.visible:
                delete_hidden(child)

        layer.implementation.children = [child for child in layer.implementation.children if child.visible]


def delete_type(layer, type):
    """Delete all layers of a given type recursively."""
    if layer.type == "Group":
        for child in layer.implementation.children:
            if child.type == "Group":
                delete_type(child, type)

        layer.implementation.children = [child for child in layer.implementation.children if child.type != type]
