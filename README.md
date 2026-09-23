# 鹈鹕海岸骑行 · 3D

**线上地址：https://yjj0339.github.io/pelican-coast-3d/** （手机扫码见仓库内 `qr-live.png`）

一只戴船长帽的鹈鹕，骑一辆薄荷青巡游自行车，沿着阳光海岸一直骑下去。
全 3D：鹈鹕与自行车由 Blender 精细建模导出 GLB（带完整骨架：车轮/曲柄/脚踏/两骨腿 IK/翅膀/脖颈/喙/喉囊/七节围巾链），
世界由 three.js 实时渲染：Preetham 天空、Gerstner 海浪着色器、棕榈/沙滩小屋/救生塔/海鸥/跳鱼/螃蟹/帆船/云循环街区。

## 玩法
- 点按画面 = 打招呼（鹈鹕张喙、喉囊鼓胀、扇翅 + 合成音效）
- 双击 = 跳一下（落地压缩回弹）
- 拖拽 / 方向键 / A D = 转向侧倾；「视角」按钮循环 跟随/侧面/正面/自由轨道
- ➖ ➕ 调速；🔔 车铃；全部音效为 WebAudio 实时合成，无外部资源

## 本地运行
```bash
node tools/serve.js 5193     # 本地静态服务
node tools/smoke.js          # 无头冒烟：桌面四视角 + 手机宽度截图 + console 零报错
```

## 资产管线
```bash
blender --background --factory-startup --python tools/build_rig.py    # 鹈鹕+车 → assets/rig.glb + 预览渲染
blender --background --factory-startup --python tools/build_props.py  # 20 种场景道具 → assets/props.glb
node tools/vendor.js                                                  # three r170 平铺进 vendor/（免 importmap）
```

## 结构
- `index.html / style.css` —— 入口与明亮浅色 UI
- `js/main.js` —— 加载、相机、交互、渲染循环（桌面端 UnrealBloom 后期）
- `js/rig.js` —— 蹬踏两骨 IK、轮/曲柄联动、围巾弹簧、喉囊物理、扇翅与跳跃
- `js/world.js` —— 天空/太阳/海面着色器/道路/道具区块循环/海鸥/跳鱼/帆船/云
- `js/audio.js` —— WebAudio 合成：车铃、鸣叫、扇翅、起跳落地、海浪环境声
