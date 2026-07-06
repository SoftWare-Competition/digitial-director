# AI数字人导游 - Live2D 集成开发文档

> 最后更新: 2026-07-06  
> 模型: 音-免费版 (作者: 逐尾鲨, Cubism 3.0)  
> 方案: WebView + pixi-live2d-display + DeepSeek AI + Edge TTS

---

## 一、项目结构

```
lingshan-tour-guide/
├── backend/                          # FastAPI 后端 (Python)
│   ├── app/main.py                   # API路由 + 静态文件挂载
│   └── app/routers/                  # 各业务模块路由
│
├── miniprogram/                      # 微信小程序前端
│   ├── app.js                        # 全局配置 (apiBase: 域名)
│   ├── pages/digital-human/          # 数字人页面 (当前用web-view)
│   │   ├── digital-human.wxml        # web-view 全屏
│   │   └── digital-human.js          # 简化的通信逻辑
│   ├── components/digital-human-character/  # 数字人组件 (旧方案,备用)
│   ├── assets/live2d/model/          # Live2D模型文件
│   └── lib/live2d/                   # Cubism SDK
│
├── build/                            # WebView 构建目录
│   ├── live2d-viewer/                # ★ 当前使用的Live2D查看器
│   │   ├── index.html                # 主页面 (PixiJS + pixi-live2d-display)
│   │   ├── pixi.min.js               # PixiJS v7 (456KB)
│   │   ├── live2dcubismcore.min.js   # Cubism 4 Core (150KB)
│   │   ├── cubism4.min.js            # pixi-live2d Cubism4插件
│   │   └── index.min.js              # pixi-live2d-display主库
│   └── node_modules/                 # npm依赖
│       ├── pixi.js/                  # PixiJS v7
│       └── pixi-live2d-display/      # Live2D PixiJS渲染插件
│
└── 音-免费版/                         # 原始Live2D模型文件
    ├── 音.moc3                        # 模型二进制 (3.1MB)
    ├── 音.model3.json                 # 模型配置入口
    ├── 音.physics3.json               # 物理参数
    ├── 音.cdi3.json                   # 参数显示信息
    └── 音.8192/texture_00.png         # 纹理贴图 (8192×8192, 16MB)
```

---

## 二、模型文件部署

原始 `音-免费版` 模型已复制并重命名到小程序资源目录：

```
miniprogram/assets/live2d/model/
├── model.bin              ← 音.moc3 (3.1MB)
├── model.model3.json      ← 音.model3.json (引用路径已修正)
├── model.physics3.json    ← 音.physics3.json
├── model.cdi3.json        ← 音.cdi3.json
└── texture/
    └── texture_00.png     ← 音.8192/texture_00.png (16.4MB, 8192x8192)
```

模型通过后端静态服务提供: `https://xinphotoshare.click/static/model/model.model3.json`

> 本地开发: `http://localhost:8000/static/model/model.model3.json`
> 
> `index.html` 使用相对路径 `/static/model/...`，本地和远程无需修改代码即可自动适配。

---

## 三、方案演进历史

### 方案A: 小程序 Canvas + Cubism Core 底层API (❌ 已废弃)

**文件**: `miniprogram/components/digital-human-character/renderers/live2d.js`

使用 Live2D Cubism 4 Core 底层 API 直接在小程序 WebGL Canvas 上渲染。

**问题**:
- 手写 WebGL 渲染器无法正确处理剪裁遮罩 (Clipping Mask)
- 无法加载 physics3.json 物理引擎 (头发/衣服不动)
- 渲染排序错误，模型支离破碎
- 纹理8192px过大，GPU兼容性问题

### 方案B: WebView + pixi-live2d-display (✅ 当前方案)

**文件**: `build/live2d-viewer/index.html`

利用 pixi-live2d-display (基于 PixiJS 的 Live2D 渲染库) 在独立 HTML 页面中渲染，小程序通过 `<web-view>` 嵌入。

**优势**:
- ✅ 完整的剪裁遮罩支持
- ✅ 物理引擎 (physics3.json 自动加载)
- ✅ 正确的渲染排序
- ✅ 眨眼/呼吸等自动动画
- ✅ 成熟的 PixiJS WebGL 渲染管线

**局限**:
- web-view 全屏覆盖，无法叠加小程序原生UI组件
- 需要后端服务运行
- 小程序与WebView通信有限制

---

## 四、启动步骤

### 1. 启动后端 (必须)

```powershell
cd "C:\Claude工作区间\AI数字人导游分析\lingshan-tour-guideackend"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 2. 测试 Live2D 页面 (浏览器)

打开 `http://localhost:8000/live2d-viewer` (公网: `https://xinphotoshare.click/live2d-viewer`)

- 模型从 `/static/model/model.model3.json` 加载
- JS库从 `/live2d-viewer/static/xxx` 加载

### 3. 微信开发者工具

- 设置 → 项目设置 → 勾选 "不校验合法域名、web-view（业务域名）、TLS 版本以及 HTTPS 证书"
- 进入 "数字人" 页面 → web-view 加载 Live2D 模型

---

## 五、后端路由说明

| 路径 | 用途 |
|------|------|
| `/live2d-viewer` | Live2D查看器HTML页面 (FastAPI路由直接返回) |
| `/live2d-viewer/static/*` | JS/CSS静态文件 (StaticFiles挂载) |
| `/static/model/*` | Live2D模型文件 |
| `/api/v1/*` | 业务API |

