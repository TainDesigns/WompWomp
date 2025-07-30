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
    """Search ``directory`` recursively for a texture file.

    The search is performed in two passes:
    1. filenames containing ``material`` and a keyword
    2. filenames containing only the keyword

    Parameters
    ----------
    directory : str
        Base directory to search.
    material : str
        Name of the material to prioritise in the search.
    keywords : List[str]
        Keywords describing the texture type (e.g. ``roughness``).

    Returns
    -------
    str or None
        Path to the matching texture file or ``None`` if nothing is found.
    """

    material = material.lower()
    first_pass = None
    for root, _, files in os.walk(directory):
        for filename in files:
            name = filename.lower()
            if not any(name.endswith(ext) for ext in EXTENSIONS):
                continue
            for kw in keywords:
                if kw in name:
                    path = os.path.join(root, filename)
                    if material in name:
                        return path
                    if not first_pass:
                        first_pass = path
                    break
    return first_pass

def connect_file(shader, attribute, texture_path, use_red=False):
    """Create a ``file`` node with a ``place2dTexture`` and connect it.

    Parameters
    ----------
    shader : str
        Target shader to receive the texture connection.
    attribute : str
        Attribute on the shader to connect to.
    texture_path : str
        Path to the texture file.
    use_red : bool, optional
        Connect the red channel (``outColorR``) of the file node rather than the
        full color output. This is useful for scalar maps such as roughness,
        metalness and opacity.
    """

    file_node = cmds.shadingNode('file', asTexture=True, name=f"{shader}_{attribute}_file")
    place = cmds.shadingNode('place2dTexture', asUtility=True, name=f"{file_node}_place2d")

    for attr in (
        'coverage', 'translateFrame', 'rotateFrame', 'mirrorU', 'mirrorV',
        'stagger', 'wrapU', 'wrapV', 'repeatUV', 'offset', 'rotateUV',
        'noiseUV', 'vertexUvOne', 'vertexUvTwo', 'vertexUvThree', 'vertexCameraOne'
    ):
        cmds.connectAttr(place + '.' + attr, file_node + '.' + attr, force=True)
    cmds.connectAttr(place + '.outUV', file_node + '.uvCoord', force=True)
    cmds.connectAttr(place + '.outUvFilterSize', file_node + '.uvFilterSize', force=True)

    cmds.setAttr(file_node + '.fileTextureName', texture_path, type='string')
    out_attr = 'outColorR' if use_red else 'outColor'
    cmds.connectAttr(file_node + '.' + out_attr, shader + '.' + attribute, force=True)
    return file_node

def connect_normal_map(shader, texture_path):
    """Create an ``aiNormalMap`` node for a normal texture and connect it."""

    file_node = cmds.shadingNode('file', asTexture=True, name=f"{shader}_normal_file")
    place = cmds.shadingNode('place2dTexture', asUtility=True, name=f"{file_node}_place2d")
    for attr in (
        'coverage', 'translateFrame', 'rotateFrame', 'mirrorU', 'mirrorV',
        'stagger', 'wrapU', 'wrapV', 'repeatUV', 'offset', 'rotateUV',
        'noiseUV', 'vertexUvOne', 'vertexUvTwo', 'vertexUvThree', 'vertexCameraOne'
    ):
        cmds.connectAttr(place + '.' + attr, file_node + '.' + attr, force=True)
    cmds.connectAttr(place + '.outUV', file_node + '.uvCoord', force=True)
    cmds.connectAttr(place + '.outUvFilterSize', file_node + '.uvFilterSize', force=True)

    cmds.setAttr(file_node + '.fileTextureName', texture_path, type='string')

    ai_normal = cmds.shadingNode('aiNormalMap', asUtility=True, name=f"{shader}_aiNormalMap")
    cmds.connectAttr(file_node + '.outColor', ai_normal + '.input', force=True)
    cmds.connectAttr(ai_normal + '.outValue', shader + '.normalCamera', force=True)

