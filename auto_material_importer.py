"""Automated FBX material importer for Autodesk Maya.

This script imports an FBX file and rebuilds every material as an
``aiStandardSurface``. Textures are searched in a user chosen directory and
connected based on common suffix conventions.
"""

import os
import re

import maya.cmds as cmds


# Accepted texture extensions
EXTENSIONS = [
    '.png', '.jpg', '.jpeg', '.tga', '.tif', '.tiff', '.exr'
]

# Mapping of texture suffixes to aiStandardSurface attributes
TEXTURE_MAPS = {
    'baseColor': ['_BaseColor', '_Diffuse', '_Albedo'],
    'metalness': ['_Metalness'],
    'specularRoughness': ['_SpecularRoughness', '_Roughness'],
    'normal': ['_Normal'],
    'displacement': ['_Height', '_Displace'],
    'opacity': ['_Opacity', '_Alpha'],
}


def ensure_plugins():
    """Load Arnold and FBX plugins if required."""
    for plugin in ('mtoa', 'fbxmaya'):
        if not cmds.pluginInfo(plugin, query=True, loaded=True):
            try:
                cmds.loadPlugin(plugin)
            except Exception:
                cmds.warning('Unable to load plugin: %s' % plugin)


def pick_fbx():
    result = cmds.fileDialog2(fileMode=1, caption='Select FBX File', fileFilter='*.fbx')
    if not result:
        cmds.error('FBX selection cancelled')
    return result[0]


def pick_texture_dir(default_dir):
    result = cmds.fileDialog2(fileMode=3, caption='Select Textures Folder')
    return result[0] if result else default_dir


def import_fbx(path):
    """Import FBX file without altering material names."""
    cmds.file(path, i=True, type='FBX', options='fbx', ignoreVersion=True)
    print('Imported FBX:', path)


def get_material_base(name):
    """Strip common suffixes like SG or Material from a name."""
    pattern = re.compile(r'(SG$|_SG$|_Material$|Material$)', re.I)
    return pattern.sub('', name)


def create_file_node(texture, colorspace='sRGB'):
    file_node = cmds.shadingNode('file', asTexture=True)
    place = cmds.shadingNode('place2dTexture', asUtility=True)
    # Connect standard place2dTexture attributes
    for attr in [
        'coverage', 'translateFrame', 'rotateFrame', 'mirrorU', 'mirrorV',
        'stagger', 'wrapU', 'wrapV', 'repeatUV', 'offset', 'rotateUV',
        'noiseUV', 'vertexUvOne', 'vertexUvTwo', 'vertexUvThree', 'vertexCameraOne'
    ]:
        cmds.connectAttr(place + '.' + attr, file_node + '.' + attr, force=True)
    cmds.connectAttr(place + '.outUV', file_node + '.uvCoord', force=True)
    cmds.connectAttr(place + '.outUvFilterSize', file_node + '.uvFilterSize', force=True)
    cmds.setAttr(file_node + '.fileTextureName', texture, type='string')
    try:
        cmds.setAttr(file_node + '.colorSpace', colorspace, type='string')
    except Exception:
        pass
    return file_node


def find_texture(directory, base, suffixes):
    """Recursively search for the first texture that matches."""
    target_prefixes = [base.lower() + suf.lower() for suf in suffixes]
    for root, _, files in os.walk(directory):
        for name in files:
            lower = name.lower()
            if not any(lower.endswith(ext) for ext in EXTENSIONS):
                continue
            if any(lower.startswith(pref) for pref in target_prefixes):
                return os.path.join(root, name)
    return None


def build_ai_shader(material, sg, texture_dir):
    """Replace ``material`` with an aiStandardSurface and reconnect textures."""
    base_name = get_material_base(sg)

    temp = cmds.shadingNode('aiStandardSurface', asShader=True, name=material + '_tmp')
    cmds.connectAttr(temp + '.outColor', sg + '.surfaceShader', force=True)

    # Look for textures
    textures = {}
    for attr, suff in TEXTURE_MAPS.items():
        tex = find_texture(texture_dir, base_name, suff)
        if tex:
            textures[attr] = tex

    # Connect textures if found
    try:
        if 'baseColor' in textures:
            node = create_file_node(textures['baseColor'], 'sRGB')
            cmds.connectAttr(node + '.outColor', temp + '.baseColor', force=True)
            print('Connected', textures['baseColor'], '->', temp + '.baseColor')
        if 'metalness' in textures:
            node = create_file_node(textures['metalness'], 'Raw')
            cmds.connectAttr(node + '.outAlpha', temp + '.metalness', force=True)
        if 'specularRoughness' in textures:
            node = create_file_node(textures['specularRoughness'], 'Raw')
            cmds.connectAttr(node + '.outAlpha', temp + '.specularRoughness', force=True)
        if 'opacity' in textures:
            node = create_file_node(textures['opacity'], 'Raw')
            cmds.connectAttr(node + '.outAlpha', temp + '.opacity', force=True)
        if 'normal' in textures:
            node = create_file_node(textures['normal'], 'Raw')
            normal = cmds.shadingNode('aiNormalMap', asUtility=True, name=temp + '_aiNormal')
            cmds.connectAttr(node + '.outColor', normal + '.input', force=True)
            cmds.connectAttr(normal + '.outValue', temp + '.normalCamera', force=True)
        if 'displacement' in textures:
            node = create_file_node(textures['displacement'], 'Raw')
            disp = cmds.shadingNode('displacementShader', asShader=True, name=temp + '_disp')
            cmds.connectAttr(node + '.outAlpha', disp + '.displacement', force=True)
            cmds.connectAttr(disp + '.displacement', sg + '.displacementShader', force=True)
    except Exception as err:
        cmds.warning('Texture connection failed: %s' % err)

    # Remove original and rename temp to original name
    cmds.delete(material)
    final_shader = cmds.rename(temp, material)
    return final_shader


def process_scene(texture_dir):
    """Convert every material in the scene."""
    for sg in cmds.ls(type='shadingEngine'):
        if sg in ('initialShadingGroup', 'initialParticleSE'):
            continue
        materials = cmds.ls(cmds.listConnections(sg + '.surfaceShader'), materials=True) or []
        if not materials:
            continue
        mat = materials[0]
        if cmds.nodeType(mat) != 'aiStandardSurface':
            build_ai_shader(mat, sg, texture_dir)


def main():
    ensure_plugins()
    fbx_path = pick_fbx()
    import_fbx(fbx_path)
    texture_dir = pick_texture_dir(os.path.dirname(fbx_path))
    process_scene(texture_dir)
    print('All materials converted.')


if __name__ == '__main__':
    main()

