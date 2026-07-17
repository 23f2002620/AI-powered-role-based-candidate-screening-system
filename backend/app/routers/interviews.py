from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from app.config import get_settings
from app.database import get_db
from app.models import InterviewSession
from app.schemas import (
    QuestionOut, SessionOut, StartInterviewRequest, SubmitAnswerRequest, SubmitAnswerResponse,
)
from app.services import interview_service
from app.services.interview_service import ServiceError

router = APIRouter(prefix="/api/interviews", tags=["interviews"])
settings = get_settings()


def _session_to_out(session: InterviewSession) -> SessionOut:
    return SessionOut(
        id=session.id,
        role=session.role,
        status=session.status,
        current_question_index=session.current_question_index,
        total_questions_planned=settings.max_questions_per_session,
        questions=[QuestionOut.model_validate(q) for q in session.questions],
    )


@router.post("/start", response_model=SessionOut)
def start_interview(payload: StartInterviewRequest, db: DBSession = Depends(get_db)):
    try:
        session = interview_service.start_session(db, payload.candidate_id)
    except ServiceError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _session_to_out(session)


@router.get("/{session_id}", response_model=SessionOut)
def get_interview(session_id: str, db: DBSession = Depends(get_db)):
    session = db.get(InterviewSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return _session_to_out(session)


@router.post("/{session_id}/answer", response_model=SubmitAnswerResponse)
def submit_answer(session_id: str, payload: SubmitAnswerRequest, db: DBSession = Depends(get_db)):
    session_check = db.get(InterviewSession, session_id)
    if session_check is None:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        session, next_question = interview_service.submit_answer(
            db, payload.question_id, payload.answer_text
        )
    except ServiceError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return SubmitAnswerResponse(
        accepted=True,
        session_status=session.status,
        next_question=QuestionOut.model_validate(next_question) if next_question else None,
    )
