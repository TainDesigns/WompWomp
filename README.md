# WompWomp

This repository contains `auto_material_importer.py`, a Maya Python script that
automates material setup when importing FBX files. The script searches for
textures located next to the FBX and connects them to `aiStandardSurface`
shaders.

## Usage
1. Open Autodesk Maya and launch the Script Editor.
2. Load `auto_material_importer.py` and execute it.
3. When prompted, choose the FBX file to import.
4. The script imports the file, builds shaders, and connects any matching
   textures automatically.
