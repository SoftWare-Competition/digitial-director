from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import QASession, QAMessage, ScenicSpot
from app.models.schemas import (
    APIResponse,
    QAAskResponse,
    QASessionDetail,
    QAMessageItem,
    QAFeedbackRequest,
)
from app.services.qa_service import process_question
from app.services.llm_client import chat as llm_chat

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
):
    audio_bytes = await audio.read()

    # If text is provided directly, skip ASR
    if text and text.strip():
        import asyncio
        result = await process_question(
            audio_bytes=audio_bytes,
            db=db,
            lat=lat,
            lng=lng,
            session_id=session_id,
            user_id="anonymous",
            text_override=text.strip(),
        )
        return APIResponse(
            data=QAAskResponse(
                session_id=result["session_id"],
                question_text=result["question_text"],
                answer_text=result["answer_text"],
                answer_audio_base64=result.get("answer_audio_base64","")
                answer_audio_url=result["answer_audio_url"],
                duration_sec=result["duration_sec"],
                related_spots=result["related_spots"],
            ).model_dump()
        )

    if len(audio_bytes) < 200:
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
        user_id="anonymous",
    )

    return APIResponse(
        data=QAAskResponse(
            session_id=result["session_id"],
            question_text=result["question_text"],
            answer_text=result["answer_text"],
            answer_audio_base64=result.get("answer_audio_base64","")
                answer_audio_url=result["answer_audio_url"],
            duration_sec=result["duration_sec"],
            related_spots=result["related_spots"],
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
                created_at=str(msg.created_at),
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
