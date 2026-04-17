import logging
import os
import threading
from typing import Optional

from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

from backend.app.core.config import settings

logger = logging.getLogger(__name__)

# Thread-safe singleton pattern for vector store
_embeddings_instance: Optional[OpenAIEmbeddings] = None
_vectorstore_instance: Optional[Chroma] = None
_embeddings_lock = threading.Lock()  # embeddings 独立的锁
_vectorstore_lock = threading.Lock()  # vectorstore 独立的锁


def get_embeddings() -> OpenAIEmbeddings:
    """Get or create embeddings instance (thread-safe singleton)."""
    global _embeddings_instance
    if _embeddings_instance is None:
        with _embeddings_lock:  # 使用独立的锁
            if _embeddings_instance is None:
                logger.info(f"[VectorStore] 初始化 embeddings: model={settings.embedding_model}")
                logger.info(f"[VectorStore] 初始化 embeddings: base_url={settings.embedding_base_url}")
                _embeddings_instance = OpenAIEmbeddings(
                    model=settings.embedding_model,
                    api_key=settings.embedding_api_key,
                    base_url=settings.embedding_base_url,
                )
                logger.info("[VectorStore] embeddings 实例创建完成")
    return _embeddings_instance


def get_vectorstore() -> Chroma:
    """Get or create vector store instance (thread-safe singleton)."""
    global _vectorstore_instance
    if _vectorstore_instance is None:
        with _vectorstore_lock:  # 使用独立的锁
            if _vectorstore_instance is None:
                logger.info("[VectorStore] 初始化: 创建目录")
                os.makedirs(settings.chroma_dir, exist_ok=True)
                logger.info("[VectorStore] 初始化: 获取 embeddings")
                embeddings = get_embeddings()  # 不再需要获取 vectorstore_lock
                logger.info("[VectorStore] 初始化: 创建 Chroma 实例")
                _vectorstore_instance = Chroma(
                    collection_name=settings.chroma_collection,
                    embedding_function=embeddings,
                    persist_directory=settings.chroma_dir,
                )
                logger.info("[VectorStore] 初始化完成")
    return _vectorstore_instance


def reset_vectorstore() -> None:
    """Reset vector store instance (useful for testing or config reload)."""
    global _vectorstore_instance, _embeddings_instance
    with _vectorstore_lock:
        _vectorstore_instance = None
        _embeddings_instance = None


def delete_documents_by_source(source_name: str) -> int:
    """Delete all documents with matching source name from vector store.

    Returns:
        Number of documents deleted
    """
    logger.info(f"[VectorStore] 开始删除文档: source={source_name}")
    vectorstore = get_vectorstore()
    try:
        # Chroma doesn't support direct metadata filtering for deletion
        # So we query first, then delete by IDs
        results = vectorstore.get(where={"source": source_name})
        
        if not results:
            logger.info(f"[VectorStore] 删除完成: source={source_name}, 文档数量=0 (查询结果为空)")
            return 0
            
        if "ids" not in results:
            logger.info(f"[VectorStore] 删除完成: source={source_name}, 文档数量=0 (无ids字段)")
            return 0
            
        if not results["ids"]:
            logger.info(f"[VectorStore] 删除完成: source={source_name}, 文档数量=0 (无匹配文档)")
            return 0
        
        deleted_count = len(results["ids"])
        vectorstore.delete(ids=results["ids"])
        logger.info(f"[VectorStore] 删除成功: source={source_name}, 删除文档数={deleted_count}")
        return deleted_count
        
    except Exception as e:
        logger.error(f"[VectorStore] 删除失败: source={source_name}, error={e}")
        return 0

