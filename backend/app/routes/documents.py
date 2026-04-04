import os
from pathlib import Path
from typing import List

from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.app.core.config import settings
from backend.app.services.etl import run_document_etl


router = APIRouter(prefix="/api/docs", tags=["documents"])


def _safe_filename(name: str) -> str:
    # 简单处理路径分隔符与特殊字符，避免目录穿越
    name = name.replace("\\", "_").replace("/", "_")
    return name


@router.post("/ingest")
async def ingest(files: List[UploadFile] = File(...)):
    docs_dir = Path(settings.docs_dir)
    docs_dir.mkdir(parents=True, exist_ok=True)

    ingested: List[str] = []
    failed: List[str] = []

    for f in files:
        if not f.filename:
            continue

        filename = _safe_filename(f.filename)
        dest_path = docs_dir / filename
        try:
            content = await f.read()
            with open(dest_path, "wb") as out:
                out.write(content)

            run_document_etl(str(dest_path))
            ingested.append(filename)
        except Exception as e:
            failed.append(filename)
            print(e)

    if not ingested and failed:
        raise HTTPException(status_code=400, detail={"failed_files": failed})

    return {"ingested_files": ingested, "failed_files": failed}

