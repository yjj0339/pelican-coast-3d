# build_rig.py —— Blender 5.2 无头建模：鹈鹕船长 + 海滨巡游自行车，带完整动画骨架
# 坐标系：X 前进，Y 左，Z 上（导出 GLB 时自动转 Y-up）
# 运行：blender --background --factory-startup --python tools/build_rig.py
import bpy, bmesh, math, os
from mathutils import Vector, Matrix

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT_GLB = os.path.join(ROOT, 'assets', 'rig.glb')
os.makedirs(os.path.join(ROOT, 'assets'), exist_ok=True)
R = math.radians

# 清场（--factory-startup 会带默认 Cube/Camera/Light）
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

ALL = []  # 所有要导出的对象

# ---------------------------------------------------------------- 材质
def lin(hexs):
    """sRGB hex -> 线性颜色（Principled BSDF 必须线性值，否则 GLB 发粉）"""
    r, g, b = ((hexs >> 16) & 255) / 255, ((hexs >> 8) & 255) / 255, (hexs & 255) / 255
    f = lambda c: ((c + 0.055) / 1.055) ** 2.4 if c > 0.04045 else c / 12.92
    return (f(r), f(g), f(b), 1.0)

def mat(name, hexs, rough=0.6, metal=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value = lin(hexs)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    return m

PAL = dict(
    frame=mat('FrameMint', 0x2EC4A6, 0.32, 0.25),
    fender=mat('FenderCream', 0xFBF3E2, 0.4),
    tire=mat('TireDark', 0x37393C, 0.85),
    rim=mat('RimSilver', 0xCBD4D8, 0.3, 0.85),
    spoke=mat('SpokeSilver', 0xB9C2C6, 0.35, 0.8),
    hub=mat('HubSilver', 0xAEB8BD, 0.4, 0.7),
    leather=mat('SaddleTan', 0xC88B5A, 0.65),
    grip=mat('GripCoral', 0xFF7A5C, 0.7),
    gold=mat('BrassGold', 0xE8B64C, 0.25, 0.9),
    chain=mat('ChainSteel', 0x5A6165, 0.5, 0.75),
    wicker=mat('BasketWicker', 0xD9A96B, 0.8),
    bodyW=mat('PelicanWhite', 0xF8F4EB, 0.55),
    belly=mat('PelicanBelly', 0xFDF9EF, 0.55),
    neckW=mat('PelicanNeck', 0xFAF6EC, 0.55),
    featherG=mat('FeatherGray', 0xB7C2C7, 0.6),
    beakY=mat('BeakYellow', 0xF2A93B, 0.45),
    beakTip=mat('BeakTipHorn', 0xE0902E, 0.45),
    pouch=mat('PouchCoral', 0xF09A6E, 0.42),
    legO=mat('LegOrange', 0xF08A4B, 0.5),
    eyeB=mat('EyeBlack', 0x1B1D20, 0.15),
    eyeW=mat('EyeGlint', 0xFFFFFF, 0.1),
    iris=mat('IrisPale', 0xC3D4DC, 0.35),
    hatW=mat('HatWhite', 0xFCFCFA, 0.5),
    hatN=mat('HatNavy', 0x2E4A7D, 0.55),
    scarfR=mat('ScarfRed', 0xE84B3C, 0.7),
    scarfW=mat('ScarfWhite', 0xFBF6EA, 0.7),
    flowerR=mat('FlowerRed', 0xF25C54, 0.6),
    flowerY=mat('FlowerYellow', 0xFFD24C, 0.6),
    flowerP=mat('FlowerPink', 0xFF9EC4, 0.6),
    stemG=mat('StemGreen', 0x6FA84E, 0.7),
    bottleM=mat('BottleMint', 0x7FE0C8, 0.3),
)

# ---------------------------------------------------------------- 基础建模
def _reg(obj):
    ALL.append(obj)
    return obj

def _mat_assign(obj, m):
    obj.data.materials.clear()
    obj.data.materials.append(m)

def shade(obj, subdiv=0):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    try:
        bpy.ops.object.shade_smooth()
    except RuntimeError:
        pass
    if subdiv:
        s = obj.modifiers.new('sub', 'SUBSURF')
        s.levels = subdiv
        s.render_levels = subdiv
    return obj

def sph(name, r, loc, matl, scale=(1, 1, 1), rot=(0, 0, 0), seg=32, rings=16, subdiv=1):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, segments=seg, ring_count=rings,
                                         location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    o.scale = scale
    _mat_assign(o, matl)
    return _reg(shade(o, subdiv))

def cube(name, size, loc, matl, rot=(0, 0, 0), subdiv=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    o.scale = size
    _mat_assign(o, matl)
    return _reg(shade(o, subdiv))

def cyl(name, r, d, loc, matl, rot=(0, 0, 0), r2=None, verts=20, subdiv=0):
    """圆锥/圆柱：radius1=底(-Z)，radius2=顶(+Z)，默认与底同粗"""
    bpy.ops.mesh.primitive_cone_add(radius1=r, radius2=(r if r2 is None else r2),
                                    depth=d, vertices=verts, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    _mat_assign(o, matl)
    return _reg(shade(o, subdiv))

def tor(name, rj, rn, loc, matl, rot=(0, 0, 0), seg=36, sides=10, scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_torus_add(major_radius=rj, minor_radius=rn, major_segments=seg,
                                     minor_segments=sides, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    o.scale = scale
    _mat_assign(o, matl)
    return _reg(shade(o))

def tube(name, pts, radii, matl, res=6, cyclic=False, yscale=1.0, subdiv=1):
    """Catmull-Rom -> 贝塞尔 -> 圆管网格；radii 可为标量或每点列表；
    yscale 绕世界原点缩放（截面贴近 y=0 时安全）"""
    cu = bpy.data.curves.new(name + '_cu', 'CURVE')
    cu.dimensions = '3D'
    cu.bevel_resolution = res
    cu.bevel_mode = 'ROUND'
    cu.bevel_depth = 1.0          # 每点 radius 是乘数，基准必须为 1，否则管子零粗细
    cu.use_fill_caps = True       # 管口封盖，否则喙/挡泥板是空心管
    cu.resolution_u = 16
    sp = cu.splines.new('BEZIER')
    sp.bezier_points.add(len(pts) - 1)
    sp.use_cyclic_u = cyclic
    P = [Vector(p) for p in pts]
    n = len(P)
    for i, bp in enumerate(sp.bezier_points):
        bp.co = P[i]
        if cyclic:
            prev, nxt = P[(i - 1) % n], P[(i + 1) % n]
        else:
            prev = P[i - 1] if i > 0 else P[0] + (P[0] - P[1])
            nxt = P[i + 1] if i < n - 1 else P[-1] + (P[-1] - P[-2])
        bp.handle_left = P[i] - (nxt - prev) / 6.0
        bp.handle_right = P[i] + (nxt - prev) / 6.0
        bp.handle_left_type = 'ALIGNED'
        bp.handle_right_type = 'ALIGNED'
        rv = radii[i] if isinstance(radii, (list, tuple)) else radii
        try:
            bp.radius = rv
        except AttributeError:
            bp.bevel_radius = rv
    o = bpy.data.objects.new(name, cu)
    bpy.context.collection.objects.link(o)
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.convert(target='MESH')
    o = bpy.context.active_object
    o.name = name
    if yscale != 1.0:
        o.scale = (1.0, yscale, 1.0)
        bpy.ops.object.transform_apply(scale=True)
    _mat_assign(o, matl)
    return _reg(shade(o, subdiv))

def arc_pts(cx, cz, r, a0, a1, n=9, y=0.0):
    return [(cx + r * math.cos(a0 + (a1 - a0) * i / (n - 1)), y,
             cz + r * math.sin(a0 + (a1 - a0) * i / (n - 1))) for i in range(n)]

def join(objs, name):
    objs = [o for o in objs if o is not None]
    if not objs:
        return None
    if len(objs) == 1:
        objs[0].name = name
        return objs[0]
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[-1]
    bpy.ops.object.join()
    m = bpy.context.active_object
    m.name = name
    for o in objs[:-1]:
        if o in ALL:
            ALL.remove(o)
    return m

def empty(name, loc, parent=None):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = 'PLAIN_AXES'
    e.empty_display_size = 0.06
    bpy.context.collection.objects.link(e)
    _reg(e)
    if parent:
        e.parent = parent
        e.matrix_parent_inverse = Matrix.Identity(4)
        bpy.context.view_layer.update()
        # 显式算局部变换：local = parent.world^-1 @ 期望世界
        e.matrix_basis = parent.matrix_world.inverted() @ Matrix.Translation(Vector(loc))
    else:
        e.location = loc
    return e

def parent_to(child, par):
    """child 当前无父级：basis 即世界变换；挂到 par 下后保持世界位置不变"""
    W = child.matrix_basis.copy()
    child.parent = par
    child.matrix_parent_inverse = Matrix.Identity(4)
    bpy.context.view_layer.update()
    child.matrix_basis = par.matrix_world.inverted() @ W

# ================================================================ 自行车
BIKE = empty('BikeRoot', (0, 0, 0))

WR = 0.34                       # 轮外半径
AXLE_F = (0.62, 0, WR)
AXLE_R = (-0.62, 0, WR)
BB = (0, 0, 0.30)
CRANK_R = 0.15

def build_wheel(prefix, axle, cog=False):
    """轮组网格：局部原点=轴心，挂到轮空物体后绕轴心旋转"""
    parts = [
        tor('t_tire', WR - 0.032, 0.032, axle, PAL['tire'], rot=(R(90), 0, 0), seg=48, sides=12),
        tor('t_rim', 0.285, 0.012, axle, PAL['rim'], rot=(R(90), 0, 0), seg=48, sides=8),
        tor('t_wall', 0.306, 0.004, axle, PAL['fender'], rot=(R(90), 0, 0), seg=48, sides=6),
        cyl('t_hub', 0.035, 0.07, axle, PAL['hub'], rot=(R(90), 0, 0), verts=16),
    ]
    spokes = []
    for i in range(16):
        a = i * math.tau / 16
        mid = (0.032 + 0.285) / 2
        spokes.append(cyl('t_sp%d' % i, 0.0035, 0.253,
                          (axle[0] + mid * math.sin(a), axle[1], axle[2] + mid * math.cos(a)),
                          PAL['spoke'], rot=(0, a, 0), verts=6))
    parts.append(join(spokes, 't_spokes'))
    if cog:
        parts.append(cyl('t_cog', 0.052, 0.012, (axle[0], axle[1] + 0.058, axle[2]),
                         PAL['hub'], rot=(R(90), 0, 0), verts=18))
        teeth = []
        for i in range(14):
            a = i * math.tau / 14
            teeth.append(cyl('t_ct%d' % i, 0.006, 0.016,
                             (axle[0] + 0.055 * math.cos(a), axle[1] + 0.058, axle[2] + 0.055 * math.sin(a)),
                             PAL['hub'], rot=(R(90), a, 0), verts=4))
        parts.append(join(teeth, 't_cogteeth'))
    w = join(parts, prefix + '_geo')
    # 原点重设到轴心（用游标，保留旋转分量；直接赋 matrix_world 会丢旋转）
    bpy.ops.object.select_all(action='DESELECT')
    w.select_set(True)
    bpy.context.view_layer.objects.active = w
    bpy.context.scene.cursor.location = axle
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    bpy.context.scene.cursor.location = (0, 0, 0)
    return w

WheelF = empty('WheelF', AXLE_F, BIKE)
WheelR = empty('WheelR', AXLE_R, BIKE)
parent_to(build_wheel('WF', AXLE_F), WheelF)
parent_to(build_wheel('WR', AXLE_R, cog=True), WheelR)

# ---------------- 车架（低跨 monotube 巡游架）
frame_parts = [
    tube('frame_main',
         [(0.455, 0, 0.60), (0.24, 0, 0.455), (-0.02, 0, 0.44), (-0.20, 0, 0.52),
          (-0.285, 0, 0.78), (-0.30, 0, 0.96)],
         [0.030, 0.032, 0.030, 0.028, 0.026, 0.024], PAL['frame'], res=6),
    cyl('frame_head', 0.028, 0.32, (0.478, 0, 0.775), PAL['frame'], rot=(0, R(-8), 0), verts=16),
]
stays = []
for s in (1, -1):
    stays.append(tube('st%d' % s, [(-0.29, 0.028 * s, 0.90), (-0.62, 0.03 * s, WR)],
                      [0.014, 0.011], PAL['frame'], res=4))
    stays.append(tube('cs%d' % s, [(0.02, 0.03 * s, 0.30), (-0.62, 0.032 * s, WR)],
                      [0.016, 0.011], PAL['frame'], res=4))
frame_parts.append(join(stays, 'frame_stays'))
fork = []
for s in (1, -1):
    fork.append(tube('fk%d' % s,
                     [(0.47, 0.022 * s, 0.62), (0.56, 0.024 * s, 0.47), (AXLE_F[0], 0.026 * s, AXLE_F[2])],
                     [0.015, 0.013, 0.011], PAL['rim'], res=4))
fork.append(cyl('fk_steer', 0.016, 0.34, (0.485, 0, 0.79), PAL['rim'], rot=(0, R(-8), 0), verts=12))
frame_parts.append(join(fork, 'frame_fork'))
parent_to(join(frame_parts, 'Frame'), BIKE)

# ---------------- 车把 + 把套 + 铃铛
bars = []
for s in (1, -1):
    bars.append(tube('bar%d' % s,
                     [(0.498, 0, 0.965), (0.47, 0.09 * s, 0.985), (0.40, 0.19 * s, 0.985), (0.325, 0.265 * s, 0.955)],
                     [0.013, 0.012, 0.012, 0.011], PAL['rim'], res=5))
    bars.append(cyl('grip%d' % s, 0.019, 0.105, (0.315, 0.278 * s, 0.95), PAL['grip'],
                    rot=(R(90), R(s * 20), 0), verts=14, subdiv=1))
bars.append(cyl('stem_top', 0.017, 0.10, (0.497, 0, 0.945), PAL['rim'], rot=(0, R(-8), 0), verts=12))
parent_to(join(bars, 'Bars'), BIKE)
parent_to(sph('Bell', 0.024, (0.365, 0.255, 0.985), PAL['gold'], scale=(1, 1, 0.75), seg=20, rings=12, subdiv=0), BIKE)

# ---------------- 座垫 + 座管 + 水壶
parent_to(cyl('Seatpost', 0.016, 0.16, (-0.295, 0, 1.01), PAL['rim'], rot=(0, R(-6), 0), verts=12), BIKE)
saddle = sph('Saddle', 1.0, (-0.285, 0, 1.085), PAL['leather'], scale=(0.175, 0.115, 0.05), subdiv=2)
bm = bmesh.new(); bm.from_mesh(saddle.data)   # 单位球局部坐标
for v in bm.verts:
    t = (v.co.x + 1) / 2                       # 0=尾 1=鼻
    v.co.y *= (1 - 0.62 * t ** 1.4)            # 收窄座垫鼻
    v.co.z += 0.10 * (1 - t) ** 2              # 尾部上翘
bm.to_mesh(saddle.data); bm.free(); saddle.data.update()
parent_to(saddle, BIKE)
parent_to(cyl('Bottle', 0.033, 0.17, (-0.245, 0.062, 0.80), PAL['bottleM'], rot=(0, R(6), 0), verts=16, subdiv=1), BIKE)
parent_to(cyl('BottleCap', 0.017, 0.03, (-0.251, 0.062, 0.90), PAL['fender'], rot=(0, R(6), 0), verts=12), BIKE)

# ---------------- 曲柄 + 牙盘 + 脚踏
Crank = empty('Crank', BB, BIKE)
PedalL = empty('PedalL', (0, 0.105, BB[2] - CRANK_R), Crank)   # 初始：左下右上
PedalR = empty('PedalR', (0, -0.105, BB[2] + CRANK_R), Crank)

ring = [
    tor('chainring', 0.082, 0.006, (0, 0.058, BB[2]), PAL['gold'], rot=(R(90), 0, 0), seg=40, sides=6),
    cyl('ring_plate', 0.068, 0.005, (0, 0.058, BB[2]), PAL['chain'], rot=(R(90), 0, 0), verts=28),
    cyl('bb_axle', 0.014, 0.20, (0, 0, BB[2]), PAL['rim'], rot=(R(90), 0, 0), verts=12),
    cube('crankArmL', (0.024, 0.02, CRANK_R + 0.02), (0.0, 0.08, BB[2] - CRANK_R / 2), PAL['chain'], subdiv=1),
    cube('crankArmR', (0.024, 0.02, CRANK_R + 0.02), (0.0, -0.08, BB[2] + CRANK_R / 2), PAL['chain'], subdiv=1),
]
teeth = []
for i in range(26):
    a = i * math.tau / 26
    teeth.append(cyl('rt%d' % i, 0.005, 0.014,
                     (0.088 * math.cos(a), 0.058, BB[2] + 0.088 * math.sin(a)),
                     PAL['gold'], rot=(R(90), a, 0), verts=4))
ring.append(join(teeth, 'ring_teeth'))
parent_to(join(ring, 'CrankGeo'), Crank)

def pedal_geo(name, par, s):
    g = [
        cube('p_body', (0.095, 0.058, 0.018), (0, 0, 0.012), PAL['frame'], subdiv=1),
        cube('p_pad', (0.08, 0.05, 0.008), (0, 0, 0.025), PAL['grip']),
        cyl('p_axle', 0.009, 0.045, (0, -0.022 * s, 0.008), PAL['rim'], rot=(R(90), 0, 0), verts=8),
    ]
    parent_to(join(g, name), par)

pedal_geo('PedalLGeo', PedalL, 1)
pedal_geo('PedalRGeo', PedalR, -1)

# ---------------- 链条（闭环：上边+后绕+下边+前绕）
cy = 0.058
chain_pts = (
    [(0.0, cy, BB[2] + 0.082), (-0.31, cy, 0.387), (-0.62, cy, 0.392)] +
    arc_pts(-0.62, BB[2] + 0.04, 0.052, R(90), R(270), 5, y=cy) +
    [(-0.31, cy, 0.253), (0.0, cy, BB[2] - 0.082)] +
    arc_pts(0.0, BB[2] + 0.04, 0.082, R(270), R(450), 5, y=cy)
)
parent_to(tube('Chain', chain_pts, 0.0065, PAL['chain'], res=4, cyclic=True, subdiv=0), BIKE)

# ---------------- 挡泥板
fend = [
    tube('fenderF', arc_pts(AXLE_F[0], WR, 0.395, R(15), R(165), 11), 0.026, PAL['fender'], res=4, yscale=2.0),
    tube('fenderR', arc_pts(AXLE_R[0], WR, 0.395, R(25), R(195), 13), 0.026, PAL['fender'], res=4, yscale=2.0),
]
parent_to(join(fend, 'Fenders'), BIKE)

# ---------------- 前车筐 + 鲜花
bx, bz = 0.60, 0.845
basket = [cyl('bk_floor', 0.115, 0.012, (bx, 0, bz - 0.055), PAL['wicker'], verts=20)]
for k in range(10):
    a = k * math.tau / 10
    basket.append(cyl('bk_v%d' % k, 0.0055, 0.135,
                      (bx + 0.118 * math.cos(a), 0.118 * math.sin(a), bz + 0.008), PAL['wicker'], verts=6))
for i, zz in enumerate((bz - 0.04, bz + 0.01, bz + 0.06)):
    basket.append(tor('bk_r%d' % i, 0.119, 0.0055, (bx, 0, zz), PAL['wicker'], rot=(R(90), 0, 0), seg=28, sides=6))
basket.append(cyl('bk_mount1', 0.008, 0.16, (0.545, 0.06, 0.79), PAL['rim'], rot=(0, R(35), 0), verts=8))
basket.append(cyl('bk_mount2', 0.008, 0.16, (0.545, -0.06, 0.79), PAL['rim'], rot=(0, R(35), 0), verts=8))
parent_to(join(basket, 'Basket'), BIKE)
flowers = []
for i, (fx, fy, fz, fm) in enumerate([(0.57, 0.05, 0.93, 'flowerR'), (0.61, -0.04, 0.95, 'flowerY'),
                                      (0.635, 0.03, 0.925, 'flowerP'), (0.585, -0.01, 0.955, 'flowerR')]):
    flowers.append(cyl('fl_st%d' % i, 0.004, fz - 0.86, (fx, fy, (fz + 0.86) / 2), PAL['stemG'], verts=6))
    flowers.append(sph('fl_h%d' % i, 0.026, (fx, fy, fz), PAL[fm], scale=(1, 1, 0.8), seg=14, rings=8, subdiv=0))
    flowers.append(sph('fl_c%d' % i, 0.011, (fx, fy, fz + 0.016), PAL['flowerY'], seg=10, rings=6, subdiv=0))
parent_to(join(flowers, 'BasketFlowers'), BIKE)

# ================================================================ 鹈鹕船长
HIP = (-0.10, 0, 1.02)
Rider = empty('Rider', HIP, BIKE)

# ---------------- 躯干 + 尾羽
TorsoP = empty('TorsoPivot', (HIP[0] + 0.02, 0, HIP[2] + 0.05), Rider)
torso = [
    sph('torso_main', 1.0, (-0.02, 0, 1.205), PAL['bodyW'], scale=(0.30, 0.185, 0.215), rot=(0, R(-12), 0), seg=36, rings=20, subdiv=2),
    sph('torso_chest', 1.0, (0.16, 0, 1.16), PAL['belly'], scale=(0.17, 0.145, 0.16), rot=(0, R(-12), 0), seg=28, rings=16, subdiv=2),
    sph('torso_rump', 1.0, (-0.22, 0, 1.17), PAL['bodyW'], scale=(0.15, 0.13, 0.14), seg=24, rings=14, subdiv=1),
]
tail = []
for i, (tx, tz, tw) in enumerate([(-0.33, 1.16, 0.10), (-0.375, 1.135, 0.085), (-0.415, 1.115, 0.062)]):
    tail.append(sph('tail%d' % i, 1.0, (tx, 0, tz),
                    PAL['featherG'] if i == 2 else PAL['bodyW'],
                    scale=(tw * 1.5, tw * 0.55, tw * 0.5), rot=(0, R(18), 0), seg=18, rings=10, subdiv=1))
torso.append(join(tail, 'tail_all'))
parent_to(join(torso, 'Torso'), TorsoP)

# ---------------- 脖子 + 头
Neck = empty('Neck', (0.085, 0, 1.285), Rider)
parent_to(tube('neck_tube',
               [(0.085, 0, 1.285), (0.155, 0, 1.40), (0.245, 0, 1.495), (0.325, 0, 1.545)],
               [0.082, 0.062, 0.052, 0.048], PAL['neckW'], res=6, subdiv=2), Neck)
Head = empty('Head', (0.325, 0, 1.545), Neck)
parent_to(sph('head_main', 1.0, (0.368, 0, 1.585), PAL['bodyW'], scale=(0.088, 0.064, 0.078), seg=28, rings=16, subdiv=2), Head)
parent_to(sph('head_crown', 1.0, (0.35, 0, 1.618), PAL['bodyW'], scale=(0.06, 0.055, 0.045), seg=20, rings=10, subdiv=1), Head)

# 眼睛（两侧鼓出的鸟眼）
for s in (1, -1):
    tag = 'L' if s > 0 else 'R'
    ex, ey, ez = 0.400, 0.058 * s, 1.618
    parent_to(tor('eyeRing' + tag, 0.021, 0.0055, (ex - 0.012, ey * 0.88, ez), PAL['iris'], rot=(R(90), 0, 0), seg=18, sides=6), Head)
    parent_to(sph('eye' + tag, 0.0155, (ex, ey, ez), PAL['eyeB'], seg=14, rings=10, subdiv=0), Head)
    parent_to(sph('eyeGlint' + tag, 0.0045, (ex + 0.007, ey * 1.15, ez + 0.009), PAL['eyeW'], seg=8, rings=6, subdiv=0), Head)

# 上喙（Beak 空物体 = 下颌铰链，honk 时上抬）
Beak = empty('Beak', (0.415, 0, 1.585), Head)
parent_to(tube('beak_upper',
               [(0.415, 0, 1.585), (0.56, 0, 1.582), (0.695, 0, 1.562), (0.788, 0, 1.528)],
               [0.040, 0.032, 0.020, 0.011], PAL['beakY'], res=6, yscale=0.72, subdiv=1), Beak)
parent_to(cyl('beak_hook', 0.008, 0.024, (0.780, 0, 1.522), PAL['beakTip'], rot=(R(16), 0, 0), verts=10), Beak)

# 喉囊（Pouch 空物体 = 下巴铰链；honk 膨胀 + 常态弹簧抖动）
Pouch = empty('Pouch', (0.408, 0, 1.545), Head)
pouch_m = sph('pouch_main', 1.0, (0.555, 0, 1.468), PAL['pouch'], scale=(0.150, 0.052, 0.078), rot=(0, R(8), 0), seg=28, rings=16, subdiv=2)
bm = bmesh.new(); bm.from_mesh(pouch_m.data)   # 单位球局部坐标
for v in bm.verts:
    t = (v.co.x + 1) / 2                       # 0=靠下巴 1=喙尖方向
    v.co.y *= (1 - 0.5 * t ** 1.6)             # 向喙尖收窄
    v.co.z -= 0.12 * t * (1 - t) * 2           # 中段下坠
bm.to_mesh(pouch_m.data); bm.free(); pouch_m.data.update()
parent_to(pouch_m, Pouch)
parent_to(sph('pouch_throat', 1.0, (0.440, 0, 1.518), PAL['pouch'], scale=(0.050, 0.042, 0.042), seg=16, rings=10, subdiv=1), Pouch)

# ---------------- 船长帽
hat = [
    cyl('hat_crown', 0.060, 0.040, (0.335, 0, 1.668), PAL['hatW'], rot=(R(6), R(-8), 0), verts=24, subdiv=1),
    cyl('hat_band', 0.0625, 0.014, (0.340, 0, 1.648), PAL['hatN'], rot=(R(6), R(-8), 0), verts=24),
    cyl('hat_brim', 0.088, 0.008, (0.356, 0, 1.640), PAL['hatN'], rot=(R(8), R(-8), 0), verts=28, subdiv=1),
    cube('hat_badge', (0.016, 0.006, 0.020), (0.382, 0, 1.654), PAL['gold']),
    sph('hat_top', 0.018, (0.330, 0, 1.690), PAL['hatW'], scale=(1.4, 1.4, 0.5), seg=12, rings=8, subdiv=0),
]
parent_to(join(hat, 'Hat'), Head)

# ---------------- 翅膀（半收拢；WingL/R 绕 X 轴扇动）
def build_wing(side):
    s = 1 if side == 'L' else -1
    yb = 0.155 * s
    g = [
        sph('w_arm', 1.0, (0.0, yb, 1.28), PAL['bodyW'], scale=(0.10, 0.055, 0.085),
            rot=(R(8 * s), 0, R(28 * s)), seg=22, rings=12, subdiv=1),
        sph('w_fore', 1.0, (-0.145, yb * 1.08, 1.185), PAL['bodyW'], scale=(0.115, 0.042, 0.070),
            rot=(R(6 * s), 0, R(52 * s)), seg=22, rings=12, subdiv=1),
        sph('w_cov', 1.0, (-0.06, yb * 1.02, 1.235), PAL['belly'], scale=(0.09, 0.05, 0.062),
            rot=(0, 0, R(40 * s)), seg=18, rings=10, subdiv=1),
    ]
    for i in range(4):
        t = i / 3.0
        # 初级飞羽：贴体收拢、向下垂，别伸成灰板
        g.append(sph('w_pri%d' % i, 1.0,
                     (-0.185 - 0.055 * t, yb * (1.0 + 0.05 * t) + 0.010 * s * (i - 1.5), 1.10 - 0.075 * t + 0.010 * i),
                     PAL['featherG'] if i >= 2 else PAL['bodyW'],
                     scale=(0.070 + 0.015 * t, 0.020, 0.034), rot=(R(10 * s), R(10 * s), R(64 * s)),
                     seg=14, rings=8, subdiv=1))
    return join(g, 'WingGeo' + side)

WingL = empty('WingL', (0.02, 0.145, 1.30), Rider)
WingR = empty('WingR', (0.02, -0.145, 1.30), Rider)
parent_to(build_wing('L'), WingL)
parent_to(build_wing('R'), WingR)

# ---------------- 腿（两骨 IK：Thigh -> Shin -> Foot）
THIGH_LEN = 0.42
SHIN_LEN = 0.46

def build_leg(side):
    s = 1 if side == 'L' else -1
    yb = 0.09 * s
    Thigh = empty('Thigh' + side, (HIP[0], yb, HIP[2]), Rider)
    parent_to(join([
        cyl('thigh', 0.034, THIGH_LEN * 0.92, (HIP[0] + 0.005, yb, HIP[2] - THIGH_LEN / 2),
            PAL['bodyW'], verts=16, r2=0.055, subdiv=2),
        sph('thigh_top', 0.058, (HIP[0] + 0.005, yb, HIP[2] - 0.02), PAL['bodyW'], scale=(1, 0.9, 1), seg=16, rings=10, subdiv=1),
    ], 'ThighGeo' + side), Thigh)
    knee = (HIP[0] + 0.01, yb, HIP[2] - THIGH_LEN)
    Shin = empty('Shin' + side, knee, Thigh)
    parent_to(join([
        sph('knee', 0.036, knee, PAL['legO'], scale=(1, 0.85, 1), seg=14, rings=8, subdiv=1),
        cyl('tarsus', 0.016, SHIN_LEN * 0.96, (knee[0] + 0.005, yb, knee[2] - SHIN_LEN / 2),
            PAL['legO'], verts=14, r2=0.022, subdiv=1),
    ], 'ShinGeo' + side), Shin)
    ankle = (knee[0] + 0.01, yb, knee[2] - SHIN_LEN)
    Foot = empty('Foot' + side, ankle, Shin)
    footm = sph('foot', 1.0, (ankle[0] + 0.055, yb, ankle[2] - 0.012), PAL['legO'],
                scale=(0.085, 0.052, 0.012), seg=18, rings=10, subdiv=1)
    bm = bmesh.new(); bm.from_mesh(footm.data)  # 单位球局部坐标
    for v in bm.verts:
        t = (v.co.x + 1) / 2
        v.co.y *= (1 - 0.35 * t)                # 脚尖收窄
    bm.to_mesh(footm.data); bm.free(); footm.data.update()
    fg = [footm]
    for i, ty in enumerate([-0.03, 0.0, 0.03]):
        fg.append(cyl('toe%d' % i, 0.009, 0.05, (ankle[0] + 0.148, yb + ty * 0.85, ankle[2] - 0.017),
                      PAL['legO'], rot=(0, R(88), 0), verts=8))
    parent_to(join(fg, 'FootGeo' + side), Foot)

build_leg('L')
build_leg('R')

# ---------------- 围巾（7 节链条：Scarf0..6，JS 弹簧飘动）
Scarf0 = empty('Scarf0', (0.175, 0, 1.415), Rider)
parent_to(tor('ScarfRing', 0.060, 0.026, (0.19, 0, 1.425), PAL['scarfR'],
              rot=(0, R(40), 0), seg=26, sides=10), Scarf0)
prev = Scarf0
for i in range(1, 7):
    # 围巾链是局部偏移（相对上一节），不是世界坐标
    e = bpy.data.objects.new('Scarf%d' % i, None)
    e.empty_display_type = 'PLAIN_AXES'
    e.empty_display_size = 0.04
    bpy.context.collection.objects.link(e)
    _reg(e)
    e.parent = prev
    e.matrix_parent_inverse = Matrix.Identity(4)
    e.location = (-0.050, 0, -0.020) if i == 1 else (-0.060, 0, -0.010)
    parent_to(cube('ScarfSeg%d' % i, (0.068, 0.052 - 0.004 * i, 0.016),
                   (-0.034, 0, -0.010), PAL['scarfR'] if i % 2 else PAL['scarfW'], subdiv=1), e)
    if i == 6:
        parent_to(sph('ScarfKnot', 0.028, (-0.075, 0, -0.018), PAL['scarfR'],
                      scale=(1, 0.8, 1), seg=12, rings=8, subdiv=1), e)
    prev = e

# 兜底：所有还没父亲的对象挂到 BikeRoot
for o in ALL:
    if o.parent is None and o is not BIKE:
        parent_to(o, BIKE)

bpy.context.view_layer.update()
for nm in ('Frame', 'head_main', 'Torso', 'Basket', 'WheelF', 'ThighL', 'FootL', 'Scarf0', 'beak_upper'):
    o = bpy.data.objects.get(nm)
    if o:
        print('WPOS', nm, tuple(round(v, 3) for v in o.matrix_world.translation))

# ================================================================ 预览渲染
def setup_scene():
    bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, 0))
    g = bpy.context.active_object
    g.name = 'prev_ground'
    _mat_assign(g, mat('prev_sand', 0xF0E0C0, 0.9))
    w = bpy.data.worlds.new('prev_world')
    bpy.context.scene.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes.get('Background')
    bg.inputs[0].default_value = lin(0xBFE4F5)
    bg.inputs[1].default_value = 1.0
    sd = bpy.data.lights.new('prev_sun', 'SUN')
    sd.energy = 3.2
    sd.angle = R(18)
    so = bpy.data.objects.new('prev_sun', sd)
    bpy.context.collection.objects.link(so)
    so.rotation_euler = (R(48), R(12), R(35))
    ad = bpy.data.lights.new('prev_fill', 'AREA')
    ad.energy = 150
    ad.size = 6
    ao = bpy.data.objects.new('prev_fill', ad)
    bpy.context.collection.objects.link(ao)
    ao.location = (-3.2, -2.6, 2.8)
    ao.rotation_euler = (R(52), 0, R(-40))
    scn = bpy.context.scene
    try:
        scn.render.engine = 'BLENDER_EEVEE_NEXT'
    except TypeError:
        scn.render.engine = 'BLENDER_EEVEE'
    scn.render.resolution_x = 1500
    scn.render.resolution_y = 950
    if hasattr(scn, 'eevee'):
        if hasattr(scn.eevee, 'taa_render_samples'):
            scn.eevee.taa_render_samples = 48
        if hasattr(scn.eevee, 'use_gtao'):
            scn.eevee.use_gtao = True
    return scn

def render(cam_loc, target, fname, lens=62):
    scn = bpy.context.scene
    cam_d = bpy.data.cameras.new('prev_cam')
    cam_d.lens = lens
    cam_o = bpy.data.objects.new('prev_cam', cam_d)
    bpy.context.collection.objects.link(cam_o)
    cam_o.location = cam_loc
    te = bpy.data.objects.new('prev_target', None)
    bpy.context.collection.objects.link(te)
    te.location = target
    c = cam_o.constraints.new('TRACK_TO')
    c.target = te
    c.track_axis = 'TRACK_NEGATIVE_Z'
    c.up_axis = 'UP_Y'
    scn.camera = cam_o
    scn.render.filepath = os.path.join(ROOT, 'assets', fname)
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam_o, do_unlink=True)
    bpy.data.objects.remove(te, do_unlink=True)

setup_scene()
render((3.6, -3.4, 2.3), (0, 0, 0.95), 'prev_rig_wide.png', lens=40)
render((2.55, -2.35, 1.95), (0.05, 0, 0.95), 'prev_rig_hero.png')
render((1.55, -0.75, 1.90), (0.44, 0, 1.52), 'prev_rig_face.png', lens=85)
render((0.05, -3.30, 1.25), (0.0, 0, 0.90), 'prev_rig_side.png')
render((-2.30, -2.10, 1.60), (0.0, 0, 1.00), 'prev_rig_back.png')

# ================================================================ 导出 GLB
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
print('OBJECTS:', len(ALL))
