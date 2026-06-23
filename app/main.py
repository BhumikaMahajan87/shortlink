"""ShortLink FastAPI application entrypoint.

Run locally with:  uvicorn app.main:app --reload
Then open:          http://localhost:8000/        (web UI)
                    http://localhost:8000/docs     (interactive API)
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.routes import api_router, redirect_router

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="A scalable URL shortener with click analytics, caching and rate limiting.",
)

_STATIC_DIR = Path(__file__).parent / "static"
if _STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def index() -> str:
    index_file = _STATIC_DIR / "index.html"
    if index_file.exists():
        return index_file.read_text(encoding="utf-8")
    return "<h1>ShortLink</h1><p>See <a href='/docs'>/docs</a>.</p>"


# API routes first, then the catch-all redirect route last so it never
# shadows /api, /docs, etc.
app.include_router(api_router)
app.include_router(redirect_router)
