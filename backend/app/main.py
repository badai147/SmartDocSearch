import asyncio
import logging
import signal
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.routes.chat import router as chat_router
from backend.app.routes.documents import router as documents_router


def setup_logging():
    """配置日志系统，输出到控制台"""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    # 设置第三方库的日志级别，减少噪音
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('uvicorn.access').setLevel(logging.INFO)


setup_logging()
logger = logging.getLogger(__name__)

logger.info(f"嵌入模型：{settings.embedding_model}")
logger.info(f"嵌入API密钥：{'已设置' if settings.embedding_api_key else '未设置'}")
logger.info(f"嵌入API基础URL：{settings.embedding_base_url}")
logger.info(f"LLM模型：{settings.llm_model}")
logger.info(f"LLM API密钥：{'已设置' if settings.llm_api_key else '未设置'}")
logger.info(f"LLM API基础URL：{settings.llm_base_url}")


def create_app() -> FastAPI:
    shutdown_event = None

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # 存储关闭事件引用
        nonlocal shutdown_event
        from fastapi import Request
        # 创建一个事件用于通知关闭
        shutdown_event = asyncio.Event()

        # 设置信号处理器
        def signal_handler(signum, frame):
            print(f"\n收到信号 {signum}，正在关闭...")
            if shutdown_event and not shutdown_event.is_set():
                shutdown_event.set()
            raise KeyboardInterrupt

        # 注册信号处理器（仅在非 Windows 平台有效）
        if sys.platform != "win32":
            signal.signal(signal.SIGTERM, signal_handler)
            signal.signal(signal.SIGINT, signal_handler)

        # 存储 shutdown_event 到 app state
        app.state.shutdown_event = shutdown_event

        yield

        # 清理资源
        if shutdown_event and not shutdown_event.is_set():
            shutdown_event.set()

    app = FastAPI(title=settings.app_name, lifespan=lifespan)

    cors_origins = settings.cors_allow_origins
    if cors_origins.strip() == "*":
        allow_origins = ["*"]
    else:
        allow_origins = [s.strip() for s in cors_origins.split(",") if s.strip()]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health():
        return {"status": "ok", "app": settings.app_name}

    app.include_router(documents_router)
    app.include_router(chat_router)
    return app


app = create_app()

