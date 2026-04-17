import threading
from typing import Optional

from langchain_openai import ChatOpenAI

from backend.app.core.config import settings

# Thread-safe singleton pattern for LLM instance
_llm_instance: Optional[ChatOpenAI] = None
_llm_lock = threading.Lock()


def get_chat_llm() -> ChatOpenAI:
    """Get or create LLM instance (thread-safe singleton)."""
    global _llm_instance
    if _llm_instance is None:
        with _llm_lock:
            if _llm_instance is None:
                _llm_instance = ChatOpenAI(
                    model=settings.llm_model,
                    api_key=settings.llm_api_key,
                    base_url=settings.llm_base_url,
                    temperature=settings.llm_temperature
                )
    return _llm_instance


def reset_chat_llm() -> None:
    """Reset LLM instance (useful for testing or config reload)."""
    global _llm_instance
    with _llm_lock:
        _llm_instance = None

