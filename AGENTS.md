# KWC GN Asset Save

Save a selected Geometry Nodes tree into a configured Asset Library as a clean `.blend` (Mark as Asset included). Nested node groups and referenced dependencies are written automatically via `bpy.data.libraries.write`.

## Install (Extension Repository)

Remote Repository URL:

```text
https://hjakikwc.github.io/kwc-gn-asset-save/index.json
```

1. Blender **Edit > Preferences > Get Extensions > Repositories > + > Add Remote Repository**
2. Paste the URL above, confirm
3. Install / enable **KWC GN Asset Save**

### Install from Disk (dev)

1. **Get Extensions > Install from Disk…**
2. Select this repository folder (contains `blender_manifest.toml`)
3. Enable **KWC GN Asset Save**

## Use

1. Open **Geometry Node Editor**
2. **N** panel > **KWC** > **GN Asset Save**
3. **Save to Asset Library…**
4. Pick Geometry Nodes tree + Asset Library (+ optional subfolder / file name)
5. Confirm — a `.blend` with only that tree (and its deps) is written under the library path

Default destination preference: Preferences > Add-ons > KWC GN Asset Save.

## Release

1. Bump `version` in `blender_manifest.toml`
2. Commit and push to `main`
3. Tag and push: `git tag vX.Y.Z && git push origin vX.Y.Z`
4. GitHub Actions builds the zip, creates a Release, and updates `docs/index.json` for Pages
