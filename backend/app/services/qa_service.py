"""Q&A Pipeline: ASR -> LLM (with RAG) -> TTS."""
import asyncio
import json
import os
import time
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
    t0 = time.time()

    # Step 1: ASR (or use text override)
    if text_override:
        question_text = text_override
        confidence = 1.0
    else:
        try:
            question_text, confidence = await asyncio.wait_for(
                speech_to_text(audio_bytes), timeout=15.0
            )
        except asyncio.TimeoutError:
            print("[QA] ASR timed out after 15s")
            question_text = "[语音识别超时]"
            confidence = 0.0
        except Exception as e:
            print(f"[QA] ASR error: {e}")
            question_text = "[语音识别异常]"
            confidence = 0.0
        if confidence < 0.5:
            question_text = "[未能识别语音内容]"

    t1 = time.time()
    print(f"[QA] Step1 ASR: {t1-t0:.1f}s, text={question_text[:40]}")

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
    try:
        answer_text = await asyncio.wait_for(
            llm_chat(
                user_message=question_text,
                spot_context=spot_context,
                conversation_history=history,
            ),
            timeout=25.0,
        )
    except asyncio.TimeoutError:
        print("[QA] LLM timed out after 25s")
        answer_text = "小灵正在思考中，请稍后再试~"
    except Exception as e:
        print(f"[QA] LLM error: {e}")
        answer_text = "抱歉，小灵暂时开小差了，请再问一次吧~"

    t2 = time.time()
    print(f"[QA] Step5 LLM: {t2-t1:.1f}s, answer_len={len(answer_text)}")

    # Step 6: TTS
    import base64
    audio_base64 = ""
    try:
        audio_bytes_out = await asyncio.wait_for(
            text_to_speech(answer_text), timeout=20.0
        )
        if audio_bytes_out:
            audio_base64 = base64.b64encode(audio_bytes_out).decode("ascii")
    except asyncio.TimeoutError:
        print("[QA] TTS timed out after 20s, returning text only")
    except Exception as e:
        print(f"[QA] TTS error: {e}")

    t3 = time.time()
    print(f"[QA] Step6 TTS: {t3-t2:.1f}s, audio_base64_len={len(audio_base64)}")

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

    total = time.time() - t0
    print(f"[QA] TOTAL pipeline: {total:.1f}s")

    return {
        "session_id": session.id,
        "question_text": question_text,
        "answer_text": answer_text,
        "answer_audio_base64": audio_base64,
        "answer_audio_url": "",
        "duration_sec": len(answer_text) // 3,
        "related_spots": [],
    }
