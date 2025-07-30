# WompWomp

This repository contains `auto_material_importer.py`, a Maya Python script that
automates material setup when importing FBX files. The tool rebuilds
`aiStandardSurface` materials, reuses any texture nodes imported with the FBX,
and can optionally search a folder for missing textures.

## Usage
1. Open Autodesk Maya and launch the Script Editor.
2. Load `auto_material_importer.py` and execute it.
3. When prompted, choose the FBX file to import.
4. Optionally select a folder where textures are stored. If skipped, the script
   searches the FBX directory.
5. The script imports the file, creates or reuses `aiStandardSurface` shaders,
   copies placeholder attributes, reconnects any imported textures and searches
   the selected folder for missing maps. Default values are applied when maps
   are not found. UV sets assigned to meshes are preserved during material
   replacement, so texture mapping remains intact.
