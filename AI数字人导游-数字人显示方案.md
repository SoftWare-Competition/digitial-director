# AI 数字人导游 —— 数字人显示 + AI 智能问答方案

## 架构概览

```
小程序 (miniprogram)                         后端服务 (FastAPI :8000)
                                             部署域名: https://xinphotoshare.click
pages/digital-human/                         GET /live2d-viewer
+-----------------------+                   +---------------------------+
| <web-view              |      HTTPS       | index.html                |
|  src="https://xinphotoshare|----------------->|   PixiJS v7               |
|       /live2d-viewer/"  |                  |   Cubism 4 Core (WASM)    |
| />                     |                  |   pixi-live2d-display     |
+-----------------------+                   |   cubism4 plugin          |
                                            +---------------------------+
                                            Static files:
                                            /static/model/model.model3.json
                                            /static/model/model.bin (3.1MB)
                                            /static/model/texture/*.png
                                            /static/model/model.physics3.json
```

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 渲染引擎 | PixiJS v7 | 2D WebGL 渲染框架 |
| Live2D 核心 | Cubism 4 Core (live2dcubismcore.min.js) | 官方运行时,WebAssembly |
| Live2D 桥接 | pixi-live2d-display + cubism4 plugin | 将 Cubism 模型接入 PixiJS |
| 模型格式 | MOC3 (model.bin, 3.1MB) | Cubism 4 编译模型 |
| 纹理 | texture_00.png (16.4MB) | 模型贴图 |
| 物理模拟 | model.physics3.json (64KB) | 头发/衣物物理参数 |
| 显示信息 | model.cdi3.json (13KB) | Cubism Display Info |
| 容器 | 微信 web-view 组件 | 嵌入后端 HTML 页面 |

## 文件结构

```
lingshan-tour-guide/
|
├── backend/                          # 后端 (端口 8000)
│   └── app/main.py                   # FastAPI 入口
│       ├── mount /static/model → miniprogram/assets/live2d/model/
│       ├── mount /live2d-viewer/static → build/live2d-viewer/
│       └── GET /live2d-viewer → 返回 index.html
|
├── build/live2d-viewer/              # Live2D 网页资源(共约 853KB)
│   ├── index.html                    # 数字人展示页面(核心)
│   ├── pixi.min.js                   # PixiJS (456KB)
│   ├── live2dcubismcore.min.js       # Cubism 4 Core (150KB)
│   ├── cubism4.min.js                # Cubism 4 插件 (120KB)
│   └── index.min.js                  # pixi-live2d-display 主库 (127KB)
|
├── miniprogram/
│   ├── app.js                        # apiBase = https://xinphotoshare.click/api/v1
│   ├── pages/digital-human/
│   │   ├── digital-human.wxml        # <web-view src="https://xinphotoshare.click/live2d-viewer/">
│   │   ├── digital-human.js          # WebView 消息通信
│   │   ├── digital-human.json        # 页面配置
│   │   └── digital-human.wxss        # 样式
│   ├── assets/live2d/model/          # Live2D 模型文件
│   │   ├── model.model3.json         # 模型描述 (434B)
│   │   ├── model.bin                 # MOC3 编译模型 (3.1MB)
│   │   ├── model.cdi3.json           # 显示信息 (13KB)
│   │   ├── model.physics3.json       # 物理参数 (64KB)
│   │   ├── model.vtube.json          # VTube 配置 (13KB)
│   │   ├── texture/texture_00.png    # 贴图 (16.4MB)
│   │   ├── expressions/              # 表情(预留)
│   │   └── motions/                  # 动作(预留)
│   ├── components/digital-human-character/
│   │   └── renderers/
│   │       ├── canvas2d.js           # Canvas2D 程序化绘制(备用)
│   │       └── live2d.js             # Live2D WebGL 原生渲染器(备用)
│   └── lib/live2d/
│       └── live2dcubismcore.min.js   # Cubism 4 Core
|
└── 音-免费版/                         # 原始 MOC3 模型副本
    ├── *.moc3                         # 与 model.bin 内容相同 (3.1MB)
    ├── *.model3.json
    ├── *.physics3.json
    └── *.cdi3.json
```

## index.html 加载流程

### JS 加载顺序(必须严格按照此顺序!)

```
1. pixi.min.js              → 提供 PIXI 全局对象
2. live2dcubismcore.min.js  → 提供 Live2DCubismCore 全局对象
3. cubism4.min.js           → 注册 Cubism4Model 到 PIXI.live2d
4. index.min.js             → 提供 Live2DModel 到 PIXI.live2d
```

### 初始化步骤

