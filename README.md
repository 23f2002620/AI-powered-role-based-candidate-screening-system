# Screening Room — AI-Powered Role-Based Candidate Screening System

A full-stack system that simulates a structured technical interview whose questions are
generated on the fly from **(resume) × (role) × (retrieved knowledge-base context)**, rather
than pulled from a static question bank.

```
project/
├── backend/     FastAPI service: resume parsing, RAG pipeline, question generation,
│                session orchestration, persistence
└── frontend/    React (Vite) app: upload flow, live interview, results summary
```

---

## 1. Architecture overview

```
 ┌──────────────┐      ┌────────────────────────────────────────────────────────────┐
 │   Frontend    │      │                        Backend (FastAPI)                   │
 │  React / Vite │      │                                                            │
 │              │──────▶│  routers/          → HTTP concerns only (validation, codes)│
 │  Upload      │       │  services/         → business logic + AI orchestration     │
 │  Interview   │       │    resume_parser   → PDF/text → skills/tech/domain/seniority│
 │  Summary     │       │    rag_pipeline    → chunk KB, build/query vector index     │
 │              │       │    vector_store    → TF-IDF embeddings + FAISS ANN index    │
 │              │       │    question_gen    → query construction + LLM/template Qgen │
 │              │       │    llm_client      → Anthropic API wrapper (optional)       │
 │              │       │    interview_svc   → session lifecycle, scoring, reports    │
 │              │       │  models.py         → SQLAlchemy ORM (candidates/sessions/   │
 │              │       │                       questions/answers/reports)            │
 │              │       │  database.py       → SQLite by default, swappable via env   │
 └──────────────┘      └────────────────────────────────────────────────────────────┘
```

This is a layered service architecture with a strict one-way dependency rule: **routers depend
on services, services depend on models/DB and the RAG/LLM modules — never the reverse.** That
keeps HTTP concerns (status codes, request parsing) out of business logic, and keeps the RAG/LLM
pipeline testable in isolation from the web framework.

---

## 2. End-to-end flow (Context → Question → Answer → Storage)

1. **Candidate Entry** — user uploads a resume (PDF/txt/md) and picks a role.
2. **Resume Processing** (`resume_parser.py`) — extracts skills, technologies, domain exposure,
   and a seniority signal using a curated keyword taxonomy + regex heuristics (see §4 for why).
3. **Context Construction** (`question_generator.build_query`) — for each turn, the system picks
   an unasked KB topic that best overlaps the candidate's resume terms, and combines it with the
   resume profile into a natural-language retrieval query, e.g.:
   > "Caching for a Backend Engineer candidate with experience in redis, kafka, postgresql.
   > Domain exposure: fintech, payments."
4. **Knowledge Retrieval / RAG** (`rag_pipeline.py`, `vector_store.py`) — that query is embedded
   and matched against a per-role vector index built from curated knowledge-base documents,
   returning the top-k most relevant, semantically coherent chunks (with a minimum similarity
   floor so irrelevant chunks are dropped rather than padded in).
5. **Question Generation** (`question_generator.generate_question`) — the retrieved chunks +
   resume profile + prior Q&A history are passed to Claude with instructions to write one
   grounded, non-generic question at a calibrated difficulty. If no API key is configured, a
   deterministic template generator produces a structurally similar (if less nuanced) question,
   so the whole pipeline still runs end-to-end offline.
