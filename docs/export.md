# Exporting Blender scenes

This page details the supported features when exporting Blender scenes to Quill using the addon.

Features are listed from the point of view of Blender.

The following key is used:
- ✅: full support
- ⚠️: partial support
- ❌: not supported

## Scene hierarchy
Blender organizes the scene into hierarchies of parented objects.

The following objects types are supported when exporting Blender scenes:

| Feature |Status|
| ------------- |:---:|
| Mesh | ⚠️ |
| Curve | ❌ |
| Surface    | ❌ |
| Metaball  | ❌ |
| Text  | ❌ |
| Volume  | ❌ |
| Grease Pencil  | ⚠️ |
| Armature  | ⚠️ |
| Lattice  | ❌ |
| Empty  | ✅ |
| Image  | ❌ |
| Light  | ❌ |
| Light probe  | ❌ |
| Camera  | ⚠️ |
| Speaker  | ❌ |
| Force field  | ❌ |
| Collection instance  | ❌ |

## Animation

Blender has many animation features, none of which are currently supported by the exporter.

| Feature |Status|
| ------------- |:---:|
| Transform key frames | ❌ |
| Armature parenting | ❌ |
| Shape keys | ❌ |
| Constraints | ❌ |
| Drivers | ❌ |
| Mesh caches | ❌ |


## Mesh
Mesh are converted to their wire frame representation. Each edge of each polygon is converted to a paint stroke.

## Grease Pencil
Grease pencil is the closest thing to Quill. The addon tries to convert Grease Pencil objects to Quill paint layers with corresponding data.

The options under Grease Pencil object > Data > Strokes are ignored and always match Quill model which corresponds to:
- Stroke depth order: `3D`
- Stroke thickness: `World space`


### Layers

Each Grease Pencil object can contain several layers. In this case the exporter creates a Quill Layer Group and converts each GP layer to a Quill paint layer.

#### Layer level features

| Feature |Status|
| ------------- |:---:|
| Blend mode | ❌ |
| Opacity | ✅ |
| Masks | ❌ |
| Transform | ❌ |
| Adjustments | ⚠️ |
| Relations | ❌ |

In Adjustments, Stroke thickness is supported. Tint color and Tint factor are not supported.

### Material

Each stroke can use a specific [material](https://docs.blender.org/manual/en/latest/grease_pencil/materials/properties.html). This is what controls the visual aspect of the stroke in Blender.

#### Surface component types

| Feature |Status|
| ------------- |:---:|
| Stroke | ✅ |
| Fill | ❌ |

Fill are not supported as such in Quill.

#### Stroke component

| Feature |Status|
| ------------- |:---:|
| Line type (Line, Dot, Square) | ❌ |
| Line style (Solid, Texture) | ❌ |
| Base color | ✅ |
| Hold out | ❌ |
| Self overlap | ❌ |

Line type and line style don't exist in Quill. The paint strokes generated are always using the Cylinder brush type.

The final color is a mix between the base color and the vertex color.

### Vertex data

| Feature |Status|
| ------------- |:---:|
| Width | ✅ |
| Color | ✅ |
| Opacity | ✅ |


## Armature

Armature objects (hierarchies of bones) are converted to a single paint layer with one stroke per bone.

Animation is not currently supported.

The bones can be produced as octahedral or stick-like paint strokes. The color of the generated strokes is random.


## Empty

Empty objects are converted to layer groups and their children are processed recursively.

## Camera

Camera objects are converted to Quill viewpoints. Most of the camera properties aside from the transform aren't currently supported.


## Export dialog

The export dialog has the following options:

### Include

**Object Types**

Types of objects exported: Empty, Grease Pencil, Camera, Mesh, Armature. All other object types aren't supported.

**Limit to**

Behavior when exporting objects.
- Selected Objects
- Visible Objects

### Mesh Wireframe

Mesh objects are converted to their wireframe representation. These options control the generation of the wireframe paint strokes.

**Width**
Width of paint strokes

**Resolution**
Density of paint strokes, in number of points per stroke.

### Armature

Armature objects are flattened and converted to a single paint layer. These options control the generation of the armature paint strokes.

**Bone shape**
- Octahedral
- Stick