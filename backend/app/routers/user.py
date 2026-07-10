import os
import uuid
import httpx
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.config import settings
from app.database import get_db
from app.models import User, Checkin, QASession, QAMessage, ScenicSpot
from app.models.schemas import (
    APIResponse,
    WxLoginRequest,
    WxLoginResponse,
    UserProfile,
    UserUpdateRequest,
    UserHistory,
    CheckinRecord,
    QASessionSummary,
)
from app.utils.auth import create_access_token, get_current_user, get_optional_user
from app.services.wechat_client import wechat_code_to_session, exchange_phone_number

# avatars 存储目录（与 main.py 中 StaticFiles mount 路径一致）
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AVATARS_DIR = os.path.join(BASE_DIR, "backend", "static", "avatars")

router = APIRouter()

# ---------- Login / Register ----------

@router.post("/user/login", response_model=APIResponse)
async def wx_login(req: WxLoginRequest, db: Session = Depends(get_db)):
    """WeChat mini-program login.

    Flow:
    1. Mini-program: wx.login() -> code
    2. Mini-program: POST /user/login {code, nickname?, avatar_url?, phone_code?}
    3. Backend: exchange code for openid via WeChat API
    4. Backend: exchange phone_code for real phone number (official getPhoneNumber)
    5. Backend: find or create user, issue JWT token
    6. Return JWT token -> mini-program stores in storage
    """
    # Step 1: Exchange code for openid (real WeChat API or dev mock)
    wx_data = await wechat_code_to_session(req.code)
    if not wx_data:
        # Dev fallback: if WeChat not configured, use code prefix as mock openid
        wx_data = {
            "openid": f"wx_dev_{req.code[:8]}",
            "session_key": "dev_session_key",
            "unionid": None,
        }

    openid = wx_data["openid"]
    unionid = wx_data.get("unionid")

    # Step 1.5: Exchange phone code for real phone number (official WeChat popup)
    phone = None
    if req.phone_code:
        try:
            phone = await exchange_phone_number(req.phone_code)
        except Exception as e:
            print(f"[Login] 手机号获取失败: {e}")

    # Step 2: Find or create user
    user = db.query(User).filter(User.wx_openid == openid).first()
    is_new = False

    if not user:
        # New user: register
        nickname = req.nickname or f"游客{openid[-6:]}"
        avatar_url = req.avatar_url or ""
        user = User(
            wx_openid=openid,
            wx_unionid=unionid,
            nickname=nickname,
            avatar_url=avatar_url,
            phone=phone,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        is_new = True
    else:
        # Existing user: update login time and optional unionid
        user.last_login_at = func.now()
        if unionid and not user.wx_unionid:
            user.wx_unionid = unionid
        # Update nickname/avatar if provided
        if req.nickname:
            user.nickname = req.nickname
        if req.avatar_url:
            user.avatar_url = req.avatar_url
        if phone and not user.phone:
            user.phone = phone
        db.commit()

    # Step 3: Issue JWT token
    token = create_access_token(user_id=user.id, openid=openid)

    return APIResponse(
        data=WxLoginResponse(
            token=token,
            is_new_user=is_new,
            user=UserProfile(
                id=user.id,
                nickname=user.nickname,
                avatar_url=user.avatar_url,
            ),
        ).model_dump()
    )


# ---------- Avatar Upload ----------

@router.post("/user/avatar", response_model=APIResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload user avatar image (requires auth).

    Returns: {"avatar_url": "/static/avatars/xxx.jpg"}
    """
    # 限制文件类型
    ext = os.path.splitext(file.filename or "avatar.jpg")[1].lower()
    if ext not in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
        raise HTTPException(status_code=400, detail="仅支持 JPG/PNG/GIF/WebP 格式")

    # 限制文件大小（2MB）
    content = await file.read()
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="图片大小不能超过 2MB")

    # 生成唯一文件名
    filename = f"avatar_{user['sub']}_{uuid.uuid4().hex[:8]}{ext}"
    filepath = os.path.join(AVATARS_DIR, filename)

    # 确保目录存在
    os.makedirs(AVATARS_DIR, exist_ok=True)

    # 写入文件
    with open(filepath, "wb") as f:
        f.write(content)

    # 更新用户头像 URL
    avatar_url = f"/static/avatars/{filename}"
    db_user = db.query(User).filter(User.id == user["sub"]).first()
    if db_user:
        db_user.avatar_url = avatar_url
        db.commit()

    return APIResponse(data={"avatar_url": avatar_url})


# ---------- Profile ----------

@router.get("/user/profile", response_model=APIResponse)
def get_profile(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get current user profile (requires auth)."""
    user_id = user["sub"]
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="用户不存在")

    return APIResponse(
        data=UserProfile(
            id=u.id,
            nickname=u.nickname,
            avatar_url=u.avatar_url,
        ).model_dump()
    )


@router.put("/user/profile", response_model=APIResponse)
def update_profile(
    req: UserUpdateRequest,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update current user's nickname or avatar (requires auth)."""
    user_id = user["sub"]
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="用户不存在")

    if req.nickname is not None:
        u.nickname = req.nickname
    if req.avatar_url is not None:
        u.avatar_url = req.avatar_url
    db.commit()

    return APIResponse(
        data=UserProfile(
            id=u.id,
            nickname=u.nickname,
            avatar_url=u.avatar_url,
        ).model_dump()
    )


# ---------- Check Token ----------

@router.post("/user/check-token", response_model=APIResponse)
def check_token(user: dict = Depends(get_current_user)):
    """Verify that a token is still valid (requires auth)."""
    return APIResponse(
        data={
            "valid": True,
            "user_id": user["sub"],
            "openid": user.get("openid", ""),
        }
    )


# ---------- History ----------

@router.get("/user/history", response_model=APIResponse)
def user_history(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get current user's check-in and Q&A history (requires auth)."""
    user_id = user["sub"]

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
