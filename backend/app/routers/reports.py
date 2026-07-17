import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.models import InterviewSession
from app.schemas import QAPair, ReportOut
from app.services import interview_service
from app.services.interview_service import ServiceError

router = APIRouter(prefix="/api/interviews", tags=["reports"])


@router.get("/{session_id}/report", response_model=ReportOut)
def get_report(session_id: str, db: DBSession = Depends(get_db)):
    try:
        report = interview_service.get_or_create_report(db, session_id)
    except ServiceError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    session = db.get(InterviewSession, session_id)
    transcript = [
        QAPair(
            order_index=q.order_index,
            topic=q.topic,
            difficulty=q.difficulty,
            question_text=q.question_text,
            answer_text=q.answer.answer_text if q.answer else None,
            quality_score=q.answer.quality_score if q.answer else None,
        )
        for q in session.questions
    ]

    return ReportOut(
        session_id=session.id,
        role=session.role,
        summary_text=report.summary_text,
        strengths=json.loads(report.strengths),
        gaps=json.loads(report.gaps),
        topic_coverage=json.loads(report.topic_coverage),
        overall_score=report.overall_score,
        recommendation=report.recommendation,
        transcript=transcript,
    )
