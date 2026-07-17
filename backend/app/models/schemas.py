from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# --- Uniform response envelope ---
class APIResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: object | None = None


# --- User schemas ---
class UserLoginRequest(BaseModel):
    code: str


class WxLoginRequest(BaseModel):
    code: str
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None
    phone_code: Optional[str] = None


class WxLoginResponse(BaseModel):
    token: str
    is_new_user: bool
    user: "UserProfile"


class UserUpdateRequest(BaseModel):
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None


class UserProfile(BaseModel):
    id: str
    nickname: str
    avatar_url: str = ""
    email: str | None = None
    username: str | None = None


class UserLoginResponse(BaseModel):
    token: str
    is_new_user: bool
    user: UserProfile


# --- Email login schemas ---
class EmailSendCodeRequest(BaseModel):
    email: str


class EmailLoginRequest(BaseModel):
    email: str
    code: str
    nickname: Optional[str] = None


class EmailLoginResponse(BaseModel):
    token: str
    is_new_user: bool
    user: UserProfile


# --- Register / Password login schemas ---
class RegisterRequest(BaseModel):
    email: str
    code: str          # 邮箱验证码
    username: str
    password: str


class UsernameLoginRequest(BaseModel):
    username: str
    password: str


class UserHistory(BaseModel):
    checkins: list[CheckinRecord] = []
    qa_sessions: list[QASessionSummary] = []


class CheckinRecord(BaseModel):
    spot_id: str
    spot_name: str
    trigger_type: str
    created_at: str


class QASessionSummary(BaseModel):
    session_id: str
    spot_name: str | None = None
    message_count: int
    created_at: str


# --- Scenic spot schemas ---
class SpotLocation(BaseModel):
    lat: float
    lng: float


class SpotBasic(BaseModel):
    id: str
    name: str
    category: str | None = None
    location: SpotLocation
    geofence_radius: int = 30
    thumbnail: str | None = None
    narration_duration_sec: int | None = None
    audio_url: str | None = None


class SpotListResponse(BaseModel):
    spots: list[SpotBasic]


class SpotDetail(BaseModel):
    id: str
    name: str
    scenic_area: str = "灵山胜境"
    category: str | None = None
    location: SpotLocation
    geofence_radius: int = 30
    scale: str | None = None
    function_desc: str | None = Field(None, alias="function")
    cultural_meaning: str | None = None
    detailed_description: str | None = None
    photo_spots: str | None = None
    visitor_info: str | None = None
    images: list[str] = []
    narration_audio_url: str | None = None
    narration_text: str | None = None
    narration_duration: int | None = None
    adjacent_spots: list[str] = []


# --- Route schemas ---
class RouteBasic(BaseModel):
    id: str
    name: str
    type: str
    duration_hours: float
    description: str | None = None
    spot_count: int


class RouteListResponse(BaseModel):
    routes: list[RouteBasic]


class RouteSpotItem(BaseModel):
    id: str
    name: str
    sequence: int
    location: SpotLocation | None = None
    description: str | None = None


class RouteDetail(BaseModel):
    id: str
    name: str
    type: str
    duration_hours: float
    description: str | None = None
    overview_text: str | None = None
    overview_audio_url: str | None = None
    spots: list[RouteSpotItem]


# --- Narration schemas ---
class CheckinRequest(BaseModel):
    lat: float
    lng: float
    accuracy: float = 15.0
    timestamp: str | None = None


class SmartTip(BaseModel):
    type: str
    priority: str = "medium"
    icon: str | None = None
    title: str | None = None
    text: str
    action: object | None = None


class CheckinResponse(BaseModel):
    matched: bool
    spot: SpotBasic | None = None
    narration: NarrationInfo | None = None
    tips: list[SmartTip] = []


class NarrationInfo(BaseModel):
    audio_url: str
    text: str
    duration_sec: int
    is_repeat: bool = False


class ManualNarrationRequest(BaseModel):
    spot_id: str


# --- Q&A schemas ---
class QAAskResponse(BaseModel):
    session_id: str
    question_text: str
    answer_text: str
    answer_audio_base64: str = ""
    answer_audio_url: str
    duration_sec: int
    related_spots: list[str] = []


class QAMessageItem(BaseModel):
    role: str
    text: str | None = None
    audio_url: str | None = None
    created_at: str


class QASessionDetail(BaseModel):
    session_id: str
    messages: list[QAMessageItem]
    spot_name: str | None = None


class QAFeedbackRequest(BaseModel):
    feedback: str  # "thumbs_up" or "thumbs_down"


# --- Tips schemas ---
class TipsResponse(BaseModel):
    tips: list[SmartTip]
