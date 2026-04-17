from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class SSEEventType(str, Enum):
    """SSE 流式事件类型"""
    THINKING = "thinking"      # 思考阶段（问题改写、意图分析等）
    SEARCHING = "searching"    # 检索阶段
    ANSWER = "answer"          # 最终答案片段
    SOURCES = "sources"       # 参考来源
    ERROR = "error"            # 错误信息
    DONE = "done"              # 流结束标记


class SourceInfo(BaseModel):
    source: str
    page: Optional[int] = None
    snippet: Optional[str] = None


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, description="用户问题")
    top_k: Optional[int] = Field(None, ge=1, le=20, description="返回的最相关片段数量")


class AskResponse(BaseModel):
    answer: str
    sources: List[SourceInfo] = []


class IngestResponse(BaseModel):
    ingested_files: List[str]
    failed_files: List[str] = []

