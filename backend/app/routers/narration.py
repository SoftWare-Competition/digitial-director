import os
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ScenicSpot, Checkin
from app.utils.auth import get_optional_user
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
from app.services.speech_client import text_to_speech

router = APIRouter()

CHECKIN_COOLDOWN_MINUTES = 30


@router.post("/narration/checkin", response_model=APIResponse)
def checkin(req: CheckinRequest, db: Session = Depends(get_db), user: dict = Depends(get_optional_user)):
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
            user_id=user.get("sub", "anonymous") if user else "anonymous",
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
def manual_narration(req: ManualNarrationRequest, db: Session = Depends(get_db), user: dict = Depends(get_optional_user)):
    spot = db.query(ScenicSpot).filter(ScenicSpot.id == req.spot_id, ScenicSpot.is_active == 1).first()
    if not spot:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="景点不存在")

    checkin_record = Checkin(
        user_id=user.get("sub", "anonymous") if user else "anonymous",
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


@router.get("/narration/spot-audio/{spot_id}")
async def get_spot_audio(spot_id: str, db: Session = Depends(get_db)):
    """TTS 生成景点语音讲解，返回 MP3 URL + 时长，缓存 24h"""
    spot = db.query(ScenicSpot).filter(ScenicSpot.id == spot_id, ScenicSpot.is_active == 1).first()
    if not spot:
        raise HTTPException(status_code=404, detail="Spot not found")

    text = spot.narration_text or ""
    if not text.strip():
        raise HTTPException(status_code=404, detail="No narration text")

    audio_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "audio")
    os.makedirs(audio_dir, exist_ok=True)
    audio_path = os.path.join(audio_dir, f"narration_{spot_id}.mp3")

    need_regenerate = True
    if os.path.exists(audio_path):
        age_hours = (datetime.utcnow().timestamp() - os.path.getmtime(audio_path)) / 3600
        if age_hours < 24:
            need_regenerate = False

    if need_regenerate:
        try:
            audio_bytes = await text_to_speech(text)
            if audio_bytes:
                tmp_path = audio_path + ".tmp"
                with open(tmp_path, "wb") as f:
                    f.write(audio_bytes)
                try:
                    import subprocess
                    subprocess.run([
                        "ffmpeg", "-y", "-i", tmp_path,
                        "-acodec", "mp3", "-ar", "44100", "-ab", "128k", "-ac", "1",
                        audio_path
                    ], capture_output=True, timeout=60)
                    os.unlink(tmp_path)
                except Exception:
                    os.rename(tmp_path, audio_path)
        except Exception as e:
            print(f"[Narration] TTS failed for {spot_id}: {e}")

    audio_url = ""
    duration_sec = 0
    if os.path.exists(audio_path):
        audio_url = f"/static/audio/narration_{spot_id}.mp3"
        duration_sec = max(5, len(text) // 3)

    spot.narration_audio_url = audio_url
    spot.narration_duration = duration_sec
    db.commit()

    return JSONResponse({
        "code": 0,
        "message": "success",
        "data": {
            "spot_id": spot_id,
            "audio_url": audio_url,
            "duration_sec": duration_sec,
            "text": text,
            "cached": not need_regenerate
        }
    })
