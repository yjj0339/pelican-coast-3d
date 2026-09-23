// rig.js —— 鹈鹕+自行车的逐帧姿态：蹬踏两骨 IK、轮/曲柄滚动、围巾弹簧、喉囊物理、扇翅、跳跃
import * as THREE from '../vendor/three.module.js';

export const RIG = {
  WHEEL_R: 0.34,
  CRANK_R: 0.15,
  CHAINRING_R: 0.082,
  COG_R: 0.052,
  THIGH: 0.42,
  SHIN: 0.46,
  HIP: { x: -0.10, y: 1.02, z: 0.09 },   // 髋关节（rig 局部，y=上）
  BB: { x: 0.0, y: 0.30 },               // 中轴（侧平面 x,y=上）
};

export function collectRig(root) {
  const g = (n) => root.getObjectByName(n);
  // 围巾链整体抬到背线之上（rest 姿态埋在身子里）
  const s0 = g('Scarf0');
  if (s0) {
    s0.position.y += 0.05;
    for (let i = 1; i <= 6; i++) {
      const s = g('Scarf' + i);
      if (s) { s.position.y += 0.022; s.scale.setScalar(1.5); }   // 放大到看得见的飘带
    }
  }
  return {
    root,
    wheelF: g('WheelF'), wheelR: g('WheelR'),
    crank: g('Crank'), pedalL: g('PedalL'), pedalR: g('PedalR'),
    rider: g('Rider'), torso: g('TorsoPivot'),
    neck: g('Neck'), head: g('Head'), beak: g('Beak'), pouch: g('Pouch'),
    wingL: g('WingL'), wingR: g('WingR'),
    thighL: g('ThighL'), shinL: g('ShinL'), footL: g('FootL'),
    thighR: g('ThighR'), shinR: g('ShinR'), footR: g('FootR'),
    scarf: [0, 1, 2, 3, 4, 5, 6].map((i) => g('Scarf' + i)),
  };
}

// 两骨 IK：髋 H、足 F（侧平面 x 前 / y 上），膝朝前
function ik2(H, F, a, b) {
  const dx = F.x - H.x, dy = F.y - H.y;
  let d = Math.hypot(dx, dy);
  d = Math.min(Math.max(d, Math.abs(a - b) + 0.01), a + b - 0.01);
  const base = Math.atan2(dy, dx);
  const cosA = (a * a + d * d - b * b) / (2 * a * d);
  const A = Math.acos(Math.min(1, Math.max(-1, cosA)));
  const dir = base + A;                       // 大腿方向角（膝朝 +x 前）
  const K = { x: H.x + a * Math.cos(dir), y: H.y + a * Math.sin(dir) };
  const dirS = Math.atan2(F.y - K.y, F.x - K.x);
  return { dir, dirS };
}

export function createRigState() {
  return {
    dist: 0,
    speed: 4.5,            // m/s
    crank: 0,
    hopY: 0, hopV: 0, hopping: false,
    squash: 0,
    pouchRot: 0, pouchV: 0, pouchScale: 1, pouchScaleV: 0,
    honkT: 0,
    flapT: 99,             // 扇翅计时（>1 静止）
    scarfV: new Array(7).fill(0), scarfA: new Array(7).fill(0),
    scarfVY: new Array(7).fill(0), scarfAY: new Array(7).fill(0),
    steer: 0, steerV: 0, lean: 0,
    bob: 0,
  };
}

export function honk(st) { st.honkT = 0.55; st.flapT = 0; }
export function hop(st) {
  if (st.hopping) return false;
  st.hopping = true; st.hopV = 3.1; st.flapT = 0;
  return true;
}

const _v = new THREE.Vector3();

