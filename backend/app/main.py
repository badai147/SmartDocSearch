from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.routes.chat import router as chat_router
from backend.app.routes.documents import router as documents_router


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)

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

