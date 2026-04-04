from __future__ import annotations

from typing import List

from langchain.agents import create_agent
from langchain.messages import AIMessageChunk

from backend.app.core.config import settings
from backend.app.prompts.rag import RAG_SYSTEM_PROMPT, build_rag_user_prompt
from backend.app.services.llm_provider import get_chat_llm
from backend.app.services.query_enhancer import enhance_queries
from backend.app.services.vector_store import get_vectorstore
from backend.app.tools.rag_search import create_search_docs_tool


def answer_with_rag(question: str, top_k: int | None = None) -> dict:
    """
    RAG（Retrieval-Augmented Generation）主流程：
    1) Query Enhancement：用 LLM 改写问题为多条检索查询
    2) 向量检索：在向量库中检索相关片段
    3) 生成：Agent 调用检索工具并结合上下文回答
    """
    top_k = top_k or settings.top_k

    vectorstore = get_vectorstore()
    llm = get_chat_llm()
    enhanced_queries = enhance_queries(question, n=settings.query_enhance_n)

    used_sources: List[dict] = []
    search_docs = create_search_docs_tool(
        vectorstore, top_k, used_sources, max_chars=8000
    )

    agent = create_agent(
        model=llm,
        tools=[search_docs],
        system_prompt=RAG_SYSTEM_PROMPT,
    )

    user_prompt = build_rag_user_prompt(question, enhanced_queries)
    result = agent.invoke({"messages": [{"role": "user", "content": user_prompt}]})

    print("回答数据：")
    print(result)
    print("---------------------------------------")

    messages = result.get("messages", [])
    answer = ""
    for m in reversed(messages):
        if getattr(m, "type", "") == "ai":
            answer = getattr(m, "content", "") or str(m)
            break
    if not answer:
        answer = "在已导入文档中未找到足够信息。"
    if not used_sources:
        answer = "在已导入文档中未找到足够信息。请尝试换个问法，或确认文档已成功导入。"

    return {"answer": answer, "sources": used_sources[:top_k]}


def stream_answer_with_rag(question: str, top_k: int | None = None):
    """
    与 answer_with_rag 逻辑保持一致，但通过 LangChain 的 stream 接口
    以流式形式返回答案文本。
    """
    top_k = top_k or settings.top_k

    vectorstore = get_vectorstore()
    llm = get_chat_llm()
    enhanced_queries = enhance_queries(question, n=settings.query_enhance_n)

    used_sources: List[dict] = []
    search_docs = create_search_docs_tool(
        vectorstore, top_k, used_sources, max_chars=8000
    )

    agent = create_agent(
        model=llm,
        tools=[search_docs],
        system_prompt=RAG_SYSTEM_PROMPT,
    )

    user_prompt = build_rag_user_prompt(question, enhanced_queries)

    def token_generator():
        yield "🔍 正在分析问题...\n"

        for token, _ in agent.stream(
            {"messages": [{"role": "user", "content": user_prompt}]},
            stream_mode="messages",
        ):
            if not isinstance(token, AIMessageChunk):
                continue
            text = [b for b in token.content_blocks if b["type"] == "text"]
            if text:
                yield text[0]["text"]

    return token_generator()
