"""Baidu Maps route planning."""
import httpx
from app.config import settings

BAIDU_URL = "https://api.map.baidu.com/directionlite/v1/walking"


async def plan_walking_route(spots: list[dict]) -> dict:
    """Plan walking route via Baidu Direction API."""
    if not settings.baidu_map_ak:
        return {"polylines": [], "distance": 0, "duration": 0}

    all_polylines = []
    total_distance = 0
    total_duration = 0

    async with httpx.AsyncClient(timeout=15) as client:
        for i in range(len(spots) - 1):
            origin = spots[i]
            dest = spots[i + 1]
            params = {
                "origin": f"{origin['lat']},{origin['lng']}",
                "destination": f"{dest['lat']},{dest['lng']}",
                "ak": settings.baidu_map_ak,
                "coord_type": "bd09ll",
            }
            try:
                resp = await client.get(BAIDU_URL, params=params)
                data = resp.json()
                if data.get("status") == 0 and data.get("result"):
                    route = data["result"].get("routes", [{}])[0]
                    total_distance += route.get("distance", 0)
                    total_duration += route.get("duration", 0)
                    for step in route.get("steps", []):
                        path = step.get("path", "")
                        if path:
                            pts = [[float(p.split(",")[1]), float(p.split(",")[0])] for p in path.split(";") if p]
                            all_polylines.append(pts)
            except Exception as e:
                print(f"[Baidu] Error: {e}")

    return {"polylines": all_polylines, "distance": total_distance, "duration": total_duration}
