// main.js —— 入口：加载 GLB、相机与交互、渲染循环、截图钩子
import * as THREE from '../vendor/three.module.js';
import { GLTFLoader } from '../vendor/addons/GLTFLoader.js';
import { EffectComposer } from '../vendor/addons/EffectComposer.js';
import { RenderPass } from '../vendor/addons/RenderPass.js';
import { UnrealBloomPass } from '../vendor/addons/UnrealBloomPass.js';
import { OutputPass } from '../vendor/addons/OutputPass.js';
import { buildWorld, buildChunks, buildActors, updateActors, LANE } from './world.js';
import { collectRig, createRigState, poseRig, honk as rigHonk, hop as rigHop } from './rig.js';
import * as SFX from './audio.js';

const $ = (id) => document.getElementById(id);
const params = new URLSearchParams(location.search);
const isTouch = matchMedia('(pointer: coarse)').matches;
const portrait = () => innerWidth / innerHeight < 0.8;

// ---------------------------------------------------------------- 渲染器
const canvas = $('stage');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.06;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(50, innerWidth / innerHeight, 0.1, 900);
camera.position.set(-3.1, 1.75, -2.3);

const W = buildWorld(scene, renderer);

// 后期：桌面端加轻微泛光（手机省性能）
let composer = null;
if (!isTouch) {
  composer = new EffectComposer(renderer);
  composer.addPass(new RenderPass(scene, camera));
  const bloom = new UnrealBloomPass(new THREE.Vector2(innerWidth, innerHeight), 0.22, 0.7, 0.92);
  composer.addPass(bloom);
  composer.addPass(new OutputPass());
}

// ---------------------------------------------------------------- 加载
const tips = ['正在给自行车打气…', '鹈鹕船长在戴帽子…', '往车筐里插鲜花…', '海鸥们集合中…', '海浪调音中…'];
let tipI = 0;
const tipTimer = setInterval(() => { tipI = (tipI + 1) % tips.length; $('load-tip').textContent = tips[tipI]; }, 900);

const loader = new GLTFLoader();
// 按字节显示进度（GLB 有几 MB，慢网上给用户看得见的百分比）
const bytes = {};
function progress(url, ev) {
  if (ev && ev.lengthComputable) bytes[url] = ev.loaded;
  const done = (bytes['assets/rig.glb'] || 0) + (bytes['assets/props.glb'] || 0);
  const total = 5900000;   // 两 GLB 合计约 5.9MB，未知总量时按此估算
  $('load-fill').style.width = Math.min(99, done / total * 100).toFixed(0) + '%';
}
function loadGLB(url) {
  return new Promise((res, rej) => loader.load(url, (g) => { progress(url, null); res(g); }, (ev) => progress(url, ev), rej));
}

const st = createRigState();
let R = null;
let chunks = null;
let actors = null;

Promise.all([loadGLB('assets/rig.glb'), loadGLB('assets/props.glb')]).then(([rigG, propG]) => {
  // 鹈鹕+车
  scene.add(rigG.scene);
  R = collectRig(rigG.scene);
  rigG.scene.traverse((n) => { if (n.isMesh) { n.castShadow = true; n.receiveShadow = true; } });

  // 道具原型表
  const protos = {};
  for (const child of propG.scene.children) protos[child.name] = child;
  propG.scene.removeFromParent();
  chunks = buildChunks(scene, protos);
  actors = buildActors(scene, protos);

  clearInterval(tipTimer);
  $('load-fill').style.width = '100%';
  setTimeout(() => {
    $('loading').classList.add('gone');
    setTimeout(() => { $('hint').classList.add('gone'); }, 7000);
  }, 350);
  window.__shotReady = true;
}).catch((e) => {
  $('load-tip').textContent = '加载失败：' + e.message;
  console.error(e);
});

