# build_props.py —— Blender 5.2 无头建模：海滨世界场景道具集（props.glb）
# 每个道具一个顶层命名节点，JS 里克隆摆放；海鸥带 WingL/WingR、棕榈带 Crown 空物体供动画
# 运行：blender --background --factory-startup --python tools/build_props.py
import bpy, bmesh, math, os, random
from mathutils import Vector, Matrix, noise

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT_GLB = os.path.join(ROOT, 'assets', 'props.glb')
R = math.radians
random.seed(7)

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

ALL = []          # 导出对象
TOPS = []         # 顶层道具根

def lin(hexs):
    r, g, b = ((hexs >> 16) & 255) / 255, ((hexs >> 8) & 255) / 255, (hexs & 255) / 255
    f = lambda c: ((c + 0.055) / 1.055) ** 2.4 if c > 0.04045 else c / 12.92
    return (f(r), f(g), f(b), 1.0)

def mat(name, hexs, rough=0.6, metal=0.0, emit=None, emit_s=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value = lin(hexs)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    if emit is not None:
        b.inputs['Emission Color'].default_value = lin(emit)
        b.inputs['Emission Strength'].default_value = emit_s
    return m

P = dict(
    trunk=mat('PalmTrunk', 0xA9855F, 0.8),
    trunkring=mat('PalmRing', 0x8A6A45, 0.85),
    frond=mat('PalmFrond', 0x4E9A46, 0.65),
    frond2=mat('PalmFrondLight', 0x6FB356, 0.65),
    coco=mat('Coconut', 0x7A5A38, 0.7),
    wallB=mat('HutWallBlue', 0xBFE3EA, 0.7),
    wallY=mat('HutWallYellow', 0xFFE9A8, 0.7),
    trim=mat('HutTrim', 0xFCFAF4, 0.6),
    roofC=mat('RoofCoral', 0xFF8A70, 0.65),
    roofM=mat('RoofMint', 0x6FD6B0, 0.65),
    roofR=mat('RoofRed', 0xE4573D, 0.65),
    glass=mat('WindowGlass', 0xBFE3F2, 0.15),
    wood=mat('DeckWood', 0xC89B6C, 0.75),
    white=mat('PureWhite', 0xFCFCFA, 0.6),
    gullW=mat('GullWhite', 0xFBFBF8, 0.6),
    gullG=mat('GullGray', 0x9FB3BC, 0.6),
    gullB=mat('GullBeak', 0xF2A93B, 0.5),
    fishB=mat('FishBlue', 0x9BC4DE, 0.35),
    fishW=mat('FishBelly', 0xF6F8F8, 0.5),
    crabO=mat('CrabOrange', 0xF2793D, 0.55),
    starP=mat('StarPink', 0xF2889B, 0.7),
    shellC=mat('ShellCream', 0xF6D9C0, 0.6),
    rockG=mat('RockGray', 0x9AA3A6, 0.9),
    umbR=mat('UmbRed', 0xE8574A, 0.7),
    umbW=mat('UmbWhite', 0xFBFAF5, 0.7),
    ballR=mat('BallRed', 0xE8574A, 0.4),
    sailW=mat('SailWhite', 0xFDFDF9, 0.6),
    hullW=mat('HullWhite', 0xFAF8F2, 0.5),
    hullR=mat('HullStripe', 0xE4573D, 0.6),
    mast=mat('MastSilver', 0xC8D0D4, 0.4, 0.6),
    lampW=mat('LampWhite', 0xF4F2EC, 0.5),
    lampG=mat('LampGlow', 0xFFF6D8, 0.3, 0.0, emit=0xFFF2C0, emit_s=2.0),
    stemG=mat('StemGreen', 0x6FA84E, 0.7),
    grassG=mat('GrassGreen', 0x7CB65A, 0.8),
    flR=mat('FlowerRed', 0xF25C54, 0.6),
    flY=mat('FlowerYellow', 0xFFD24C, 0.6),
    flP=mat('FlowerPink', 0xFF9EC4, 0.6),
    flW=mat('FlowerWhite', 0xFDFBF4, 0.6),
    bushG=mat('BushGreen', 0x5E9C4A, 0.8),
    cloudW=mat('CloudWhite', 0xFFFFFF, 1.0, 0.0, emit=0xFFFFFF, emit_s=0.35),
    isleG=mat('IsleGreen', 0x69A86B, 0.85),
    isleS=mat('IsleSand', 0xEFD9A8, 0.9),
    signW=mat('SignWhite', 0xFCFCFA, 0.5),
    signR=mat('SignRed', 0xE4573D, 0.6),
    signB=mat('SignBlue', 0x2E77C8, 0.5),
    eyeB=mat('EyeBlack', 0x1B1D20, 0.15),
)

def _reg(o):
    ALL.append(o)
    return o

def _ma(o, m):
    o.data.materials.clear()
    o.data.materials.append(m)

def shade(o, subdiv=0):
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    try:
        bpy.ops.object.shade_smooth()
    except RuntimeError:
        pass
    if subdiv:
        s = o.modifiers.new('sub', 'SUBSURF')
        s.levels = subdiv
        s.render_levels = subdiv
    return o

def sph(name, r, loc, m, scale=(1, 1, 1), rot=(0, 0, 0), seg=24, rings=14, subdiv=1):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, segments=seg, ring_count=rings, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name; o.scale = scale
    _ma(o, m); return _reg(shade(o, subdiv))

def ico(name, r, loc, m, scale=(1, 1, 1), subdiv=2):
    bpy.ops.mesh.primitive_ico_sphere_add(radius=r, subdivisions=subdiv, location=loc)
    o = bpy.context.active_object; o.name = name; o.scale = scale
    _ma(o, m); return _reg(shade(o))

def cube(name, size, loc, m, rot=(0, 0, 0), subdiv=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name; o.scale = size
    _ma(o, m); return _reg(shade(o, subdiv))

def cyl(name, r, d, loc, m, rot=(0, 0, 0), r2=None, verts=16, subdiv=0):
    bpy.ops.mesh.primitive_cone_add(radius1=r, radius2=(r if r2 is None else r2), depth=d,
                                    vertices=verts, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name
    _ma(o, m); return _reg(shade(o, subdiv))

def tor(name, rj, rn, loc, m, rot=(0, 0, 0), seg=28, sides=8, scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_torus_add(major_radius=rj, minor_radius=rn, major_segments=seg,
                                     minor_segments=sides, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name; o.scale = scale
    _ma(o, m); return _reg(shade(o))

def tube(name, pts, radii, m, res=5, cyclic=False, subdiv=1):
    cu = bpy.data.curves.new(name + '_cu', 'CURVE')
    cu.dimensions = '3D'; cu.bevel_resolution = res; cu.bevel_mode = 'ROUND'
    cu.bevel_depth = 1.0; cu.use_fill_caps = True; cu.resolution_u = 12
    sp = cu.splines.new('BEZIER'); sp.bezier_points.add(len(pts) - 1)
    sp.use_cyclic_u = cyclic
    Pv = [Vector(p) for p in pts]; n = len(Pv)
    for i, bp in enumerate(sp.bezier_points):
        bp.co = Pv[i]
        if cyclic:
            prev, nxt = Pv[(i - 1) % n], Pv[(i + 1) % n]
        else:
            prev = Pv[i - 1] if i > 0 else Pv[0] + (Pv[0] - Pv[1])
            nxt = Pv[i + 1] if i < n - 1 else Pv[-1] + (Pv[-1] - Pv[-2])
        bp.handle_left = Pv[i] - (nxt - prev) / 6.0
        bp.handle_right = Pv[i] + (nxt - prev) / 6.0
        bp.handle_left_type = 'ALIGNED'; bp.handle_right_type = 'ALIGNED'
        rv = radii[i] if isinstance(radii, (list, tuple)) else radii
        try:
            bp.radius = rv
        except AttributeError:
            bp.bevel_radius = rv
    o = bpy.data.objects.new(name, cu)
    bpy.context.collection.objects.link(o)
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.convert(target='MESH')
    o = bpy.context.active_object; o.name = name
    _ma(o, m); return _reg(shade(o, subdiv))

def join(objs, name):
    objs = [o for o in objs if o is not None]
    if not objs:
        return None
    if len(objs) == 1:
        objs[0].name = name; return objs[0]
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[-1]
    bpy.ops.object.join()
    m = bpy.context.active_object; m.name = name
    for o in objs[:-1]:
        if o in ALL:
            ALL.remove(o)
    return m

def empty(name, loc, parent=None):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = 'PLAIN_AXES'; e.empty_display_size = 0.1
    bpy.context.collection.objects.link(e); _reg(e)
    if parent:
        e.parent = parent
        e.matrix_parent_inverse = Matrix.Identity(4)
        bpy.context.view_layer.update()
        e.matrix_basis = parent.matrix_world.inverted() @ Matrix.Translation(Vector(loc))
    else:
        e.location = loc
    return e

def parent_to(child, par):
    W = child.matrix_basis.copy()
    child.parent = par
    child.matrix_parent_inverse = Matrix.Identity(4)
    bpy.context.view_layer.update()
    child.matrix_basis = par.matrix_world.inverted() @ W

def vcol(obj, fn):
    """逐面恒定顶点色：同一面的所有 corner 同色，避免面内插值糊掉条纹"""
    me = obj.data
    if not me.color_attributes:
        me.color_attributes.new('Col', 'BYTE_COLOR', 'CORNER')
    ca = me.color_attributes[0]
    for p in me.polygons:
        c = fn(p.center)
        for li in p.loop_indices:
            ca.data[li].color = c

def top(root, name):
    root.name = name
    TOPS.append(root)
    return root

# ================================================================ 棕榈树
def build_palm(name, h, lean, nfrond, scale=1.0):
    root = empty(name + '_root', (0, 0, 0))
    pts = [(0, 0, 0)]
    n = 6
    for i in range(1, n + 1):
        t = i / n
        pts.append((lean * t * t * h * 0.35, lean * 0.25 * t * t * h * 0.2, t * h))
    radii = [0.13 * scale] + [ (0.13 - 0.055 * (i / n)) * scale for i in range(1, n + 1)]
    trunk = tube('p_trunk', pts, radii, P['trunk'], res=5)
    rings = []
    for i in range(1, n):
        t = i / n
        rings.append(tor('p_ring%d' % i, (0.13 - 0.055 * t) * scale + 0.004, 0.012,
                         (lean * t * t * h * 0.35, lean * 0.25 * t * t * h * 0.2, t * h),
                         P['trunkring'], seg=16, sides=6))
    trunk = join([trunk] + rings, 'p_trunk_all')
    parent_to(trunk, root)
    crown_pos = Vector(pts[-1])
    Crown = empty(name + '_Crown', crown_pos, root)
    fronds = []
    for k in range(nfrond):
        a = k * math.tau / nfrond + 0.3
        d = Vector((math.cos(a), math.sin(a), 0))
        L = (1.5 + 0.25 * ((k * 37) % 3)) * scale
        seg = 7
        rib_pts = []
        for i in range(seg + 1):
            t = i / seg
            rib_pts.append(crown_pos + d * (L * t) + Vector((0, 0, 0.35 * L * t - 0.55 * L * t * t)))
        rib = tube('p_rib%d' % k, rib_pts, [0.02 * scale] * (seg + 1), P['frond'], res=3)
        leaves = [rib]
        for i in range(1, seg + 1):
            t = i / seg
            base = crown_pos + d * (L * t) + Vector((0, 0, 0.35 * L * t - 0.55 * L * t * t))
            llen = (0.50 * (1 - 0.5 * t) + 0.12) * scale
            for sgn in (1, -1):
                la = a + sgn * R(56)
                ld = Vector((math.cos(la), math.sin(la), 0))
                droop = -0.35 - 0.45 * t
                lc = base + ld * (llen / 2) + Vector((0, 0, droop * llen / 2))
                leaves.append(cube('p_leaf%d_%d' % (k, i * 2 + sgn), (llen, 0.085 * scale, 0.008),
                                   lc, P['frond'] if (i + k) % 2 else P['frond2'],
                                   rot=(0, R(droop * 34), la)))
        fronds.append(join(leaves, 'p_frond%d' % k))
    cocos = []
    for i in range(3):
        a = i * math.tau / 3
        cocos.append(sph('p_coco%d' % i, 0.06 * scale,
                         crown_pos + Vector((0.09 * math.cos(a), 0.09 * math.sin(a), -0.08)),
                         P['coco'], seg=12, rings=8, subdiv=0))
    parent_to(join(fronds + cocos, name + '_crown_geo'), Crown)
    return top(root, name)

build_palm('Palm', 3.2, 0.5, 8)
build_palm('PalmSmall', 1.9, -0.4, 6, scale=0.8)

# ================================================================ 沙滩小屋 x2
def build_hut(name, wallm, roofm, h=2.2, w=2.4, dpt=2.2, balcony=False):
    root = empty(name + '_root', (0, 0, 0))
    parts = [
        cube('h_wall', (w, dpt, h), (0, 0, h / 2 + 0.25), wallm),
        cyl('h_roof', w * 0.78, 0.95, (0, 0, h + 0.25 + 0.475), roofm, r2=0.06, verts=4, rot=(0, 0, R(45))),
        cube('h_deck', (w + 0.7, dpt + 0.7, 0.12), (0, 0, 0.19), P['wood']),
        cube('h_door', (0.55, 0.06, 1.15), (0, -dpt / 2 - 0.02, 0.25 + 0.62), P['trim']),
        cube('h_win1', (0.5, 0.06, 0.5), (-w * 0.3, -dpt / 2 - 0.02, 1.35), P['glass']),
        cube('h_win1f', (0.6, 0.05, 0.6), (-w * 0.3, -dpt / 2 - 0.015, 1.35), P['trim']),
        cube('h_win2', (0.5, 0.06, 0.5), (w * 0.3, -dpt / 2 - 0.02, 1.35), P['glass']),
        cube('h_win2f', (0.6, 0.05, 0.6), (w * 0.3, -dpt / 2 - 0.015, 1.35), P['trim']),
    ]
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts.append(cyl('h_post', 0.05, 0.5, (sx * w * 0.45, sy * dpt * 0.45, 0.0), P['trim'], verts=8))
    if balcony:
        parts.append(cube('h_balc', (w * 0.8, 0.5, 0.08), (0, -dpt / 2 - 0.3, 1.75), P['wood']))
        for i in range(6):
            parts.append(cyl('h_br%d' % i, 0.02, 0.4, (-w * 0.35 + i * w * 0.14, -dpt / 2 - 0.52, 1.98), P['trim'], verts=6))
        parts.append(cube('h_brail', (w * 0.8, 0.05, 0.05), (0, -dpt / 2 - 0.52, 2.18), P['trim']))
    parent_to(join(parts, name + '_geo'), root)
    return top(root, name)

build_hut('Hut1', P['wallB'], P['roofC'])
build_hut('Hut2', P['wallY'], P['roofM'], h=2.6, w=2.1, dpt=2.0, balcony=True)

# ================================================================ 救生塔
def build_tower():
    root = empty('Tower_root', (0, 0, 0))
    parts = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts.append(cyl('t_leg', 0.05, 1.9, (sx * 0.62, sy * 0.62, 0.95), P['trim'],
                             rot=(R(-6 * sy), R(6 * sx), 0), verts=8))
    parts.append(cube('t_plat', (1.7, 1.7, 0.1), (0, 0, 1.9), P['wood']))
    parts.append(cube('t_cab', (1.5, 1.5, 1.1), (0, 0, 2.5), P['white']))
    parts.append(cyl('t_roof', 1.25, 0.6, (0, 0, 3.35), P['roofR'], r2=0.05, verts=4, rot=(0, 0, R(45))))
    parts.append(cube('t_win', (1.0, 0.05, 0.5), (0, -0.76, 2.7), P['glass']))
    for i in range(5):
        parts.append(cyl('t_lad%d' % i, 0.025, 0.5, (0.35, -0.78, 0.35 + i * 0.35), P['trim'], rot=(R(90), 0, 0), verts=6))
    for s in (-1, 1):
        parts.append(cyl('t_ladrail%d' % s, 0.02, 1.9, (0.35 + s * 0.25, -0.78, 1.05), P['trim'], verts=6))
    parts.append(cyl('t_pole', 0.02, 0.7, (0.5, 0.5, 3.9), P['trim'], verts=6))
    parts.append(cube('t_flag', (0.3, 0.02, 0.18), (0.66, 0.5, 4.1), P['signR']))
    parent_to(join(parts, 'Tower_geo'), root)
    return top(root, 'Tower')

build_tower()

# ================================================================ 海鸥（带扇翅空物体）
def build_gull():
    root = empty('Gull_root', (0, 0, 0))
    body = join([
        sph('g_body', 1.0, (0, 0, 0), P['gullW'], scale=(0.105, 0.052, 0.058), seg=20, rings=12, subdiv=1),
        sph('g_head', 0.042, (0.105, 0, 0.055), P['gullW'], seg=16, rings=10, subdiv=1),
        cyl('g_beak', 0.010, 0.05, (0.155, 0, 0.05), P['gullB'], rot=(0, R(90), 0), r2=0.002, verts=8),
        sph('g_eyeL', 0.007, (0.115, 0.032, 0.065), P['eyeB'], seg=8, rings=6, subdiv=0),
        sph('g_eyeR', 0.007, (0.115, -0.032, 0.065), P['eyeB'], seg=8, rings=6, subdiv=0),
        sph('g_tail', 1.0, (-0.115, 0, 0.012), P['gullG'], scale=(0.055, 0.030, 0.014), rot=(0, R(-14), 0), seg=12, rings=8, subdiv=0),
    ], 'Gull_body')
    parent_to(body, root)
    for s, tag in ((1, 'L'), (-1, 'R')):
        W = empty('Gull_Wing' + tag, (0.01, 0.045 * s, 0.02), root)
        wg = cube('g_wing', (0.13, 0.30, 0.012), (0.0, 0.19 * s, 0.012), P['gullW'], subdiv=1)
        bm = bmesh.new(); bm.from_mesh(wg.data)
        for v in bm.verts:
            t = (v.co.y * s + 0.15) / 0.30
            v.co.x *= (1 - 0.55 * max(0, t))
            v.co.z += 0.05 * max(0, t) ** 1.5
        bm.to_mesh(wg.data); bm.free(); wg.data.update()
        tip = cube('g_wtip', (0.07, 0.10, 0.010), (-0.015, 0.30 * s, 0.055), P['gullG'], rot=(R(8 * s), 0, 0))
        parent_to(join([wg, tip], 'Gull_wing' + tag), W)
    return top(root, 'Gull')

build_gull()

# ================================================================ 小鱼 / 螃蟹 / 海星 / 贝壳
def build_fish():
    root = empty('Fish_root', (0, 0, 0))
    f = join([
        sph('f_body', 1.0, (0, 0, 0), P['fishB'], scale=(0.12, 0.035, 0.055), seg=20, rings=12, subdiv=1),
        sph('f_belly', 1.0, (0.01, 0, -0.02), P['fishW'], scale=(0.09, 0.032, 0.03), seg=14, rings=8, subdiv=1),
        sph('f_tail', 1.0, (-0.135, 0, 0.005), P['fishB'], scale=(0.045, 0.012, 0.045), rot=(0, R(20), 0), seg=12, rings=8, subdiv=0),
        sph('f_fin', 1.0, (0.0, 0, 0.055), P['fishB'], scale=(0.035, 0.008, 0.03), rot=(0, R(-25), 0), seg=10, rings=6, subdiv=0),
        sph('f_eyeL', 0.008, (0.085, 0.026, 0.015), P['eyeB'], seg=8, rings=6, subdiv=0),
        sph('f_eyeR', 0.008, (0.085, -0.026, 0.015), P['eyeB'], seg=8, rings=6, subdiv=0),
    ], 'Fish_geo')
    parent_to(f, root)
    return top(root, 'Fish')

def build_crab():
    root = empty('Crab_root', (0, 0, 0))
    parts = [sph('c_body', 1.0, (0, 0, 0.05), P['crabO'], scale=(0.075, 0.095, 0.048), seg=20, rings=12, subdiv=1)]
    for s in (1, -1):
        parts.append(cyl('c_arm%d' % s, 0.012, 0.09, (0.075, 0.075 * s, 0.055), P['crabO'], rot=(R(60 * s), R(20), 0), verts=8))
        parts.append(sph('c_claw%d' % s, 0.032, (0.115, 0.115 * s, 0.085), P['crabO'], scale=(1.2, 0.8, 0.7), seg=12, rings=8, subdiv=0))
        parts.append(cyl('c_pin%d' % s, 0.012, 0.045, (0.15, 0.125 * s, 0.09), P['crabO'], rot=(0, R(70), R(20 * s)), r2=0.002, verts=6))
        for i in range(3):
            parts.append(cyl('c_leg%d_%d' % (s, i), 0.007, 0.10,
                             (-0.02 - i * 0.03, (0.09 + i * 0.012) * s, 0.03),
                             P['crabO'], rot=(R(55 * s), 0, R(-15 * i * s)), verts=6))
    parts.append(cyl('c_eyestL', 0.006, 0.035, (0.03, 0.025, 0.10), P['crabO'], verts=6))
    parts.append(cyl('c_eyestR', 0.006, 0.035, (0.03, -0.025, 0.10), P['crabO'], verts=6))
    parts.append(sph('c_eyeL', 0.011, (0.032, 0.026, 0.12), P['eyeB'], seg=8, rings=6, subdiv=0))
    parts.append(sph('c_eyeR', 0.011, (0.032, -0.026, 0.12), P['eyeB'], seg=8, rings=6, subdiv=0))
    parent_to(join(parts, 'Crab_geo'), root)
    return top(root, 'Crab')

def build_star():
    root = empty('Starfish_root', (0, 0, 0))
    parts = [sph('s_c', 0.045, (0, 0, 0.018), P['starP'], scale=(1, 1, 0.5), seg=14, rings=8, subdiv=0)]
    for i in range(5):
        a = i * math.tau / 5
        parts.append(cyl('s_a%d' % i, 0.028, 0.11, (0.062 * math.cos(a), 0.062 * math.sin(a), 0.014),
                         P['starP'], rot=(0, R(80), a + R(90)), r2=0.004, verts=8))
    parent_to(join(parts, 'Starfish_geo'), root)
    return top(root, 'Starfish')

def build_shell():
    root = empty('Shell_root', (0, 0, 0))
    sh = sph('sh_body', 1.0, (0, 0, 0.012), P['shellC'], scale=(0.055, 0.05, 0.02), seg=16, rings=10, subdiv=1)
    bm = bmesh.new(); bm.from_mesh(sh.data)
    for v in bm.verts:
        if v.co.y < 0:
            v.co.z *= 0.2
        v.co.z += 0.012 * math.sin(v.co.x * 90) * max(0, v.co.y + 0.2)
    bm.to_mesh(sh.data); bm.free(); sh.data.update()
    parent_to(sh, root)
    return top(root, 'Shell')

build_fish(); build_crab(); build_star(); build_shell()

# ================================================================ 礁石
def build_rock(name, r, seed):
    root = empty(name + '_root', (0, 0, 0))
    rk = ico(name + '_geo', r, (0, 0, r * 0.45), P['rockG'], scale=(1, 0.85, 0.62), subdiv=3)
    bm = bmesh.new(); bm.from_mesh(rk.data)
    for v in bm.verts:
        n = noise.noise(v.co * 2.4 + Vector((seed, seed, seed)))
        v.co += v.normal * n * r * 0.22
        if v.co.z < -r * 0.25:
            v.co.z = -r * 0.25
    bm.to_mesh(rk.data); bm.free(); rk.data.update()
    parent_to(rk, root)
    return top(root, name)

build_rock('Rock1', 0.34, 3.1)
build_rock('Rock2', 0.18, 8.7)

# ================================================================ 遮阳伞 + 沙滩球
def build_umbrella():
    root = empty('Umbrella_root', (0, 0, 0))
    pole = cyl('u_pole', 0.022, 1.7, (0, 0, 0.85), P['trim'], verts=10)
    canopy = cyl('u_canopy', 0.95, 0.60, (0, 0, 1.58), P['umbR'], r2=0.03, verts=8, subdiv=1)
    vcol(canopy, lambda co: lin(0xE8574A) if (math.atan2(co.y, co.x) // (math.tau / 8)) % 2 == 0 else lin(0xFBFAF5))
    fin = sph('u_fin', 0.035, (0, 0, 1.86), P['umbR'], seg=10, rings=6, subdiv=0)
    u = join([pole, canopy, fin], 'Umbrella_geo')
    u.rotation_euler = (R(8), R(4), 0)
    parent_to(u, root)
    return top(root, 'Umbrella')

def build_ball():
    root = empty('Ball_root', (0, 0, 0))
    b = sph('Ball_geo', 0.14, (0, 0, 0.14), P['ballR'], seg=20, rings=12, subdiv=1)
    cols = [lin(0xE8574A), lin(0xFBFAF5), lin(0x2E77C8)]
    vcol(b, lambda co: cols[int((math.atan2(co.y, co.x) + math.pi) // (math.tau / 3)) % 3])
    parent_to(b, root)
    return top(root, 'Ball')

build_umbrella(); build_ball()

# ================================================================ 帆船
def build_sailboat():
    root = empty('Sailboat_root', (0, 0, 0))
    hull = sph('sb_hull', 1.0, (0, 0, 0.16), P['hullW'], scale=(0.95, 0.20, 0.30), seg=24, rings=12, subdiv=1)
    bm = bmesh.new(); bm.from_mesh(hull.data)
    for v in bm.verts:
        if v.co.z > 0.05:
            v.co.z = 0.05
        t = abs(v.co.x) / 0.95
        v.co.y *= (1 - 0.5 * t ** 2)
    bm.to_mesh(hull.data); bm.free(); hull.data.update()
    stripe = tor('sb_stripe', 0.80, 0.02, (0, 0, 0.19), P['hullR'], rot=(0, 0, 0), seg=32, sides=6, scale=(1.15, 0.26, 1))
    mast = cyl('sb_mast', 0.02, 1.9, (0.05, 0, 1.1), P['mast'], verts=8)
    mains = cube('sb_main', (0.02, 0.02, 1.5), (-0.35, 0, 1.15), P['sailW'])
    bm = bmesh.new(); bm.from_mesh(mains.data)
    for v in bm.verts:
        t = (v.co.z + 0.75) / 1.5
        v.co.x *= (0.15 + 0.85 * (1 - t))
        v.co.y += 0.10 * math.sin(t * 2.2) * (1 - t)
    bm.to_mesh(mains.data); bm.free(); mains.data.update()
    jib = cube('sb_jib', (0.02, 0.02, 1.1), (0.42, 0, 0.95), P['sailW'])
    bm = bmesh.new(); bm.from_mesh(jib.data)
    for v in bm.verts:
        t = (v.co.z + 0.55) / 1.1
        v.co.x *= (0.2 + 0.8 * (1 - t))
    bm.to_mesh(jib.data); bm.free(); jib.data.update()
    flag = cube('sb_flag', (0.16, 0.015, 0.09), (0.14, 0, 2.02), P['signR'])
    parent_to(join([hull, stripe, mast, mains, jib, flag], 'Sailboat_geo'), root)
    return top(root, 'Sailboat')

build_sailboat()

# ================================================================ 长椅 / 路灯 / 花丛 / 灌木
def build_bench():
    root = empty('Bench_root', (0, 0, 0))
    parts = []
    for i in range(4):
        parts.append(cube('b_sl%d' % i, (1.5, 0.11, 0.035), (0, -0.18 + i * 0.12, 0.45), P['wood']))
    for i in range(2):
        parts.append(cube('b_bk%d' % i, (1.5, 0.035, 0.11), (0, 0.24, 0.72 + i * 0.14), P['wood']))
    for sx in (-1, 1):
        parts.append(cube('b_leg%d' % sx, (0.06, 0.5, 0.45), (sx * 0.65, 0.0, 0.225), P['lampW']))
        parts.append(cube('b_bks%d' % sx, (0.06, 0.05, 0.5), (sx * 0.65, 0.24, 0.72), P['lampW']))
    parent_to(join(parts, 'Bench_geo'), root)
    return top(root, 'Bench')

def build_lamp():
    root = empty('Lamp_root', (0, 0, 0))
    parts = [
        cyl('l_base', 0.09, 0.18, (0, 0, 0.09), P['lampW'], verts=12),
        cyl('l_pole', 0.035, 2.9, (0, 0, 1.5), P['lampW'], verts=10),
        tube('l_arm', [(0, 0, 2.9), (0.12, 0, 3.05), (0.35, 0, 3.08)], [0.03, 0.026, 0.024], P['lampW'], res=4),
        sph('l_head', 0.09, (0.38, 0, 3.02), P['lampG'], scale=(1, 1, 0.85), seg=16, rings=10, subdiv=1),
        cyl('l_cap', 0.10, 0.03, (0.38, 0, 3.10), P['lampW'], verts=12),
    ]
    parent_to(join(parts, 'Lamp_geo'), root)
    return top(root, 'Lamp')

def build_flowers():
    root = empty('Flowers_root', (0, 0, 0))
    parts = []
    fm = [P['flR'], P['flY'], P['flP'], P['flW']]
    for i in range(14):
        a = random.uniform(0, math.tau)
        rr = random.uniform(0, 0.42)
        x, y = rr * math.cos(a), rr * math.sin(a)
        h = random.uniform(0.16, 0.30)
        parts.append(cyl('fl_st%d' % i, 0.006, h, (x, y, h / 2), P['stemG'], verts=5))
        parts.append(sph('fl_h%d' % i, 0.035, (x, y, h), fm[i % 4], scale=(1, 1, 0.75), seg=10, rings=6, subdiv=0))
        parts.append(sph('fl_c%d' % i, 0.014, (x, y, h + 0.02), P['flY'], seg=8, rings=5, subdiv=0))
    for i in range(10):
        a = random.uniform(0, math.tau)
        rr = random.uniform(0.1, 0.5)
        parts.append(cyl('fl_g%d' % i, 0.012, 0.16, (rr * math.cos(a), rr * math.sin(a), 0.07),
                         P['grassG'], r2=0.001, verts=4))
    parent_to(join(parts, 'Flowers_geo'), root)
    return top(root, 'Flowers')

def build_bush():
    root = empty('Bush_root', (0, 0, 0))
    parts = []
    for i, (x, y, r) in enumerate([(0, 0, 0.34), (0.26, 0.1, 0.26), (-0.24, -0.08, 0.24), (0.05, -0.24, 0.2)]):
        b = ico('bu%d' % i, r, (x, y, r * 0.75), P['bushG'], subdiv=2)
        bm = bmesh.new(); bm.from_mesh(b.data)
        for v in bm.verts:
            v.co += v.normal * noise.noise(v.co * 3 + Vector((i, i, i))) * r * 0.18
        bm.to_mesh(b.data); bm.free(); b.data.update()
        parts.append(b)
    parent_to(join(parts, 'Bush_geo'), root)
    return top(root, 'Bush')

build_bench(); build_lamp(); build_flowers(); build_bush()

# ================================================================ 云 / 远岛 / 路牌
def build_cloud():
    root = empty('Cloud_root', (0, 0, 0))
    parts = []
    for i, (x, y, z, r) in enumerate([(0, 0, 0, 0.62), (0.55, 0.1, 0.08, 0.48), (-0.55, -0.05, 0.05, 0.45),
                                      (0.25, -0.3, 0.0, 0.4), (-0.25, 0.28, 0.02, 0.38), (0.9, -0.15, -0.05, 0.3)]):
        parts.append(ico('cl%d' % i, r, (x, y, z), P['cloudW'], scale=(1, 0.8, 0.62), subdiv=2))
    parent_to(join(parts, 'Cloud_geo'), root)
    return top(root, 'Cloud')

def build_island():
    root = empty('Island_root', (0, 0, 0))
    parts = [
        cyl('i_base', 7.5, 0.5, (0, 0, 0.1), P['isleS'], r2=6.5, verts=28),
        cyl('i_hill', 5.0, 1.5, (0, 0, 0.9), P['isleG'], r2=2.6, verts=24),
        cyl('i_hill2', 2.2, 0.9, (1.2, 0.6, 1.9), P['isleG'], r2=1.0, verts=16),
    ]
    parent_to(join(parts, 'Island_geo'), root)
    return top(root, 'Island')

def build_sign():
    root = empty('Sign_root', (0, 0, 0))
    parts = [
        cyl('sg_post', 0.04, 1.5, (0, 0, 0.75), P['lampW'], verts=10),
        cyl('sg_board', 0.32, 0.035, (0, 0, 1.72), P['signW'], rot=(R(90), 0, 0), verts=28),
        tor('sg_rim', 0.32, 0.022, (0, -0.012, 1.72), P['signR'], rot=(R(90), 0, 0), seg=28, sides=6),
        tor('sg_w1', 0.075, 0.014, (-0.10, -0.030, 1.66), P['signB'], rot=(R(90), 0, 0), seg=16, sides=5),
        tor('sg_w2', 0.075, 0.014, (0.10, -0.030, 1.66), P['signB'], rot=(R(90), 0, 0), seg=16, sides=5),
        tube('sg_fr', [(-0.10, -0.030, 1.66), (-0.02, -0.030, 1.78), (0.06, -0.030, 1.76), (0.10, -0.030, 1.66),
                       (0.0, -0.030, 1.70), (-0.10, -0.030, 1.66)], 0.012, P['signB'], res=3, cyclic=True),
    ]
    parent_to(join(parts, 'Sign_geo'), root)
    return top(root, 'Sign')

build_cloud(); build_island(); build_sign()

# ================================================================ 预览（目录式排布）
def setup_scene():
    bpy.ops.mesh.primitive_plane_add(size=80, location=(0, 0, 0))
    g = bpy.context.active_object
    g.name = 'prev_ground'
    _ma(g, mat('prev_sand', 0xF0E0C0, 0.9))
    w = bpy.data.worlds.new('prev_world')
    bpy.context.scene.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes.get('Background')
    bg.inputs[0].default_value = lin(0xBFE4F5)
    bg.inputs[1].default_value = 1.0
    sd = bpy.data.lights.new('prev_sun', 'SUN')
    sd.energy = 3.2
    so = bpy.data.objects.new('prev_sun', sd)
    bpy.context.collection.objects.link(so)
    so.rotation_euler = (R(48), R(12), R(35))
    scn = bpy.context.scene
    try:
        scn.render.engine = 'BLENDER_EEVEE_NEXT'
    except TypeError:
        scn.render.engine = 'BLENDER_EEVEE'
    scn.render.resolution_x = 1600
    scn.render.resolution_y = 900
    if hasattr(scn, 'eevee') and hasattr(scn.eevee, 'taa_render_samples'):
        scn.eevee.taa_render_samples = 32
    return scn

def render(cam_loc, target, fname, lens=50):
    scn = bpy.context.scene
    cd = bpy.data.cameras.new('prev_cam'); cd.lens = lens
    co = bpy.data.objects.new('prev_cam', cd)
    bpy.context.collection.objects.link(co)
    co.location = cam_loc
    te = bpy.data.objects.new('prev_target', None)
    bpy.context.collection.objects.link(te)
    te.location = target
    c = co.constraints.new('TRACK_TO'); c.target = te
    c.track_axis = 'TRACK_NEGATIVE_Z'; c.up_axis = 'UP_Y'
    scn.camera = co
    scn.render.filepath = os.path.join(ROOT, 'assets', fname)
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(co, do_unlink=True)
    bpy.data.objects.remove(te, do_unlink=True)

# 目录排布：小件一排 / 大件一排
small = ['Fish', 'Crab', 'Starfish', 'Shell', 'Ball', 'Flowers', 'Bush', 'Sign', 'Gull']
big = ['Palm', 'PalmSmall', 'Hut1', 'Hut2', 'Tower', 'Umbrella', 'Bench', 'Lamp', 'Sailboat', 'Rock1']
order = {n: i for i, n in enumerate(small + big)}
for t in TOPS:
    i = order.get(t.name, 0)
    t.location = (i * 2.6 if i < len(small) else (i - len(small)) * 4.2, 0 if i < len(small) else -8, 0)
bpy.context.view_layer.update()
setup_scene()
render((len(small) * 1.3, -9.5, 2.2), (len(small) * 1.3, 0, 0.5), 'prev_props_small.png', lens=45)
render(((len(big) - 1) * 2.1, -16.5, 4.0), ((len(big) - 1) * 2.1, -8, 1.6), 'prev_props_big.png', lens=45)
for t in TOPS:
    t.location = (0, 0, 0)
bpy.context.view_layer.update()
# 展示位：棕榈+小屋+帆船+长椅+路灯 合影自检
show = {'Palm': (0, 0, 0), 'Hut1': (6.5, 3, 0), 'Sailboat': (10, -6, 0), 'Bench': (3.2, -2.6, 0),
        'Lamp': (1.6, -1.6, 0), 'Flowers': (4.6, -1.2, 0), 'Rock1': (8, -1.5, 0), 'Umbrella': (6.8, -3.4, 0)}
for t in TOPS:
    if t.name in show:
        t.location = show[t.name]
bpy.context.view_layer.update()
render((5.2, -10.5, 3.0), (4.6, 0.2, 1.3), 'prev_props_show.png', lens=40)
for t in TOPS:
    t.location = (0, 0, 0)
bpy.context.view_layer.update()

# ================================================================ 导出
bpy.ops.object.select_all(action='DESELECT')
for o in ALL:
    o.select_set(True)
bpy.ops.export_scene.gltf(
    filepath=OUT_GLB,
    export_format='GLB',
    use_selection=True,
    export_apply=True,
    export_animations=False,
    export_skins=False,
    export_yup=True,
)
print('EXPORTED:', OUT_GLB, os.path.getsize(OUT_GLB) // 1024, 'KB')
print('TOPS:', [t.name for t in TOPS])
