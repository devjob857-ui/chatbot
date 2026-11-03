from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import chat, health
from app.core.config import get_settings

# app/main.py -> app -> backend -> src. La UI está en src/frontend.
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(title="Medicalidad AI", version="0.1.0")

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_methods=["GET", "POST"],
            allow_headers=["Content-Type"],
        )

    # Las rutas de API se registran antes que la UI estática para que tengan prioridad.
    app.include_router(health.router)
    app.include_router(chat.router)

    # La UI se sirve desde la raíz. Debe montarse al final.
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

    return app


app = create_app()
