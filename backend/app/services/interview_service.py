"""
Orchestration layer for the interview lifecycle: candidate creation, session
start, question generation, answer submission, and report finalization.

This module is the only place that touches both the DB (via SQLAlchemy
session) and the AI pipeline (rag_pipeline / question_generator / llm_client),
keeping routers thin (HTTP concerns only) and services (rag/llm) free of any
persistence concerns -- a standard layered-service separation.
"""
from __future__ import annotations

import datetime as dt
import json
from typing import List, Optional

from sqlalchemy.orm import Session as DBSession

from app.config import get_settings
from app.models import Answer, Candidate, InterviewSession, Question, Report
from app.services import llm_client, question_generator as qgen
from app.services.resume_parser import ExtractionResult, extract_resume_data, read_resume_bytes

settings = get_settings()


class ServiceError(Exception):
    """Raised for expected, user-facing error conditions (mapped to 4xx by routers)."""


# ---------------------------------------------------------------------------
# Candidate / resume ingestion
# ---------------------------------------------------------------------------

def ingest_resume(
    db: DBSession, filename: str, content: bytes, target_role: str,
    name: Optional[str] = None, email: Optional[str] = None,
) -> Candidate:
    if target_role not in settings.role_list:
        raise ServiceError(f"Unsupported role '{target_role}'. Supported roles: {settings.role_list}")
    if not content:
        raise ServiceError("Uploaded resume file is empty.")

    try:
        resume_text = read_resume_bytes(filename, content)
    except Exception as exc:
        raise ServiceError(f"Could not read resume file: {exc}") from exc

    if not resume_text.strip():
        raise ServiceError("No extractable text was found in the uploaded resume.")

    extraction: ExtractionResult = extract_resume_data(resume_text)

    candidate = Candidate(
        name=name,
        email=email,
        target_role=target_role,
        resume_raw_text=resume_text,
        extracted_skills=json.dumps(extraction.skills),
        extracted_technologies=json.dumps(extraction.technologies),
        domain_exposure=json.dumps(extraction.domain_exposure),
        seniority_signal=extraction.seniority_signal,
    )
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return candidate


def _resume_context_from_candidate(candidate: Candidate) -> qgen.ResumeContext:
    return qgen.ResumeContext(
        skills=json.loads(candidate.extracted_skills),
        technologies=json.loads(candidate.extracted_technologies),
        domain_exposure=json.loads(candidate.domain_exposure),
        seniority_signal=candidate.seniority_signal,
    )


# ---------------------------------------------------------------------------
# Session lifecycle
# ---------------------------------------------------------------------------

def start_session(db: DBSession, candidate_id: str) -> InterviewSession:
    candidate = db.get(Candidate, candidate_id)
    if candidate is None:
        raise ServiceError(f"No candidate found with id '{candidate_id}'")

    session = InterviewSession(candidate_id=candidate.id, role=candidate.target_role)
    db.add(session)
    db.commit()
    db.refresh(session)

    _create_next_question(db, session, candidate)
    db.commit()
    db.refresh(session)
    return session


def _create_next_question(db: DBSession, session: InterviewSession, candidate: Candidate) -> Question:
    resume_ctx = _resume_context_from_candidate(candidate)
    asked_topics = [q.topic for q in session.questions]
    history = [
        {
            "order_index": q.order_index,
            "question_text": q.question_text,
            "answer_text": q.answer.answer_text if q.answer else None,
        }
        for q in session.questions
    ]
    last_answer = session.questions[-1].answer if session.questions else None
    last_score = last_answer.quality_score if last_answer else None

    generated = qgen.generate_question(
        role=session.role,
        resume=resume_ctx,
        asked_topics=asked_topics,
        conversation_history=history,
        last_quality_score=last_score,
    )

    question = Question(
        session_id=session.id,
        order_index=len(session.questions) + 1,
        topic=generated.topic,
        difficulty=generated.difficulty,
        question_text=generated.question_text,
        retrieved_context=generated.retrieved_context,
        source_chunk_ids=json.dumps(generated.source_chunk_ids),
        generation_query=generated.generation_query,
        generation_method=generated.generation_method,
    )
    db.add(question)
    session.current_question_index = question.order_index
    db.add(session)
    db.commit()
    db.refresh(question)
    return question


