This repository contains auto_material_importer.py, a Maya Python script that automates material setup when importing FBX files.
The tool rebuilds aiStandardSurface materials, reuses any texture nodes imported with the FBX, copies basic material attributes, and can optionally search a folder for missing textures. If no textures are found, default material values are assigned automatically.

Usage
Open Autodesk Maya and launch the Script Editor.

Load auto_material_importer.py and execute it.

When prompted, choose the FBX file to import.

Optionally select a folder where textures are stored. If skipped, the script searches the FBX directory.

The script imports the file, builds shaders, copies material attributes, and connects any matching textures automatically, using default values if textures are missing.