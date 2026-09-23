/**
 * vendor.js —— 把 three.js 官方构建产物复制进 vendor/，并把裸导入 'three' 改写成相对路径。
 * 不用 importmap（微信内置浏览器会白屏），所以 addons 里的 import 必须全部相对化。
 * 用法：node tools/vendor.js
 */
const fs = require('fs');
const path = require('path');

const SRC_ROOT = 'E:\\ZCODE\\node_modules\\three';
const DST_ROOT = path.resolve(__dirname, '..', 'vendor');

// [源相对路径, 目标相对路径]（全部是写死的白名单，无任何外部输入）
const FILES = [
  ['build/three.module.js', 'three.module.js'],
  ['examples/jsm/loaders/GLTFLoader.js', 'addons/GLTFLoader.js'],
  ['examples/jsm/objects/Sky.js', 'addons/Sky.js'],
  ['examples/jsm/postprocessing/EffectComposer.js', 'addons/EffectComposer.js'],
  ['examples/jsm/postprocessing/RenderPass.js', 'addons/RenderPass.js'],
  ['examples/jsm/postprocessing/ShaderPass.js', 'addons/ShaderPass.js'],
  ['examples/jsm/postprocessing/MaskPass.js', 'addons/MaskPass.js'],
  ['examples/jsm/postprocessing/Pass.js', 'addons/Pass.js'],
  ['examples/jsm/postprocessing/OutputPass.js', 'addons/OutputPass.js'],
  ['examples/jsm/postprocessing/UnrealBloomPass.js', 'addons/UnrealBloomPass.js'],
  ['examples/jsm/shaders/CopyShader.js', 'addons/CopyShader.js'],
  ['examples/jsm/utils/BufferGeometryUtils.js', 'addons/BufferGeometryUtils.js'],
  ['examples/jsm/shaders/LuminosityHighPassShader.js', 'addons/LuminosityHighPassShader.js'],
  ['examples/jsm/shaders/OutputShader.js', 'addons/OutputShader.js'],
];

// 边界校验：任何解析后的路径都必须落在允许的根目录内
function safeJoin(root, rel) {
  const target = path.resolve(root, rel);
  if (target !== root && !target.startsWith(root + path.sep)) {
    throw new Error('路径越界，已拒绝: ' + rel);
  }
  return target;
}

// 改写规则：
//  from 'three'                        -> '../three.module.js'
//  from 'three/addons/xxx/Yyy.js'      -> './Yyy.js'（都在 addons/ 同层）
//  from '../shaders/CopyShader.js'     -> './CopyShader.js'
function rewrite(code, isAddon) {
  // 路径段禁止跨行/含引号，否则 ';\n\n/**' 会被吞进路径（踩过）
  code = code.replace(/from\s+'three'/g, "from '../three.module.js'");
  code = code.replace(/from\s+'three\/addons\/[^/'\n]+\/([^'\n]+)'/g, "from './$1'");
  if (isAddon) {
    code = code.replace(/from\s+'\.\.\/[^/'\n]+\/([^'\n]+)'/g, "from './$1'");
    // 子目录式相对导入：'./utils/X.js' / './shaders/X.js' -> './X.js'（全部平铺在 addons/）
    code = code.replace(/from\s+'\.\/(?:shaders|utils|objects|loaders|postprocessing|curves|maths|lines)\/([^'\n]+)'/g, "from './$1'");
  }
  return code;
}

fs.mkdirSync(safeJoin(DST_ROOT, 'addons'), { recursive: true });
for (const [rel, out] of FILES) {
  const srcFile = safeJoin(SRC_ROOT, rel);
  const dstFile = safeJoin(DST_ROOT, out);
  if (!fs.existsSync(srcFile)) { console.error('缺文件:', srcFile); process.exit(1); }
  let code = fs.readFileSync(srcFile, 'utf8');
  code = rewrite(code, out.startsWith('addons/'));
  fs.writeFileSync(dstFile, code);
  console.log('vendor <-', out, Math.round(code.length / 1024) + 'KB');
}
console.log('DONE');
