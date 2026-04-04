import os
from functools import lru_cache

from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

from backend.app.core.config import settings


@lru_cache(maxsize=1)
def get_embeddings():
    return OpenAIEmbeddings(
        model=settings.embedding_model,
        api_key=settings.embedding_api_key,
        base_url=settings.embedding_base_url,
    )


@lru_cache(maxsize=1)
def get_vectorstore() -> Chroma:
    # persist_directory 用于体现“向量数据库”的持久化
    os.makedirs(settings.chroma_dir, exist_ok=True)
    embeddings = get_embeddings()
    return Chroma(
        collection_name=settings.chroma_collection,
        embedding_function=embeddings,
        persist_directory=settings.chroma_dir,
    )

