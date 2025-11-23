# Changelog


## 1.3.0

Importer
- Option to import paint layers as Curve objects.
- Option to generate UVs when importing as Mesh.

Exporter
- Export Blender Image references to Image layers.

## 1.2.0

Importer
- Grease Pencil: support frame by frame animation and looping.
- Support image layers.
- Improved handling of scenes where the existing Blender scene starts after frame 1.

Exporter
- Export Blender cameras as Quill cameras instead of spawn areas.
- Export animated transforms.
- Always include empties on export since they are used for hierarchy.
- Added option to not include groups with no children.
- Added option to export Grease Pencil as Ribbon strokes, facing up.
- Made matching round caps of Grease Pencil optional.
- Sanitize layer names before exporting.


## 1.1.1

- Fixes for Grease Pencil v3
- Fix crash when importing as mesh in Blender 4.3


## 1.1.0

Importer
- Support transform keyframes.
- Support visibility keyframes.
- Mesh: support frame by frame animation and looping.
- Mesh: basic support for spans and offsets at the paint layer level.
- Mesh: fix normals orientation.

Exporter
- Grease Pencil: export frame by frame animations to Quill.
- Grease Pencil: support layer-level transform.
- Grease Pencil: generate round and square caps.
- Grease Pencil: support single-point round cap strokes.
- Grease Pencil: fixed Grease Pencil width.
- Grease Pencil: support thickness scale.
- Grease Pencil: fixed last vertex was not exported.
- Grease Pencil: fixed exception on GP objects with no material.
- Fixed stroke Id in exported qbin.
- Fixed normals and tangent when exporting.


## 1.0.0

First official release. No changes compared to 0.0.4.


## 0.0.4

Importer
- Import Camera layers as Blender Camera objects.
- Fixed some corner cases in Mesh importer that weren't tesselated correctly.
- Fixed importing into non default Collection.

Exporter
- Export armatures as sticks.
- Fixed exported files could not be loaded in Quill.
- Fixed export of armatures.


## 0.0.3

Importer
- Import Paint layers as Mesh objects.
- Create a shared material for linking vertex colors and alpha.
- Fixed flip transforms.


## 0.0.2

Importer
- Improved UI with foldable panels.

Exporter
- Export Grease pencil to paint layers.
- Export Armatures to paint layers.
- Export Mesh wireframe to paint layers.


## 0.0.1

Importer
- Import the Quill layer hierarchy as Blender objects under a "Root" object.
- Import Paint layers as Grease pencil objects.
- Chain of transforms.
- Vertex colors.
- Import Viewpoint layers as Blender cameras.
- Other assets are converted to empty layers of some type.
- Options to include or exclude hidden layers and viewpoints.







