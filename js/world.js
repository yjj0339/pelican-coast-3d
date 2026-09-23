// world.js —— 明亮海滨世界：天空/太阳/海面着色器/道路/沙滩/草地 + 道具区块循环 + 海鸥/跳鱼/螃蟹
import * as THREE from '../vendor/three.module.js';
import { Sky } from '../vendor/addons/Sky.js';

export const LANE = { roadHalf: 2.3, sandFrom: 2.3, sandTo: 6.2, seaFrom: 6.2 };

// 稳定哈希（同一种子每次刷新景色一致）
export function rnd(n) {
  const s = Math.sin(n * 127.1 + 311.7) * 43758.5453;
  return s - Math.floor(s);
}

const SEA_VERT = /* glsl */`
uniform float uTime;
varying vec3 vWorld;
varying vec3 vNormalW;
varying float vCrest;
vec3 wave(vec3 p, vec2 dir, float amp, float freq, float speed, out vec3 n) {
  float ph = dot(p.xz, dir) * freq + uTime * speed;
  float s = sin(ph), c = cos(ph);
  n = vec3(-dir.x * amp * freq * c, 1.0, -dir.y * amp * freq * c);
  return vec3(0.0, s * amp, 0.0);
}
void main() {
  vec3 p = position;
  vec3 n1, n2, n3;
  vec3 w = wave(p, normalize(vec2(1.0, 0.25)), 0.075, 0.55, 1.6, n1);
  w += wave(p, normalize(vec2(0.6, 1.0)), 0.05, 0.9, 2.3, n2);
  w += wave(p, normalize(vec2(-0.3, 1.0)), 0.028, 1.7, 3.1, n3);
  p += w;
  vCrest = w.y;
  vNormalW = normalize(mat3(modelMatrix) * normalize(n1 + n2 + n3 - vec3(0.0, 1.0, 0.0)));
  vec4 wp = modelMatrix * vec4(p, 1.0);
  vWorld = wp.xyz;
  gl_Position = projectionMatrix * viewMatrix * wp;
}`;

const SEA_FRAG = /* glsl */`
uniform vec3 uSunDir;
uniform vec3 uDeep;
uniform vec3 uShallow;
uniform float uShoreZ;
uniform float uTime;
varying vec3 vWorld;
varying vec3 vNormalW;
varying float vCrest;
float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
void main() {
  vec3 N = normalize(vNormalW);
  vec3 V = normalize(cameraPosition - vWorld);
  float shore = smoothstep(uShoreZ + 7.0, uShoreZ + 0.5, vWorld.z);   // 靠岸渐浅
  vec3 col = mix(uDeep, uShallow, shore);
  // 阳光碎金
  vec3 H = normalize(uSunDir + V);
  float spec = pow(max(dot(N, H), 0.0), 240.0);
  col += vec3(1.0, 0.96, 0.85) * spec * 1.6;
  // 浪尖白沫（只留在近岸，远海否则像浮冰）+ 岸边泡沫带
  float near = smoothstep(uShoreZ + 14.0, uShoreZ + 2.0, vWorld.z);
  float foam = smoothstep(0.055, 0.095, vCrest) * near;
  float edge = smoothstep(uShoreZ + 1.6, uShoreZ + 0.2, vWorld.z)
             * (0.55 + 0.45 * sin(vWorld.x * 1.7 + uTime * 2.2));
  col = mix(col, vec3(0.97, 0.99, 0.98), clamp(foam * 0.75 + edge * 0.85, 0.0, 1.0));
  //  Fresnel 天空反光（掠射角别把海洗白）
  float fr = pow(1.0 - max(dot(N, V), 0.0), 3.0);
  col = mix(col, vec3(0.72, 0.88, 0.95), fr * 0.28);
  gl_FragColor = vec4(col, 0.96);
}`;

