"""
Context Construction + Question Generation.

Pipeline for a single question:
  1. build_query()      -- combine resume signal (skills/tech/domain/seniority)
                             with a candidate KB topic to form a natural-language
                             retrieval query. This is the "Context Construction"
                             step: it decides *what to ask about* before ever
                             touching the knowledge base.
  2. rag_pipeline.retrieve() -- pulls grounded chunks for that query.
  3. generate_question() -- prompts the LLM with resume context + retrieved
                             chunks + interview history to produce one
                             non-generic, context-aware question. Falls back
                             to a deterministic template if no LLM key is
                             configured, so the pipeline is always runnable.

Resume influence on difficulty:
  - seniority_signal and years_of_experience_estimate raise/lower requested
    difficulty.
  - Prior answer quality (see assess_answer_quality) nudges difficulty up on
    strong answers and down (or repeats a related, more foundational
    question) on weak ones -- this is the "adapt based on previous
    responses" behaviour.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Optional

from app.services import llm_client, rag_pipeline
from app.services.vector_store import Chunk

# KB section titles double as the canonical topic universe per role, so the
# topics we quiz on are always grounded in something that actually exists in
# the retrieval corpus.
ROLE_TOPICS = {
    "backend_engineer": [
        "API Design", "Databases and Data Modeling", "Caching",
        "Concurrency and Asynchronous Processing", "Authentication and Authorization",
        "System Design and Scalability", "Testing and Reliability", "Security Fundamentals",
    ],
    "ai_ml_engineer": [
        "Machine Learning Foundations", "Deep Learning", "Transformers and Large Language Models",
        "Retrieval-Augmented Generation (RAG)", "Embeddings and Vector Search",
        "MLOps and Productionization", "Practical Considerations and Failure Modes",
    ],
    "frontend_engineer": [
        "Core Web Platform", "JavaScript Fundamentals", "React and Component Architecture",
        "Performance", "State Management and Data Fetching", "Accessibility and Semantics",
        "Styling and Design Systems", "Testing and Tooling",
    ],
}

ROLE_LABELS = {
    "backend_engineer": "Backend Engineer",
    "ai_ml_engineer": "AI/ML Engineer",
    "frontend_engineer": "Frontend Engineer",
}


@dataclass
class ResumeContext:
    skills: List[str]
    technologies: List[str]
    domain_exposure: List[str]
    seniority_signal: Optional[str]


@dataclass
class GeneratedQuestion:
    topic: str
    difficulty: str
    question_text: str
    retrieved_context: str
    source_chunk_ids: List[str]
    generation_query: str
    generation_method: str  # "llm" | "template_fallback"


def _pick_topic(role: str, asked_topics: List[str], resume: ResumeContext) -> str:
    """Prefer topics that connect to something on the resume and haven't been asked yet."""
    topics = ROLE_TOPICS.get(role, [])
    remaining = [t for t in topics if t not in asked_topics] or topics

    resume_terms = " ".join(resume.skills + resume.technologies).lower()
    # naive relevance score: does the resume mention words that overlap the topic?
    def relevance(topic: str) -> int:
        return sum(1 for word in topic.lower().split() if word in resume_terms)

    remaining.sort(key=relevance, reverse=True)
    return remaining[0]


def build_query(role: str, topic: str, resume: ResumeContext) -> str:
    role_label = ROLE_LABELS.get(role, role)
    resume_terms = resume.technologies + resume.skills
    anchor = ", ".join(resume_terms[:4]) if resume_terms else "general professional experience"
    return (
        f"{topic} for a {role_label} candidate with experience in {anchor}. "
        f"Domain exposure: {', '.join(resume.domain_exposure) or 'not specified'}."
    )


def _target_difficulty(resume: ResumeContext, last_quality_score: Optional[float]) -> str:
    base = {"senior": "hard", "mid": "medium", "junior": "easy"}.get(resume.seniority_signal, "medium")
    if last_quality_score is None:
        return base
    order = ["easy", "medium", "hard"]
    idx = order.index(base)
    if last_quality_score >= 4.0 and idx < 2:
        idx += 1
    elif last_quality_score <= 2.0 and idx > 0:
        idx -= 1
    return order[idx]


def _format_context(chunks_with_scores) -> str:
    return "\n\n".join(f"[{c.section}] {c.text}" for c, _ in chunks_with_scores)


