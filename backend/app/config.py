"""
Central configuration, loaded from environment variables / .env file.
Keeping configuration in one place is the main lever we have for making the
system deployable across dev/staging/prod without touching code.
"""
from functools import lru_cache
from pathlib import Path
from typing import List
import os

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    # --- General ---
    app_name: str = "AI Candidate Screening System"
    environment: str = "development"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # --- Database ---
    database_url: str = f"sqlite:///{BASE_DIR.parent}/data/screening.db"

    # --- LLM / Gemini ---
    gemini_api_key: str = os.getenv("GEMINI_API_KEY")
    gemini_model: str = "gemini-3.5-flash"
    llm_max_tokens: int = 1024
    # If no API key is configured, the system falls back to deterministic
    # template-based question generation so the pipeline is still runnable
    # end-to-end in offline / evaluation environments.
    use_llm_fallback_if_no_key: bool = True

    # --- RAG / Vector store ---
    knowledge_base_dir: Path = BASE_DIR / "knowledge_base"
    vector_index_dir: Path = BASE_DIR.parent / "data" / "vector_index"
    chunk_max_words: int = 180
    chunk_overlap_words: int = 40
    retrieval_top_k: int = 4

    # --- Interview lifecycle ---
    max_questions_per_session: int = 6
    supported_roles: str = "backend_engineer,ai_ml_engineer,frontend_engineer"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def role_list(self) -> List[str]:
        return [r.strip() for r in self.supported_roles.split(",") if r.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()