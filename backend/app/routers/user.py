import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.config import settings
from app.database import get_db
from app.models import User, Checkin, QASession, QAMessage, ScenicSpot, EmailVerificationCode
from app.models.schemas import (
    APIResponse,
    UserProfile,
    UserUpdateRequest,
    UserHistory,
    CheckinRecord,
    QASessionSummary,
    EmailSendCodeRequest,
    EmailLoginRequest,
    EmailLoginResponse,
    RegisterRequest,
    UsernameLoginRequest,
)
from app.utils.auth import create_access_token, get_current_user, get_optional_user, hash_password, verify_password
from app.services.email_client import generate_code, send_verification_email
from datetime import timedelta as _td

def _bj_time(dt):
    """Convert UTC timestamp to Beijing time string (UTC+8)."""
    if dt is None:
        return ""
    bj = dt + _td(hours=8)
    return bj.strftime("%Y-%m-%d %H:%M:%S")

# avatars 存储目录（与 main.py 中 StaticFiles mount 路径一致）
# user.py 在 backend/app/routers/，需 4 层到项目根
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
AVATARS_DIR = os.path.join(BASE_DIR, "backend", "static", "avatars")

router = APIRouter()

# ---------- Register ----------

@router.post("/user/register", response_model=APIResponse)
async def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """邮箱注册账号。

    - 验证邮箱验证码
    - 校验用户名格式（3-20位字母数字下划线）
    - 校验密码强度（至少6位）
    - 创建用户，返回 token
    """
    email = req.email.strip().lower()
    code = req.code.strip()
    username = req.username.strip()
    password = req.password

    # 参数校验
    if not re.match(r"^[一-龥a-zA-Z0-9_]{2,20}$", username):
        raise HTTPException(status_code=400, detail="用户名需2-20位，支持中文/字母/数字/下划线")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="密码至少6位")

    # 验证邮箱验证码
    now = datetime.now(timezone.utc)
    vc = (
        db.query(EmailVerificationCode)
        .filter(
            EmailVerificationCode.email == email,
            EmailVerificationCode.code == code,
            EmailVerificationCode.is_used == 0,
            EmailVerificationCode.expires_at > now,
        )
        .first()
    )
    if not vc:
        raise HTTPException(status_code=400, detail="验证码错误或已过期")

    # 检查邮箱/用户名是否已被注册
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="该邮箱已被注册")
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="该用户名已被使用")

    # 标记验证码已使用
    vc.is_used = 1

    # 创建用户
    placeholder_openid = f"em_{uuid.uuid4().hex[:16]}"
    user = User(
        email=email,
        username=username,
        password_hash=hash_password(password),
        nickname=username,  # 默认昵称 = 用户名
        wx_openid=placeholder_openid,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # 签发 token
    token = create_access_token(user_id=user.id, email=email, username=username)

    return APIResponse(
        data=EmailLoginResponse(
            token=token,
            is_new_user=True,
            user=UserProfile(
                id=user.id,
                nickname=user.nickname,
                avatar_url=user.avatar_url or "",
                email=user.email,
                username=user.username,
            ),
        ).model_dump()
    )


# ---------- Username + Password Login ----------

@router.post("/user/username-login", response_model=APIResponse)
async def username_login(req: UsernameLoginRequest, db: Session = Depends(get_db)):
    """用户名 + 密码登录"""
    username = req.username.strip()
    password = req.password

    if not username or not password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")

    user = db.query(User).filter(User.username == username).first()
    if not user or not user.password_hash:
        raise HTTPException(status_code=400, detail="用户名或密码错误")

    if not verify_password(password, user.password_hash):
        raise HTTPException(status_code=400, detail="用户名或密码错误")

    # 更新登录时间
    user.last_login_at = func.now()
    db.commit()

    token = create_access_token(user_id=user.id, email=user.email or "", username=username)

    return APIResponse(
        data=EmailLoginResponse(
            token=token,
            is_new_user=False,
            user=UserProfile(
                id=user.id,
                nickname=user.nickname,
                avatar_url=user.avatar_url or "",
                email=user.email,
                username=user.username,
            ),
        ).model_dump()
    )


# ---------- Email Login ----------

@router.post("/user/send-code", response_model=APIResponse)
async def send_verification_code(req: EmailSendCodeRequest, db: Session = Depends(get_db)):
    """发送邮箱验证码。

    - 60 秒内同一邮箱不可重复发送
    - 验证码 10 分钟有效
    - 每日每邮箱最多 10 次
    """
    email = req.email.strip().lower()

    # 简单邮箱格式校验
    if "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(status_code=400, detail="邮箱格式不正确")

    # 60 秒发送冷却
    one_minute_ago = datetime.now(timezone.utc) - timedelta(seconds=60)
    recent = (
        db.query(EmailVerificationCode)
        .filter(
            EmailVerificationCode.email == email,
            EmailVerificationCode.created_at > one_minute_ago,
        )
        .first()
    )
    if recent:
        wait_sec = 60 - int((datetime.now(timezone.utc) - recent.created_at.replace(tzinfo=timezone.utc)).total_seconds())
        raise HTTPException(status_code=429, detail=f"发送过于频繁，请 {max(1, wait_sec)} 秒后再试")

    # 每日发送次数限制
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_count = (
        db.query(EmailVerificationCode)
        .filter(
            EmailVerificationCode.email == email,
            EmailVerificationCode.created_at >= today_start,
        )
        .count()
    )
    if today_count >= 10:
        raise HTTPException(status_code=429, detail="今日发送次数已达上限，请明日再试")

    # 生成验证码
    code = generate_code()

    # 保存到数据库
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    vc = EmailVerificationCode(email=email, code=code, expires_at=expires_at)
    db.add(vc)
    db.commit()

    # 发送邮件
    success, msg = send_verification_email(email, code)
    if not success:
        raise HTTPException(status_code=500, detail=msg)

    return APIResponse(data={"message": msg, "expires_in": 600})


@router.post("/user/email-login", response_model=APIResponse)
async def email_login(req: EmailLoginRequest, db: Session = Depends(get_db)):
    """邮箱验证码登录。

    - 验证码正确 → 查找/创建用户 → 返回 JWT token
    - 新用户自动创建账户，nickname 取 @ 前部分
    """
    email = req.email.strip().lower()
    code = req.code.strip()

    if not email or not code:
        raise HTTPException(status_code=400, detail="邮箱和验证码不能为空")

    # 查找最新有效验证码
    now = datetime.now(timezone.utc)
    vc = (
        db.query(EmailVerificationCode)
        .filter(
            EmailVerificationCode.email == email,
            EmailVerificationCode.code == code,
            EmailVerificationCode.is_used == 0,
            EmailVerificationCode.expires_at > now,
        )
        .order_by(EmailVerificationCode.created_at.desc())
        .first()
    )

    if not vc:
        # 再查一下是不是验证码错误（区别于过期）
        wrong_code = (
            db.query(EmailVerificationCode)
            .filter(
                EmailVerificationCode.email == email,
                EmailVerificationCode.is_used == 0,
                EmailVerificationCode.expires_at > now,
            )
            .first()
        )
        if wrong_code:
            raise HTTPException(status_code=400, detail="验证码错误，请重新输入")
        else:
            raise HTTPException(status_code=400, detail="验证码已过期或不存在，请重新获取")

    # 标记验证码已使用
    vc.is_used = 1
    db.commit()

    # 查找或创建用户
    user = db.query(User).filter(User.email == email).first()
    is_new = False

    if not user:
        # 新用户注册
        nickname = req.nickname or email.split("@")[0]
        # 确保昵称唯一（如果已有用户占用）
        existing_nick = db.query(User).filter(User.nickname == nickname).first()
        if existing_nick:
            nickname = f"{nickname}_{email[-4:]}"
        # 邮箱用户生成唯一 wx_openid 占位（兼容旧表 NOT NULL + UNIQUE 约束）
        placeholder_openid = f"em_{uuid.uuid4().hex[:16]}"
        user = User(
            email=email,
            nickname=nickname,
            wx_openid=placeholder_openid,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        is_new = True
    else:
        # 更新登录时间
        user.last_login_at = func.now()
        if req.nickname:
            user.nickname = req.nickname
        db.commit()

    # 签发 JWT
    token = create_access_token(user_id=user.id, email=email, username=user.username or "")

    return APIResponse(
        data=EmailLoginResponse(
            token=token,
            is_new_user=is_new,
            user=UserProfile(
                id=user.id,
                nickname=user.nickname,
                avatar_url=user.avatar_url or "",
                email=user.email,
                username=user.username,
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

    # 限制文件大小（10MB）
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="图片大小不能超过 10MB")

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
            email=u.email,
            username=u.username,
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
            email=u.email,
            username=u.username,
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
                    spot_id=c.spot_id, spot_name=name, trigger_type=c.trigger_type, created_at=_bj_time(c.created_at)
                )
                for c, name in checkins
            ],
            qa_sessions=[
                QASessionSummary(
                    session_id=s.id, spot_name=name, message_count=msg_count, created_at=_bj_time(s.created_at)
                )
                for s, name, msg_count in qa_sessions
            ],
        ).model_dump()
    )