// ---------------------------------------------------------------- 交互
const camNames = ['跟随', '侧面', '正面', '自由'];
let camMode = parseInt(params.get('cam') ?? '0', 10) || 0;
if (params.get('cam') === 'side') camMode = 1;
if (params.get('cam') === 'front') camMode = 2;
if (params.get('cam') === 'free') camMode = 3;
let orbit = { th: -2.2, ph: 1.15, r: 5.4 };

function setSpeed(v) {
  st.speed = Math.min(12, Math.max(1.5, v));
  $('speed-tag').textContent = Math.round(st.speed * 3.6) + ' km/h';
}
setSpeed(parseFloat(params.get('speed')) || 4.5);

$('btn-cam').onclick = () => { camMode = (camMode + 1) % 4; };
$('btn-slow').onclick = () => setSpeed(st.speed - 1);
$('btn-fast').onclick = () => setSpeed(st.speed + 1);
$('btn-bell').onclick = () => SFX.bell();
$('btn-hi').onclick = () => { SFX.honk(); SFX.flap(); rigHonk(st); };

let ptr = { down: false, x: 0, y: 0, t: 0, moved: 0, lastTap: 0 };
canvas.addEventListener('pointerdown', (e) => {
  SFX.unlock();
  ptr = { down: true, x: e.clientX, y: e.clientY, t: performance.now(), moved: 0, lastTap: ptr.lastTap };
});
addEventListener('pointermove', (e) => {
  if (!ptr.down) return;
  const dx = e.clientX - ptr.x, dy = e.clientY - ptr.y;
  ptr.moved += Math.abs(dx) + Math.abs(dy);
  if (camMode === 3) {
    orbit.th -= dx * 0.006;
    orbit.ph = Math.min(1.45, Math.max(0.25, orbit.ph - dy * 0.005));
  } else if (ptr.moved > 10) {
    st.steerT = Math.min(1.6, Math.max(-1.6, (st.steerT || 0) - dx * 0.012));
  }
  ptr.x = e.clientX; ptr.y = e.clientY;
});
addEventListener('pointerup', () => {
  if (!ptr.down) return;
  ptr.down = false;
  const dt = performance.now() - ptr.t;
  if (ptr.moved < 10 && dt < 400) {
    const now = performance.now();
    if (now - ptr.lastTap < 300) {
      if (rigHop(st)) SFX.boing();
      ptr.lastTap = 0;
    } else {
      ptr.lastTap = now;
      SFX.honk(); SFX.flap(); rigHonk(st);
    }
  }
});
addEventListener('keydown', (e) => {
  SFX.unlock();
  const k = e.key.toLowerCase();
  if (k === 'arrowleft' || k === 'a') st.keyL = true;
  if (k === 'arrowright' || k === 'd') st.keyR = true;
  if (k === 'arrowup' || k === 'w') setSpeed(st.speed + 0.5);
  if (k === 'arrowdown' || k === 's') setSpeed(st.speed - 0.5);
  if (k === ' ') { if (rigHop(st)) SFX.boing(); }
  if (k === 'h') { SFX.honk(); SFX.flap(); rigHonk(st); }
  if (k === 'b') SFX.bell();
  if (k === 'c') camMode = (camMode + 1) % 4;
  if (k >= '1' && k <= '4') camMode = +k - 1;
});
addEventListener('keyup', (e) => {
  const k = e.key.toLowerCase();
  if (k === 'arrowleft' || k === 'a') st.keyL = false;
  if (k === 'arrowright' || k === 'd') st.keyR = false;
});