def connect_height_map(shader, sg, texture_path):
    file_node = cmds.shadingNode('file', asTexture=True, name=f"{shader}_disp_file")
    place = cmds.shadingNode('place2dTexture', asUtility=True, name=f"{file_node}_place2d")
    for attr in (
        'coverage', 'translateFrame', 'rotateFrame', 'mirrorU', 'mirrorV',
        'stagger', 'wrapU', 'wrapV', 'repeatUV', 'offset', 'rotateUV',
        'noiseUV', 'vertexUvOne', 'vertexUvTwo', 'vertexUvThree', 'vertexCameraOne'
    ):
        cmds.connectAttr(place + '.' + attr, file_node + '.' + attr, force=True)
    cmds.connectAttr(place + '.outUV', file_node + '.uvCoord', force=True)
    cmds.connectAttr(place + '.outUvFilterSize', file_node + '.uvFilterSize', force=True)

    cmds.setAttr(file_node + '.fileTextureName', texture_path, type='string')
    disp = cmds.shadingNode('displacementShader', asShader=True, name=f"{shader}_disp")
    cmds.connectAttr(file_node + '.outAlpha', disp + '.displacement', force=True)
    cmds.connectAttr(disp + '.displacement', sg + '.displacementShader', force=True)

def copy_material_attributes(original, shader):
    """Copy basic color and transparency attributes from ``original`` to ``shader``.

    Parameters
    ----------
    original : str
        Name of the placeholder material imported with the FBX.
    shader : str
        Name of the new aiStandardSurface shader.
    """

    try:
        if cmds.objExists(original + '.color'):
            color = cmds.getAttr(original + '.color')[0]
            cmds.setAttr(shader + '.baseColor', *color, type='double3')
    except Exception:
        pass

    try:
        if cmds.objExists(original + '.specularColor'):
            spec = cmds.getAttr(original + '.specularColor')[0]
            cmds.setAttr(shader + '.specularColor', *spec, type='double3')
    except Exception:
        pass

    try:
        if cmds.objExists(original + '.transparency'):
            trans = cmds.getAttr(original + '.transparency')[0]
            inv = [1 - t for t in trans]
            cmds.setAttr(shader + '.opacity', *inv, type='double3')
    except Exception:
        pass

    try:
        if cmds.objExists(original + '.metalness'):
            metal = cmds.getAttr(original + '.metalness')
            if isinstance(metal, (list, tuple)):
                metal = metal[0]
            cmds.setAttr(shader + '.metalness', metal)
    except Exception:
        pass

    try:
        if cmds.objExists(original + '.emission'):
            emis = cmds.getAttr(original + '.emission')
            if isinstance(emis, (list, tuple)):
                emis = emis[0]
            cmds.setAttr(shader + '.emission', emis)
        if cmds.objExists(original + '.emissionColor'):
            ecolor = cmds.getAttr(original + '.emissionColor')[0]
            cmds.setAttr(shader + '.emissionColor', *ecolor, type='double3')
    except Exception:
        pass

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
        'roughness': ('specularRoughness', 'outColorR'),
        'metalness': ('metalness', 'outColorR'),
        'metallic': ('metalness', 'outColorR'),
        'opacity': ('opacity', 'outColorR'),
        'transparency': ('opacity', 'outTransparency'),
        'emissionColor': ('emissionColor', 'outColor'),
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
            if new_attr == 'emissionColor':
                try:
                    cmds.setAttr(shader + '.emission', 1)
                except Exception:
                    pass
            reconnected = True

    normal_conns = cmds.listConnections(
        f"{original}.normalCamera", source=True, destination=False, plugs=True
    ) or []
    for plug in normal_conns:
        node = plug.split('.')[0]
        file_node = None
        ai_normal = None

        if cmds.nodeType(node) == 'aiNormalMap':
            ai_normal = node
            conns = cmds.listConnections(
                ai_normal + '.input', source=True, destination=False, plugs=True
            ) or []
            if conns and cmds.nodeType(conns[0].split('.')[0]) == 'file':
                file_node = conns[0].split('.')[0]
        elif cmds.nodeType(node) == 'file':
            file_node = node

        if file_node:
            if not ai_normal:
                ai_normal = cmds.shadingNode(
                    'aiNormalMap', asUtility=True, name=f"{shader}_aiNormalMap"
                )
                cmds.connectAttr(
                    file_node + '.outColor', ai_normal + '.input', force=True
                )
            cmds.connectAttr(
                ai_normal + '.outValue', shader + '.normalCamera', force=True
            )
            try:
                cmds.disconnectAttr(ai_normal + '.outValue', plug)
            except Exception:
                try:
                    cmds.disconnectAttr(file_node + '.outColor', plug)
                except Exception:
                    pass
            reconnected = True

    return reconnected

