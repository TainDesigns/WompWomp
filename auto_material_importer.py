import os
import maya.cmds as cmds

EXTENSIONS = ['.png', '.jpg', '.jpeg', '.tga', '.tif', '.tiff', '.exr']

# Mapping of texture suffixes to aiStandardSurface destinations
TEXTURE_RULES = {
    'baseColor': {
        'suffixes': ['_basecolor', '_diffuse', '_albedo'],
        'attr': 'baseColor',
        'colorSpace': 'sRGB',
        'channel': 'outColor'
    },
    'roughness': {
        'suffixes': ['_roughness', '_specularroughness'],
        'attr': 'specularRoughness',
        'colorSpace': 'Raw',
        'channel': 'outAlpha'
    },
    'metalness': {
        'suffixes': ['_metalness', '_metallic'],
        'attr': 'metalness',
        'colorSpace': 'Raw',
        'channel': 'outAlpha'
    },
    'opacity': {
        'suffixes': ['_opacity', '_alpha'],
        'attr': 'opacity',
        'colorSpace': 'Raw',
        'channel': 'outAlpha'
    },
    'normal': {
        'suffixes': ['_normal'],
        'attr': 'normalCamera',
        'colorSpace': 'Raw',
        'channel': 'outColor'
    },
    'height': {
        'suffixes': ['_height', '_displace'],
        'attr': 'displacementShader',
        'colorSpace': 'Raw',
        'channel': 'outAlpha'
    },
    'emission': {
        'suffixes': ['_emission', '_emissive'],
        'attr': 'emissionColor',
        'colorSpace': 'sRGB',
        'channel': 'outColor'
    },
}

def ensure_plugins():
    """Load required plugins if not already loaded."""
    for plug in ('mtoa', 'fbxmaya'):
        try:
            if not cmds.pluginInfo(plug, query=True, loaded=True):
                cmds.loadPlugin(plug)
        except Exception as e:
            cmds.warning('Could not load plugin %s: %s' % (plug, e))


def pick_fbx():
    """Prompt the user to choose an FBX file."""
    res = cmds.fileDialog2(fileMode=1, caption='Select FBX to Import')
    return res[0] if res else None


def pick_texture_dir(fbx_path):
    """Prompt the user for a texture directory or use the FBX folder."""
    res = cmds.fileDialog2(fileMode=3, caption='Select Textures Folder')
    return res[0] if res else os.path.dirname(fbx_path)


def find_texture(material, directory, suffixes):
    """Search ``directory`` for a texture starting with ``material`` and any suffix."""
    mat = material.lower()
    for root, _, files in os.walk(directory):
        for fname in files:
            name, ext = os.path.splitext(fname)
            if ext.lower() not in EXTENSIONS:
                continue
            lname = name.lower()
            if not lname.startswith(mat):
                continue
            for suf in suffixes:
                if suf.lower() in lname:
                    return os.path.join(root, fname)
    return None


def _create_file_node(shader, attribute, texture_path, color_space):
    file_node = cmds.shadingNode('file', asTexture=True, name='%s_%s_file' % (shader, attribute))
    place = cmds.shadingNode('place2dTexture', asUtility=True, name=file_node + '_place2d')
    for attr in (
        'coverage', 'translateFrame', 'rotateFrame', 'mirrorU', 'mirrorV',
        'stagger', 'wrapU', 'wrapV', 'repeatUV', 'offset', 'rotateUV',
        'noiseUV', 'vertexUvOne', 'vertexUvTwo', 'vertexUvThree', 'vertexCameraOne'
    ):
        cmds.connectAttr(place + '.' + attr, file_node + '.' + attr, force=True)
    cmds.connectAttr(place + '.outUV', file_node + '.uvCoord', force=True)
    cmds.connectAttr(place + '.outUvFilterSize', file_node + '.uvFilterSize', force=True)
    cmds.setAttr(file_node + '.fileTextureName', texture_path, type='string')
    try:
        cmds.setAttr(file_node + '.colorSpace', color_space, type='string')
    except Exception:
        pass
    return file_node


def connect_file(shader, attribute, texture_path, color_space='sRGB', channel='outColor'):
    """Connect a texture file to ``shader.attribute``."""
    file_node = _create_file_node(shader, attribute, texture_path, color_space)
    cmds.connectAttr(file_node + '.' + channel, shader + '.' + attribute, force=True)
    return file_node


