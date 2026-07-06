"""Narration service: GPS matching, dedup, checkin recording."""
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models import ScenicSpot, Checkin
from app.utils.geo import within_geofence


def find_nearest_spot(lat: float, lng: float, db: Session) -> ScenicSpot | None:
    """Find the nearest scenic spot within geofence radius."""
    spots = db.query(ScenicSpot).filter(ScenicSpot.is_active == 1).all()

    matched_spot = None
    closest_distance = float("inf")

    for spot in spots:
        matched, dist = within_geofence(lat, lng, spot.lat, spot.lng, spot.geofence_radius)
        if matched and dist < closest_distance:
            closest_distance = dist
            matched_spot = spot

    return matched_spot


def should_narrate(spot_id: str, user_id: str = "anonymous", cooldown_minutes: int = 30, db: Session = None) -> bool:
    """Check if narration should play (not a recent repeat)."""
    if db is None:
        return True
    cutoff = datetime.utcnow() - timedelta(minutes=cooldown_minutes)
    recent = (
        db.query(Checkin)
        .filter(
            Checkin.spot_id == spot_id,
            Checkin.created_at >= cutoff,
        )
        .first()
    )
    return recent is None


def record_checkin(
    spot_id: str,
    lat: float,
    lng: float,
    user_id: str = "anonymous",
    route_id: str = None,
    trigger_type: str = "gps",
    db: Session = None,
) -> Checkin:
    """Record a checkin event."""
    if db is None:
        return None
    checkin = Checkin(
        user_id=user_id,
        spot_id=spot_id,
        route_id=route_id,
        lat=lat,
        lng=lng,
        trigger_type=trigger_type,
        narration_played=1,
    )
    db.add(checkin)
    db.commit()
    return checkin
