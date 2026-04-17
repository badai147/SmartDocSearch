import os
import sys
from dotenv import load_dotenv
from pathlib import Path
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    _backend_dir = Path(__file__).resolve().parents[2]

    app_name: str = "DocQnA-RAG"

    # Storage (uploaded docs + vector DB)
    docs_dir: str = str(_backend_dir / "data" / "docs")
    chroma_dir: str = str(_backend_dir / "data" / "chroma")
    chroma_collection: str = "documents"

    # Embeddings - use os.getenv with default empty string to avoid validation errors on import
    embedding_model: str = os.getenv("embedding_model", "")
    embedding_base_url: str = os.getenv("embedding_base_url", "")
    embedding_api_key: str = os.getenv("embedding_api_key", "")

    # LLM
    llm_backend: str = "openai"  # openai only in this starter
    llm_model: str = os.getenv("llm_model", "")
    llm_api_key: str = os.getenv("llm_api_key", "")
    llm_base_url: str = os.getenv("llm_base_url", "")
    llm_temperature: float = 0.2

    # ETL chunking
    chunk_size: int = 400
    chunk_overlap: int = 100

    # Retrieval
    top_k: int = 6
    query_enhance_n: int = 3
    retrieval_score_threshold: float = 0.3

    # API
    cors_allow_origins: str = "*"  # comma-separated, or "*"

    # Security
    max_file_size_mb: int = 50
    max_files_per_upload: int = 10
    allowed_file_extensions: set[str] = {".pdf", ".docx", ".doc", ".txt", ".md", ".html", ".pptx"}

    @field_validator("embedding_model", "embedding_base_url", "embedding_api_key",
                     "llm_model", "llm_api_key", "llm_base_url", mode="after")
    @classmethod
    def check_required_env_vars(cls, v, info):
        field_name = info.field_name
        env_var_name = field_name
        if v is None or (isinstance(v, str) and v.strip() == ""):
            print(f"\n❌ Error: Environment variable '{env_var_name}' is required but not set.")
            print(f"   Please set it in your .env file or environment.\n")
            sys.exit(1)
        return v


settings = Settings()

