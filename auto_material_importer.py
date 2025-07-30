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
    """Search recursively for a texture. Pass 1: material+keyword, Pass 2: keyword only."""
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

def connect_file(shader, attribute, texture_path, use_alpha=False):
    """Create file node with place2dTexture and connect it to shader attribute."""
    file_node = cmds.shadingNode('file', asTexture=True, name=f"{shader}_{attribute}_file")
    place = cmds.shadingNode('place2dTexture', asUtility=True, name=f"{file_node}_place2d")
    for attr in (
        'coverage','translateFrame','rotateFrame','mirrorU','mirrorV',
        'stagger','wrapU','wrapV','repeatUV','offset','rotateUV',
        'noiseUV','vertexUvOne','vertexUvTwo','vertexUvThree','vertexCameraOne'
    ):
        cmds.connectAttr(place + '.' + attr, file_node + '.' + attr, force=True)
    cmds.connectAttr(place + '.outUV', file_node + '.uvCoord', force=True)
    cmds.connectAttr(place + '.outUvFilterSize', file_node + '.uvFilterSize', force=True)

    cmds.setAttr(file_node + '.fileTextureName', texture_path, type='string')
    out_attr = 'outAlpha' if use_alpha else 'outColor'
    cmds.connectAttr(file_node + '.' + out_attr, shader + '.' + attribute, force=True)
    return file_node

def connect_normal_map(shader, texture_path):
    file_node = cmds.shadingNode('file', asTexture=True, name=f"{shader}_normal_file")
    place = cmds.shadingNode('place2dTexture', asUtility=True, name=f"{file_node}_place2d")
    for attr in (
        'coverage','translateFrame','rotateFrame','mirrorU','mirrorV',
        'stagger','wrapU','wrapV','repeatUV','offset','rotateUV',
        'noiseUV','vertexUvOne','vertexUvTwo','vertexUvThree','vertexCameraOne'
    ):
        cmds.connectAttr(place + '.' + attr, file_node + '.' + attr, force=True)
    cmds.connectAttr(place + '.outUV', file_node + '.uvCoord', force=True)
    cmds.connectAttr(place + '.outUvFilterSize', file_node + '.uvFilterSize', force=True)

    cmds.setAttr(file_node + '.fileTextureName', texture_path, type='string')
    bump = cmds.shadingNode('bump2d', asUtility=True, name=f"{shader}_bump")
    cmds.setAttr(bump + '.bumpInterp', 1)
    cmds.connectAttr(file_node + '.outAlpha', bump + '.bumpValue', force=True)
    cmds.connectAttr(bump + '.outNormal', shader + '.normalCamera', force=True)

def connect_height_map(shader, sg, texture_path):
    file_node = cmds.shadingNode('file', asTexture=True, name=f"{shader}_disp_file")
    place = cmds.shadingNode('place2dTexture', asUtility=True, name=f"{file_node}_place2d")
    for attr in (
        'coverage','translateFrame','rotateFrame','mirrorU','mirrorV',
        'stagger','wrapU','wrapV','repeatUV','offset','rotateUV',
        'noiseUV','vertexUvOne','vertexUvTwo','vertexUvThree','vertexCameraOne'
    ):
        cmds.connectAttr(place + '.' + attr, file_node + '.' + attr, force=True)
    cmds.connectAttr(place + '.outUV', file_node + '.uvCoord', force=True)
    cmds.connectAttr(place + '.outUvFilterSize', file_node + '.uvFilterSize', force=True)

    cmds.setAttr(file_node + '.fileTextureName', texture_path, type='string')
    disp = cmds.shadingNode('displacementShader', asShader=True, name=f"{shader}_disp")
    cmds.connectAttr(file_node + '.outAlpha', disp + '.displacement', force=True)
    cmds.connectAttr(disp + '.displacement', sg + '.displacementShader', force=True)

def copy_material_attributes(original, shader):
    """Copy basic color, specular, transparency, metalness, emission from FBX material."""
    try:
        if cmds.objExists(original + '.color'):
            color = cmds.getAttr(original + '.color')[0]
            cmds.setAttr(shader + '.baseColor', *color, type='double3')
    except: pass
    try:
        if cmds.objExists(original + '.specularColor'):
            spec = cmds.getAttr(original + '.specularColor')[0]
            cmds.setAttr(shader + '.specularColor', *spec, type='double3')
    except: pass
    try:
        if cmds.objExists(original + '.transparency'):
            trans = cmds.getAttr(original + '.transparency')[0]
            inv = [1 - t for t in trans]
            cmds.setAttr(shader + '.opacity', *inv, type='double3')
    except: pass
    try:
        if cmds.objExists(original + '.metalness'):
            metal = cmds.getAttr(original + '.metalness')
            if isinstance(metal, (list, tuple)):
                metal = metal[0]
            cmds.setAttr(shader + '.metalness', metal)
    except: pass
    try:
        if cmds.objExists(original + '.emission'):
            emis = cmds.getAttr(original + '.emission')
            if isinstance(emis, (list, tuple)):
                emis = emis[0]
            cmds.setAttr(shader + '.emission', emis)
        if cmds.objExists(original + '.emissionColor'):
            ecolor = cmds.getAttr(original + '.emissionColor')[0]
            cmds.setAttr(shader + '.emissionColor', *ecolor, type='double3')
    except: pass

