"""
Application configuration via environment variables.
"""
from __future__ import annotations

from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ------------------------------------------------------------------
    # App
    # ------------------------------------------------------------------
    app_env: str = "development"
    log_level: str = "INFO"
    cors_origins: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    # ------------------------------------------------------------------
    # Database (PostgreSQL)
    # ------------------------------------------------------------------
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/literature_survey"

    # ------------------------------------------------------------------
    # Redis
    # ------------------------------------------------------------------
    redis_url: str = "redis://localhost:6379/0"

    # ------------------------------------------------------------------
    # OpenAI
    # ------------------------------------------------------------------
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    embedding_model: str = "text-embedding-3-large"

    # ------------------------------------------------------------------
    # Pinecone
    # ------------------------------------------------------------------
    pinecone_api_key: str = ""
    pinecone_environment: str = "us-east-1-aws"
    pinecone_index_name: str = "literature-survey"

    # ------------------------------------------------------------------
    # External Academic APIs
    # ------------------------------------------------------------------
    semantic_scholar_api_key: str = ""
    arxiv_max_results: int = 20
    semantic_scholar_max_results: int = 20
    crossref_max_results: int = 20

    # ------------------------------------------------------------------
    # Survey settings
    # ------------------------------------------------------------------
    max_papers_per_survey: int = 50
    embedding_batch_size: int = 32


settings = Settings()
