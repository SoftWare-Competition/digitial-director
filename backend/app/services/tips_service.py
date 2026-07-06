"""Smart tips rule engine for weather/time/location-based suggestions."""
import json
from datetime import datetime

from app.services.weather_client import get_current_weather


def evaluate_tips(lat: float = None, lng: float = None, user_id: str = None) -> list[dict]:
    """Evaluate all tips rules against current conditions."""

    weather = get_current_weather()

    rules = []
    try:
        with open("data/tips_rules.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            rules = data.get("rules", [])
    except Exception:
        pass

    context = _build_context(weather, lat, lng)

    tips = []
    for rule in rules:
        if _evaluate_condition(rule["condition"], context):
            tip = rule["tip"]
            tips.append(tip)

    tips.sort(key=lambda t: {"high": 0, "medium": 1, "low": 2}.get(t.get("priority", "medium"), 5))
    return tips[:3]


def _build_context(weather: dict, lat: float = None, lng: float = None) -> dict:
    now = datetime.now()
    return {
        "weather": weather,
        "time": {
            "hour": now.hour,
            "month": now.month,
            "weekday": now.weekday(),
        },
        "location": {
            "lat": lat,
            "lng": lng,
            "distance_to_exit_m": _estimate_distance_to_exit(lat, lng),
        },
        "user": {
            "continuous_walk_min": 0,
        },
    }


def _evaluate_condition(condition: dict, context: dict) -> bool:
    cond_type = condition.get("type", "")
    op = condition.get("operator", "eq")
    value = condition.get("value")

    if cond_type == "weather":
        field = condition.get("field", "")
        actual = context.get("weather", {}).get(field)
        return _compare(actual, op, value)

    elif cond_type == "time":
        field = condition.get("field", "")
        actual = context.get("time", {}).get(field)
        return _compare(actual, op, value)

    elif cond_type == "location":
        field = condition.get("field", "")
        actual = context.get("location", {}).get(field)
        return _compare(actual, op, value)

    elif cond_type == "user":
        field = condition.get("field", "")
        actual = context.get("user", {}).get(field)
        return _compare(actual, op, value)

    elif cond_type == "composite":
        conditions = condition.get("conditions", [])
        if op == "and":
            return all(_evaluate_condition(c, context) for c in conditions)
        elif op == "or":
            return any(_evaluate_condition(c, context) for c in conditions)

    return False


def _compare(actual, op: str, expected) -> bool:
    if actual is None:
        return False
    if op == "eq":
        return actual == expected
    elif op == "neq":
        return actual != expected
    elif op == "gt":
        return actual > expected
    elif op == "gte":
        return actual >= expected
    elif op == "lt":
        return actual < expected
    elif op == "lte":
        return actual <= expected
    return False


def _estimate_distance_to_exit(lat: float = None, lng: float = None) -> float:
    """Estimate distance to exit from current position."""
    if lat is None or lng is None:
        return 1000  # Default: not far from exit
    # Exit GPS is approximately LS-001 location
    from app.utils.geo import haversine
    return haversine(lat, lng, 31.4280, 120.1180)