```
1. 检查依赖 (PIXI / Live2DCubismCore / PIXI.live2d)
2. 创建 PIXI.Application (透明背景, 自适应窗口, devicePixelRatio)
3. PIXI.live2d.Live2DModel.from("/static/model/model.model3.json")
   +-- 解析 model3.json
       |-- Moc: model.bin        -> fetch ArrayBuffer -> Cubism Core 解析
       |-- Textures: texture/*   -> fetch PNG -> PIXI Texture
       |-- Physics: *.json       -> fetch JSON -> 物理模拟初始化
4. 模型添加到 stage, 自适应缩放居中 (scale * 0.85)
5. 启动渲染循环 (PIXI.Ticker, ~60fps)
```

### 加载状态提示

页面底部有状态文字,依次显示:
```
初始化中... -> PixiJS v7.x.x -> CubismCore OK -> pixi-live2d-display OK
-> 创建画布... -> 画布创建完成 -> 加载: /static/model/model.model3.json
-> 模型加载成功! -> 就绪 (1秒后自动消失)
```

---

## 动画系统

### 呼吸动画

```
breathPhase += 0.03 (每帧)
ParamBreath = (sin(breathPhase) + 1) / 2  → 0~1 正弦波
```

### 眨眼动画(状态机)

```
Phase 0: 等待 (3~6秒随机间隔)
Phase 1: 闭眼 (4帧, ParamEyeLOpen/ROpen 从 1 到 0)
Phase 2: 保持闭眼 (1帧)
Phase 3: 睁眼 (4帧, ParamEyeLOpen/ROpen 从 0 到 1)
```

### 口型同步

口型序列(8帧循环, 120ms/帧):
```
[1.0, 0.65, 0.35, 0.65, 1.0, 0.0, 0.35, 0.65]
  A     B     C     B     A    D     C     B
```

### 情绪控制

| 情绪 | ParamEyeLSmile/RSmile | ParamBrowLY/RY | 效果 |
|------|----------------------|----------------|------|
| happy | +0.8 | -0.5 | 笑眼 + 眉毛上扬 |
| surprised | 0 | -0.8 | 眉毛高挑 |
| concerned | 0 | +0.5 | 眉毛内皱 |
| apologetic | 0 | +0.5 | 同 concerned |
| curious | 0 | -0.3 | 单侧眉毛微挑 |
| thinking | 0 | L+0.2, R-0.3 | 一高一低 |
| neutral | 0 (重置) | 0 (重置) | 默认表情 |

---

## 对外接口 (window 全局方法)

网页加载完成后,可通过浏览器控制台或小程序 WebView 注入 JS 调用:

```javascript
// === 情绪控制 ===
window.setEmotion('happy')       // 开心
window.setEmotion('surprised')   // 惊讶
window.setEmotion('concerned')   // 关切
window.setEmotion('apologetic')  // 抱歉
window.setEmotion('curious')     // 好奇
window.setEmotion('thinking')    // 思考

// === 口型控制 ===
window.setMouthOpen(0.0)         // 闭嘴
window.setMouthOpen(0.5)         // 半开
window.setMouthOpen(1.0)         // 大开
window.startSpeaking()           // 自动循环口型序列
window.stopSpeaking()            // 停止并闭口

// === 模型实例 ===
window._live2dModel              // PIXI.live2d.Live2DModel 实例
```

---

## 小程序与 WebView 通信

### WebView → 小程序 (postMessage)

```javascript
// index.html 中 (WebView 侧)
try {
  wx && wx.miniProgram && wx.miniProgram.postMessage({
    data: { type: 'ready' }
  })
} catch(e) {}

// digital-human.js 中 (小程序侧)
onWebViewMessage(e) {
  var data = e.detail.data
  if (data && data.type === 'ready') {
    this.setData({ webViewReady: true })
    console.log('Live2D 模型就绪')
  }
}
```

> 注意: `postMessage` 只在特定时机(小程序后退/组件销毁/分享)触发回调,
> 不是实时消息通道。实时通信需通过 URL hash 变化或 WebSocket。

---

## 模型文件详解

### model.model3.json

```json
{
  "Version": 3,
  "FileReferences": {
    "Moc": "model.bin",
    "Textures": ["texture/texture_00.png"],
    "Physics": "model.physics3.json",
    "DisplayInfo": "model.cdi3.json"
  },
  "Groups": [
    {
      "Target": "Parameter",
      "Name": "EyeBlink",
      "Ids": ["ParamEyeLOpen", "ParamEyeROpen"]
    },
    {
      "Target": "Parameter",
      "Name": "LipSync",
      "Ids": ["ParamMouthOpenY", "ParamMouthForm"]
    }
  ]
}
```

### model.bin 格式验证

```
Magic Bytes:  4D 4F 43 33 04 00 00 00
               M   O  C   3  v4(LE)
文件大小:     3,120,576 bytes
格式:         Cubism 3/4 MOC3 标准格式
验证:         与 音-免费版/ 中的 .moc3 文件完全一致(SHA 相同)
```

