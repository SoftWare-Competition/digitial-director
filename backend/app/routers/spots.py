import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ScenicSpot, Route, RouteSpot
from app.models.schemas import (
    APIResponse,
    SpotBasic,
    SpotLocation,
    SpotListResponse,
    SpotDetail,
    RouteBasic,
    RouteListResponse,
    RouteSpotItem,
    RouteDetail,
)

router = APIRouter()


def _spot_to_basic(spot: ScenicSpot) -> SpotBasic:
    return SpotBasic(
        id=spot.id,
        name=spot.name,
        category=spot.category,
        location=SpotLocation(lat=spot.lat, lng=spot.lng),
        geofence_radius=spot.geofence_radius,
        thumbnail=_first_image(spot.images),
        narration_duration_sec=spot.narration_duration,
        audio_url=spot.narration_audio_url,
    )


def _spot_to_detail(spot: ScenicSpot) -> SpotDetail:
    return SpotDetail(
        id=spot.id,
        name=spot.name,
        scenic_area=spot.scenic_area,
        category=spot.category,
        location=SpotLocation(lat=spot.lat, lng=spot.lng),
        geofence_radius=spot.geofence_radius,
        scale=spot.scale,
        function=spot.function_desc,
        cultural_meaning=spot.cultural_meaning,
        detailed_description=spot.detailed_description,
        photo_spots=spot.photo_spots,
        visitor_info=spot.visitor_info,
        images=_parse_images(spot.images),
        narration_audio_url=spot.narration_audio_url,
        narration_text=spot.narration_text,
        narration_duration=spot.narration_duration,
        adjacent_spots=[],
    )


def _parse_images(images_str: str | None) -> list[str]:
    if not images_str:
        return []
    try:
        return json.loads(images_str)
    except (json.JSONDecodeError, TypeError):
        return []


def _first_image(images_str: str | None) -> str | None:
    imgs = _parse_images(images_str)
    return imgs[0] if imgs else None


@router.get("/spots", response_model=APIResponse)
def list_spots(db: Session = Depends(get_db)):
    spots = db.query(ScenicSpot).filter(ScenicSpot.is_active == 1).order_by(ScenicSpot.sort_order).all()
    return APIResponse(
        data=SpotListResponse(spots=[_spot_to_basic(s) for s in spots]).model_dump()
    )


@router.get("/spots/{spot_id}", response_model=APIResponse)
def get_spot(spot_id: str, db: Session = Depends(get_db)):
    spot = db.query(ScenicSpot).filter(ScenicSpot.id == spot_id, ScenicSpot.is_active == 1).first()
    if not spot:
        raise HTTPException(status_code=404, detail="景点不存在")

    # Find adjacent spots (same route)
    rs = (
        db.query(RouteSpot)
        .filter(RouteSpot.spot_id == spot_id)
        .first()
    )
    adjacent = []
    if rs:
        prev_spot = (
            db.query(RouteSpot)
            .filter(RouteSpot.route_id == rs.route_id, RouteSpot.sequence == rs.sequence - 1)
            .first()
        )
        next_spot = (
            db.query(RouteSpot)
            .filter(RouteSpot.route_id == rs.route_id, RouteSpot.sequence == rs.sequence + 1)
            .first()
        )
        if prev_spot:
            adjacent.append(prev_spot.spot_id)
        if next_spot:
            adjacent.append(next_spot.spot_id)

    detail = _spot_to_detail(spot)
    detail.adjacent_spots = adjacent
    return APIResponse(data=detail.model_dump())


@router.get("/routes", response_model=APIResponse)
def list_routes(db: Session = Depends(get_db)):
    routes = db.query(Route).filter(Route.is_active == 1).all()
    result = []
    for r in routes:
        spot_count = len(r.route_spots)
        result.append(
            RouteBasic(
                id=r.id,
                name=r.name,
                type=r.type,
                duration_hours=r.duration_hours,
                description=r.description,
                spot_count=spot_count,
            )
        )
    return APIResponse(data=RouteListResponse(routes=result).model_dump())


@router.get("/routes/{route_id}", response_model=APIResponse)
def get_route(route_id: str, db: Session = Depends(get_db)):
    route = db.query(Route).filter(Route.id == route_id, Route.is_active == 1).first()
    if not route:
        raise HTTPException(status_code=404, detail="路线不存在")

    spots = []
    for rs in route.route_spots:
        spot = rs.spot
        location = SpotLocation(lat=spot.lat, lng=spot.lng) if spot else None
        spots.append(
            RouteSpotItem(
                id=rs.spot_id,
                name=spot.name if spot else "",
                sequence=rs.sequence,
                location=location,
                description=rs.description,
            )
        )

    detail = RouteDetail(
        id=route.id,
        name=route.name,
        type=route.type,
        duration_hours=route.duration_hours,
        description=route.description,
        overview_text=route.overview_text,
        overview_audio_url=route.overview_audio_url,
        spots=spots,
    )
    return APIResponse(data=detail.model_dump())
