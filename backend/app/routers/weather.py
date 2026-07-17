"""Weather API - 和风天气实时数据."""
from fastapi import APIRouter, Query

from app.models.schemas import APIResponse
from app.services.weather_client import get_current_weather

router = APIRouter()


@router.get("/weather/current", response_model=APIResponse)
def current_weather(location: str = Query("101190201", description="和风天气 Location ID, 默认无锡")):
    """获取当前天气，返回温度/天气描述/图标/湿度等信息."""
    w = get_current_weather(location)

    # 天气图标映射 (和风天气 text → emoji)
    icon_map = {
        "晴": "☀️", "少云": "🌤️", "晴间多云": "⛅", "多云": "☁️",
        "阴": "☁️", "小雨": "🌧️", "中雨": "🌧️", "大雨": "⛈️",
        "暴雨": "⛈️", "雷阵雨": "⛈️", "雪": "❄️", "雾": "🌫️",
        "霾": "🌫️", "扬沙": "🌫️", "浮尘": "🌫️",
    }
    weather_text = w.get("weather_text", "晴")
    icon = icon_map.get(weather_text, "🌤️")

    return APIResponse(data={
        "icon": icon,
        "temp": int(w.get("temperature", 25)),
        "desc": weather_text,
        "humidity": w.get("humidity", 60),
        "wind_speed": w.get("wind_speed", 0),
        "uv_index": w.get("uv_index", 2),
    })
