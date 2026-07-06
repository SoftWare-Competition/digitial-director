from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ScenicSpot, Checkin
from app.models.schemas import (
    APIResponse,
    CheckinRequest,
    CheckinResponse,
    ManualNarrationRequest,
    NarrationInfo,
    SpotBasic,
    SpotLocation,
)
from app.utils.geo import within_geofence

router = APIRouter()

CHECKIN_COOLDOWN_MINUTES = 30


@router.post("/narration/checkin", response_model=APIResponse)
def checkin(req: CheckinRequest, db: Session = Depends(get_db)):
    spots = db.query(ScenicSpot).filter(ScenicSpot.is_active == 1).all()

    matched_spot = None
    closest_distance = float("inf")

    for spot in spots:
        matched, dist = within_geofence(req.lat, req.lng, spot.lat, spot.lng, spot.geofence_radius)
        if matched and dist < closest_distance:
            closest_distance = dist
            matched_spot = spot

    if not matched_spot:
        return APIResponse(data=CheckinResponse(matched=False).model_dump())

    cutoff = datetime.utcnow() - timedelta(minutes=CHECKIN_COOLDOWN_MINUTES)
    recent = (
        db.query(Checkin)
        .filter(
            Checkin.spot_id == matched_spot.id,
            Checkin.created_at >= cutoff,
        )
        .first()
    )
    is_repeat = recent is not None

    if not is_repeat:
        checkin_record = Checkin(
            user_id="anonymous",
            spot_id=matched_spot.id,
            lat=req.lat,
            lng=req.lng,
            trigger_type="gps",
            narration_played=1,
        )
        db.add(checkin_record)
        db.commit()

    return APIResponse(
        data=CheckinResponse(
            matched=True,
            spot=SpotBasic(
                id=matched_spot.id,
                name=matched_spot.name,
                category=matched_spot.category,
                location=SpotLocation(lat=matched_spot.lat, lng=matched_spot.lng),
                geofence_radius=matched_spot.geofence_radius,
                narration_duration_sec=matched_spot.narration_duration,
                audio_url=matched_spot.narration_audio_url,
            ),
            narration=NarrationInfo(
                audio_url=matched_spot.narration_audio_url or "",
                text=matched_spot.narration_text or "",
                duration_sec=matched_spot.narration_duration or 0,
                is_repeat=is_repeat,
            ),
            tips=[],
        ).model_dump()
    )


@router.post("/narration/manual", response_model=APIResponse)
def manual_narration(req: ManualNarrationRequest, db: Session = Depends(get_db)):
    spot = db.query(ScenicSpot).filter(ScenicSpot.id == req.spot_id, ScenicSpot.is_active == 1).first()
    if not spot:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="景点不存在")

    checkin_record = Checkin(
        user_id="anonymous",
        spot_id=spot.id,
        trigger_type="manual",
        narration_played=1,
    )
    db.add(checkin_record)
    db.commit()

    return APIResponse(
        data=CheckinResponse(
            matched=True,
            spot=SpotBasic(
                id=spot.id,
                name=spot.name,
                category=spot.category,
                location=SpotLocation(lat=spot.lat, lng=spot.lng),
                geofence_radius=spot.geofence_radius,
                narration_duration_sec=spot.narration_duration,
                audio_url=spot.narration_audio_url,
            ),
            narration=NarrationInfo(
                audio_url=spot.narration_audio_url or "",
                text=spot.narration_text or "",
                duration_sec=spot.narration_duration or 0,
                is_repeat=False,
            ),
            tips=[],
        ).model_dump()
    )
