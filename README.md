
# Blender Quill scenes import/export add-on

[Quill](https://quill.art/) scenes import and export add-on for [Blender](https://www.blender.org).

Philosophy: some things are easier to work on in VR and other things are easier to work on with a flat screen and a pen. This add-on aims at minimizing the friction of moving from one technology to the other and enabling you to create workflows that best suits the strength of each.

## Installation

1. Download io_scene_quill.zip file from the Releases section.
2. Open Blender, Go to Edit > Preferences… > Add-ons.
3. Click the Install… button, navigate to and select the downloaded zip.
4. Tick the check mark next to Import-Export: Quill to activate the add-on.


## Usage

To import or export Quill scenes go to **File > Import > Quill scene** and **File > Export > Quill scene**.

For import, select a file inside the Quill scene folder, for example `Quill.json`. The import process may take a while for large scenes.

For export, it will use the file name to create the scene folder.

The import/export dialogs have options on the right hand side.

## Features

The add-on reads and writes native Quill file format.

### Import

- Import Quill layer hierarchy to Blender objects.
    - Quill groups become "Empties" with transform and children.
    - Quill paint layers become Mesh or Grease Pencil objects.
    - Quill cameras become Camera objects.
    - Quill image layers become Image objects.
- Import frame by frame animation as Mesh sequences or Grease Pencil frames.
- Import transform keyframes.


[Detailed status of supported Quill features during import](docs/import.md)

### Export

- Export the Blender scene to Quill layers
    - Grease Pencil objects to paint layers.
    - Mesh objects to painted wireframes.
    - Armature objects to painted stick figures.
    - Cameras to cameras.
    - Image references to image layers.
    - Empty objects to Quill groups.
- Export transform keyframes on groups and objects to Quill keyframes.
- Export Grease Pencil frame by frame animation to Quill drawings.

[Detailed status of supported Blender features during export](docs/export.md)

## Inherent limitations

Quill and Blender cannot always be converted correctly back and forth as the underlying models are not fully compatible. This impacts both [import](docs/import.md) and [export](docs/export.md).

Here are the main pain points.

⚠️ Paint strokes. Here is a Venn Diagram of the paint stroke representation between Quill and Blender's Grease Pencil.

![](docs/images/venn-paint-strokes.png)


⚠️ Quill sequence hierarchy with spans and loops. These are not supported yet.

⚠️ Opacity keyframes and layer-level opacity. This is not supported.

⚠️ Animation types on export. Aside from transform key frames and frame by frame animation Blender also supports armature based animation and shape keys. These will have to be baked on export (not currently supported).
