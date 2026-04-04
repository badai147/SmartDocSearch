import os
from functools import lru_cache

from langchain_openai import ChatOpenAI

from backend.app.core.config import settings


@lru_cache(maxsize=1)
def get_chat_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.llm_model, 
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        temperature=settings.llm_temperature
    )