### 纹理文件

| 文件 | 大小 | 说明 |
|------|------|------|
| texture_00.png | 16.4 MB | 角色完整贴图,包含所有部件图层 |

### 其他模型文件

| 文件 | 大小 | 说明 |
|------|------|------|
| model.cdi3.json | 13 KB | Cubism Display Info,定义画布参数和部件布局 |
| model.physics3.json | 64 KB | 物理模拟参数(头发摆动/衣物飘动) |
| model.vtube.json | 13 KB | VTube Studio 兼容配置 |
| items_pinned_to_model.json | 424 B | 模型附加物品配置 |

---

## URL 映射表

| 访问路径 | 物理路径 | 用途 |
|----------|----------|------|
| `https://xinphotoshare.click/live2d-viewer` | `build/live2d-viewer/index.html` | Live2D 网页入口 |
| 本地: `localhost:8000/live2d-viewer` | (同上) | 本地开发入口 |
| `/live2d-viewer/static/pixi.min.js` | `build/live2d-viewer/pixi.min.js` | PixiJS 渲染引擎 |
| `/live2d-viewer/static/live2dcubismcore.min.js` | `build/live2d-viewer/live2dcubismcore.min.js` | Cubism 4 Core |
| `/live2d-viewer/static/cubism4.min.js` | `build/live2d-viewer/cubism4.min.js` | Cubism4 PixiJS 插件 |
| `/live2d-viewer/static/index.min.js` | `build/live2d-viewer/index.min.js` | pixi-live2d-display 主库 |
| `/static/model/model.model3.json` | `miniprogram/assets/live2d/model/model.model3.json` | 模型描述文件 |
| `/static/model/model.bin` | `miniprogram/assets/live2d/model/model.bin` | MOC3 二进制模型 |
| `/static/model/texture/texture_00.png` | `miniprogram/assets/live2d/model/texture/texture_00.png` | 角色贴图 |
| `/static/model/model.physics3.json` | `miniprogram/assets/live2d/model/model.physics3.json` | 物理参数 |
| `/docs` | (自动生成) | Swagger API 文档 |

---

## 启动步骤

### 1. 安装依赖并启动后端

```bash
cd lingshan-tour-guide/backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. 微信开发者工具设置

打开小程序项目后:
```
详情 -> 本地设置 -> 勾选:
  [x] 不校验合法域名、web-view(业务域名)、TLS 版本以及 HTTPS 证书
```

### 3. 验证各项服务

| 验证项 | 本地命令 | 公网命令 | 预期结果 |
|--------|----------|----------|----------|
| 后端健康 | `curl localhost:8000/api/v1/health` | `curl https://xinphotoshare.click/api/v1/health` | `{"status":"ok","version":"0.1.0"}` |
| Live2D 网页 | 浏览器打开 `localhost:8000/live2d-viewer` | 浏览器 `https://xinphotoshare.click/live2d-viewer` | 可见数字人"小灵" |
| 模型 JSON | `curl localhost:8000/static/model/model.model3.json` | `curl https://xinphotoshare.click/static/model/model.model3.json` | HTTP 200 |
| 模型二进制 | `curl localhost:8000/static/model/model.bin` | `curl https://xinphotoshare.click/static/model/model.bin` | HTTP 200 (3.1MB) |
| API 文档 | `localhost:8000/docs` | `https://xinphotoshare.click/docs` | Swagger UI |
| 景点列表 | `curl localhost:8000/api/v1/spots` | `curl https://xinphotoshare.click/api/v1/spots` | 22个景点数据 |

---

## 性能数据

### 资源加载量

| 资源 | 大小 | 加载方式 | 阻塞? |
|------|------|----------|-------|
| pixi.min.js | 456 KB | `<script>` 同步 | 是 |
| live2dcubismcore.min.js | 150 KB | `<script>` 同步 | 是 |
| cubism4.min.js | 120 KB | `<script>` 同步 | 是 |
| index.min.js | 127 KB | `<script>` 同步 | 是 |
| **JS 小计** | **853 KB** | | |
| model.bin | 3.1 MB | fetch (ArrayBuffer) | 否 |
| texture_00.png | 16.4 MB | PIXI TextureLoader | 否 |
| model.physics3.json | 64 KB | fetch (JSON) | 否 |
| **总加载量** | **~20.4 MB** | | |

### 生产优化建议

| 优化项 | 预期效果 |
|--------|----------|
| JS 文件合并 + minify | 减少请求数,减小体积 ~15% |
| CDN 加速 | 降低首包延迟 |
| 贴图转 WebP | 减少 40-60% (16MB -> 6-9MB) |
| Gzip/Brotli 压缩 | JS 可再压缩 70% |
| HTTP/2 多路复用 | 并行加载 JS 资源 |
| 模型 + 贴图分包 | 按需加载,首屏只加载必要资源 |