def apply_default_values(shader):
    """Assign reasonable defaults to shader channels if they have no inputs."""

    try:
        if not cmds.listConnections(shader + '.baseColor', source=True):
            cmds.setAttr(shader + '.baseColor', 0.5, 0.5, 0.5, type='double3')
    except Exception:
        pass

    try:
        if not cmds.listConnections(shader + '.specularRoughness', source=True):
            cmds.setAttr(shader + '.specularRoughness', 0.5)
    except Exception:
        pass

    try:
        if not cmds.listConnections(shader + '.metalness', source=True):
            cmds.setAttr(shader + '.metalness', 0.0)
    except Exception:
        pass

    try:
        if not cmds.listConnections(shader + '.opacity', source=True):
            cmds.setAttr(shader + '.opacity', 1.0, 1.0, 1.0, type='double3')
    except Exception:
        pass

    try:
        if not cmds.listConnections(shader + '.emission', source=True):
            cmds.setAttr(shader + '.emission', 0)
    except Exception:
        pass

def setup_material(sg, texture_dir):
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

    # Preserve current UV sets for shapes using this shading group
    connected_shapes = cmds.listConnections(sg, type='mesh') or []
    uv_map = {}
    for shape in connected_shapes:
        try:
            uv_sets = cmds.polyUVSet(shape, query=True, allUVSets=True) or []
            current_uv = cmds.polyUVSet(shape, query=True, currentUVSet=True)
            uv_map[shape] = current_uv[0] if current_uv else (uv_sets[0] if uv_sets else None)
        except Exception:
            uv_map[shape] = None

    copy_material_attributes(original, shader)

    reused = False
    try:
        reused = reconnect_existing_textures(original, shader)
    except Exception:
        pass

    if not reused:
        for attr, keywords in TEXTURE_MAPS.items():
            tex = find_texture(texture_dir, original, keywords)
            if not tex:
                continue
            try:
                if attr == 'baseColor':
                    connect_file(shader, 'baseColor', tex)
                elif attr == 'roughness':
                    connect_file(shader, 'specularRoughness', tex, use_red=True)
                elif attr == 'metalness':
                    connect_file(shader, 'metalness', tex, use_red=True)
                elif attr == 'emission':
                    connect_file(shader, 'emissionColor', tex)
                    cmds.setAttr(shader + '.emission', 1)
                elif attr == 'opacity':
                    connect_file(shader, 'opacity', tex, use_red=True)
                elif attr == 'normal':
                    connect_normal_map(shader, tex)
                elif attr == 'height':
                    connect_height_map(shader, sg, tex)
            except Exception:
                pass

    apply_default_values(shader)

    cmds.connectAttr(shader + '.outColor', sg + '.surfaceShader', force=True)

    # Restore UV sets to avoid Maya switching to a default one
    for shape, uv in uv_map.items():
        if uv:
            try:
                cmds.polyUVSet(shape, currentUVSet=True, uvSet=uv)
            except Exception:
                pass

    # Do not delete the original material automatically to avoid UV resets

def import_fbx_with_materials(fbx_path):
    directory = os.path.dirname(fbx_path)
    tex_select = cmds.fileDialog2(fileMode=3, caption='Select Textures Folder')
    texture_dir = tex_select[0] if tex_select else directory
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
        try:
            setup_material(sg, texture_dir)
        except Exception:
            pass

if __name__ == '__main__':
    result = cmds.fileDialog2(fileMode=1, caption='Select FBX to Import')
    if result:
        import_fbx_with_materials(result[0])
