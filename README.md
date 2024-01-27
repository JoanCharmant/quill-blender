
# Blender Quill scenes import/export add-on

[Quill](https://quill.art/) scenes import and export add-on for [Blender](https://www.blender.org).

Philosophy: some things are easier to work on in VR and other things are easier to work on with a flat screen and a pen. This add-on aims at minimizing the friction of moving from one technology to the other and enabling you to create workflows that best suits the strength of each.

## Installation

1. Download io_scene_quill.zip file from the Releases section.
2. Open Blender, Go to Edit > Preferences… > Add-ons.
3. Click the Install… button, navigate to and select the downloaded zip.
4. Tick the check mark next to Import-Export: Quill to activate the plugin.


## Usage

The tool can be found in Blender under File > Import > Quill scene and File > Export > Quill scene.

When selected the add-on will present the usual file export window to import or export the Quill scene along with some options on the right side panel.

## Features

The add-on reads and writes native Quill file format.

### Import

- Import Quill layer hierarchy to Blender objects.
- Import Quill paint layers to Grease pencil.
- Import Quill viewpoints to Cameras.


### Export

- Export Grease Pencil objects to Quill paint layers.
- Export Mesh objects as painted wireframes.
- Export Armature objects as painted stick figures.
- Export Cameras to Quill viewpoints.


## Limitations/Roadmap

The following features are currently not supported but are on the roadmap:
- Import and export keyframe animation for transform and visibility.
- Import and export frame by frame animations.
- Export correct bone colors for armature export.
- Round trip workflows.



