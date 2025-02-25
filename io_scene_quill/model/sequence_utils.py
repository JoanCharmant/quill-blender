

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


def is_empty_group(layer):
        """Returns true if a layer is a group with no children."""
        return layer.type == "Group" and len(layer.implementation.children) == 0


def delete_empty_groups(layer):
    """Delete empty groups recursively."""

    if layer.type != "Group":
        return

    # Traverse depth first and delete empty leaf groups.
    for child in layer.implementation.children:
        delete_empty_groups(child)

    layer.implementation.children = list(filter(lambda x: not is_empty_group(x), layer.implementation.children))