export function poseRig(R, st, dt, t) {
  const { WHEEL_R, CRANK_R, CHAINRING_R, COG_R, THIGH, SHIN, HIP, BB } = RIG;

  // 里程与曲柄
  st.dist += st.speed * dt;
  const wheelRot = st.dist / WHEEL_R;
  st.crank = wheelRot * (COG_R / CHAINRING_R);

  R.wheelF.rotation.z = -wheelRot;
  R.wheelR.rotation.z = -wheelRot;
  R.crank.rotation.z = -st.crank;
  R.pedalL.rotation.z = st.crank;      // 反向保持脚踏水平
  R.pedalR.rotation.z = st.crank;

  // 跳跃物理
  if (st.hopping) {
    st.hopV -= 9.8 * dt;
    st.hopY += st.hopV * dt;
    if (st.hopY <= 0) { st.hopY = 0; st.hopV = 0; st.hopping = false; st.squash = 1; }
  }
  st.squash = Math.max(0, st.squash - dt * 4);
  const sq = st.squash * 0.12;
  R.root.position.y = st.hopY;
  R.root.scale.set(1 + sq * 0.6, 1 - sq, 1 + sq * 0.6);

  // 蹬踏 IK（左右脚踏相差半圈）
  const cad = st.crank;
  for (const [side, Thigh, Shin, Foot, ph] of [
    ['L', R.thighL, R.shinL, R.footL, Math.PI],
    ['R', R.thighR, R.shinR, R.footR, 0],
  ]) {
    const s = side === 'L' ? 1 : -1;
    const a = cad + ph;
    // 脚踏销在侧平面（x 前, y 上）的位置：初始 L 在下死点
    const px = BB.x + CRANK_R * Math.sin(a) * (s === 1 ? -1 : 1) * -1;
    const py = BB.y - CRANK_R * Math.cos(a) * (s === 1 ? -1 : 1) * -1;
    // 上面等价于：L 相位 π → 初始 (0, BB.y - CRANK_R*(-1)) = 上? 统一用旋转公式：
    const c0 = s === 1 ? { x: 0, y: -CRANK_R } : { x: 0, y: CRANK_R };
    const th = -cad;   // 曲柄绕 Z 旋转 -cad
    const cx = c0.x * Math.cos(th) - c0.y * Math.sin(th);
    const cy = c0.x * Math.sin(th) + c0.y * Math.cos(th);
    const F = { x: BB.x + cx, y: BB.y + cy + 0.045 };   // 踝关节目标=脚踏面+鞋底厚
    const H = { x: HIP.x, y: HIP.y + st.hopY * 0.0 };
    const { dir, dirS } = ik2(H, F, THIGH, SHIN);
    Thigh.rotation.z = dir + Math.PI / 2;
    Shin.rotation.z = dirS - dir;
    Foot.rotation.z = -dirS + 0.12;
    void px; void py; void a;
  }

  // 身体：踩踏起伏 + 落地压缩
  const cadence = Math.sin(st.crank * 2) * 0.5 + Math.sin(st.crank * 2 + Math.PI) * 0.5;
  st.bob = cadence * 0.012 * Math.min(1, st.speed / 4);
  R.torso.rotation.z = Math.sin(t * 1.7) * 0.015 + st.bob;
  R.torso.position.y = 0.05 + st.bob * 0.6;

  // 脖子/头：基础昂首姿态（鹈鹕的 S 颈）+ 缓慢环顾 + 颠簸
  R.neck.rotation.z = 0.20 + Math.sin(t * 1.3) * 0.045 + st.bob * 1.4;
  R.head.rotation.z = -0.14 - Math.sin(t * 1.3) * 0.03 - st.bob * 1.2;
  R.head.rotation.y = Math.sin(t * 0.47) * 0.22;

  // 打招呼：喙张 + 喉囊膨胀
  st.honkT = Math.max(0, st.honkT - dt);
  const hk = st.honkT > 0 ? Math.sin(Math.min(1, (0.55 - st.honkT) / 0.55) * Math.PI) : 0;
  R.beak.rotation.z = hk * 0.30;
  const pTarget = 1 + hk * 0.42;
  st.pouchScaleV += ((pTarget - st.pouchScale) * 60 - st.pouchScaleV * 9) * dt;
  st.pouchScale += st.pouchScaleV * dt;
  R.pouch.scale.setScalar(st.pouchScale);
  // 喉囊颠簸弹簧（绕侧轴晃）
  const bump = (Math.sin(st.crank * 2) * 0.5 + Math.sin(t * 3.1) * 0.5) * st.speed * 0.006;
  st.pouchV += ((bump - st.pouchRot) * 46 - st.pouchV * 6.5) * dt;
  st.pouchRot += st.pouchV * dt;
  R.pouch.rotation.z = st.pouchRot;

  // 翅膀：静止微张 + 扇翅/跳跃时大扇
  st.flapT += dt;
  const flapping = st.flapT < 0.9;
  const flapA = flapping ? Math.sin(st.flapT * 16) * Math.exp(-st.flapT * 2.4) * 0.85 : 0;
  const idle = Math.sin(t * 2.2) * 0.045 + st.speed * 0.012;
  const w = idle + flapA + (st.hopping ? 0.5 : 0);
  R.wingL.rotation.x = w;
  R.wingR.rotation.x = -w;

  // 围巾：逐节弹簧（竖摆 + 侧摆）。每节角度会沿链累积，幅度必须小，否则卷成蕨菜
  const lift = Math.min(0.09, st.speed * 0.012);
  for (let i = 1; i < 7; i++) {
    const tz = lift + Math.sin(t * 7 - i * 0.9) * 0.045 * (0.4 + st.speed * 0.06);
    const ty = Math.sin(t * 5.3 - i * 0.7) * 0.05 * (0.4 + st.speed * 0.05);
    st.scarfV[i] += ((tz - st.scarfA[i]) * 70 - st.scarfV[i] * 8) * dt;
    st.scarfA[i] += st.scarfV[i] * dt;
    st.scarfVY[i] += ((ty - st.scarfAY[i]) * 60 - st.scarfVY[i] * 7) * dt;
    st.scarfAY[i] += st.scarfVY[i] * dt;
    if (R.scarf[i]) {
      R.scarf[i].rotation.z = st.scarfA[i];
      R.scarf[i].rotation.y = st.scarfAY[i];
    }
  }

  // 转向侧倾
  st.lean += (st.steerV * 0.35 - st.lean) * Math.min(1, dt * 6);
  R.root.rotation.x = -st.lean;
  R.root.rotation.z = 0;
  R.root.position.z = st.steer;
  R.root.rotation.y = -st.steerV * 0.06;
  void _v;
}