---

## 备用方案: 小程序原生渲染

如果 web-view 方案不可用(如真机对 localhost 限制),项目已预留原生方案:

```
components/digital-human-character/renderers/live2d.js
```

特点:
- 使用小程序 Canvas WebGL 上下文直接渲染
- 通过 `wx.request` 下载 model.bin 和贴图
- 不依赖 web-view,纯小程序原生
- 与 Canvas2D 降级方案共享同一套接口

切换方法: 在 `character.js` 的 `_initRenderer()` 中将 `new Canvas2DRenderer()` 替换为 `new Live2DRenderer()`.

---

## AI 智能问答系统

### 架构: ASR → RAG → LLM → TTS → 口型同步

```
小程序/浏览器输入
    │
    ▼
后端 /api/v1/qa/ask
    │
    ├─ 文字输入 → 直接使用文字 (跳过 ASR)
    ├─ 语音输入 → ASR 转文字 (当前 mock, 待接阿里云)
    │
    ▼
RAG 知识检索 (llm_client.py)
    ├─ 关键词匹配 从 44KB 知识库中抽取相关内容
    ├─ 8 个检索维度: FAQ → 概况 → 文化 → 景点 → 路线 → 实用
    └─ 组装 Context 注入 System Prompt
    │
    ▼
DeepSeek LLM (deepseek-chat)
    ├─ 基于知识库生成回答 (不编造)
    ├─ 150 字以内, 适合语音播报
    └─ 无可信信息时诚实说"还在学习"
    │
    ▼
Edge TTS 语音合成 (speech_client.py)
    ├─ 微软神经网络语音 (免费, 无 API Key)
    ├─ 生成 MP3 → base64 返回前端
    └─ 当前语音: zh-CN-XiaoyiNeural (晓依 - 温柔女声)
    │
    ▼
前端播放 + Live2D 口型同步 (index.html)
    ├─ <audio> 播放 MP3
    ├─ 播放期间驱动 ParamMouthOpenY 口型动画
    └─ 播放完毕 → 停止口型 + 恢复表情
```

### 知识库 (knowledge_base.json)

| 模块 | 条目数 | 来源 |
|------|--------|------|
| 景区概况 | 7 项 | 游览指南 docx (历史/起源/现代复兴) |
| 文化内涵 | 4 项 | 游览指南 docx (佛教传承/工艺融合/沉浸体验) |
| 核心景点 | 22 个 | spots.json + 结构化数据集 docx |
| 游览路线 | 3 条 | 游览指南 docx (历史文化线/自然风光线/亲子线) |
| 实用信息 | 3 项 | 游览指南 docx (最佳时间/住宿/建议) |
| 常见问答 | 5 条 | 游览指南 docx (预置高频问答) |
| **总计** | **44KB** | 示范景区公开资料包 全文提取 |

### 语音配置

| 参数 | 值 |
|------|------|
| TTS 引擎 | Microsoft Edge TTS (edge-tts) |
| 当前语音 | `zh-CN-XiaoyiNeural` (晓依) |
| 可选语音 | Xiaoxiao / Yunxi / Xiaoyi / Yunjian (普通话), HsiaoChen / HsiaoYu / YunJhe (台湾腔), HiuMaan / WanLung (粤语) |
| 费用 | 免费, 无需 API Key |

### LLM 配置

| 参数 | 值 |
|------|------|
| 模型 | DeepSeek chat (deepseek-chat) |
| API | `https://api.deepseek.com/v1/chat/completions` |
| Temperature | 0.7 |
| Max Tokens | 400 |
| 兜底策略 | LLM 不可用时, 本地知识库关键词匹配 |

---

## 部署配置

### 公网部署 (当前生效)

| 服务 | 地址 |
|------|------|
| 后端 API + Live2D | `https://xinphotoshare.click` (Nginx → uvicorn :8000) |
| 小程序 API 请求 | `app.js` → `apiBase: 'https://xinphotoshare.click/api/v1'` |
| 小程序 WebView | `digital-human.js` → `webViewSrc: 'https://xinphotoshare.click/live2d-viewer/'` |

### 本地开发

| 服务 | 端口 | 配置文件 |
|------|------|----------|
| 后端 API + Live2D | **8000** | `backend/.env` → `PORT=8000` |
| 小程序 API 请求 | **8000** | `app.js` → `apiBase: 'http://localhost:8000/api/v1'` |
| 小程序 WebView | **8000** | `digital-human.wxml` → `src="http://localhost:8000/live2d-viewer/"` |
| 后端起机命令 | **8000** | `uvicorn app.main:app --host 0.0.0.0 --port 8000` |

> **所有服务统一使用端口 8000,不要使用 8001!**
