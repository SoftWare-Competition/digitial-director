"""Q&A Pipeline: ASR -> LLM (with RAG) -> TTS."""
import json
import os
import uuid

from sqlalchemy.orm import Session

from app.models import ScenicSpot, QASession, QAMessage
from app.services.llm_client import chat as llm_chat
from app.services.speech_client import speech_to_text, text_to_speech


async def process_question(
    audio_bytes: bytes,
    db: Session,
    lat: float = None,
    lng: float = None,
    session_id: str = None,
    user_id: str = "anonymous",
    text_override: str = None,
) -> dict:
    """Full Q&A pipeline. Returns dict with question_text, answer_text, etc."""

    # Step 1: ASR (or use text override)
    if text_override:
        question_text = text_override
        confidence = 1.0
    else:
        question_text, confidence = await speech_to_text(audio_bytes)
        if confidence < 0.5:
            question_text = "[未能识别语音内容]"

    # Step 2: Find current spot context (RAG)
    spot_name = None
    spot_context = ""

    if lat and lng:
        from app.utils.geo import within_geofence

        spots = db.query(ScenicSpot).filter(ScenicSpot.is_active == 1).all()
        for spot in spots:
            matched, _ = within_geofence(lat, lng, spot.lat, spot.lng, spot.geofence_radius)
            if matched:
                spot_name = spot.name
                parts = []
                if spot.name:
                    parts.append(f"景点: {spot.name}")
                if spot.cultural_meaning:
                    parts.append(f"文化内涵: {spot.cultural_meaning[:200]}")
                if spot.detailed_description:
                    parts.append(f"详细介绍: {spot.detailed_description[:300]}")
                if spot.scale:
                    parts.append(f"规模: {spot.scale}")
                if spot.visitor_info:
                    parts.append(f"参观信息: {spot.visitor_info}")
                spot_context = "\n".join(parts)
                break

    # Step 3: Get or create session
    session = None
    if session_id:
        session = db.query(QASession).filter(QASession.id == session_id).first()

    if not session:
        session = QASession(
            user_id=user_id,
            spot_id=None,
            status="active",
        )
        db.add(session)
        db.commit()
        db.refresh(session)

    # Step 4: Get conversation history
    history = []
    if session_id:
        messages = (
            db.query(QAMessage)
            .filter(QAMessage.session_id == session.id)
            .order_by(QAMessage.created_at)
            .limit(10)
            .all()
        )
        for msg in messages:
            history.append({"role": msg.role, "text": msg.question_text or msg.answer_text})

    # Step 5: LLM with RAG context
    answer_text = await llm_chat(
        user_message=question_text,
        spot_context=spot_context,
        conversation_history=history,
    )

    # Step 6: TTS
    import base64
    audio_bytes_out = await text_to_speech(answer_text)
    audio_base64 = ""
    if audio_bytes_out:
        audio_base64 = base64.b64encode(audio_bytes_out).decode("ascii")

    # Save to DB
    user_msg = QAMessage(
        session_id=session.id,
        role="user",
        question_text=question_text,
        asr_confidence=confidence,
    )
    assistant_msg = QAMessage(
        session_id=session.id,
        role="assistant",
        answer_text=answer_text,
        llm_model="deepseek-chat",
        llm_tokens=len(answer_text),
    )
    db.add_all([user_msg, assistant_msg])
    db.commit()

    return {
        "session_id": session.id,
        "question_text": question_text,
        "answer_text": answer_text,
        "answer_audio_base64": audio_base64,
        "answer_audio_url": "",
        "duration_sec": len(answer_text) // 3,
        "related_spots": [],
    }
