import asyncio
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from backend.app.schemas import AskRequest
from backend.app.services.rag import answer_with_rag, stream_answer_with_rag

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/ask")
def ask(req: AskRequest):
    """非流式问答接口"""
    try:
        result = answer_with_rag(req.question, top_k=req.top_k)
        return result
    except Exception as e:
        logger.error(f"Ask error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ask/stream")
async def ask_stream(req: AskRequest):
    """
    流式问答接口，使用 SSE 协议返回思考过程和答案。

    返回的事件类型：
    - thinking: 思考阶段消息（如问题改写分析）
    - searching: 检索阶段消息
    - answer: 答案文本片段
    - sources: 参考来源列表
    - error: 错误消息
    - done: 流结束标记
    """
    try:
        generator = stream_answer_with_rag(req.question, top_k=req.top_k)
        return StreamingResponse(
            generator,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # 禁用 Nginx 等代理缓冲
            },
        )
    except Exception as e:
        logger.error(f"Stream ask error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

