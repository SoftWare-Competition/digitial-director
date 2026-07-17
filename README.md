# 灵山胜境 AI 数字人导游

> 微信小程序 + Live2D 数字人 + LLM 智能问答，为无锡灵山胜境景区提供沉浸式 AI 导游体验。
>
> **服务地址**: https://xinphotoshare.click  |  **后端**: FastAPI 0.1.0  |  **分支**: MiniProgram

---

## 项目结构

```
lingshan-tour-guide/
├── backend/                    # FastAPI 后端
│   ├── app/
│   │   ├── main.py            # 入口，路由注册，静态文件挂载
│   │   ├── config.py          # .env 配置读取
│   │   ├── database.py        # SQLAlchemy 引擎 + Session
│   │   ├── models/            # ORM 模型 + Pydantic Schema
│   │   ├── routers/           # API 路由 (user/qa/spots/narration/tips/weather)
│   │   ├── services/          # 业务逻辑 (LLM/ASR/TTS/微信/天气/邮件)
│   │   └── utils/             # 工具 (JWT/地理围栏)
│   ├── data/                  # 静态数据 (spots.json/knowledge_base.json/routes.json)
│   ├── audio/                 # TTS 景点讲解 MP3
│   ├── static/                # Live2D 模型 + 用户头像
│   └── requirements.txt
│
├── miniprogram/               # 微信小程序
│   ├── pages/
│   │   ├── index/             # 首页 (精选景点/路线/天气)
│   │   ├── digital-human/     # 数字人问答页 (WebView 嵌入 Live2D)
│   │   ├── map/               # 地图 + GPS 签到
│   │   ├── routes/            # 游览路线选择
│   │   ├── spot-detail/       # 景点详情 + 语音讲解
│   │   ├── profile/           # 个人中心
│   │   └── qa-history/        # 对话历史
│   ├── components/            # 公共组件 (audio-player 等)
│   ├── utils/                 # API/认证/位置 工具
│   └── app.js                 # 小程序入口
│
└── build/
    └── live2d-viewer/         # WebView HTML (PixiJS + Live2D Cubism4 + 聊天UI)
```

---

## 核心功能

### 数字人问答
- **Live2D 模型** — 渲染/拖拽/缩放/双击复位，眨眼/呼吸/表情切换
- **语音输入** — 小程序原生录音 → 阿里云 ASR → LLM → Edge TTS 播报
- **文字输入** — WebView 内输入 → LLM → TTS
- **口型同步** — 播放语音时自动驱动嘴部参数
- **多轮对话** — 最近 10 条历史注入 system prompt
- **位置感知** — GPS → 地理围栏 → 注入景点上下文

### 景区服务
- **22 个景点** — GPS/规模/文化内涵/详细介绍/参观信息/拍照建议
- **3 条路线** — 历史文化 6h / 自然风光 5h / 亲子家庭 4h
- **GPS 签到** — 30m 地理围栏自动触发语音讲解
- **景点详情** — 文字介绍 + 语音讲解播放器

### 用户系统
- 微信一键登录 / 邮箱注册登录
- JWT Token 认证
- 对话历史 / 签到记录

---

## 快速开始

### 环境要求
- Python 3.10+
- ffmpeg (ASR 音频转码)
- 微信开发者工具

### 1. 后端

```bash
cd backend
pip install -r requirements.txt

# 配置 .env (复制 .env.example 填入真实密钥)
cp .env.example .env

# 启动
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. 小程序

1. 微信开发者工具 → 导入 `miniprogram/`
2. AppID: `wxa7ecb1e815ef6378`
3. 开发阶段勾选「不校验合法域名」

### 3. 环境变量 (.env)

```env
HOST=0.0.0.0
PORT=8000
SECRET_KEY=change-me-to-a-random-string
DATABASE_URL=sqlite:///./lingshan.db

# 微信小程序
WECHAT_APPID=your_wechat_appid
WECHAT_SECRET=your_wechat_secret

# DeepSeek LLM
DEEPSEEK_API_KEY=your_deepseek_api_key
DEEPSEEK_BASE_URL=https://api.deepseek.com

# 阿里云 ASR
ALIBABA_ACCESS_KEY_ID=your_alibaba_access_key_id
ALIBABA_ACCESS_KEY_SECRET=your_alibaba_access_key_secret
ALIBABA_ASR_APPKEY=your_asr_appkey

