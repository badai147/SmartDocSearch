import asyncio
import logging
from pathlib import Path
from typing import List

from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.app.core.config import settings
from backend.app.services.etl import run_document_etl_async
from backend.app.services.vector_store import delete_documents_by_source

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/docs", tags=["documents"])


def _safe_filename(name: str) -> str:
    # 简单处理路径分隔符与特殊字符，避免目录穿越
    name = name.replace("\\", "_").replace("/", "_")
    return name


def _validate_file(f: UploadFile) -> tuple[bool, str]:
    """Validate file before processing.

    Returns:
        (is_valid, error_message)
    """
    if not f.filename:
        return False, "Filename is empty"

    # Check file extension
    ext = Path(f.filename).suffix.lower()
    if ext not in settings.allowed_file_extensions:
        allowed = ", ".join(settings.allowed_file_extensions)
        return False, f"File type '{ext}' not allowed. Allowed: {allowed}"

    return True, ""


# 并发处理文件的最大数量（单文件上传限制为1）
MAX_CONCURRENT_INGEST = 1


async def _process_single_file(f: UploadFile, docs_dir: Path) -> tuple[str, bool, str | None]:
    """处理单个文件，返回 (filename, success, error_message)"""
    logger.info("[Document] 进入_process_single_file")
    
    is_valid, error_msg = _validate_file(f)
    if not is_valid:
        return f.filename or "unknown", False, error_msg

    logger.info(f"[Document] 验证文件成功")

    filename = _safe_filename(f.filename)
    dest_path = docs_dir / filename
    try:
        content = await f.read()

        # Check file size
        file_size_mb = len(content) / (1024 * 1024)
        if file_size_mb > settings.max_file_size_mb:
            return filename, False, f"File too large ({file_size_mb:.1f}MB). Maximum {settings.max_file_size_mb}MB allowed"

        with open(dest_path, "wb") as out:
            out.write(content)

        # Delete existing documents with same source before re-ingesting
        delete_documents_by_source(filename)

        logger.info(f"[Document] 删除成功")
        
        # Run ETL in thread pool to avoid blocking event loop
        await run_document_etl_async(str(dest_path))
        logger.info(f"Successfully ingested file: {filename}")
        return filename, True, None
    except Exception as e:
        logger.error(f"Failed to ingest file {filename}: {e}")
        return filename, False, str(e)


@router.post("/ingest")
async def ingest(files: List[UploadFile] = File(...)):
    logger.info(f"[Documents] 开始处理 {len(files)} 个文件")
    # Validate file count (单文件上传限制)
    if len(files) > 1:
        raise HTTPException(
            status_code=400,
            detail="只支持单文件上传，请一次选择一个文件"
        )
    if len(files) == 0:
        raise HTTPException(
            status_code=400,
            detail="请选择要上传的文件"
        )

    docs_dir = Path(settings.docs_dir)
    docs_dir.mkdir(parents=True, exist_ok=True)

    ingested: List[str] = []
    failed: List[dict] = []

    # 使用信号量限制并发数量
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_INGEST)

    async def process_with_semaphore(f: UploadFile) -> tuple[str, bool, str | None]:
        async with semaphore:
            return await _process_single_file(f, docs_dir)

    # 并发执行所有文件处理
    tasks = [process_with_semaphore(f) for f in files]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, Exception):
            failed.append({"filename": "unknown", "error": str(result)})
        else:
            filename, success, error = result
            if success:
                ingested.append(filename)
            else:
                failed.append({"filename": filename, "error": error})

    if not ingested and failed:
        raise HTTPException(status_code=400, detail={"failed_files": failed})

    logger.info(f"[Documents] 处理完成: 成功 {len(ingested)} 个, 失败 {len(failed)} 个")
    
    return {"ingested_files": ingested, "failed_files": failed}

