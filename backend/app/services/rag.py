from __future__ import annotations

import asyncio
import json
import time
from typing import AsyncGenerator, List

from langchain.agents import create_agent
from langchain.messages import AIMessageChunk

from backend.app.core.config import settings
from backend.app.prompts.rag import RAG_SYSTEM_PROMPT, build_rag_user_prompt
from backend.app.schemas import SSEEventType, SourceInfo
from backend.app.services.llm_provider import get_chat_llm
from backend.app.services.query_enhancer import enhance_queries
from backend.app.services.vector_store import get_vectorstore
from backend.app.tools.rag_search import create_search_docs_tool


def _sse_message(event: SSEEventType, data: dict | str) -> str:
    """构建 SSE 格式消息"""
    if isinstance(data, str):
        content = data
    else:
        content = json.dumps(data, ensure_ascii=False)
    return f"event: {event.value}\ndata: {content}\n\n"


def _sse_heartbeat() -> str:
    """发送心跳保活连接"""
    return ": heartbeat\n\n"


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


async def stream_answer_with_rag(question: str, top_k: int | None = None):
    """
    流式 RAG 回答，包含思考过程输出。

    流程：
    1. 发送思考阶段消息（问题改写）
    2. 发送检索阶段消息
    3. 流式发送答案片段
    4. 发送参考来源
    5. 发送完成标记

    使用 SSE (Server-Sent Events) 协议，支持不同类型的消息事件。
    """
    top_k = top_k or settings.top_k

    # 初始化组件
    vectorstore = get_vectorstore()
    llm = get_chat_llm()

    # 检查是否收到取消信号
    try:
        loop = asyncio.get_running_loop()
        is_cancelled = False
        try:
            # 尝试在循环开始前检查取消状态
            current_task = asyncio.current_task()
            if current_task and current_task.done():
                return
        except RuntimeError:
            pass
    except RuntimeError:
        pass

    start_time = time.time()

    try:
        # 阶段1: 发送思考消息 - 问题改写
        yield _sse_message(SSEEventType.THINKING, {
            "stage": "query_rewrite",
            "message": "正在分析并改写问题，以便更精准地检索相关文档...",
            "thinking": None
        })

        # 执行问题改写
        rewrite_start = time.time()
        enhanced_queries = enhance_queries(question, n=settings.query_enhance_n)
        rewrite_time = time.time() - rewrite_start

        # 发送改写结果
        yield _sse_message(SSEEventType.THINKING, {
            "stage": "query_rewrite_done",
            "message": "问题已优化",
            "thinking": "我将用以下查询词检索相关文档：\n" + "\n".join(f"• {q}" for q in enhanced_queries),
            "rewrite_time": round(rewrite_time, 2)
        })

        # 心跳保活
        yield _sse_heartbeat()

        # 阶段2: 发送检索准备消息
        yield _sse_message(SSEEventType.SEARCHING, {
            "message": f"正在检索相关文档片段（top_k={top_k}）...",
            "query_count": len(enhanced_queries)
        })

        # 创建搜索工具
        used_sources: List[dict] = []
        search_docs = create_search_docs_tool(
            vectorstore, top_k, used_sources, max_chars=8000
        )

        # 创建 Agent
        agent = create_agent(
            model=llm,
            tools=[search_docs],
            system_prompt=RAG_SYSTEM_PROMPT,
        )

        user_prompt = build_rag_user_prompt(question, enhanced_queries)

        # 发送检索开始消息
        yield _sse_message(SSEEventType.SEARCHING, {
            "message": "检索完成，正在分析文档内容并生成回答...",
            "query_count": len(enhanced_queries)
        })

        # 心跳保活
        yield _sse_heartbeat()

        # 阶段3: 流式发送答案（使用异步迭代）
        answer_buffer = ""
        last_chunk_time = time.time()

        # 将同步流转换为异步迭代，每步检查取消状态
        for token, _ in agent.stream(
            {"messages": [{"role": "user", "content": user_prompt}]},
            stream_mode="messages",
        ):
            # 定期让出控制权，允许信号处理
            await asyncio.sleep(0)

            if not isinstance(token, AIMessageChunk):
                continue
            text_blocks = [b for b in token.content_blocks if b["type"] == "text"]
            if text_blocks:
                chunk = text_blocks[0]["text"]
                answer_buffer += chunk

                # 定期发送心跳和状态更新
                current_time = time.time()
                if current_time - last_chunk_time > 5:
                    yield _sse_heartbeat()
                    last_chunk_time = current_time

                # 流式发送答案片段
                yield _sse_message(SSEEventType.ANSWER, {
                    "delta": chunk,
                    "is_first": len(answer_buffer) == len(chunk)
                })

        # 阶段4: 发送参考来源
        if used_sources:
            sources_data = [
                SourceInfo(
                    source=s.get("source", ""),
                    page=s.get("page"),
                    snippet=s.get("snippet")
                ).model_dump()
                for s in used_sources[:top_k]
            ]
            yield _sse_message(SSEEventType.SOURCES, {
                "sources": sources_data,
                "count": len(sources_data)
            })
        else:
            yield _sse_message(SSEEventType.THINKING, {
                "stage": "no_sources",
                "message": "未找到相关文档片段",
                "thinking": "在已导入的文档中未找到与您问题相关的内容，请尝试：\n• 换一种问法\n• 确认文档已成功导入"
            })

        # 阶段5: 发送完成标记
        total_time = time.time() - start_time
        yield _sse_message(SSEEventType.DONE, {
            "total_time": round(total_time, 2),
            "source_count": len(used_sources),
            "answer_length": len(answer_buffer)
        })

    except asyncio.CancelledError:
        # 处理取消信号
        yield _sse_message(SSEEventType.ERROR, {
            "message": "请求已被用户取消",
            "code": "CANCELLED"
        })
        raise
    except Exception as e:
        # 发送错误消息
        yield _sse_message(SSEEventType.ERROR, {
            "message": f"处理过程中发生错误：{str(e)}",
            "code": "PROCESSING_ERROR"
        })
        raise