export function buildWorld(scene, renderer) {
  const W = {};

  // ---- 天空 + 太阳
  const sky = new Sky();
  sky.scale.setScalar(4000);
  scene.add(sky);
  const sunPos = new THREE.Vector3();
  const phi = THREE.MathUtils.degToRad(90 - 38);
  const theta = THREE.MathUtils.degToRad(140);
  sunPos.setFromSphericalCoords(1, phi, theta);
  sky.material.uniforms.sunPosition.value.copy(sunPos);
  sky.material.uniforms.turbidity.value = 3.4;
  sky.material.uniforms.rayleigh.value = 1.5;
  sky.material.uniforms.mieCoefficient.value = 0.004;
  sky.material.uniforms.mieDirectionalG.value = 0.85;
  W.sunDir = sunPos.clone().normalize();

  const sun = new THREE.DirectionalLight(0xFFF3DC, 2.5);
  sun.position.copy(sunPos).multiplyScalar(30);
  sun.castShadow = true;
  sun.shadow.mapSize.set(2048, 2048);
  const sc = sun.shadow.camera;
  sc.left = -9; sc.right = 9; sc.top = 9; sc.bottom = -9;
  sc.near = 5; sc.far = 80;
  sun.shadow.bias = -0.0004;
  sun.shadow.normalBias = 0.02;
  scene.add(sun);
  scene.add(sun.target);
  W.sun = sun;

  scene.add(new THREE.HemisphereLight(0xBFE4F5, 0xE8D9B8, 0.75));

  scene.fog = new THREE.Fog(0xCFE8F5, 70, 260);

  // ---- 海面
  const seaGeo = new THREE.PlaneGeometry(520, 220, 160, 80);
  seaGeo.rotateX(-Math.PI / 2);
  const seaMat = new THREE.ShaderMaterial({
    vertexShader: SEA_VERT,
    fragmentShader: SEA_FRAG,
    transparent: true,
    uniforms: {
      uTime: { value: 0 },
      uSunDir: { value: W.sunDir },
      uDeep: { value: new THREE.Color(0x0F86B0).convertSRGBToLinear() },
      uShallow: { value: new THREE.Color(0x55CCC2).convertSRGBToLinear() },
      uShoreZ: { value: LANE.seaFrom },
    },
  });
  const sea = new THREE.Mesh(seaGeo, seaMat);
  sea.position.set(0, -0.06, LANE.seaFrom + 110);
  scene.add(sea);
  W.sea = sea;
  W.seaMat = seaMat;

  // ---- 沙滩 / 草地 / 道路
  const sand = new THREE.Mesh(
    new THREE.PlaneGeometry(520, LANE.sandTo - LANE.sandFrom + 1.2).rotateX(-Math.PI / 2),
    new THREE.MeshStandardMaterial({ color: 0xF2E3C4, roughness: 1 }));
  sand.position.set(0, -0.02, (LANE.sandFrom + LANE.sandTo) / 2 - 0.4);
  sand.receiveShadow = true;
  scene.add(sand);

  const grass = new THREE.Mesh(
    new THREE.PlaneGeometry(520, 40).rotateX(-Math.PI / 2),
    new THREE.MeshStandardMaterial({ color: 0x93C46D, roughness: 1 }));
  grass.position.set(0, -0.015, -LANE.roadHalf - 20 + 0.4);
  grass.receiveShadow = true;
  scene.add(grass);

  // 道路贴图：浅色沥青 + 白边线 + 黄虚线
  const cv = document.createElement('canvas');
  cv.width = 256; cv.height = 256;
  const g2 = cv.getContext('2d');
  g2.fillStyle = '#B9BEC2'; g2.fillRect(0, 0, 256, 256);
  for (let i = 0; i < 260; i++) {   // 沥青颗粒
    g2.fillStyle = `rgba(${140 + rnd(i) * 60 | 0},${145 + rnd(i + 999) * 60 | 0},${150 + rnd(i + 555) * 60 | 0},0.35)`;
    g2.fillRect(rnd(i + 7) * 256, rnd(i + 13) * 256, 2, 2);
  }
  g2.fillStyle = '#F7F5EE'; g2.fillRect(0, 10, 256, 7); g2.fillRect(0, 239, 256, 7);
  g2.fillStyle = '#F5C64E';
  g2.fillRect(0, 122, 150, 12);
  const roadTex = new THREE.CanvasTexture(cv);
  roadTex.wrapS = roadTex.wrapT = THREE.RepeatWrapping;
  roadTex.repeat.set(520 / 8, 1);
  roadTex.colorSpace = THREE.SRGBColorSpace;
  roadTex.anisotropy = renderer.capabilities.getMaxAnisotropy();
  const road = new THREE.Mesh(
    new THREE.PlaneGeometry(520, LANE.roadHalf * 2).rotateX(-Math.PI / 2),
    new THREE.MeshStandardMaterial({ map: roadTex, roughness: 0.95 }));
  road.position.set(0, 0, 0);
  road.receiveShadow = true;
  scene.add(road);
  W.roadTex = roadTex;

  return W;
}

