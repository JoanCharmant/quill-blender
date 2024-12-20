# Importing Quill files

Quill files represent the scene as a hierarchy of layers.

The following layer types are converted to Blender objects with matching data
- Group
- Paint
- Viewpoint
- Camera

The following layer types are converted to Empty objects with no data
- Sound
- Model
- Picture

## Quill layer groups

Layer groups are more versatile in Quill than the available options in Blender.

Quill layer groups have a transform and a visibility status that is inherited by the children layers and can have animated visibility and transform. Blender objects don't inherit visibility, and Blender collections don't carry transformation data.

Currently Quill layer groups are converted to Empty objects and the children layers are parented to the empty. This respects the transformation chain but not the visibility.

By default hidden layers are not imported. You can force their import by checking Include > Hidden layers in the import dialog. In this case hidden layer groups will be imported and forced visible. Visibility animation data is not imported on layer groups.

## Quill paint layers

The following features are supported on import:
- import as Mesh
- Import as Grease Pencil
- Quill brush types (import as Mesh only)
- Stroke width, color and opacity

### Material

A single "Principled BSDF" material is created and shared by all imported objects. This material reads the vertex colors and alpha attributes that were stored in the mesh during import.

## Animation

The importer supports the following types of animation:
- Transform keys (all layer types)
- Visibility keys (paint layers only)
- Frame by frame animation of paint layers

In case of mismatching frame rate the importer will try to convert the Quill time to the closest frame on the Blender timeline.

### Frame by frame animation

This is currently only supported when using Mesh import.

The Quill frames are imported as separate objects and their visibility is animated. Looping is supported. The drawings are imported into the frame range of the current Blender scene.

## Import options

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