def submit_answer(db: DBSession, question_id: str, answer_text: str):
    question = db.get(Question, question_id)
    if question is None:
        raise ServiceError(f"No question found with id '{question_id}'")
    if question.answer is not None:
        raise ServiceError("This question has already been answered.")

    session = db.get(InterviewSession, question.session_id)
    if session.status == "completed":
        raise ServiceError("This interview session has already been completed.")

    score, rationale = qgen.assess_answer_quality(
        question.question_text, question.retrieved_context, answer_text
    )
    answer = Answer(
        question_id=question.id,
        answer_text=answer_text,
        quality_score=score,
        quality_notes=rationale,
    )
    db.add(answer)
    db.commit()

    next_question = None
    if len(session.questions) >= settings.max_questions_per_session:
        session.status = "completed"
        session.completed_at = dt.datetime.utcnow()
        db.add(session)
        db.commit()
    else:
        candidate = db.get(Candidate, session.candidate_id)
        db.refresh(session)
        next_question = _create_next_question(db, session, candidate)

    db.refresh(session)
    return session, next_question


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def get_or_create_report(db: DBSession, session_id: str) -> Report:
    session = db.get(InterviewSession, session_id)
    if session is None:
        raise ServiceError(f"No session found with id '{session_id}'")
    if session.report is not None:
        return session.report
    if not all(q.answer is not None for q in session.questions) or not session.questions:
        raise ServiceError("Cannot generate a report until at least one question has been answered.")

    report = _build_report(session)
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def _build_report(session: InterviewSession) -> Report:
    qa_pairs = [
        {
            "topic": q.topic,
            "difficulty": q.difficulty,
            "question": q.question_text,
            "answer": q.answer.answer_text if q.answer else "",
            "score": q.answer.quality_score if q.answer else 0.0,
        }
        for q in session.questions
    ]

    topic_scores: dict[str, list[float]] = {}
    for qa in qa_pairs:
        topic_scores.setdefault(qa["topic"], []).append(qa["score"] or 0.0)
    topic_coverage = {t: round(sum(v) / len(v), 2) for t, v in topic_scores.items()}

    overall_score = round(sum(topic_coverage.values()) / len(topic_coverage), 2) if topic_coverage else None

    summary_text, strengths, gaps, recommendation = _summarize(session, qa_pairs, overall_score)

    return Report(
        session_id=session.id,
        summary_text=summary_text,
        strengths=json.dumps(strengths),
        gaps=json.dumps(gaps),
        topic_coverage=json.dumps(topic_coverage),
        overall_score=overall_score,
        recommendation=recommendation,
    )


def _recommendation_from_score(score: Optional[float]) -> str:
    if score is None:
        return "insufficient_data"
    if score >= 4.0:
        return "strong_yes"
    if score >= 3.0:
        return "yes"
    if score >= 2.0:
        return "borderline"
    return "no"


def _summarize(session: InterviewSession, qa_pairs: list[dict], overall_score: Optional[float]):
    recommendation = _recommendation_from_score(overall_score)

    if llm_client.is_available():
        transcript = "\n\n".join(
            f"[{qa['topic']} | {qa['difficulty']} | score {qa['score']}]\nQ: {qa['question']}\nA: {qa['answer']}"
            for qa in qa_pairs
        )
        system_prompt = (
            "You are summarizing a completed technical screening interview for a hiring manager. "
            "Be specific and evidence-based, referencing the actual answers given. Be balanced."
        )
        user_prompt = f"""
Role: {session.role}
Transcript:
{transcript}

Return JSON with keys:
- "summary": 3-5 sentence overall narrative summary of the candidate's performance
- "strengths": list of up to 4 short strength bullet points, each grounded in a specific answer
- "gaps": list of up to 4 short bullet points on weaknesses or missing depth
"""
        result = llm_client.generate_json(system_prompt, user_prompt, max_tokens=600)
        if result and result.get("summary"):
            return (
                result["summary"].strip(),
                [str(s) for s in result.get("strengths", [])][:4],
                [str(g) for g in result.get("gaps", [])][:4],
                recommendation,
            )

    # Deterministic fallback summary
    strong = [qa for qa in qa_pairs if (qa["score"] or 0) >= 3.5]
    weak = [qa for qa in qa_pairs if (qa["score"] or 0) < 2.5]
    strengths = [f"Solid answer on {qa['topic']} (score {qa['score']})" for qa in strong[:4]] or [
        "No answers reached the strong-performance threshold in this session."
    ]
    gaps = [f"Weak or shallow answer on {qa['topic']} (score {qa['score']})" for qa in weak[:4]] or [
        "No major gaps identified in this session."
    ]
    summary = (
        f"The candidate answered {len(qa_pairs)} questions for the {session.role} role with an "
        f"average score of {overall_score}. Performance was strongest on "
        f"{', '.join(qa['topic'] for qa in strong[:2]) or 'no single topic in particular'} and "
        f"weakest on {', '.join(qa['topic'] for qa in weak[:2]) or 'no single topic in particular'}. "
        "(Generated via deterministic fallback -- no LLM configured.)"
    )
    return summary, strengths, gaps, recommendation