def connect_normal_map(shader, texture_path):
    file_node = _create_file_node(shader, 'normal', texture_path, 'Raw')
    ai_normal = cmds.shadingNode('aiNormalMap', asUtility=True, name='%s_aiNormalMap' % shader)
    cmds.connectAttr(file_node + '.outColor', ai_normal + '.input', force=True)
    cmds.connectAttr(ai_normal + '.outValue', shader + '.normalCamera', force=True)


def connect_height_map(shader, sg, texture_path):
    file_node = _create_file_node(shader, 'height', texture_path, 'Raw')
    disp = cmds.shadingNode('displacementShader', asShader=True, name='%s_displacement' % shader)
    cmds.connectAttr(file_node + '.outAlpha', disp + '.displacement', force=True)
    cmds.connectAttr(disp + '.displacement', sg + '.displacementShader', force=True)


def copy_basic_attrs(original, shader):
    """Copy simple attributes from ``original`` to ``shader``."""
    try:
        if cmds.objExists(original + '.color'):
            col = cmds.getAttr(original + '.color')[0]
            cmds.setAttr(shader + '.baseColor', *col, type='double3')
    except Exception:
        pass
    try:
        if cmds.objExists(original + '.transparency'):
            tr = cmds.getAttr(original + '.transparency')[0]
            inv = [1 - v for v in tr]
            cmds.setAttr(shader + '.opacity', *inv, type='double3')
    except Exception:
        pass
    try:
        if cmds.objExists(original + '.specularColor'):
            spec = cmds.getAttr(original + '.specularColor')[0]
            cmds.setAttr(shader + '.specularColor', *spec, type='double3')
    except Exception:
        pass
    for attr in ('roughness', 'specularRoughness'):
        if cmds.objExists(original + '.' + attr):
            try:
                val = cmds.getAttr(original + '.' + attr)
                if isinstance(val, list):
                    val = val[0]
                cmds.setAttr(shader + '.specularRoughness', val)
                break
            except Exception:
                pass
    try:
        if cmds.objExists(original + '.metalness'):
            val = cmds.getAttr(original + '.metalness')
            if isinstance(val, list):
                val = val[0]
            cmds.setAttr(shader + '.metalness', val)
    except Exception:
        pass
    try:
        if cmds.objExists(original + '.emissionColor'):
            col = cmds.getAttr(original + '.emissionColor')[0]
            cmds.setAttr(shader + '.emissionColor', *col, type='double3')
            cmds.setAttr(shader + '.emission', 1)
    except Exception:
        pass
    try:
        if cmds.objExists(original + '.emission'):
            val = cmds.getAttr(original + '.emission')
            if isinstance(val, list):
                val = val[0]
            cmds.setAttr(shader + '.emission', val)
    except Exception:
        pass


def reconnect_existing_textures(original, shader):
    """Reconnect file textures from ``original`` to ``shader``."""
    mapping = {
        'color': ('baseColor', 'outColor'),
        'specularColor': ('specularColor', 'outColor'),
        'specular': ('specularRoughness', 'outAlpha'),
        'roughness': ('specularRoughness', 'outAlpha'),
        'metallic': ('metalness', 'outAlpha'),
        'metalness': ('metalness', 'outAlpha'),
        'opacity': ('opacity', 'outAlpha'),
        'transparency': ('opacity', 'outTransparency'),
        'emissionColor': ('emissionColor', 'outColor'),
    }

    found = False
    for src_attr, (dst_attr, chan) in mapping.items():
        plugs = cmds.listConnections('%s.%s' % (original, src_attr), source=True, destination=False, plugs=True) or []
        for plug in plugs:
            node = plug.split('.')[0]
            if cmds.nodeType(node) != 'file':
                continue
            cmds.connectAttr('%s.%s' % (node, chan), '%s.%s' % (shader, dst_attr), force=True)
            try:
                cmds.disconnectAttr('%s.%s' % (node, chan), plug)
            except Exception:
                pass
            if dst_attr == 'emissionColor':
                try:
                    cmds.setAttr(shader + '.emission', 1)
                except Exception:
                    pass
            found = True

    norm_conns = cmds.listConnections(original + '.normalCamera', source=True, destination=False, plugs=True) or []
    for plug in norm_conns:
        node = plug.split('.')[0]
        file_node = None
        ai_normal = None
        if cmds.nodeType(node) == 'aiNormalMap':
            ai_normal = node
            links = cmds.listConnections(ai_normal + '.input', source=True, destination=False, plugs=True) or []
            if links and cmds.nodeType(links[0].split('.')[0]) == 'file':
                file_node = links[0].split('.')[0]
        elif cmds.nodeType(node) == 'file':
            file_node = node
        if file_node:
            if not ai_normal:
                ai_normal = cmds.shadingNode('aiNormalMap', asUtility=True, name='%s_aiNormalMap' % shader)
                cmds.connectAttr(file_node + '.outColor', ai_normal + '.input', force=True)
            cmds.connectAttr(ai_normal + '.outValue', shader + '.normalCamera', force=True)
            try:
                cmds.disconnectAttr(ai_normal + '.outValue', plug)
            except Exception:
                try:
                    cmds.disconnectAttr(file_node + '.outColor', plug)
                except Exception:
                    pass
            found = True
    return found


