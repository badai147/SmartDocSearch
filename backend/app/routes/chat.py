from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from backend.app.schemas import AskRequest
from backend.app.services.rag import answer_with_rag, stream_answer_with_rag


router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/ask")
def ask(req: AskRequest):
    try:
        result = answer_with_rag(req.question, top_k=req.top_k)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ask/stream")
def ask_stream(req: AskRequest):
    try:
        generator = stream_answer_with_rag(req.question, top_k=req.top_k)
        return StreamingResponse(generator, media_type="text/plain; charset=utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