// ---------------------------------------------------------------- 道具区块
const CHUNK = 24;             // 每块长度(m)
const NCHUNK = 10;            // 循环区块数（240m 一轮回）

export function buildChunks(scene, protos) {
  const group = new THREE.Group();
  scene.add(group);
  const chunks = [];
  for (let i = 0; i < NCHUNK; i++) {
    const c = new THREE.Group();
    c.userData.wx = i * CHUNK;
    populateChunk(c, i, protos);
    group.add(c);
    chunks.push(c);
  }
  return { group, chunks };
}

function put(parent, proto, x, y, z, ry, s) {
  const o = proto.clone(true);
  o.position.set(x, y, z);
  o.rotation.y = ry;
  if (s !== 1) o.scale.setScalar(s);
  o.traverse((n) => { if (n.isMesh) { n.castShadow = true; n.receiveShadow = true; } });
  parent.add(o);
  return o;
}

function populateChunk(c, i, pr) {
  const r = (k) => rnd(i * 57.31 + k * 13.7);
  // 左侧草地：棕榈 / 路灯 / 长椅 / 小屋 / 花丛 / 灌木
  if (r(1) < 0.85) put(c, pr.Palm, 4 + r(2) * 12, 0, -4.2 - r(3) * 3.5, r(4) * 6.28, 0.85 + r(5) * 0.4);
  if (r(6) < 0.5) put(c, pr.PalmSmall, 6 + r(7) * 12, 0, -3.4 - r(8) * 2.5, r(9) * 6.28, 0.8 + r(10) * 0.4);
  put(c, pr.Lamp, 12, 0, -3.7, Math.PI / 2, 1);   // 别挡跟随相机（相机 z≈-2.9）
  if (r(11) < 0.45) put(c, pr.Bench, 6 + r(12) * 10, 0, -2.9, Math.PI / 2 + (r(13) - 0.5) * 0.3, 1);
  if (r(14) < 0.4) put(c, r(15) < 0.5 ? pr.Hut1 : pr.Hut2, 8 + r(16) * 10, 0, -9 - r(17) * 5, (r(18) - 0.5) * 0.5, 1);
  if (r(19) < 0.3) put(c, pr.Tower, 10 + r(20) * 8, 0, -8 - r(21) * 4, (r(22) - 0.5) * 0.6, 1);
  for (let k = 0; k < 3; k++) {
    if (r(30 + k) < 0.6) put(c, pr.Flowers, 2 + r(40 + k) * 18, 0, -2.8 - r(50 + k) * 4, r(60 + k) * 6.28, 0.8 + r(70 + k) * 0.6);
    if (r(80 + k) < 0.4) put(c, pr.Bush, 3 + r(90 + k) * 18, 0, -3.2 - r(100 + k) * 4, r(110 + k) * 6.28, 0.7 + r(120 + k) * 0.7);
  }
  if (r(23) < 0.35) put(c, pr.Sign, 18, 0, -3.4, Math.PI / 2, 1);
  // 右侧沙滩：遮阳伞 / 球 / 礁石 / 海星 / 贝壳 / 螃蟹
  if (r(24) < 0.5) put(c, pr.Umbrella, 5 + r(25) * 12, 0, 3.4 + r(26) * 2.0, r(27) * 6.28, 1);
  if (r(28) < 0.5) put(c, pr.Ball, 4 + r(29) * 14, 0, 3.1 + r(31) * 2.4, 0, 0.9 + r(32) * 0.4);
  for (let k = 0; k < 2; k++) {
    if (r(33 + k) < 0.6) put(c, r(43 + k) < 0.5 ? pr.Rock1 : pr.Rock2, 3 + r(53 + k) * 18, 0, 3.0 + r(63 + k) * 2.8, r(73 + k) * 6.28, 0.7 + r(83 + k) * 0.8);
    if (r(93 + k) < 0.55) put(c, r(103 + k) < 0.5 ? pr.Starfish : pr.Shell, 2 + r(113 + k) * 20, 0.01, 2.7 + r(123 + k) * 3.0, r(133 + k) * 6.28, 0.8 + r(143 + k) * 0.6);
  }
  if (r(25 + 100) < 0.5) {
    const crab = put(c, pr.Crab, 6 + r(26 + 100) * 12, 0, 2.9 + r(27 + 100) * 2.2, r(28 + 100) * 6.28, 0.9 + r(29 + 100) * 0.5);
    crab.userData.crab = { phase: r(30 + 100) * 6.28, z0: crab.position.z };
    c.userData.crabs = c.userData.crabs || [];
    c.userData.crabs.push(crab);
  }
}