// ---------------------------------------------------------------- 相机
const camPos = new THREE.Vector3().copy(camera.position);
const camLook = new THREE.Vector3(0.4, 1.05, 0);
function updateCamera(dt) {
  const back = portrait() ? 1.4 : 1.0;
  let p, l;
  if (camMode === 0) {
    p = new THREE.Vector3(-3.0 * back, 1.78, -2.05 * back + st.steer * 0.5);
    l = new THREE.Vector3(0.55, 1.02, st.steer * 0.75);
  } else if (camMode === 1) {
    p = new THREE.Vector3(-0.3, 1.12, -5.4 * back);
    l = new THREE.Vector3(0, 1.0, st.steer);
  } else if (camMode === 2) {
    p = new THREE.Vector3(3.7 * back, 1.32, -1.8);
    l = new THREE.Vector3(-0.25, 1.12, st.steer * 0.6);
  } else {
    p = new THREE.Vector3(
      Math.sin(orbit.th) * Math.sin(orbit.ph) * orbit.r,
      Math.cos(orbit.ph) * orbit.r + 0.9,
      Math.cos(orbit.th) * Math.sin(orbit.ph) * orbit.r);
    l = new THREE.Vector3(0, 1.0, 0);
  }
  const k = Math.min(1, dt * 3.2);
  camPos.lerp(p, k);
  camLook.lerp(l, k);
  camera.position.copy(camPos);
  camera.position.y += st.hopY * 0.25;
  camera.lookAt(camLook);
}

// ---------------------------------------------------------------- 主循环
const clock = new THREE.Clock();
let T = 0;
let hudT = 0;
let wasHopping = false;
const freezeAt = params.get('freeze') ? parseFloat(params.get('freeze')) : 0;
let frozen = false;

function frame() {
  requestAnimationFrame(frame);
  const dt = Math.min(0.05, clock.getDelta());
  if (frozen) return;
  T += dt;

  if (!R || !chunks || !actors) {   // GLB 未到：只渲染空景，载入页盖着
    updateCamera(dt);
    if (composer) composer.render(); else renderer.render(scene, camera);
    return;
  }

  // 键盘转向
  const keyIn = (st.keyR ? 1 : 0) - (st.keyL ? 1 : 0);
  if (keyIn) st.steerT = Math.min(1.6, Math.max(-1.6, (st.steerT || 0) + keyIn * dt * 3));
  else if (!ptr.down) st.steerT = (st.steerT || 0) * (1 - Math.min(1, dt * 1.5));
  const prevSteer = st.steer;
  st.steer += ((st.steerT || 0) - st.steer) * Math.min(1, dt * 4);
  st.steerV = (st.steer - prevSteer) / Math.max(dt, 1e-4);

  poseRig(R, st, dt, T);
  if (wasHopping && !st.hopping) SFX.thud();
  wasHopping = st.hopping;

  // 世界滚动
  for (const c of chunks.chunks) {
    c.position.x = c.userData.wx - st.dist;
    if (c.userData.wx - st.dist < -36) c.userData.wx += 240;
    for (const crab of (c.userData.crabs || [])) {
      crab.position.z = crab.userData.crab.z0 + Math.sin(T * 1.8 + crab.userData.crab.phase) * 0.45;
      crab.rotation.y += Math.sin(T * 3 + crab.userData.crab.phase) * dt * 0.6;
    }
  }
  W.roadTex.offset.x = st.dist / 8;
  W.seaMat.uniforms.uTime.value = T;
  updateActors(actors, st, T, dt);

  // 太阳阴影跟随
  W.sun.position.set(st.steer * 0.3, 0, st.steer).addScaledVector(W.sunDir, 30);
  W.sun.target.position.set(0, 0.6, st.steer);
  W.sun.target.updateMatrixWorld();

  updateCamera(dt);

  hudT += dt;
  if (hudT > 0.2) {
    hudT = 0;
    $('dash-dist').textContent = Math.round(st.dist);
    $('dash-speed').textContent = (st.speed * 3.6).toFixed(1);
  }

  if (composer) composer.render();
  else renderer.render(scene, camera);

  if (freezeAt && T >= freezeAt) frozen = true;
}
frame();

addEventListener('resize', () => {
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
  if (composer) composer.setSize(innerWidth, innerHeight);
});

// 截图/冒烟钩子
window.__game = {
  get state() { return st; },
  setCam(i) { camMode = i; },
  setSpeed(v) { setSpeed(v); },
  honk() { SFX.honk(); rigHonk(st); },
  hop() { rigHop(st); },
  get ready() { return !!window.__shotReady; },
  get t() { return T; },
};
void LANE;
