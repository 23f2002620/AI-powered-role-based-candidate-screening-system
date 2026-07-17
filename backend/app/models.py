"""
Persistence models.

Design notes:
- Candidate holds parsed resume data (skills / technologies / domain exposure)
  as JSON so the extraction schema can evolve without migrations.
- InterviewSession is the aggregate root for one screening run; Question and
  Answer are 1:1 (a question is created, then answered), which keeps the
  Context -> Question -> Answer -> Storage trace explicit and queryable.
- Every Question stores the retrieved context and source chunk ids it was
  generated from, so the system is traceable/auditable end to end.
"""
import datetime as dt
import uuid

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    target_role = Column(String, nullable=False)
    resume_raw_text = Column(Text, nullable=False)
    extracted_skills = Column(Text, nullable=False, default="[]")        # JSON list
    extracted_technologies = Column(Text, nullable=False, default="[]")  # JSON list
    domain_exposure = Column(Text, nullable=False, default="[]")        # JSON list
    seniority_signal = Column(String, nullable=True)  # junior/mid/senior heuristic
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    sessions = relationship("InterviewSession", back_populates="candidate")


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id = Column(String, primary_key=True, default=_uuid)
    candidate_id = Column(String, ForeignKey("candidates.id"), nullable=False)
    role = Column(String, nullable=False)
    status = Column(String, nullable=False, default="in_progress")  # in_progress|completed
    current_question_index = Column(Integer, default=0)
    created_at = Column(DateTime, default=dt.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    candidate = relationship("Candidate", back_populates="sessions")
    questions = relationship("Question", back_populates="session", order_by="Question.order_index")
    report = relationship("Report", back_populates="session", uselist=False)


class Question(Base):
    __tablename__ = "questions"

    id = Column(String, primary_key=True, default=_uuid)
    session_id = Column(String, ForeignKey("interview_sessions.id"), nullable=False)
    order_index = Column(Integer, nullable=False)
    topic = Column(String, nullable=False)
    difficulty = Column(String, nullable=False, default="medium")  # easy|medium|hard
    question_text = Column(Text, nullable=False)
    retrieved_context = Column(Text, nullable=False, default="")     # concatenated chunk text used
    source_chunk_ids = Column(Text, nullable=False, default="[]")    # JSON list, for traceability
    generation_query = Column(Text, nullable=False, default="")      # the query used for retrieval
    generation_method = Column(String, nullable=False, default="llm")  # llm|template_fallback
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    session = relationship("InterviewSession", back_populates="questions")
    answer = relationship("Answer", back_populates="question", uselist=False)


class Answer(Base):
    __tablename__ = "answers"

    id = Column(String, primary_key=True, default=_uuid)
    question_id = Column(String, ForeignKey("questions.id"), nullable=False, unique=True)
    answer_text = Column(Text, nullable=False)
    quality_score = Column(Float, nullable=True)      # 0-5 heuristic/LLM assessed
    quality_notes = Column(Text, nullable=True)        # brief rationale, drives adaptation
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    question = relationship("Question", back_populates="answer")


class Report(Base):
    __tablename__ = "reports"

    id = Column(String, primary_key=True, default=_uuid)
    session_id = Column(String, ForeignKey("interview_sessions.id"), nullable=False, unique=True)
    summary_text = Column(Text, nullable=False)
    strengths = Column(Text, nullable=False, default="[]")     # JSON list
    gaps = Column(Text, nullable=False, default="[]")          # JSON list
    topic_coverage = Column(Text, nullable=False, default="{}")  # JSON dict topic -> avg score
    overall_score = Column(Float, nullable=True)
    recommendation = Column(String, nullable=True)  # strong_yes/yes/borderline/no
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    session = relationship("InterviewSession", back_populates="report")
