# Importing Quill files

This page details the supported features when importing Quill files into Blender using the addon.

The following key is used:
- ✅: full support
- ⚠️: partial support
- ❌: not supported

## Scene hierarchy
Quill files represent the scene as a hierarchy of layers, this hierarchy is imported as a hierarchy of Blender objects.

The following layer types are converted to Blender objects with matching data
- Group layer
- Paint layer
- Camera layer

The following layer types are converted to Empty objects with no data
- Viewpoint layer
- Sound layer
- Model layer
- Picture layer

## All layer types

Properties shared by all layer types

### General properties

| Feature |Status|
| ------------- |:---:|
| Name    | ✅ |
| Visible    | ⚠️ |
| Locked    | ❌ |
| Collapsed    | ❌ |
| Transform    | ✅ |
| Pivot    | ❌ |

Visibility is imported but the inheritance of the parent group visibility is not respected at this point. This is because Blender objects don't natively support visibility inheritance (hiding the parent doesn't hide the children).

By default hidden layers are not imported. You can force their import by checking Include > Hidden layers in the import dialog. In this case hidden layer groups will be imported and forced visible.

### Key framed animation data

| Feature |Status|
| ------------- |:---:|
| Visibility key frames    | ⚠️ |
| Transform  key frames  | ✅ |
| Offset key frames  | ❌ |
| Opacity key frames  | ❌ |
| Key frame interpolation  | ✅ |



Visibility key frames are not imported on layer groups.

Transform and transform keys are imported and inherited between the parent group and children.

Key frame interpolation (None, Linear, Ease in, Ease out, Ease in/out) is generally supported but may not be an exact mathematical match on the intermediate frames.

## Quill paint layers

Paint layers contain one or more drawings made of paint strokes. On import the drawings are converted to either Mesh objects or Grease pencil objects, this can be configured in the import dialog.

### Import as Mesh

The following features are supported when importing paint layers as Mesh

| Feature |Status|
| ------------- |:---:|
| Ribbon brush    | ✅ |
| Cylinder brush    | ✅ |
| Ellipse brush    | ✅ |
| Cube brush  | ✅ |
| Width  | ✅ |
| Color  | ✅ |
| Opacity  | ✅ |
| Directional opacity  | ❌ |
| Frame by frame animation  | ⚠️ |
| Looping  | ⚠️ |

#### Mesh material
Color is implemented via Vertex colors.

A single "Principled BSDF" material is created and shared by all imported meshes. This material reads the vertex colors and alpha attributes that were stored in the mesh during import.

#### Mesh animation
When importing the Quill timeline is currently fit into the Blender frame range and Quill frames outside that range are discarded.

Frame by frame animation of Mesh isn't natively supported in Blender. Blender has other ways of animating meshes but for frame by frame animation it relies on "Mesh caches" stored in external files like Alembic or FBX.

In order to import frame by frame animation as meshes the addon creates a separate object for each drawing and animate the visibility of these objects so that only one object is visible on each frame.

Infinite loop is generally supported but restricting the number of loops is done in Quill via visibility keyframes on the parent which isn't supported.

### Import as Grease Pencil

The following features are supported when importing paint layers as Grease Pencil

| Feature |Status|
| ------------- |:---:|
| Ribbon brush    | ❌ |
| Cylinder brush    | ✅ |
| Ellipse brush    | ❌ |
| Cube brush  | ❌ |
| Width  | ✅ |
| Color  | ✅ |
| Opacity  | ✅ |
| Directional opacity  | ❌ |
| Frame by frame animation  | ❌ |
| Looping  | ❌ |

#### Grease Pencil material
Width, color and opacity are assigned to the corresponding fields in the Grease Pencil stroke:  pressure, vertex color and strength respectively.

The created strokes use the default Grease Pencil material with Line type = Line, Style = Solid.

#### Grease Pencil animation
Currently only the first drawing is imported.


## Quill camera layers

Quill cameras are imported as Camera objects.

| Feature |Status|
| ------------- |:---:|
| Field of view    | ✅ |


## Import dialog

The import dialog has the following options

### Include

**Hidden layers**

Import invisible Quill layers.

**Cameras**

Import Quill cameras and viewpoints.

### Paint layers

**Convert to**

Behavior when importing paint layers
- Mesh
- Grease Pencil








