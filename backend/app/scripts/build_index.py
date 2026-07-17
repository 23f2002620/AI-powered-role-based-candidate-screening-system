"""
Standalone script to (re)build the RAG vector indexes for every configured
role from the markdown knowledge base. Useful at deploy time or after editing
knowledge_base/*.md, so the app doesn't have to rebuild on every cold start.

Usage:
    python -m app.scripts.build_index
"""
from app.services.rag_pipeline import build_all_indexes

if __name__ == "__main__":
    build_all_indexes(force_rebuild=True)
    print("Vector indexes rebuilt for all configured roles.")
