"""Weather service client using 和风天气 (Hefeng) API."""
import json
import time
import httpx
from datetime import datetime, timedelta

from app.database import SessionLocal
from app.models import WeatherCache
from app.config import settings

CACHE_TTL_MINUTES = 15


def get_current_weather(location: str = "101190201") -> dict:
    """Get current weather for a location.

    Default location: 101190201 = 无锡

    Returns dict with: temperature, uv_index, precip_probability,
                       weather_text, humidity, wind_speed
    """
    cached = _get_from_cache()
    if cached:
        return cached

    if not settings.hefeng_api_key:
        return _mock_weather()

    try:
        url = f"https://devapi.qweather.com/v7/weather/now"
        params = {"location": location, "key": settings.hefeng_api_key}
        resp = httpx.get(url, params=params, timeout=10)
        data = resp.json()

        if data.get("code") == "200":
            now = data.get("now", {})
            weather_data = {
                "temperature": float(now.get("temp", 25)),
                "weather_text": now.get("text", "晴"),
                "humidity": int(now.get("humidity", 60)),
                "wind_speed": float(now.get("windSpeed", 10)),
                "uv_index": _get_uv_index(location),
                "precip_probability": 0,
            }
            _save_to_cache(weather_data)
            return weather_data
    except Exception:
        pass

    return _mock_weather()


def _get_uv_index(location: str) -> int:
    """Get UV index from Hefeng API."""
    if not settings.hefeng_api_key:
        return 2
    try:
        url = f"https://devapi.qweather.com/v7/indices/1d"
        params = {"location": location, "key": settings.hefeng_api_key, "type": "5"}
        resp = httpx.get(url, params=params, timeout=10)
        data = resp.json()
        if data.get("code") == "200":
            daily = data.get("daily", [])
            if daily:
                return int(daily[0].get("value", 2))
    except Exception:
        pass
    return 2


def _get_from_cache() -> dict | None:
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        cache = (
            db.query(WeatherCache)
            .filter(WeatherCache.expires_at > now)
            .order_by(WeatherCache.fetched_at.desc())
            .first()
        )
        if cache:
            return json.loads(cache.raw_response)
    finally:
        db.close()
    return None


def _save_to_cache(weather_data: dict):
    db = SessionLocal()
    try:
        expires = datetime.utcnow() + timedelta(minutes=CACHE_TTL_MINUTES)
        entry = WeatherCache(
            provider="hefeng",
            raw_response=json.dumps(weather_data),
            expires_at=expires,
        )
        db.add(entry)
        db.commit()
    finally:
        db.close()


def _mock_weather() -> dict:
    """Mock weather data for development without API key."""
    now = datetime.now()
    month = now.month
    hour = now.hour

    if month in (6, 7, 8):
        temp, uv, text = 33, 7, "晴"
    elif month in (12, 1, 2):
        temp, uv, text = 5, 2, "多云"
    else:
        temp, uv, text = 22, 5, "晴转多云"

    return {
        "temperature": temp,
        "weather_text": text,
        "humidity": 55,
        "wind_speed": 12,
        "uv_index": uv,
        "precip_probability": 0,
    }
