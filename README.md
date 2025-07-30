# WompWomp

This repository contains `auto_material_importer.py`, a Maya Python script that
automates aiStandardSurface material creation when importing FBX files. The
tool loads the Arnold and FBX plugins, imports the chosen model and connects PBR
textures from a user‑selected directory. Normal maps are handled with
`aiNormalMap` and scalar maps sample the red channel for proper roughness and
metalness values.

## Usage
1. Open Autodesk Maya and launch the Script Editor.
2. Load `auto_material_importer.py` and execute it.
3. When prompted, choose the FBX file to import. After loading, a file named
   `phong_relationships.txt` will be created alongside the FBX describing all
   connections involving imported Phong materials. Those materials are then
   replaced with `aiStandardSurface` nodes automatically.
4. Select the directory that contains the texture maps.
5. The script connects textures by matching suffixes such as `_basecolor`,
   `_roughness`, `_metalness` and `_normal`. Roughness and metalness read from
   the red channel and normal maps use `aiNormalMap` automatically.
