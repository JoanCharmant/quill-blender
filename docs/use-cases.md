# Use cases

## Quill > Blender

- Start painting in Quill and finish in Grease Pencil
- Bypass Quill export step
    - For non animated scene
    - Import as Mesh for max fidelity.


## Blender > Quill

- Start painting in Grease Pencil and finish in Quill
- Send a mesh as wireframe to Quill for a painting reference
- Write text for a Quill scene with a stylus on a perfect plane using Grease Pencil.
- Use Grease Pencil in Surface mode to stick the paint strokes to other scene objects.
- Create perfect spheres for Quill by using single-point strokes with round cap in Grease Pencil.

## Blender > Quill > Blender

- Export an existing armature to Quill, paint a character over the armature, import back and animate in Blender.


## Quill > Blender > Quill

- Modify a Quill painting with Grease Pencil and send it back to Quill.
    - To minize data loss:
        - Quill: Brush type: `Cylinder`. Blender: Line type: `Line`, Line style: `Solid`.
        - Import using Grease Pencil mode
    - What can be modified in Blender
        - Adding and deleting paint layers
        - Adding and deleting paint strokes on a layer
        - Change existing strokes
            - To change color use the Tint tool in Draw mode.
            - To change width and opacity use the Thickness tool and the Strength tool in Sculpt mode.


