from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import Any, Dict, List

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.outputs import ChatResult
from langchain_text_splitters import RecursiveCharacterTextSplitter
from markitdown import MarkItDown

from backend.app.core.config import settings
from backend.app.prompts.etl import ETL_AGENT_SYSTEM_PROMPT, build_etl_user_prompt
from backend.app.services.llm_provider import get_chat_llm
from backend.app.services.vector_store import get_vectorstore

logger = logging.getLogger(__name__)

# MarkItDown 输出为 Markdown，优先在标题与段落边界切分
_MD_SPLITTERS = ["\n## ", "\n### ", "\n#### ", "\n\n", "\n", " ", ""]

# MarkItDown 模块级单例
_md_instance: MarkItDown | None = None


def _get_markitdown() -> MarkItDown:
    """获取 MarkItDown 单例实例"""
    global _md_instance
    if _md_instance is None:
        _md_instance = MarkItDown()
    return _md_instance


def _load_single_file(file_path: str) -> str:
    md = _get_markitdown()
    result = md.convert(file_path)
    return result.text_content or ""


def _strip_text(text: str) -> str:
    return text.strip()


def _total_chars(text: str) -> int:
    return len(text)


def _markdown_segment_count(text: str) -> int:
    """按空行分段粗算段落数，供 ETL Agent 参考。"""
    parts = [p for p in text.split("\n\n") if p.strip()]
    return max(1, len(parts))


def _plan_split_strategy(total: int) -> str:
    if total <= 0:
        return "empty"
    if total <= settings.chunk_size:
        return "single_chunk"
    if total <= settings.chunk_size * 4:
        return "short_recursive"
    return "full_recursive"


def _splitter(chunk_size: int, chunk_overlap: int) -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=_MD_SPLITTERS,
    )


