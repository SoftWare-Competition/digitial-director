from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import User, Checkin, QASession, QAMessage, ScenicSpot
from app.models.schemas import (
    APIResponse,
    UserLoginRequest,
    UserLoginResponse,
    UserProfile,
    UserHistory,
    CheckinRecord,
    QASessionSummary,
)

router = APIRouter()


@router.post("/user/login", response_model=APIResponse)
def user_login(req: UserLoginRequest, db: Session = Depends(get_db)):
    # MVP: simplified login — accept any code as guest id
    # In production, exchange wx.login code for openid via WeChat API
    openid = f"wx_{req.code}" if req.code else f"guest_{__import__('uuid').uuid4().hex[:8]}"

    user = db.query(User).filter(User.wx_openid == openid).first()
    is_new = False
    if not user:
        user = User(wx_openid=openid, nickname=f"游客{openid[-4:]}")
        db.add(user)
        db.commit()
        db.refresh(user)
        is_new = True
    else:
        user.last_login_at = func.now()
        db.commit()

    token = f"token_{user.id}_{__import__('secrets').token_hex(8)}"

    return APIResponse(
        data=UserLoginResponse(
            token=token,
            is_new_user=is_new,
            user=UserProfile(id=user.id, nickname=user.nickname, avatar_url=user.avatar_url),
        ).model_dump()
    )


@router.get("/user/profile", response_model=APIResponse)
def user_profile(token: str = "", db: Session = Depends(get_db)):
    user_id = _extract_user_id(token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        user = User(id=user_id, wx_openid=f"wx_{user_id}", nickname=f"游客_{user_id[:4]}")
        db.add(user)
        db.commit()
    return APIResponse(
        data=UserProfile(id=user.id, nickname=user.nickname, avatar_url=user.avatar_url).model_dump()
    )


@router.get("/user/history", response_model=APIResponse)
def user_history(token: str = "", db: Session = Depends(get_db)):
    user_id = _extract_user_id(token)

    checkins = (
        db.query(Checkin, ScenicSpot.name)
        .join(ScenicSpot, Checkin.spot_id == ScenicSpot.id)
        .filter(Checkin.user_id == user_id)
        .order_by(Checkin.created_at.desc())
        .limit(50)
        .all()
    )

    qa_sessions = (
        db.query(QASession, ScenicSpot.name, func.count(QAMessage.id).label("msg_count"))
        .outerjoin(ScenicSpot, QASession.spot_id == ScenicSpot.id)
        .outerjoin(QAMessage, QASession.id == QAMessage.session_id)
        .filter(QASession.user_id == user_id)
        .group_by(QASession.id)
        .order_by(QASession.created_at.desc())
        .limit(20)
        .all()
    )

    return APIResponse(
        data=UserHistory(
            checkins=[
                CheckinRecord(
                    spot_id=c.spot_id, spot_name=name, trigger_type=c.trigger_type, created_at=str(c.created_at)
                )
                for c, name in checkins
            ],
            qa_sessions=[
                QASessionSummary(
                    session_id=s.id, spot_name=name, message_count=msg_count, created_at=str(s.created_at)
                )
                for s, name, msg_count in qa_sessions
            ],
        ).model_dump()
    )


def _extract_user_id(token: str) -> str | None:
    """Extract user ID from simple token, or create anonymous user."""
    if not token:
        return "anonymous"
    if token.startswith("token_"):
        parts = token.split("_")
        if len(parts) >= 2:
            return parts[1]
    # For any non-empty token, treat as valid for MVP
    return "anonymous"
