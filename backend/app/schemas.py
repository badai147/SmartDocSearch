from typing import List, Optional

from pydantic import BaseModel, Field


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

