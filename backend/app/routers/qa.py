from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import QASession, QAMessage, ScenicSpot
from app.utils.auth import get_optional_user
from app.models.schemas import (
    APIResponse,
    QAAskResponse,
    QASessionDetail,
    QAMessageItem,
    QAFeedbackRequest,
)
from app.services.qa_service import process_question
from app.services.llm_client import chat as llm_chat
from datetime import timedelta as _td

def _bj_time(dt):
    if dt is None: return ""
    return (dt + _td(hours=8)).strftime("%Y-%m-%d %H:%M:%S")

router = APIRouter()


@router.post("/qa/ask", response_model=APIResponse)
async def ask_question(
    audio: UploadFile = File(...),
    text: str = Form(None),
    lat: float = Form(None),
    lng: float = Form(None),
    session_id: str = Form(None),
    token: str = Form(""),
    db: Session = Depends(get_db),
    user: dict = Depends(get_optional_user),
):
    import time as _time
    _t0 = _time.time()
    try:
        # Support token from formData (wx.uploadFile) or Authorization header
        uid = "anonymous"
        if user:
            uid = user.get("sub", "anonymous")
        elif token:
            from app.utils.auth import verify_access_token
            payload = verify_access_token(token)
            if payload:
                uid = payload.get("sub", "anonymous")

        audio_bytes = await audio.read()
        print(f"[QA] audio_size={len(audio_bytes)} uid={uid} lat={lat} lng={lng} text_provided={bool(text and text.strip())}")

        # If text is provided directly, skip ASR
        if text and text.strip():
            result = await process_question(
                audio_bytes=audio_bytes,
                db=db,
                lat=lat,
                lng=lng,
                session_id=session_id,
                user_id=uid,
                text_override=text.strip(),
            )
            print(f"[QA] text_qa done in {_time.time()-_t0:.1f}s, answer_len={len(result['answer_text'])}")
            return APIResponse(
                data=QAAskResponse(
                    session_id=result["session_id"],
                    question_text=result["question_text"],
                    answer_text=result["answer_text"],
                    answer_audio_base64=result.get("answer_audio_base64",""),
                    answer_audio_url=result["answer_audio_url"],
                    duration_sec=result["duration_sec"],
                    related_spots=result["related_spots"],
                ).model_dump()
            )

        if len(audio_bytes) < 200:
            print(f"[QA] audio too short ({len(audio_bytes)} bytes), returning prompt")
            return APIResponse(
                data=QAAskResponse(
                    session_id=session_id or "",
                    question_text="",
                    answer_text="请按住按钮说话，我可以为您解答任何关于灵山胜境的问题。",
                    answer_audio_url="",
                    duration_sec=0,
                    related_spots=[],
                ).model_dump()
            )

        result = await process_question(
            audio_bytes=audio_bytes,
            db=db,
            lat=lat,
            lng=lng,
            session_id=session_id,
            user_id=uid,
        )
        print(f"[QA] audio_qa done in {_time.time()-_t0:.1f}s, answer_len={len(result['answer_text'])}")

        return APIResponse(
            data=QAAskResponse(
                session_id=result["session_id"],
                question_text=result["question_text"],
                answer_text=result["answer_text"],
                answer_audio_base64=result.get("answer_audio_base64",""),
                answer_audio_url=result["answer_audio_url"],
                duration_sec=result["duration_sec"],
                related_spots=result["related_spots"],
            ).model_dump()
        )

    except Exception as e:
        import traceback
        elapsed = _time.time() - _t0
        print(f"[QA] CRASH after {elapsed:.1f}s: {e}")
        traceback.print_exc()
        return APIResponse(
            code=0,  # 返回 code=0 让前端成功解析，错误信息放在 answer_text 中
            data=QAAskResponse(
                session_id=session_id or "",
                question_text="",
                answer_text="抱歉，服务暂时繁忙，请稍后再试~",
                answer_audio_url="",
                duration_sec=0,
                related_spots=[],
            ).model_dump()
        )


@router.get("/qa/sessions/{session_id}", response_model=APIResponse)
def get_qa_session(session_id: str, db: Session = Depends(get_db)):
    session = db.query(QASession).filter(QASession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    spot_name = None
    if session.spot_id:
        spot = db.query(ScenicSpot).filter(ScenicSpot.id == session.spot_id).first()
        if spot:
            spot_name = spot.name

    messages = []
    for msg in session.messages:
        messages.append(
            QAMessageItem(
                role=msg.role,
                text=msg.question_text if msg.role == "user" else msg.answer_text,
                audio_url=msg.question_audio_url if msg.role == "user" else msg.answer_audio_url,
                created_at=_bj_time(msg.created_at),
            )
        )

    return APIResponse(
        data=QASessionDetail(session_id=session.id, messages=messages, spot_name=spot_name).model_dump()
    )


@router.post("/qa/feedback", response_model=APIResponse)
def submit_feedback(req: QAFeedbackRequest, message_id: int = 0, db: Session = Depends(get_db)):
    if message_id:
        msg = db.query(QAMessage).filter(QAMessage.id == message_id).first()
        if msg:
            msg.feedback = req.feedback
            db.commit()
    return APIResponse(message="感谢反馈")
