"""RAG：文档检索工具与底层检索逻辑（与 Agent / Prompt 解耦）。"""

from __future__ import annotations

from typing import List, Tuple

from langchain_core.tools import tool

from backend.app.core.config import settings


def dedupe_key(doc) -> Tuple[str, int | None, int | None]:
    meta = doc.metadata or {}
    source = meta.get("file_name") or meta.get("source") or "unknown"
    page = meta.get("page")
    chunk_id = meta.get("chunk_id")
    return (source, page, chunk_id)


def search_docs_with_threshold(vectorstore, query: str, top_k: int):
    """
    带相关度分数的检索；先多取候选再按阈值过滤，无命中时软回退为 top_k（提高召回）。
    """
    threshold = settings.retrieval_score_threshold
    k_fetch = max(top_k * 2, top_k)
    try:
        pairs = vectorstore.similarity_search_with_relevance_scores(query, k=k_fetch)
        filtered = [doc for doc, score in pairs if score >= threshold]
        if filtered:
            return filtered[:top_k]
        if pairs:
            return [doc for doc, _ in pairs[:top_k]]
        return []
    except Exception:
        return vectorstore.similarity_search(query, k=top_k)


def create_search_docs_tool(
    vectorstore,
    top_k: int,
    used_sources: List[dict],
    max_chars: int = 8000,
):
    """
    闭包工具：写入 used_sources（与调用方共享同一列表以汇总引用）。
    """

    @tool("search_docs")
    def search_docs(query: str) -> str:
        """在向量库中检索文档片段并返回可引用上下文。"""
        docs = search_docs_with_threshold(vectorstore, query, top_k)
        local_lines: List[str] = []
        local_seen = set()
        total_chars = 0

        for d in docs:
            key = dedupe_key(d)
            if key in local_seen:
                continue
            local_seen.add(key)

            meta = d.metadata or {}
            source = meta.get("file_name") or meta.get("source") or "unknown"
            page = meta.get("page")
            snippet = (d.page_content or "").strip()

            idx = len(used_sources) + 1
            header = f"[{idx}] {source}" + (f" (page={page})" if page is not None else "")
            part = f"{header}\n{snippet}"
            if total_chars + len(part) > max_chars:
                break

            local_lines.append(part)
            total_chars += len(part)
            used_sources.append({"source": source, "page": page})

        return "\n\n".join(local_lines) if local_lines else "未检索到相关片段。"

    return search_docs