关键代码 (`backend/app/main.py`):
```python
app.mount("/live2d-viewer/static", StaticFiles(directory="../build/live2d-viewer"), name="live2d_viewer_static")
app.mount("/static/model", StaticFiles(directory="../miniprogram/assets/live2d/model"), name="static_model")

@app.get("/live2d-viewer", response_class=HTMLResponse)
async def live2d_viewer():
    html_path = os.path.join(os.path.dirname(__file__), "..", "..", "build", "live2d-viewer", "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read()
```

---

## 六、Live2D 页面 JS 加载顺序

HTML 中必须严格按此顺序加载:

```html
<script src="/live2d-viewer/static/pixi.min.js"></script>              <!-- 1. PixiJS -->
<script src="/live2d-viewer/static/live2dcubismcore.min.js"></script>  <!-- 2. Cubism Core -->
<script src="/live2d-viewer/static/cubism4.min.js"></script>           <!-- 3. Cubism4 插件 -->
<script src="/live2d-viewer/static/index.min.js"></script>             <!-- 4. pixi-live2d 主库 -->
```

加载后注册: `PIXI.live2d.Live2DModel`

---

## 七、模型参数

`音` 模型包含 113 个参数，关键参数:

| 参数ID | 用途 | 范围 |
|--------|------|------|
| ParamEyeLOpen / ParamEyeROpen | 左右眼开闭 | 0(闭)~1(开) |
| ParamEyeLSmile / ParamEyeRSmile | 笑眼程度 | 0~1 |
| ParamBrowLY / ParamBrowRY | 眉毛上下 | -1~1 |
| ParamMouthOpenY | 嘴张开 | 0~1 |
| ParamMouthForm | 嘴型变形 | 0~1 |
| ParamBreath | 呼吸幅度 | 0~1 |
| ParamAngleX/Y/Z | 头部旋转 | -30~30 |

---

## 八、AI 智能问答系统

### 流水线: ASR → RAG → LLM → TTS → 口型同步

后端 `/api/v1/qa/ask` 接收文字或语音，依次处理:

| 阶段 | 组件 | 说明 |
|------|------|------|
| 文字输入 | `qa.py` text 参数 | 跳过 ASR，直接使用文字 |
| 语音输入 | `speech_client.py` ASR | 当前 mock，待接阿里云 Paraformer |
| 知识检索 | `llm_client.py` RAG | 8 维关键词匹配，从 44KB 知识库精准抽取 |
| AI 生成 | DeepSeek chat API | 基于知识库生成 150 字内回答 |
| 语音合成 | `speech_client.py` TTS | Microsoft Edge TTS (免费), 神经网络语音 |
| 前端播放 | `index.html` `<audio>` | base64 MP3 播放 + Live2D 口型同步 |

### 知识库

`data/knowledge_base.json` — 44KB，从`示范景区公开资料包`全文提取:

- 景区概况 (历史渊源/现代复兴) — 7 项
- 文化内涵 (佛教传承/工艺融合) — 4 项  
- 核心景点 (22 个，含位置/规模/文化/详情/参观/拍照) — 22 项
- 游览路线 (历史线/自然线/亲子线) — 3 条
- 实用信息 (时间/住宿/建议) — 3 项
- 常见问答 (FAQ 预置) — 5 条

### 语音: Edge TTS

- 当前: `zh-CN-XiaoyiNeural` (晓依 - 温柔女声)
- 可选: Xiaoxiao / Yunxi / Xiaoyi (普通话), HsiaoChen / HsiaoYu (台湾腔), HiuMaan (粤语)
- 免费, 无需 API Key, 通过 `edge-tts` Python 库调用

### LLM: DeepSeek

- 模型: `deepseek-chat`
- 兜底: API 不可用时本地知识库关键词匹配

---

## 九、已知问题和待办

1. **ASR 语音识别**: 当前返回 mock 数据，需接入阿里云/Whisper
2. **小程序通信**: 实时双向通信需通过 URL hash 或 WebSocket
3. **纹理优化**: 8192×8192 原图，可预压缩为 WebP
4. **多端适配**: 不同屏幕尺寸下模型位置/缩放需优化
5. **语音可配置**: 后续支持前端切换 TTS 语音

---

## 十、部署与开发配置

### 远程部署 (生产环境)

| 服务 | 地址 |
|------|------|
| 域名 | `https://xinphotoshare.click` |
| Live2D 查看器 | `https://xinphotoshare.click/live2d-viewer` |
| 后端 API | `https://xinphotoshare.click/api/v1` |
| 模型静态资源 | `https://xinphotoshare.click/static/model/` |

> Nginx 监听 443 (HTTPS) → 反向代理到 uvicorn `127.0.0.1:8000`

### 本地开发

| 服务 | 地址 |
|------|------|
| 后端 | `http://localhost:8000` |
| Live2D 查看器 | `http://localhost:8000/live2d-viewer` |

启动命令: `uvicorn app.main:app --host 0.0.0.0 --port 8000`

小程序切回本地时修改两处:
- `app.js`: `apiBase: 'http://localhost:8000/api/v1'`
- `digital-human.js`: `BASE` 和 `webViewSrc` 改为 `http://localhost:8000`

> 💡 `index.html` 全部使用相对路径 (`/api/v1`, `/static/model/...`)，本地和远程无需修改即可自动适配。