def _split_text(text: str) -> List[str]:
    """启发式切分（Agent 未给出参数时的回退）。"""
    text = _strip_text(text)
    total = _total_chars(text)
    strategy = _plan_split_strategy(total)

    if strategy == "empty":
        return []

    overlap_cap = max(0, settings.chunk_size // 2 - 1)
    overlap = min(settings.chunk_overlap, overlap_cap)

    if strategy == "single_chunk":
        return [text] if text else []

    if strategy == "short_recursive":
        dynamic_size = min(max(settings.chunk_size, total // 2 + 1), total)
        overlap = min(overlap, max(0, dynamic_size // 5))
        splitter = _splitter(dynamic_size, overlap)
        chunks = splitter.split_text(text)
    else:
        splitter = _splitter(settings.chunk_size, overlap)
        chunks = splitter.split_text(text)

    return [c for c in chunks if c.strip()]


def _apply_agent_params_text(text: str, p: Dict[str, Any]) -> List[str]:
    """按 Agent 提交的参数对 Markdown 文本切分。"""
    text = _strip_text(text)
    if not text:
        return []
    if p.get("use_single_chunk"):
        return [text]
    cs = max(50, int(p.get("chunk_size", settings.chunk_size)))
    co = max(0, int(p.get("chunk_overlap", settings.chunk_overlap)))
    co = min(co, max(0, cs // 2 - 1))
    splitter = _splitter(cs, co)
    return [c for c in splitter.split_text(text) if c.strip()]


# 短文本阈值：<= 1600 字符时跳过 LLM Agent 调用
_SHORT_TEXT_THRESHOLD = 1600


def _run_etl_agent(file_path: str, body: str) -> Dict[str, Any] | None:
    """
    由 LLM 直接决定 chunk_size / chunk_overlap / use_single_chunk。
    直接调用 LLM 并解析 JSON 结果；失败则返回 None 走回退逻辑。
    """
    body = _strip_text(body)
    total = _total_chars(body)  # 字符数量

    # 短文本跳过 LLM 调用，直接返回 None 走启发式切分
    if total <= _SHORT_TEXT_THRESHOLD:
        logger.debug(f"File {os.path.basename(file_path)} has only {total} chars, skipping LLM agent")
        return None

    nseg = _markdown_segment_count(body)  # 段落数量
    ext = os.path.splitext(file_path)[1].lower()
    preview = body[:600].replace("\n", " ") if body else ""

    user_prompt = build_etl_user_prompt(
        os.path.basename(file_path),
        ext,
        nseg,
        total,
        settings.chunk_size,
        settings.chunk_overlap,
        preview,
    )

    try:
        llm = get_chat_llm()
        messages = [
            SystemMessage(content=ETL_AGENT_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]
        response: ChatResult = llm.invoke(messages)
        content = response.content if hasattr(response, 'content') else str(response)

        logger.debug(f"ETL LLM output for {os.path.basename(file_path)}: {content}")

        # 解析 JSON 结果
        params = _parse_etl_params(content)
        if params:
            return params

    except Exception as e:
        logger.warning(f"ETL LLM failed for {os.path.basename(file_path)}, using fallback: {e}")

    return None


def _parse_etl_params(content: str) -> Dict[str, Any] | None:
    """从 LLM 输出中解析切分参数 JSON。"""
    # 尝试提取 JSON 对象
    patterns = [
        r'\{[^{}]*"chunk_size"\s*:\s*\d+[^{}]*"use_single_chunk"\s*:\s*(?:true|false)[^{}]*\}',
        r'```json\s*(\{[^}]+\})\s*```',
        r'```\s*(\{[^}]+\})\s*```',
    ]

    for pattern in patterns:
        match = re.search(pattern, content, re.DOTALL)
        if match:
            json_str = match.group(1) if match.lastindex else match.group(0)
            try:
                params = json.loads(json_str)
                # 验证必要字段
                if "chunk_size" in params and "use_single_chunk" in params:
                    params["chunk_overlap"] = params.get("chunk_overlap", settings.chunk_overlap)
                    # 简单验证
                    cs = int(params["chunk_size"])
                    co = int(params["chunk_overlap"])
                    single = bool(params["use_single_chunk"])
                    if 50 <= cs <= 32000 and 0 <= co < cs:
                        return params
            except (json.JSONDecodeError, ValueError, KeyError):
                continue

    # 尝试直接在内容中查找 JSON
    json_match = re.search(r'\{[^{}]+\}', content, re.DOTALL)
    if json_match:
        try:
            params = json.loads(json_match.group())
            if "chunk_size" in params and "use_single_chunk" in params:
                params["chunk_overlap"] = params.get("chunk_overlap", settings.chunk_overlap)
                return params
        except json.JSONDecodeError:
            pass

    return None


def _text_chunks_to_documents(chunks: List[str], source_name: str) -> List[Document]:
    """仅在写入向量库前转为 LangChain Document。"""
    out: List[Document] = []
    for idx, page_content in enumerate(chunks):
        out.append(
            Document(
                page_content=page_content,
                metadata={
                    "source": source_name,
                    "file_name": source_name,
                    "chunk_id": idx,
                },
            )
        )
    return out


def run_document_etl(file_path: str) -> int:
    """
    文档 ETL（MarkItDown → Markdown 文本 → Agent 驱动切分 → 向量库）：
    1) 加载并转为 Markdown 字符串
    2) 由 Agent 决定切分参数（失败则启发式回退）
    3) 生成向量并写入向量数据库

    Note: This is a synchronous function that runs in a thread pool for async usage.
    """
    logger.info(f"[ETL] 开始处理文件: {os.path.basename(file_path)}")
    
    n_chunks = 0
    file_name = os.path.basename(file_path)

    try:
        raw = _load_single_file(file_path)
        text = _strip_text(raw)
        if not text:
            logger.warning(f"File {file_name} has no valid text, skipping")
            return 0

        agent_params = _run_etl_agent(file_path, text)
        if agent_params:
            chunk_texts = _apply_agent_params_text(text, agent_params)
            strat = f"agentic"
        else:
            chunk_texts = _split_text(text)
            strat = f"fallback_{_plan_split_strategy(_total_chars(text))}"

        logger.info(f"File {file_name} strategy={strat}, split into {len(chunk_texts)} chunks")

        if len(chunk_texts) > 64:
            logger.warning(f"File {file_name} exceeds 64 chunks, processing in batches of 50")

        chunks = _text_chunks_to_documents(chunk_texts, file_name)

        if not chunks:
            logger.warning(f"File {file_name} has no valid chunks after splitting, skipping")
            return 0

        logger.info(f"[ETL] 文本提取完成: {file_name}, 字符数: {len(text)}")
        
        vectorstore = get_vectorstore()
        logger.info(f"[VectorStore] 开始向量化: {file_name}")
        BATCH_SIZE = 50
        total_chunks = len(chunks)

        for i in range(0, total_chunks, BATCH_SIZE):
            batch = chunks[i : i + BATCH_SIZE]
            vectorstore.add_documents(batch)
            logger.debug(f"Added {len(batch)} chunks ({i+1}-{min(i+BATCH_SIZE, total_chunks)}/{total_chunks})")

        n_chunks = total_chunks
        logger.info(f"Successfully processed {file_name}: {n_chunks} chunks added to vector store")

    except Exception as e:
        logger.error(f"Failed to process file {file_name}: {e}")
        return n_chunks

    return n_chunks


async def run_document_etl_async(file_path: str) -> int:
    """Async wrapper for run_document_etl to avoid blocking the event loop."""
    return await asyncio.to_thread(run_document_etl, file_path)
