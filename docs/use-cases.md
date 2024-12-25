# Use cases

## Quill > Blender

- Start painting in Quill and finish in Grease Pencil
- Bypass export step
    - For non animated scene
    - Import as Mesh for max fidelity.


## Blender > Quill

- Start painting in Grease Pencil and finish in Quill
- Send Mesh as wireframe for painting reference
- Write text for a Quill scene with a stylus and on a perfect plane using Grease Pencil.


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
        - Changing the position, width or color of any vertex of any paint stroke