def apply_default_values(shader):
    """Ensure the shader has sane defaults when no textures are connected."""
    if not cmds.listConnections(shader + '.baseColor', source=True):
        cmds.setAttr(shader + '.baseColor', 0.5, 0.5, 0.5, type='double3')
    if not cmds.listConnections(shader + '.specularRoughness', source=True):
        cmds.setAttr(shader + '.specularRoughness', 0.5)
    if not cmds.listConnections(shader + '.metalness', source=True):
        cmds.setAttr(shader + '.metalness', 0.0)
    if not cmds.listConnections(shader + '.opacity', source=True):
        cmds.setAttr(shader + '.opacity', 1.0, 1.0, 1.0, type='double3')


def setup_material(sg, texture_dir):
    shaders = cmds.ls(cmds.listConnections(sg + '.surfaceShader'), materials=True) or []
    if not shaders:
        return
    original = shaders[0]

    shapes = cmds.listConnections(sg, type='mesh') or []
    uv_state = {}
    for shp in shapes:
        try:
            current = cmds.polyUVSet(shp, query=True, currentUVSet=True)
            uv_state[shp] = current[0] if current else None
        except Exception:
            uv_state[shp] = None


    src = cmds.rename(original, original + '_src')
    shader = cmds.shadingNode('aiStandardSurface', asShader=True, name=original)
    copy_basic_attrs(src, shader)
    reused = reconnect_existing_textures(src, shader)


    if not reused:
        for key, data in TEXTURE_RULES.items():
            dst_attr = data['attr']
            if key == 'normal':
                if cmds.listConnections(shader + '.normalCamera', source=True):
                    continue
            elif key == 'height':
                if cmds.listConnections(sg + '.displacementShader', source=True):
                    continue
            else:
                if cmds.listConnections(shader + '.' + dst_attr, source=True):
                    continue
            tex = find_texture(original, texture_dir, data['suffixes'])
            if not tex:
                continue
            if key == 'normal':
                connect_normal_map(shader, tex)
            elif key == 'height':
                connect_height_map(shader, sg, tex)
            else:
                connect_file(shader, dst_attr, tex, data['colorSpace'], data['channel'])
                if key == 'emission':
                    cmds.setAttr(shader + '.emission', 1)

    apply_default_values(shader)
    cmds.connectAttr(shader + '.outColor', sg + '.surfaceShader', force=True)

    for shp, uv in uv_state.items():
        if uv:
            try:
                cmds.polyUVSet(shp, currentUVSet=True, uvSet=uv)

            except Exception:
                pass

    if shader != src:
        if not cmds.listConnections(src, source=False, destination=True):
            try:
                cmds.delete(src)

            except Exception:
                pass

    if shader != src:
        if not cmds.listConnections(src, source=False, destination=True):
            try:
                cmds.delete(src)
            except Exception:
                pass


def import_fbx_with_materials():
    ensure_plugins()
    fbx = pick_fbx()
    if not fbx:
        return
    tex_dir = pick_texture_dir(fbx)
    try:
        cmds.file(
            fbx,
            i=True,
            type='FBX',
            ignoreVersion=True,
            mergeNamespacesOnClash=False,
            options='fbx'
        )
    except Exception as e:
        cmds.warning('Could not import FBX: %s' % e)
        return

    sgs = [s for s in cmds.ls(type='shadingEngine') if s not in ('initialShadingGroup', 'initialParticleSE')]
    for sg in sgs:
        try:
            setup_material(sg, tex_dir)
        except Exception as e:
            cmds.warning('Failed to set up %s: %s' % (sg, e))


if __name__ == '__main__':
    import_fbx_with_materials()
