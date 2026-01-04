# Use cases

This page lists some ideas and workflows that are enabled by the add-on. These are not tutorials, just seeds for experimenting.


## Import (Quill → Blender)

- Import as mesh as a starting point for further work (subdivision, displacement, sculpting, materials, etc.).
- Import as mesh and render the scene using a different camera type (animated fov, depth of field, orthographic, etc.).
- Use Quill as a source for a Grease Pencil drawing (cylinder brush).
    - Quill paint strokes are truly in free space not stuck on surfaces or planes.
    - Quill animated brush.


## Export (Blender → Quill)

- Grease Pencil: write text using a graphics tablet.
- Grease Pencil: create animated 2DFX.
- Grease Pencil: create a rough animation in Grease Pencil and send it to Quill for reference.
- Grease Pencil: paint in surface mode on some 3D object.
- Grease Pencil: bake transforms and modifiers to open interesting possibilities.
- Mesh: send a reference object to Quill as a wireframe.
- Camera: create a camera path and send it to Quill.

## Round trip 1 (Quill → Blender → Quill)

- Create a progressive reveal of the paint strokes (cylinder brush only)
    - import a Quill drawing as Grease Pencil.
    - use a build modifier.
    - bake to drawings (Object > Animation > Bake Object Transform to Grease Pencil)
    - export back to Quill.
    - You can make the progression slower by adding a subdivision modifier before the build modifier.

- Attach a camera to a paint stroke
    - import a Quill stroke as curve.
    - create a camera in Blender.
    - animate the camera by attaching it to the curve.
    - export the camera back to Quill.

- Stick cylinder brush strokes to other objects
    - import a Quill scene as Mesh.
    - add a Grease Pencil object and paint over the Quill objects in surface mode.
    - export Grease Pencil back to Quill.

- Animate Quill objects and characters in Blender
    - import a Quill scene as Mesh.
    - animate the imported objects (keyframe the transform, attach to curve, attach to bones of armature, etc.).
    - export back to Quill.

- Kitbash Quill building blocks into more complex objects
    - import a Quill scene containing a library of building blocks as Mesh.
    - build more complex objects in Blender by duplicating and combining the building blocks.
    - export back to Quill.

- Lip sync Quill characters in Blender
    - import a Quill scene with a layer containing all mouth shapes as Keymesh.
    - do the lip sync (assign the mouth shapes to the right frames).
    - export back to Quill.

Note that Blender enforces alphabetical order so the original order of layers is lost when exporting back. This round trip workflow works best when importing the whole scene for context but exporting only the modified layer out of Blender and replacing it in the original scene using Quill import dialog.


## Round trip 2 (Blender → Quill → Blender)

- Skinning
    - export an existing armature to Quill
    - paint a character over the armature
    - import back the character
    - attach converted strokes to bones or weight paint
    - animate in Blender.

