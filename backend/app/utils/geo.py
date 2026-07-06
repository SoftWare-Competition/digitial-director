import math


def haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Return distance in meters between two GPS coordinates."""
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)

    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def within_geofence(
    user_lat: float, user_lng: float,
    spot_lat: float, spot_lng: float,
    radius: float
) -> tuple[bool, float]:
    """Check if user is within a spot's geofence. Returns (matched, distance_m)."""
    distance = haversine(user_lat, user_lng, spot_lat, spot_lng)
    return distance <= radius, distance
