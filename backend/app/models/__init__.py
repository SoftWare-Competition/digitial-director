import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, Float, Text, TIMESTAMP, ForeignKey, Index, func
from sqlalchemy.orm import relationship

from app.database import Base


def pk():
    return str(uuid.uuid4())[:12]


class User(Base):
    __tablename__ = "users"

    id = Column(String(20), primary_key=True, default=pk)
    wx_openid = Column(String(64), unique=True, nullable=False)
    wx_unionid = Column(String(64), nullable=True)
    nickname = Column(String(64), default="")
    avatar_url = Column(String(512), default="")
    phone = Column(String(20), nullable=True)
    created_at = Column(TIMESTAMP, default=func.now())
    last_login_at = Column(TIMESTAMP, default=func.now())



class ScenicSpot(Base):
    __tablename__ = "scenic_spots"

    id = Column(String(10), primary_key=True)
    scenic_area = Column(String(64), default="灵山胜境")
    name = Column(String(64), nullable=False)
    category = Column(String(32), nullable=True)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    geofence_radius = Column(Integer, default=30)
    scale = Column(String(256), nullable=True)
    function_desc = Column(Text, nullable=True)
    cultural_meaning = Column(Text, nullable=True)
    detailed_description = Column(Text, nullable=True)
    photo_spots = Column(Text, nullable=True)
    visitor_info = Column(Text, nullable=True)
    images = Column(Text, nullable=True)
    narration_text = Column(Text, nullable=True)
    narration_audio_url = Column(String(512), nullable=True)
    narration_duration = Column(Integer, nullable=True)
    sort_order = Column(Integer, default=0)
    is_active = Column(Integer, default=1)
    created_at = Column(TIMESTAMP, default=func.now())
    updated_at = Column(TIMESTAMP, default=func.now())

    route_spots = relationship("RouteSpot", back_populates="spot")


class Route(Base):
    __tablename__ = "routes"

    id = Column(String(10), primary_key=True)
    name = Column(String(128), nullable=False)
    type = Column(String(32), nullable=False)
    duration_hours = Column(Float, nullable=False)
    description = Column(Text, nullable=True)
    overview_text = Column(Text, nullable=True)
    overview_audio_url = Column(String(512), nullable=True)
    is_active = Column(Integer, default=1)
    created_at = Column(TIMESTAMP, default=func.now())

    route_spots = relationship("RouteSpot", back_populates="route", order_by="RouteSpot.sequence")


class RouteSpot(Base):
    __tablename__ = "route_spots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    route_id = Column(String(10), ForeignKey("routes.id"), nullable=False)
    spot_id = Column(String(10), ForeignKey("scenic_spots.id"), nullable=False)
    sequence = Column(Integer, nullable=False)
    description = Column(Text, nullable=True)

    route = relationship("Route", back_populates="route_spots")
    spot = relationship("ScenicSpot", back_populates="route_spots")

    __table_args__ = (Index("idx_route_spot", "route_id", "spot_id", unique=True),)


class Checkin(Base):
    __tablename__ = "checkins"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(20), default="anonymous")
    spot_id = Column(String(10), ForeignKey("scenic_spots.id"), nullable=False)
    route_id = Column(String(10), ForeignKey("routes.id"), nullable=True)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    trigger_type = Column(String(16), default="gps")
    narration_played = Column(Integer, default=0)
    created_at = Column(TIMESTAMP, default=func.now())

    __table_args__ = (
        Index("idx_checkins_user", "user_id", "created_at"),
        Index("idx_checkins_spot", "spot_id", "created_at"),
    )


class QASession(Base):
    __tablename__ = "qa_sessions"

    id = Column(String(20), primary_key=True, default=lambda: "qa_" + pk())
    user_id = Column(String(20), default="anonymous")
    spot_id = Column(String(10), ForeignKey("scenic_spots.id"), nullable=True)
    status = Column(String(16), default="active")
    created_at = Column(TIMESTAMP, default=func.now())
    updated_at = Column(TIMESTAMP, default=func.now())

    messages = relationship("QAMessage", back_populates="session", order_by="QAMessage.created_at")

    __table_args__ = (Index("idx_qa_sessions_user", "user_id", "created_at"),)


class QAMessage(Base):
    __tablename__ = "qa_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(20), ForeignKey("qa_sessions.id"), nullable=False)
    role = Column(String(16), nullable=False)
    question_text = Column(Text, nullable=True)
    question_audio_url = Column(String(512), nullable=True)
    answer_text = Column(Text, nullable=True)
    answer_audio_url = Column(String(512), nullable=True)
    asr_confidence = Column(Float, nullable=True)
    llm_model = Column(String(32), default="deepseek-chat")
    llm_tokens = Column(Integer, nullable=True)
    feedback = Column(String(16), nullable=True)
    created_at = Column(TIMESTAMP, default=func.now())

    session = relationship("QASession", back_populates="messages")

    __table_args__ = (Index("idx_qa_messages_session", "session_id", "created_at"),)


class TipsLog(Base):
    __tablename__ = "tips_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(20), default="anonymous")
    tip_type = Column(String(32), nullable=False)
    tip_text = Column(Text, nullable=False)
    priority = Column(String(16), default="medium")
    was_dismissed = Column(Integer, default=0)
    created_at = Column(TIMESTAMP, default=func.now())

    __table_args__ = (Index("idx_tips_log_user", "user_id", "created_at"),)


class WeatherCache(Base):
    __tablename__ = "weather_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    provider = Column(String(32), default="hefeng")
    raw_response = Column(Text, nullable=False)
    fetched_at = Column(TIMESTAMP, default=func.now())
    expires_at = Column(TIMESTAMP, nullable=False)