def reconnect_existing_textures(original, shader):
    """Reconnect existing file textures from FBX material to aiStandardSurface shader."""
    reconnected = False
    mapping = {
        'color': ('baseColor', 'outColor'),
        'specularColor': ('specularColor', 'outColor'),
        'specular': ('specularColor', 'outColor'),
        'roughness': ('specularRoughness', 'outAlpha'),
        'metalness': ('metalness', 'outAlpha'),
        'metallic': ('metalness', 'outAlpha'),
        'opacity': ('opacity', 'outAlpha'),
        'transparency': ('opacity', 'outTransparency'),
        'emissionColor': ('emissionColor', 'outColor'),
    }

    for orig_attr, (new_attr, out_attr) in mapping.items():
        plugs = cmds.listConnections(f"{original}.{orig_attr}", source=True, destination=False, plugs=True) or []
        for plug in plugs:
            node = plug.split('.')[0]
            if cmds.nodeType(node) != 'file':
                continue
            try:
                cmds.connectAttr(f"{node}.{out_attr}", f"{shader}.{new_attr}", force=True)
                cmds.disconnectAttr(f"{node}.{out_attr}", plug)
                if new_attr == 'emissionColor':
                    cmds.setAttr(shader + '.emission', 1)
                reconnected = True
            except: pass

    normal_conns = cmds.listConnections(f"{original}.normalCamera", source=True, destination=False, plugs=True) or []
    for plug in normal_conns:
        node = plug.split('.')[0]
        bump = None
        file_node = None
        if cmds.nodeType(node) == 'bump2d':
            bump = node
            file_conns = cmds.listConnections(bump + '.bumpValue', source=True, destination=False, plugs=True) or []
            if file_conns and cmds.nodeType(file_conns[0].split('.')[0]) == 'file':
                file_node = file_conns[0].split('.')[0]
        elif cmds.nodeType(node) == 'file':
            file_node = node
        if file_node:
            try:
                if not bump:
                    bump = cmds.shadingNode('bump2d', asUtility=True, name=f"{shader}_bump")
                    cmds.setAttr(bump + '.bumpInterp', 1)
                    cmds.connectAttr(file_node + '.outAlpha', bump + '.bumpValue', force=True)
                cmds.connectAttr(bump + '.outNormal', shader + '.normalCamera', force=True)
                cmds.disconnectAttr(bump + '.outNormal', plug)
            except:
                try: cmds.disconnectAttr(file_node + '.outAlpha', plug)
                except: pass
            reconnected = True
    return reconnected

def apply_default_values(shader):
    """Assign defaults if no texture is connected."""
    try:
        if not cmds.listConnections(shader + '.baseColor', source=True):
            cmds.setAttr(shader + '.baseColor', 0.5, 0.5, 0.5, type='double3')
    except: pass
    try:
        if not cmds.listConnections(shader + '.specularRoughness', source=True):
            cmds.setAttr(shader + '.specularRoughness', 0.5)
    except: pass
    try:
        if not cmds.listConnections(shader + '.metalness', source=True):
            cmds.setAttr(shader + '.metalness', 0.0)
    except: pass
    try:
        if not cmds.listConnections(shader + '.opacity', source=True):
            cmds.setAttr(shader + '.opacity', 1.0, 1.0, 1.0, type='double3')
    except: pass
    try:
        if not cmds.listConnections(shader + '.emission', source=True):
            cmds.setAttr(shader + '.emission', 0)
    except: pass

def setup_material(sg, texture_dir):
    shaders = cmds.ls(cmds.listConnections(sg + '.surfaceShader'), materials=True) or []
    if not shaders:
        return
    original = shaders[0]
    if cmds.nodeType(original) != 'aiStandardSurface':
        target = original + '_ai'
        shader = cmds.shadingNode('aiStandardSurface', asShader=True, name=target) if not cmds.objExists(target) else target
    else:
        shader = original

    copy_material_attributes(original, shader)

    reused = False
    try:
        reused = reconnect_existing_textures(original, shader)
    except: pass

    if not reused:
        for attr, keywords in TEXTURE_MAPS.items():
            tex = find_texture(texture_dir, original, keywords)
            if not tex:
                continue
            try:
                if attr == 'baseColor':
                    connect_file(shader, 'baseColor', tex)
                elif attr == 'roughness':
                    connect_file(shader, 'specularRoughness', tex, use_alpha=True)
                elif attr == 'metalness':
                    connect_file(shader, 'metalness', tex, use_alpha=True)
                elif attr == 'emission':
                    connect_file(shader, 'emissionColor', tex)
                    cmds.setAttr(shader + '.emission', 1)
                elif attr == 'opacity':
                    connect_file(shader, 'opacity', tex, use_alpha=True)
                elif attr == 'normal':
                    connect_normal_map(shader, tex)
                elif attr == 'height':
                    connect_height_map(shader, sg, tex)
            except: pass

    apply_default_values(shader)
    cmds.connectAttr(shader + '.outColor', sg + '.surfaceShader', force=True)

    if shader != original:
        remaining = cmds.listConnections(original, type='shadingEngine') or []
        if not remaining:
            try: cmds.delete(original)
            except: pass

def import_fbx_with_materials(fbx_path):
    directory = os.path.dirname(fbx_path)
    tex_select = cmds.fileDialog2(fileMode=3, caption='Select Textures Folder')
    texture_dir = tex_select[0] if tex_select else directory

    cmds.file(fbx_path, i=True, type='FBX', ignoreVersion=True, mergeNamespacesOnClash=False, namespace='fbx', options='fbx')
    sgs = [s for s in cmds.ls(type='shadingEngine') if s not in ('initialShadingGroup', 'initialParticleSE')]
    for sg in sgs:
        try:
            setup_material(sg, texture_dir)
        except:
            pass

if __name__ == '__main__':
    result = cmds.fileDialog2(fileMode=1, caption='Select FBX to Import')
    if result:
        import_fbx_with_materials(result[0])
