# KWC GN Asset Save

Save a selected Geometry Nodes tree into a configured Asset Library as a clean `.blend` (Mark as Asset included). Nested node groups and referenced dependencies are written automatically via `bpy.data.libraries.write`.

## Install

1. Blender **Edit > Preferences > Get Extensions > Install from Disk…**
2. Select this repository folder (the one that contains `blender_manifest.toml`)
   - Or zip that folder and install the zip
3. Enable **KWC GN Asset Save**

## Use

1. Open **Geometry Node Editor**
2. **N** panel > **KWC** > **GN Asset Save**
3. **Save to Asset Library…**
4. Pick Geometry Nodes tree + Asset Library (+ optional subfolder / file name)
5. Confirm — a `.blend` with only that tree (and its deps) is written under the library path

Default destination preference: Preferences > Add-ons > KWC GN Asset Save.
