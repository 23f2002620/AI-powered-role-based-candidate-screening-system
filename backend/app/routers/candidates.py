import json
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session as DBSession

from app.config import get_settings
from app.database import get_db
from app.schemas import CandidateOut, ExtractedResumeData, RoleInfo
from app.services import interview_service
from app.services.interview_service import ServiceError

router = APIRouter(prefix="/api", tags=["candidates"])
settings = get_settings()

ROLE_LABELS = {
    "backend_engineer": "Backend Engineer",
    "ai_ml_engineer": "AI/ML Engineer",
    "frontend_engineer": "Frontend Engineer",
}


@router.get("/roles", response_model=list[RoleInfo])
def list_roles():
    return [RoleInfo(id=r, label=ROLE_LABELS.get(r, r)) for r in settings.role_list]


@router.post("/candidates/upload-resume", response_model=CandidateOut)
async def upload_resume(
    target_role: str = Form(...),
    name: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: DBSession = Depends(get_db),
):
    allowed_ext = (".pdf", ".txt", ".md")
    if not file.filename.lower().endswith(allowed_ext):
        raise HTTPException(status_code=422, detail=f"Unsupported file type. Allowed: {allowed_ext}")

    content = await file.read()
    try:
        candidate = interview_service.ingest_resume(
            db, filename=file.filename, content=content, target_role=target_role, name=name, email=email
        )
    except ServiceError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return CandidateOut(
        id=candidate.id,
        name=candidate.name,
        email=candidate.email,
        target_role=candidate.target_role,
        extracted=ExtractedResumeData(
            skills=json.loads(candidate.extracted_skills),
            technologies=json.loads(candidate.extracted_technologies),
            domain_exposure=json.loads(candidate.domain_exposure),
            seniority_signal=candidate.seniority_signal,
        ),
        created_at=candidate.created_at,
    )