// ---------------------------------------------------------------- 动态演员
export function buildActors(scene, protos) {
  const A = { gulls: [], fish: [], boats: [], clouds: [], island: null };
  for (let i = 0; i < 5; i++) {
    const g = protos.Gull.clone(true);
    g.traverse((n) => { if (n.isMesh) n.castShadow = true; });
    scene.add(g);
    A.gulls.push({ obj: g, ph: rnd(i + 1) * 6.28, rad: 6 + rnd(i + 2) * 7, h: 4.5 + rnd(i + 3) * 3.5, sp: 0.25 + rnd(i + 4) * 0.2 });
  }
  for (let i = 0; i < 3; i++) {
    const f = protos.Fish.clone(true);
    f.visible = false;
    scene.add(f);
    A.fish.push({ obj: f, t: rnd(i + 11) * 6, period: 5 + rnd(i + 12) * 4, x: 20 + rnd(i + 13) * 40, z: 8 + rnd(i + 14) * 6 });
  }
  for (let i = 0; i < 2; i++) {
    const b = protos.Sailboat.clone(true);
    scene.add(b);
    A.boats.push({ obj: b, x: 60 + i * 90, z: 26 + i * 22, ph: rnd(i + 21) * 6.28 });
  }
  for (let i = 0; i < 8; i++) {
    const cl = protos.Cloud.clone(true);
    cl.scale.setScalar(2.2 + rnd(i + 31) * 2.6);
    scene.add(cl);
    A.clouds.push({ obj: cl, x: -60 + i * 40 + rnd(i + 32) * 20, z: -40 + rnd(i + 33) * 120, h: 26 + rnd(i + 34) * 14 });
  }
  const isl = protos.Island.clone(true);
  isl.position.set(180, -0.4, 90);
  scene.add(isl);
  A.island = isl;
  return A;
}

export function updateActors(A, st, t, dt) {
  // 海鸥：绕骑手盘旋 + 扇翅
  for (const g of A.gulls) {
    g.ph += dt * g.sp;
    const x = Math.cos(g.ph) * g.rad + Math.sin(t * 0.21 + g.ph) * 3;
    const z = Math.sin(g.ph) * g.rad * 0.7 - 2;
    g.obj.position.set(x, g.h + Math.sin(t * 1.3 + g.ph * 2) * 0.5, z);
    g.obj.rotation.y = -g.ph + Math.PI / 2;
    const fl = Math.sin(t * 7 + g.ph * 3) * 0.55;
    const wl = g.obj.getObjectByName('Gull_WingL');
    const wr = g.obj.getObjectByName('Gull_WingR');
    if (wl) wl.rotation.x = fl;
    if (wr) wr.rotation.x = -fl;
  }
  // 跳鱼：周期抛物线跃出海面
  for (const f of A.fish) {
    f.t += dt;
    const u = (f.t % f.period) / 1.1;
    if (u < 1) {
      f.obj.visible = true;
      const fx = ((f.x - st.dist) % 240 + 240) % 240 - 30;   // 随世界循环，始终在视野带内
      f.obj.position.set(fx, 0.1 + Math.sin(u * Math.PI) * 0.85, f.z);
      f.obj.rotation.z = (u - 0.5) * 3.4;
      f.obj.rotation.y = 2.2;
    } else f.obj.visible = false;
  }
  // 帆船：远处漂 + 摇
  for (const b of A.boats) {
    const bx = ((b.x - st.dist * 0.35) % 240 + 240) % 240 - 40;
    b.obj.position.set(bx, 0.02 + Math.sin(t * 0.8 + b.ph) * 0.05, b.z);
    b.obj.rotation.z = Math.sin(t * 0.7 + b.ph) * 0.035;
    b.obj.rotation.x = Math.sin(t * 0.53 + b.ph) * 0.02;
    b.obj.rotation.y = -0.5 + Math.sin(t * 0.1 + b.ph) * 0.2;
  }
  // 云：慢飘 + 循环
  for (const c of A.clouds) {
    const cx = ((c.x - st.dist * 0.12 - t * 0.6) % 320 + 320) % 320 - 80;
    c.obj.position.set(cx, c.h, c.z);
  }
  // 岛：永远在地平线前方
  A.island.position.x = 190;
}
