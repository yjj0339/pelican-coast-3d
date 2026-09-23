// smoke.js —— 无头冒烟：桌面四视角 + 手机宽度截图 + console 零报错检查
// 用法：node tools/smoke.js [url]   默认 http://localhost:5193/
const path = require('path');
const fs = require('fs');
const puppeteer = require('puppeteer-core');

function findEdge() {
  for (const p of [
    'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
    'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
  ]) if (fs.existsSync(p)) return p;
  return null;
}

const URL0 = process.argv[2] || 'http://localhost:5193/';
const OUT = path.join(__dirname, '..', 'shots');
fs.mkdirSync(OUT, { recursive: true });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

(async () => {
  const browser = await puppeteer.launch({
    executablePath: findEdge(),
    headless: 'new',
    args: ['--no-sandbox', '--use-gl=angle', '--enable-unsafe-swiftshader', '--mute-audio', '--window-size=1280,720'],
  });
  const errors = [];
  const hook = (page, tag) => {
    page.on('pageerror', (e) => errors.push(`[${tag} pageerror] ` + e.message));
    page.on('console', (m) => { if (m.type() === 'error') errors.push(`[${tag} console] ` + m.text()); });
  };

  // ---- 桌面
  const page = await browser.newPage();
  hook(page, 'desktop');
  await page.setViewport({ width: 1280, height: 720 });
  await page.goto(URL0, { waitUntil: 'networkidle2', timeout: 90000 });
  await page.waitForFunction('window.__shotReady === true', { timeout: 180000 });
  await sleep(2500);
  await page.screenshot({ path: path.join(OUT, 'd1-chase.png') });
  for (const [i, name] of [[1, 'd2-side'], [2, 'd3-front'], [3, 'd4-free']]) {
    await page.evaluate((m) => window.__game.setCam(m), i);
    await sleep(1400);
    await page.screenshot({ path: path.join(OUT, name + '.png') });
  }
  await page.evaluate(() => { window.__game.setCam(0); window.__game.honk(); });
  await sleep(500);
  await page.screenshot({ path: path.join(OUT, 'd5-honk.png') });
  await page.evaluate(() => window.__game.hop());
  await sleep(450);
  await page.screenshot({ path: path.join(OUT, 'd6-hop.png') });

  // ---- 手机宽度
  const mp = await browser.newPage();
  hook(mp, 'mobile');
  await mp.setViewport({ width: 390, height: 844, isMobile: true, hasTouch: true, deviceScaleFactor: 2 });
  await mp.goto(URL0, { waitUntil: 'networkidle2', timeout: 90000 });
  await mp.waitForFunction('window.__shotReady === true', { timeout: 180000 });
  await sleep(2500);
  await mp.screenshot({ path: path.join(OUT, 'm1-chase.png') });
  await mp.evaluate(() => window.__game.setCam(1));
  await sleep(1400);
  await mp.screenshot({ path: path.join(OUT, 'm2-side.png') });

  await browser.close();
  console.log(errors.length ? 'ERRORS:\n' + errors.join('\n') : 'CONSOLE CLEAN');
  process.exit(errors.length ? 1 : 0);
})().catch((e) => { console.error('SMOKE FAIL', e); process.exit(2); });