# 天气 (心知天气)
SENIVERSE_API_KEY=your_seniverse_api_key

# 百度地图
BAIDU_MAP_AK=your_baidu_map_ak

# 邮件 SMTP
SMTP_HOST=smtp.qq.com
SMTP_PORT=587
SMTP_USERNAME=your_email@qq.com
SMTP_PASSWORD=your_smtp_password
```

---

## API 概览

### 用户 `/api/v1/user`
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /user/login | 微信登录 (code → token) |
| POST | /user/login/email | 邮箱验证码登录 |
| POST | /user/register | 邮箱注册 |
| POST | /user/send-code | 发送邮箱验证码 |
| GET | /user/profile | 获取用户资料 |
| PUT | /user/profile | 更新资料 |
| GET | /user/history | 签到 + QA 历史 |

### 问答 `/api/v1/qa`
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /qa/ask | 语音/文字问答 (multipart: audio+text+token) |
| GET | /qa/sessions/{id} | 会话消息列表 |
| POST | /qa/feedback | 消息反馈 (点赞/踩) |

### 景区 `/api/v1`
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /spots | 景点列表 |
| GET | /spots/{id} | 景点详情 |
| GET | /routes | 路线列表 |
| GET | /routes/{id} | 路线详情 |
| POST | /narration/checkin | GPS 签到触发讲解 |
| POST | /narration/manual | 手动触发讲解 |
| GET | /narration/spot-audio/{id} | TTS 语音讲解 MP3 |
| GET | /tips/current | 智能提示 |
| GET | /weather/current | 实时天气 |
| POST | /admin/reseed | 从 JSON 刷新数据库 |
| GET | /health | 健康检查 |

---

## 语音问答流程

```
用户按住说话 (小程序原生录音)
    ↓
wx.uploadFile → POST /api/v1/qa/ask (multipart: audio.mp3)
    ↓
[1] 阿里云 ASR: PCM 16kHz → Paraformer → 文字
[2] RAG: 关键词匹配 → 知识库检索
[3] DeepSeek LLM: system prompt + 知识 + 对话历史 → 回答
[4] Edge TTS: 回答文字 → MP3 (base64)
    ↓
返回 JSON { answer_text, answer_audio_base64, session_id }
    ↓
小程序原生音频播放 + WebView 显示文字 + 口型动画
```

---

## 服务器部署

```bash
# 1. 拉取代码
git clone <repo-url> /opt/backend
cd /opt/backend
pip install -r requirements.txt

# 2. 配置 .env
cp .env.example .env && vim .env

# 3. 启动
nohup python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8001 > /tmp/uv.log 2>&1 &

# 4. Nginx 反向代理
# location /api/v1/ { proxy_pass http://127.0.0.1:8001; }
# location /static/audio/ { alias /opt/backend/audio/; }
nginx -s reload
```

---

## 技术栈

| 层 | 技术 |
|----|------|
| 后端框架 | FastAPI (Python) |
| 数据库 | SQLite + SQLAlchemy ORM |
| AI 对话 | DeepSeek Chat API |
| 知识检索 | 本地 JSON + 关键词 RAG |
| 语音识别 | 阿里云 Paraformer NLS |
| 语音合成 | Microsoft Edge TTS (免费) |
| 数字人 | Live2D Cubism4 + PixiJS |
| 小程序 | 微信原生框架 + WebView |
| 认证 | JWT (HMAC-SHA256) |
| 天气 | 心知天气 |
| 地图 | 百度地图 + 微信地图 |
| 邮件 | QQ SMTP |

---

## 注意事项

- **`.env` 不要提交到 Git** (含真实 API 密钥，已在 `.gitignore`)
- `__pycache__/`、`*.pyc`、`*.db`、`deploy_*.tar.gz` 已在 `.gitignore`
- SQLite 不适合高并发，生产环境建议迁移 PostgreSQL
- WebView 通过 URL hash 传数据，数据量过大 (>200KB) 时真机可能加载异常
- 阿里云 ASR 依赖 ffmpeg 转码 (浏览器录音 → PCM 16kHz)
- 小程序发布前需在 mp.weixin.qq.com 配置服务器域名白名单
