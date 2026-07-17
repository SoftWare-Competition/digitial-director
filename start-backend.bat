@echo off
chcp 65001 >nul
echo ============================================
echo   灵山胜境 AI数字人导游 - 后端启动
echo ============================================
echo.

cd /d "%~dp0backend"

echo [1/2] 检查数据库...
if not exist "lingshan.db" (
    echo   - 数据库不存在，正在初始化...
    python scripts/init_db.py
) else (
    echo   - lingshan.db 已存在
)

echo.
echo [2/2] 启动 FastAPI 服务...
echo   地址: http://localhost:8000
echo   Live2D: http://localhost:8000/live2d-viewer
echo   API:    http://localhost:8000/api/v1/health
echo   文档:   http://localhost:8000/docs
echo.
echo 按 Ctrl+C 停止服务
echo ============================================
echo.

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
pause