def _template_question(topic: str, role_label: str, resume: ResumeContext, difficulty: str) -> str:
    anchor = (resume.technologies + resume.skills)
    anchor_term = random.choice(anchor) if anchor else "your recent projects"
    templates = {
        "easy": f"Can you explain the core concepts behind {topic.lower()} and how they showed up in {anchor_term}?",
        "medium": f"Walk me through a real tradeoff you made involving {topic.lower()}, ideally connected to your experience with {anchor_term}.",
        "hard": f"Design a solution involving {topic.lower()} for a system using {anchor_term} at scale -- what would break first, and how would you address it?",
    }
    return templates.get(difficulty, templates["medium"])


def generate_question(
    role: str,
    resume: ResumeContext,
    asked_topics: List[str],
    conversation_history: List[dict],
    last_quality_score: Optional[float] = None,
) -> GeneratedQuestion:
    role_label = ROLE_LABELS.get(role, role)
    topic = _pick_topic(role, asked_topics, resume)
    query = build_query(role, topic, resume)
    difficulty = _target_difficulty(resume, last_quality_score)

    retrieved = rag_pipeline.retrieve(role, query)
    context_text = _format_context(retrieved)
    source_ids = [c.chunk_id for c, _ in retrieved]

    question_text = None
    method = "template_fallback"

    if llm_client.is_available() and retrieved:
        history_text = "\n".join(
            f"Q{h['order_index']}: {h['question_text']}\nA: {h.get('answer_text', '(no answer yet)')}"
            for h in conversation_history
        ) or "(This is the first question.)"

        system_prompt = (
            "You are an experienced, fair technical interviewer conducting a structured "
            f"screening interview for a {role_label} role. You write ONE focused interview "
            "question at a time. Questions must be grounded in the provided reference context "
            "(do not invent facts beyond it), must connect naturally to the candidate's actual "
            "background, and must avoid generic phrasing like 'tell me about a time when...'. "
            "Prefer questions that require applied reasoning over rote recall."
        )
        user_prompt = f"""
Reference context (retrieved from the {role_label} knowledge base, topic: {topic}):
---
{context_text}
---

Candidate background:
- Skills: {', '.join(resume.skills) or 'none listed'}
- Technologies: {', '.join(resume.technologies) or 'none listed'}
- Domain exposure: {', '.join(resume.domain_exposure) or 'none listed'}
- Seniority signal: {resume.seniority_signal or 'unknown'}

Target difficulty: {difficulty}

Interview so far:
{history_text}

Write ONE new interview question about "{topic}" that:
- is grounded in the reference context above
- is calibrated to {difficulty} difficulty
- meaningfully references the candidate's background where natural (but does not just restate their resume)
- has not already been asked
- avoids yes/no phrasing; it should require the candidate to reason or explain

Return JSON: {{"question": "<the question text>"}}
"""
        result = llm_client.generate_json(system_prompt, user_prompt)
        if result and result.get("question"):
            question_text = result["question"].strip()
            method = "llm"

    if question_text is None:
        question_text = _template_question(topic, role_label, resume, difficulty)
        method = "template_fallback"

    return GeneratedQuestion(
        topic=topic,
        difficulty=difficulty,
        question_text=question_text,
        retrieved_context=context_text,
        source_chunk_ids=source_ids,
        generation_query=query,
        generation_method=method,
    )


def assess_answer_quality(question_text: str, context_text: str, answer_text: str) -> tuple[float, str]:
    """Return (score 0-5, short rationale). Falls back to a length/keyword heuristic."""
    if llm_client.is_available():
        system_prompt = (
            "You are grading a single interview answer for technical accuracy and depth, "
            "using only the reference context as ground truth. Be concise and fair."
        )
        user_prompt = f"""
Reference context:
---
{context_text}
---
Question: {question_text}
Candidate answer: {answer_text}

Score the answer from 0 to 5 (0=incorrect/empty, 2.5=partial/vague, 4=solid, 5=excellent and precise).
Return JSON: {{"score": <number>, "rationale": "<one sentence>"}}
"""
        result = llm_client.generate_json(system_prompt, user_prompt, max_tokens=200)
        if result and "score" in result:
            try:
                score = float(result["score"])
                return max(0.0, min(5.0, score)), str(result.get("rationale", "")).strip()
            except (TypeError, ValueError):
                pass

    # Heuristic fallback: reward length and overlap with context vocabulary.
    words = answer_text.strip().split()
    if len(words) < 5:
        return 0.5, "Answer is very short; little substance to evaluate."
    context_vocab = set(w.lower().strip(".,()") for w in context_text.split())
    answer_vocab = set(w.lower().strip(".,()") for w in words)
    overlap = len(context_vocab & answer_vocab)
    length_score = min(2.5, len(words) / 40)
    overlap_score = min(2.5, overlap / 8)
    score = round(length_score + overlap_score, 1)
    return score, "Heuristic score based on answer length and topical vocabulary overlap (no LLM configured)."
