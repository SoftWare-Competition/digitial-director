import json, os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base
from app.routers import spots, narration, qa, tips, user

# 项目根目录 (lingshan-tour-guide/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def init_db():
    Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="AI数字人导游 API",
    description="灵山胜境 AI 数字人导游系统 MVP",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static/audio", StaticFiles(directory=os.path.join(BASE_DIR, "backend", "audio")), name="static_audio")
app.mount("/static/model", StaticFiles(directory=os.path.join(BASE_DIR, "backend", "static", "model")), name="static_model")
app.mount("/live2d-viewer/static", StaticFiles(directory=os.path.join(BASE_DIR, "build", "live2d-viewer")), name="live2d_viewer_static")

from fastapi.responses import HTMLResponse
import os

@app.get("/live2d-viewer", response_class=HTMLResponse)
@app.get("/live2d-viewer/", response_class=HTMLResponse)
async def live2d_viewer():
    html_path = os.path.join(os.path.dirname(__file__), "..", "..", "build", "live2d-viewer", "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read()

app.include_router(user.router, prefix="/api/v1", tags=["用户"])
app.include_router(spots.router, prefix="/api/v1", tags=["景点与路线"])
app.include_router(narration.router, prefix="/api/v1", tags=["讲解触发"])
app.include_router(qa.router, prefix="/api/v1", tags=["语音问答"])
app.include_router(tips.router, prefix="/api/v1", tags=["智能提示"])


@app.get("/api/v1/health")
def health():
    return {"status": "ok", "version": "0.1.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=settings.debug)
