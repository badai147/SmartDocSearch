import os
from dotenv import load_dotenv
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

class Settings(BaseSettings):
    _backend_dir = Path(__file__).resolve().parents[2]

    app_name: str = "DocQnA-RAG"

    # Storage (uploaded docs + vector DB)
    docs_dir: str = str(_backend_dir / "data" / "docs")
    chroma_dir: str = str(_backend_dir / "data" / "chroma")
    chroma_collection: str = "documents"

    # Embeddings
    embedding_model: str = os.getenv("embedding_model")
    embedding_base_url: str = os.getenv("embedding_base_url")
    embedding_api_key: str = os.getenv("embedding_api_key")
    
    # LLM
    llm_backend: str = "openai"  # openai only in this starter
    llm_model: str = os.getenv("llm_model")
    llm_api_key: str = os.getenv("llm_api_key")
    llm_base_url: str = os.getenv("llm_base_url")
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


settings = Settings()

