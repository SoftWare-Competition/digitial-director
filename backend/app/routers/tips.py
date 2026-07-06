from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.schemas import APIResponse, TipsResponse, SmartTip
from app.services.tips_service import evaluate_tips

router = APIRouter()


@router.get("/tips/current", response_model=APIResponse)
def get_current_tips(
    lat: float = Query(None),
    lng: float = Query(None),
    db: Session = Depends(get_db),
):
    tips_data = evaluate_tips(lat=lat, lng=lng)
    tips = [SmartTip(**t) for t in tips_data]

    # Add time-based tip if close to closing
    from datetime import datetime
    now = datetime.now()
    hour = now.hour

    time_tips = []
    if hour >= 16:
        time_tips.append(
            SmartTip(
                type="time",
                priority="medium",
                icon="clock",
                title="时间提醒",
                text="距离景区闭园还有一段时间，建议合理规划剩余游览路线。",
            )
        )

    # Merge and sort by priority
    all_tips = tips + time_tips
    all_tips.sort(key=lambda t: {"high": 0, "medium": 1, "low": 2}.get(t.priority, 5))
    all_tips = all_tips[:3]

    return APIResponse(data=TipsResponse(tips=all_tips).model_dump())
