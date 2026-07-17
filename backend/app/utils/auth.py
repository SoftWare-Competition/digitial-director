"""JWT authentication utilities."""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, Request
from jose import JWTError, jwt

from app.config import settings

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 72  # 3 days


def hash_password(password: str) -> str:
    """PBKDF2-SHA256 密码哈希，返回格式: salt$hash"""
    salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
    return f"{salt}${h.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """验证密码"""
    try:
        salt, h = stored.split("$", 1)
        computed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
        return secrets.compare_digest(computed.hex(), h)
    except Exception:
        return False


def create_access_token(user_id: str, openid: str = "", email: str = "", username: str = "") -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {
        "sub": user_id,
        "openid": openid,
        "email": email,
        "username": username,
        "iat": datetime.now(timezone.utc),
        "exp": expire,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def verify_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except JWTError:
        return None


def get_current_user(request: Request) -> dict:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未提供认证令牌")
    token = auth_header[len("Bearer "):]
    payload = verify_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="认证令牌无效或已过期")
    return payload


def get_optional_user(request: Request) -> Optional[dict]:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header[len("Bearer "):]
    return verify_access_token(token)
