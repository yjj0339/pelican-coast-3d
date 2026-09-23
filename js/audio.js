// audio.js —— 全合成音效，无外部音频资源；首次手势后才启动（自动播放策略）
let ctx = null;
let master = null;
let ambientOn = false;

function ac() {
  if (!ctx) {
    ctx = new (window.AudioContext || window.webkitAudioContext)();
    master = ctx.createGain();
    master.gain.value = 0.9;
    master.connect(ctx.destination);
  }
  if (ctx.state === 'suspended') ctx.resume();
  return ctx;
}

function env(g, t0, a, peak, d) {
  g.gain.setValueAtTime(0.0001, t0);
  g.gain.linearRampToValueAtTime(peak, t0 + a);
  g.gain.exponentialRampToValueAtTime(0.0001, t0 + a + d);
}

// 车铃：叮-叮 两声 FM 铃音
export function bell() {
  const c = ac();
  for (let k = 0; k < 2; k++) {
    const t0 = c.currentTime + k * 0.16;
    const car = c.createOscillator();
    const mod = c.createOscillator();
    const mg = c.createGain();
    const g = c.createGain();
    car.frequency.value = 2093;
    mod.frequency.value = 3310;
    mg.gain.value = 420;
    mod.connect(mg); mg.connect(car.frequency);
    env(g, t0, 0.004, 0.32, 0.55);
    car.connect(g); g.connect(master);
    car.start(t0); mod.start(t0);
    car.stop(t0 + 0.7); mod.stop(t0 + 0.7);
  }
}

// 鹈鹕打招呼：低沉的“咕-啊”喉音
export function honk() {
  const c = ac();
  const t0 = c.currentTime;
  const o = c.createOscillator();
  const o2 = c.createOscillator();
  const f = c.createBiquadFilter();
  const g = c.createGain();
  o.type = 'sawtooth'; o2.type = 'square';
  o.frequency.setValueAtTime(196, t0);
  o.frequency.exponentialRampToValueAtTime(132, t0 + 0.34);
  o2.frequency.setValueAtTime(98, t0);
  o2.frequency.exponentialRampToValueAtTime(70, t0 + 0.34);
  f.type = 'lowpass'; f.frequency.value = 760; f.Q.value = 6;
  env(g, t0, 0.03, 0.5, 0.42);
  o.connect(f); o2.connect(f); f.connect(g); g.connect(master);
  o.start(t0); o2.start(t0);
  o.stop(t0 + 0.55); o2.stop(t0 + 0.55);
}

// 扇翅：带通噪声嗖声
export function flap() {
  const c = ac();
  const t0 = c.currentTime;
  const len = 0.28;
  const buf = c.createBuffer(1, c.sampleRate * len, c.sampleRate);
  const d = buf.getChannelData(0);
  for (let i = 0; i < d.length; i++) d[i = i | 0] = (Math.sin(i * 12.9898) * 43758.5453 % 1) * 2 - 1;
  const src = c.createBufferSource();
  src.buffer = buf;
  const f = c.createBiquadFilter();
  f.type = 'bandpass'; f.Q.value = 1.2;
  f.frequency.setValueAtTime(380, t0);
  f.frequency.exponentialRampToValueAtTime(950, t0 + len * 0.7);
  const g = c.createGain();
  env(g, t0, 0.02, 0.30, len);
  src.connect(f); f.connect(g); g.connect(master);
  src.start(t0);
}

// 起跳：上滑boing；落地：闷响
export function boing() {
  const c = ac();
  const t0 = c.currentTime;
  const o = c.createOscillator();
  const g = c.createGain();
  o.type = 'sine';
  o.frequency.setValueAtTime(240, t0);
  o.frequency.exponentialRampToValueAtTime(620, t0 + 0.14);
  env(g, t0, 0.01, 0.25, 0.18);
  o.connect(g); g.connect(master);
  o.start(t0); o.stop(t0 + 0.3);
}
export function thud() {
  const c = ac();
  const t0 = c.currentTime;
  const o = c.createOscillator();
  const g = c.createGain();
  o.type = 'sine';
  o.frequency.setValueAtTime(120, t0);
  o.frequency.exponentialRampToValueAtTime(52, t0 + 0.16);
  env(g, t0, 0.005, 0.4, 0.2);
  o.connect(g); g.connect(master);
  o.start(t0); o.stop(t0 + 0.3);
}

// 海浪+海风环境声：滤波噪声 + 慢 LFO
export function ambient() {
  if (ambientOn) return;
  ambientOn = true;
  const c = ac();
  const len = c.sampleRate * 4;
  const buf = c.createBuffer(1, len, c.sampleRate);
  const d = buf.getChannelData(0);
  let last = 0;
  for (let i = 0; i < len; i++) {
    const w = (Math.sin(i * 78.233) * 43758.5453) % 1;
    last = last * 0.97 + w * 0.03;
    d[i] = last * 8;
  }
  const src = c.createBufferSource();
  src.buffer = buf; src.loop = true;
  const f = c.createBiquadFilter();
  f.type = 'lowpass'; f.frequency.value = 620;
  const g = c.createGain(); g.gain.value = 0.0001;
  const lfo = c.createOscillator();
  const lg = c.createGain();
  lfo.frequency.value = 0.11; lg.gain.value = 0.05;
  lfo.connect(lg); lg.connect(g.gain);
  g.gain.setValueAtTime(0.09, c.currentTime);
  src.connect(f); f.connect(g); g.connect(master);
  src.start(); lfo.start();
  // 海风
  const wsrc = c.createBufferSource();
  wsrc.buffer = buf; wsrc.loop = true; wsrc.playbackRate.value = 1.7;
  const wf = c.createBiquadFilter();
  wf.type = 'bandpass'; wf.frequency.value = 1500; wf.Q.value = 0.4;
  const wg = c.createGain(); wg.gain.value = 0.018;
  wsrc.connect(wf); wf.connect(wg); wg.connect(master);
  wsrc.start();
}

export function unlock() { ac(); ambient(); }
