from __future__ import annotations

import os
from typing import Any, Dict, List

from langchain.agents import create_agent
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from markitdown import MarkItDown

from backend.app.core.config import settings
from backend.app.prompts.etl import ETL_AGENT_SYSTEM_PROMPT, build_etl_user_prompt
from backend.app.services.llm_provider import get_chat_llm
from backend.app.services.vector_store import get_vectorstore
from backend.app.tools.etl_finalize import create_finalize_etl_params_tool

# MarkItDown 输出为 Markdown，优先在标题与段落边界切分
_MD_SPLITTERS = ["\n## ", "\n### ", "\n#### ", "\n\n", "\n", " ", ""]


def _load_single_file(file_path: str) -> str:
    md = MarkItDown()
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


def _run_etl_agent(file_path: str, body: str) -> Dict[str, Any] | None:
    """
    由 LLM Agent 决定 chunk_size / chunk_overlap / use_single_chunk。
    必须通过工具 finalize_etl_params 提交一次 JSON；失败则返回 None 走回退逻辑。
    """
    body = _strip_text(body)
    total = _total_chars(body)
    nseg = _markdown_segment_count(body)
    ext = os.path.splitext(file_path)[1].lower()
    preview = body[:600].replace("\n", " ") if body else ""

    holder: Dict[str, Any] = {}
    finalize_etl_params = create_finalize_etl_params_tool(holder)

    llm = get_chat_llm()
    agent = create_agent(
        model=llm,
        tools=[finalize_etl_params],
        system_prompt=ETL_AGENT_SYSTEM_PROMPT,
    )

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
        response = agent.invoke(
            {"messages": [{"role": "user", "content": user_prompt}]},
            config={"recursion_limit": 25},
        )

        print(f"ETL Agent 输出：")
        print(response)
        print("--------------------------------------------------------")

    except Exception as e:
        print(f"⚠️ ETL Agent 调用失败，将使用启发式回退: {e}")
        return None

    return dict(holder) if holder else None


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
    """
    n_chunks = 0
    try:
        raw = _load_single_file(file_path)
        text = _strip_text(raw)
        if not text:
            print(f"⚠️ 文件 {os.path.basename(file_path)} 无有效文本，已跳过写入向量库")
            return 0

        agent_params = _run_etl_agent(file_path, text)
        if agent_params:
            chunk_texts = _apply_agent_params_text(text, agent_params)
            strat = f"agentic {agent_params}"
        else:
            chunk_texts = _split_text(text)
            strat = f"fallback {_plan_split_strategy(_total_chars(text))}"

        print(
            f"📄 文件 {os.path.basename(file_path)} "
            f"策略={strat}，切分为 {len(chunk_texts)} 个块"
        )
        if len(chunk_texts) > 64:
            print("⚠️ 超过 OpenAI 64条限制，将分批处理（每批50条）")

        source_name = os.path.basename(file_path)
        chunks = _text_chunks_to_documents(chunk_texts, source_name)

        if not chunks:
            print(f"⚠️ 文件 {os.path.basename(file_path)} 切分后无有效块，已跳过写入向量库")
            return 0

        vectorstore = get_vectorstore()
        BATCH_SIZE = 50
        total_chunks = len(chunks)

        for i in range(0, total_chunks, BATCH_SIZE):
            batch = chunks[i : i + BATCH_SIZE]
            vectorstore.add_documents(batch)
            print(
                f"已添加 {len(batch)} 个块 ({i+1}-{min(i+BATCH_SIZE, total_chunks)}/{total_chunks})"
            )

        n_chunks = total_chunks

    except Exception as e:
        print(f"⚠️ 文件 {os.path.basename(file_path)} 处理失败：{e}")
        return n_chunks

    try:
        get_vectorstore().persist()
    except Exception:
        pass

    return n_chunks