6. **Interactive Interview** — the frontend renders one question at a time; state (which
   question is current, what's been asked, session status) lives server-side, keyed by session
   id, so the UI is a thin client over backend session state.
7. **Response Handling** — every answer is scored (LLM-graded, or heuristically if no key) and
   persisted alongside the question, retrieved context, source chunk ids, and the exact query
   used to retrieve them — so every question is traceable back to *why* it was asked.
8. **Adaptation** — the score from the last answer nudges the difficulty of the next question up
   or down a notch (see `_target_difficulty`), and topic selection avoids repeats.
9. **Final Output** — `interview_service._build_report` aggregates per-topic average scores, an
   overall score, a strong/borderline/no recommendation, and an LLM-written (or heuristic)
   narrative summary with strengths/gaps grounded in the actual transcript.

---

## 3. Data model

| Table              | Purpose                                                                 |
|--------------------|--------------------------------------------------------------------------|
| `candidates`       | Parsed resume + extracted profile (skills/tech/domain/seniority)        |
| `interview_sessions` | One screening run: role, status, current question pointer            |
| `questions`        | Question text, topic, difficulty, **retrieved context, source chunk ids, retrieval query, generation method** — full traceability |
| `answers`          | Answer text, quality score, scoring rationale                           |
| `reports`          | Final summary, strengths, gaps, per-topic coverage, overall score, recommendation |

SQLite is the default (zero-config), but every access goes through `database.get_db()`, so
switching to Postgres/MySQL in production is a one-line `DATABASE_URL` change with no code
changes elsewhere.

---

## 4. Key design decisions & trade-offs

**Why TF-IDF + FAISS instead of a pretrained dense encoder?**
Dense sentence embedding models typically need to be downloaded from a model hub at first run.
Many deployment/sandboxed/CI environments can't reach one. TF-IDF is a real, well-understood
embedding technique — sparse vectors weighted by term frequency / inverse document frequency —
and cosine similarity over TF-IDF is a strong, zero-cold-start baseline for **topical** retrieval
over a small, curated, single-domain corpus like a role's knowledge base (as opposed to open-domain
semantic retrieval, where a dense encoder would clearly win). FAISS (`IndexFlatIP` over
L2-normalized vectors = exact cosine similarity search) is a genuine vector database, not a mock —
at this corpus size exact search is cheap, and the same interface scales to `IndexIVFFlat`/HNSW
for a much larger corpus. The embedding step is isolated behind one method
(`VectorStore.embed_query`), so swapping in OpenAI/Voyage/sentence-transformers embeddings later
touches exactly one file.

**Why keyword-taxonomy resume extraction instead of an NER model?**
Same reasoning: no model download dependency, instant cold start, and fully transparent/
auditable (you can read the exact vocab that drives extraction in `resume_parser.py`). The
trade-off is recall on technologies/skills phrased in ways not in the taxonomy — acceptable for
a v1, and the taxonomy is a plain list that's trivial to extend, or to replace with an
LLM-based extractor later behind the same `extract_resume_data()` function signature.

**Why a knowledge base per role, chunked by markdown section headers?**
The KB docs are hand-curated so that each `##` header already delimits one coherent
sub-topic (e.g. "Caching", "Transformers and Large Language Models"). Chunking on those
boundaries first (and only falling back to a bounded sliding window with overlap for very long
sections) keeps each chunk topically coherent, which matters more for downstream question
quality than uniform fixed-size chunking of raw text would.

**Why does the system run fully without an Anthropic API key?**
So the pipeline is gradeable/runnable in any environment: every LLM call point
(`llm_client.generate_text/generate_json`) has a deterministic fallback (template questions,
heuristic scoring, extractive summaries), and `generation_method` is stored per question so it's
always visible in the UI/API which path produced it.

**Why is difficulty/topic adaptation kept simple (score → up/down one notch)?**
It's legible and debuggable — you can look at one score and predict the next difficulty — while
still satisfying the "adapt based on previous responses" requirement. A more sophisticated
policy (e.g. multi-turn planning, topic dependency graphs) is a natural extension but adds
complexity that isn't justified for a screening tool where interviewers mostly want intuitive,
explainable behavior.

---

## 5. Running it

### Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # add ANTHROPIC_API_KEY to enable LLM-driven Q-gen/scoring/summaries
python -m app.scripts.build_index   # optional: pre-build vector indexes
uvicorn app.main:app --reload --port 8000
```

The API is served at `http://localhost:8000`; interactive docs at `/docs`.
Health check: `GET /api/health`.

### Frontend

```bash
cd frontend
npm install
cp .env.example .env         # points VITE_API_BASE_URL at the backend
npm run dev
```

Visit `http://localhost:5173`.

---

## 6. API surface (service-layer view)

| Concern                     | Endpoint                                    |
|------------------------------|----------------------------------------------|
| List supported roles         | `GET /api/roles`                             |
| Upload resume + role         | `POST /api/candidates/upload-resume`         |
| Start an interview session   | `POST /api/interviews/start`                 |
| Fetch session state          | `GET /api/interviews/{session_id}`           |
| Submit an answer / get next Q| `POST /api/interviews/{session_id}/answer`   |
| Get final structured report  | `GET /api/interviews/{session_id}/report`    |

Errors are handled in two layers: expected, user-facing conditions raise `ServiceError` in the
service layer and are mapped to `422`/`404` by routers with a clear `detail` message; anything
unexpected is caught by a global exception handler and returns a generic `500` (with full
tracebacks going to server logs, not the client).

---

