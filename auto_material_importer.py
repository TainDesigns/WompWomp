import os
import maya.cmds as cmds

EXTENSIONS = ['.png', '.jpg', '.jpeg', '.tga', '.tif', '.tiff', '.exr']

TEXTURE_MAPS = {
    'baseColor': ['basecolor', 'diffuse', 'albedo', 'base_color'],
    'roughness': ['roughness'],
    'metalness': ['metallic', 'metalness'],
    'normal': ['normal', 'nrm', 'nor'],
    'height': ['height', 'displacement', 'disp'],
    'emission': ['emissive', 'emission'],
    'opacity': ['opacity', 'alpha', 'transparency']
}

def find_texture(directory, material, keywords):
    material = material.lower()
    for filename in os.listdir(directory):
        name = filename.lower()
        if material in name:
            for kw in keywords:
                if kw in name:
                    return os.path.join(directory, filename)
    return None

def connect_file(shader, attribute, texture_path):
    file_node = cmds.shadingNode(
        'file', asTexture=True,
        name=f"{shader}_{attribute}_file"
    )
    cmds.setAttr(file_node + '.fileTextureName', texture_path, type='string')
    cmds.connectAttr(file_node + '.outColor', shader + '.' + attribute, force=True)
    return file_node

def connect_normal_map(shader, texture_path):
    file_node = cmds.shadingNode('file', asTexture=True, name=f"{shader}_normal_file")
    cmds.setAttr(file_node + '.fileTextureName', texture_path, type='string')
    bump = cmds.shadingNode('bump2d', asUtility=True, name=f"{shader}_bump")
    cmds.setAttr(bump + '.bumpInterp', 1)
    cmds.connectAttr(file_node + '.outAlpha', bump + '.bumpValue', force=True)
    cmds.connectAttr(bump + '.outNormal', shader + '.normalCamera', force=True)

def connect_height_map(shader, sg, texture_path):
    file_node = cmds.shadingNode('file', asTexture=True, name=f"{shader}_disp_file")
    cmds.setAttr(file_node + '.fileTextureName', texture_path, type='string')
    disp = cmds.shadingNode('displacementShader', asShader=True, name=f"{shader}_disp")
    cmds.connectAttr(file_node + '.outAlpha', disp + '.displacement', force=True)
    cmds.connectAttr(disp + '.displacement', sg + '.displacementShader', force=True)

def reconnect_existing_textures(original, shader):
    """Reconnect file textures from the original material to a new shader.

    Parameters
    ----------
    original : str
        The material imported with the FBX.
    shader : str
        The newly created aiStandardSurface shader.

    Returns
    -------
    bool
        True if any textures were reconnected.
    """

    reconnected = False

    mapping = {
        'color': ('baseColor', 'outColor'),
        'specularColor': ('specularColor', 'outColor'),
        'specular': ('specularColor', 'outColor'),
        'roughness': ('specularRoughness', 'outColor'),
        'metalness': ('metalness', 'outColor'),
        'opacity': ('opacity', 'outAlpha'),
        'transparency': ('opacity', 'outTransparency'),
    }

    for orig_attr, (new_attr, out_attr) in mapping.items():
        plugs = cmds.listConnections(
            f"{original}.{orig_attr}", source=True, destination=False, plugs=True
        ) or []
        for plug in plugs:
            node = plug.split('.')[0]
            if cmds.nodeType(node) != 'file':
                continue
            cmds.connectAttr(f"{node}.{out_attr}", f"{shader}.{new_attr}", force=True)
            try:
                cmds.disconnectAttr(f"{node}.{out_attr}", plug)
            except Exception:
                pass
            reconnected = True

    normal_conns = cmds.listConnections(
        f"{original}.normalCamera", source=True, destination=False, plugs=True
    ) or []
    for plug in normal_conns:
        node = plug.split('.')[0]
        bump = None
        file_node = None
        if cmds.nodeType(node) == 'bump2d':
            bump = node
            file_conns = cmds.listConnections(
                bump + '.bumpValue', source=True, destination=False, plugs=True
            ) or []
            if file_conns and cmds.nodeType(file_conns[0].split('.')[0]) == 'file':
                file_node = file_conns[0].split('.')[0]
        elif cmds.nodeType(node) == 'file':
            file_node = node

        if file_node:
            if not bump:
                bump = cmds.shadingNode('bump2d', asUtility=True, name=f"{shader}_bump")
                cmds.setAttr(bump + '.bumpInterp', 1)
                cmds.connectAttr(file_node + '.outAlpha', bump + '.bumpValue', force=True)
            cmds.connectAttr(bump + '.outNormal', shader + '.normalCamera', force=True)
            try:
                cmds.disconnectAttr(bump + '.outNormal', plug)
            except Exception:
                try:
                    cmds.disconnectAttr(file_node + '.outAlpha', plug)
                except Exception:
                    pass
            reconnected = True

    return reconnected

def setup_material(sg, directory):
    shaders = cmds.ls(cmds.listConnections(sg + '.surfaceShader'), materials=True) or []
    if not shaders:
        return
    original = shaders[0]
    if cmds.nodeType(original) != 'aiStandardSurface':
        target = original + '_ai'
        if not cmds.objExists(target):
            shader = cmds.shadingNode('aiStandardSurface', asShader=True, name=target)
        else:
            shader = target
    else:
        shader = original
    cmds.connectAttr(shader + '.outColor', sg + '.surfaceShader', force=True)

    reused = reconnect_existing_textures(original, shader)

    if not reused:
        for attr, keywords in TEXTURE_MAPS.items():
            tex = find_texture(directory, original, keywords)
            if not tex:
                continue
            if attr == 'baseColor':
                connect_file(shader, 'baseColor', tex)
            elif attr == 'roughness':
                connect_file(shader, 'specularRoughness', tex)
            elif attr == 'metalness':
                connect_file(shader, 'metalness', tex)
            elif attr == 'emission':
                connect_file(shader, 'emissionColor', tex)
                cmds.setAttr(shader + '.emission', 1)
            elif attr == 'opacity':
                connect_file(shader, 'opacity', tex)
            elif attr == 'normal':
                connect_normal_map(shader, tex)
            elif attr == 'height':
                connect_height_map(shader, sg, tex)

    if shader != original:
        remaining = cmds.listConnections(original, type='shadingEngine') or []
        if not remaining:
            cmds.delete(original)

def import_fbx_with_materials(fbx_path):
    directory = os.path.dirname(fbx_path)
    cmds.file(
        fbx_path,
        i=True,
        type='FBX',
        ignoreVersion=True,
        mergeNamespacesOnClash=False,
        namespace='fbx',
        options='fbx'
    )
    sgs = [s for s in cmds.ls(type='shadingEngine') if s not in (
        'initialShadingGroup', 'initialParticleSE')]
    for sg in sgs:
        setup_material(sg, directory)

if __name__ == '__main__':
    result = cmds.fileDialog2(fileMode=1, caption='Select FBX to Import')
    if result:
        import_fbx_with_materials(result[0])
