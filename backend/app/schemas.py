import datetime as dt
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


# ---------- Candidate / Resume ----------

class ExtractedResumeData(BaseModel):
    skills: List[str] = Field(default_factory=list)
    technologies: List[str] = Field(default_factory=list)
    domain_exposure: List[str] = Field(default_factory=list)
    seniority_signal: Optional[str] = None
    years_of_experience_estimate: Optional[float] = None


class CandidateOut(BaseModel):
    id: str
    name: Optional[str]
    email: Optional[str]
    target_role: str
    extracted: ExtractedResumeData
    created_at: dt.datetime

    class Config:
        from_attributes = True


# ---------- Interview lifecycle ----------

class StartInterviewRequest(BaseModel):
    candidate_id: str


class QuestionOut(BaseModel):
    id: str
    order_index: int
    topic: str
    difficulty: str
    question_text: str
    generation_method: str

    class Config:
        from_attributes = True


class SessionOut(BaseModel):
    id: str
    role: str
    status: str
    current_question_index: int
    total_questions_planned: int
    questions: List[QuestionOut]

    class Config:
        from_attributes = True


class SubmitAnswerRequest(BaseModel):
    question_id: str
    answer_text: str = Field(min_length=1)


class SubmitAnswerResponse(BaseModel):
    accepted: bool
    session_status: str
    next_question: Optional[QuestionOut] = None


# ---------- Reporting ----------

class QAPair(BaseModel):
    order_index: int
    topic: str
    difficulty: str
    question_text: str
    answer_text: Optional[str]
    quality_score: Optional[float]


class ReportOut(BaseModel):
    session_id: str
    role: str
    summary_text: str
    strengths: List[str]
    gaps: List[str]
    topic_coverage: Dict[str, float]
    overall_score: Optional[float]
    recommendation: Optional[str]
    transcript: List[QAPair]


class RoleInfo(BaseModel):
    id: str
    label: str
