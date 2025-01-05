# Exporting Blender scenes

This page details the supported features when exporting Blender scenes to Quill using the addon.

Features are listed from the point of view of Blender.

The following key is used:
- ✅: full support
- ⚠️: partial support
- ❌: not supported

## Scene hierarchy
Blender organizes the scene into hierarchies of objects.

The following object types are supported when exporting Blender scenes:

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

Note: some object types can be converted to Grease Pencil objects within Blender and then exported.

## Animation

Blender has many animation features, most of which are not currently supported by the exporter.

| Feature |Status|
| ------------- |:---:|
| Animated transform (key frames) | ❌ |
| Parenting to animated object | ❌ |
| Parenting to armature bones| ❌ |
| Deformation from armature (weight painting) | ❌ |
| Lattice | ❌ |
| Constraints | ❌ |
| Drivers | ❌ |
| Shape keys | ❌ |
| Mesh caches (Alembic, FBX) | ❌ |
| Grease Pencil frame by frame | ✅ |


## Mesh
Mesh are converted to their wire frame representation. Each edge of each polygon is converted to a paint stroke.

Non-uniform scaling is not supported in Quill. You should apply the scale before exporting. (Menu Object > Apply > Scale).

## Grease Pencil
Grease pencil is the closest thing to Quill. The addon tries to convert Grease Pencil objects to Quill paint layers with corresponding data.

The options under GPencil > Data > Strokes are ignored and always match Quill model which corresponds to:
- Stroke Depth Order: `3D location`
- Stroke Thickness: `World space`

Thickness Scale applies a multiplier to all strokes in all layers. This is supported.

### Grease Pencil layers

Each Grease Pencil object can contain several layers. In this case the exporter creates a Quill Layer Group and converts each GP layer to a Quill paint layer.

#### Layer level features

| Feature |Status|
| ------------- |:---:|
| Blend mode | ❌ |
| Opacity | ✅ |
| Masks | ❌ |
| Transform | ✅ |
| Adjustments | ⚠️ |
| Relations | ❌ |

In Adjustments, Stroke Thickness is supported, it applies an offset to the thickness of all strokes of the layer. Tint color and Tint factor are not supported.

### Grease Pencil material

Each stroke can use a specific [material](https://docs.blender.org/manual/en/latest/grease_pencil/materials/properties.html). This is what controls the visual aspect of the stroke in Blender.

Exporting Grease Pencil objects that don't have any material is not supported. Such objects may be created when converting from other Blender object types like Text for example. You must add a default material prior to exporting.

#### Surface component types

| Feature |Status|
| ------------- |:---:|
| Stroke | ⚠️ |
| Fill | ❌ |

Fills don't exist as such in Quill.

#### Stroke component

| Feature |Status|
| ------------- |:---:|
| Line type: Line | ✅ |
| Line type: Dots | ❌  |
| Line type: Square | ❌ |
| Line style: Solid | ✅ |
| Line style: Texture | ❌ |
| Base color | ✅ |
| Hold out | ❌ |
| Self overlap | ❌ |

The options under Line type and Line style are ignored and forced to Quill model which corresponds to:
- Line type: `Line`
- Line style: `Solid`

The generated paint strokes use Quill brush type `Cylinder` which most closely match the behavior of the Grease Pencil strokes (always facing the viewer).

The final color is a mix between the base color and the vertex color.


### Grease Pencil stroke caps

Stroke caps data is handled differently between Blender and Quill. In Blender the caps type information is a property of the stroke. On the other hand Quill doesn't store cap information separately, caps are created with an extra vertex of zero width. This difference is problematic for round tripping.

To emulate Grease Pencil caps the exporter adds extra vertices at each end of the stroke. It only does this if the first vertex doesn't already have a zero width to try to detect round tripping. Note: The importer always configure imported Quill strokes using `Round` cap mode.

These heuristics result in the following compatibility table during export:

| Source |Status|
| ------------- |:---:|
| Native Grease Pencil stroke with Flat cap  | ✅ |
| Native Grease Pencil stroke with Round cap  | ✅ |
| Grease Pencil stroke imported from Quill stroke with cap  | ✅ |
| Grease Pencil stroke imported from Quill stroke without cap  | ❌ |

In the last case the stroke is imported into Blender Grease Pencil with Round cap since Blender doesn't have a concept of strokes without caps, and during the export it is "closed".

Single-point stroke with Round caps will generate a sphere in Quill.

### Grease Pencil vertex data

| Feature |Status|
| ------------- |:---:|
| Width | ✅ |
| Color | ✅ |
| Opacity | ✅ |

Grease Pencil doesn't have a concept of "normal" for vertices while Quill uses it to rotate the cross section of the brushes (particularly evident for Ribbon and Cube brushes) and for directional opacity. In Quill this is based on the orientation of the controller.

The exporter uses the camera as the general direction of the normal. You don't normally need to worry about this but if you don't have a camera in the scene the exporter will use the origin, and for certain strokes that happen to be on a plane crossing the origin this can cause random twisting of the paint strokes when imported back in Blender from Quill after a round-trip. To solve this issue make sure to have a camera in the scene at export time, ideally away from any strokes. This issue is only visible when exporting Grease Pencil and importing back as Mesh.


### Grease Pencil frame by frame animation

Each Grease Pencil layer can have multiple key frames with independent drawings for frame by frame animation. These are exported to Quill drawings.

| Feature |Status|
| ------------- |:---:|
| Frame rate | ✅ |
| Frame range | ✅ |
| Key frames | ✅ |
| Frame hold | ✅ |
| Empty key frame | ✅ |


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