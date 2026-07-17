"""
Resume ingestion + extraction.

Design choice: rather than depending on a heavyweight NLP model (spaCy models,
NER, etc.) which would require downloading model weights the deployment
environment might not have network access for, we use a curated keyword
taxonomy per role plus generic technology/skill dictionaries and light regex
heuristics. This is transparent, fast, has zero cold-start cost, and is easy
to extend by editing plain lists -- a reasonable trade-off for a screening
tool where recall on well-known technology terms matters more than deep
semantic parsing. Swapping in an NER model or an LLM-based extractor later
only requires reimplementing `extract_resume_data`.
"""
import io
import re
from dataclasses import dataclass, field
from typing import List, Optional

# --- Taxonomies -------------------------------------------------------------

TECHNOLOGIES = [
    "python", "java", "javascript", "typescript", "go", "golang", "rust", "c++", "c#", "ruby",
    "php", "kotlin", "swift", "scala",
    "react", "next.js", "nextjs", "vue", "angular", "svelte", "redux", "tailwind",
    "node.js", "nodejs", "express", "django", "flask", "fastapi", "spring", "spring boot",
    ".net", "rails",
    "postgresql", "postgres", "mysql", "mongodb", "redis", "cassandra", "dynamodb", "sqlite",
    "elasticsearch", "kafka", "rabbitmq", "sqs",
    "docker", "kubernetes", "terraform", "ansible", "jenkins", "github actions", "ci/cd",
    "aws", "gcp", "azure", "lambda", "s3", "ec2",
    "pytorch", "tensorflow", "keras", "scikit-learn", "sklearn", "huggingface", "transformers",
    "langchain", "llamaindex", "openai", "anthropic", "numpy", "pandas", "spark", "airflow",
    "faiss", "pinecone", "chroma", "weaviate", "vector database", "vector search",
    "graphql", "rest", "grpc", "websocket", "microservices", "rag", "llm", "nlp", "cnn", "rnn",
    "transformer", "attention mechanism", "fine-tuning", "lora", "rlhf", "prompt engineering",
    "html", "css", "sass", "webpack", "vite", "jest", "cypress", "playwright",
]

SKILLS = [
    "system design", "distributed systems", "api design", "database design",
    "data modeling", "algorithm design", "performance optimization", "debugging",
    "code review", "mentoring", "agile", "scrum", "project management",
    "problem solving", "communication", "leadership", "testing", "test automation",
    "machine learning", "deep learning", "data analysis", "data engineering",
    "model deployment", "mlops", "a/b testing", "accessibility", "responsive design",
    "state management", "authentication", "authorization", "security", "caching",
    "load balancing", "concurrency", "asynchronous programming",
]

DOMAIN_KEYWORDS = [
    "fintech", "healthcare", "e-commerce", "ecommerce", "edtech", "gaming", "logistics",
    "insurance", "banking", "payments", "healthtech", "biotech", "adtech", "media",
    "cybersecurity", "iot", "telecom", "government", "retail", "saas", "b2b", "b2c",
    "marketplace", "social media", "autonomous vehicles", "robotics",
]

SENIORITY_PATTERNS = [
    (re.compile(r"\b(1[0-9]|[7-9])\+?\s*years?\b", re.I), "senior"),
    (re.compile(r"\b([3-6])\+?\s*years?\b", re.I), "mid"),
    (re.compile(r"\b([0-2])\+?\s*years?\b", re.I), "junior"),
    (re.compile(r"\bsenior\b", re.I), "senior"),
    (re.compile(r"\bstaff\b|\bprincipal\b|\blead\b", re.I), "senior"),
    (re.compile(r"\bjunior\b|\bentry.level\b|\bintern\b", re.I), "junior"),
]

YEARS_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\+?\s*years?\s+(?:of\s+)?experience", re.I)


@dataclass
class ExtractionResult:
    skills: List[str] = field(default_factory=list)
    technologies: List[str] = field(default_factory=list)
    domain_exposure: List[str] = field(default_factory=list)
    seniority_signal: Optional[str] = None
    years_of_experience_estimate: Optional[float] = None


def read_resume_bytes(filename: str, content: bytes) -> str:
    """Extract raw text from an uploaded resume file (.pdf or .txt/.md)."""
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return _read_pdf(content)
    # Treat everything else as text-ish
    try:
        return content.decode("utf-8", errors="ignore")
    except Exception:
        return content.decode("latin-1", errors="ignore")


def _read_pdf(content: bytes) -> str:
    try:
        import pdfplumber
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "pdfplumber is required to parse PDF resumes. Install it via requirements.txt"
        ) from exc

    text_parts = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text_parts.append(page_text)
    return "\n".join(text_parts)


def _find_matches(text_lower: str, vocabulary: List[str]) -> List[str]:
    found = []
    for term in vocabulary:
        # word-boundary-ish match; tolerant of punctuation like "C++", ".NET"
        pattern = re.escape(term.lower())
        if re.search(rf"(?<![a-z0-9]){pattern}(?![a-z0-9])", text_lower):
            found.append(term)
    return found


def extract_resume_data(resume_text: str) -> ExtractionResult:
    """Pure function: raw resume text -> structured extraction result."""
    text_lower = resume_text.lower()

    technologies = _find_matches(text_lower, TECHNOLOGIES)
    skills = _find_matches(text_lower, SKILLS)
    domains = _find_matches(text_lower, DOMAIN_KEYWORDS)

    years_match = YEARS_PATTERN.search(resume_text)
    years_estimate = float(years_match.group(1)) if years_match else None

    seniority = None
    if years_estimate is not None:
        if years_estimate >= 7:
            seniority = "senior"
        elif years_estimate >= 3:
            seniority = "mid"
        else:
            seniority = "junior"
    else:
        for pattern, label in SENIORITY_PATTERNS:
            if pattern.search(resume_text):
                seniority = label
                break

    return ExtractionResult(
        skills=sorted(set(skills)),
        technologies=sorted(set(technologies)),
        domain_exposure=sorted(set(domains)),
        seniority_signal=seniority,
        years_of_experience_estimate=years_estimate,
    )
