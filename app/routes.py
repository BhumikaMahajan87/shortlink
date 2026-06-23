"""API + redirect routes for ShortLink."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

from app.config import get_settings
from app.deps import get_rate_limiter, get_service
from app.schemas import ShortenRequest, ShortenResponse, StatsResponse
from app.service import InvalidURL

api_router = APIRouter(prefix="/api")
redirect_router = APIRouter()

# Reserved paths that must never be treated as short codes.
_RESERVED = {"api", "docs", "openapi.json", "redoc", "static", "health", "favicon.ico"}


def _client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@api_router.get("/health")
def health() -> dict:
    return {"status": "ok", "links": get_service().total_links()}


@api_router.post("/shorten", response_model=ShortenResponse, status_code=201)
def shorten(payload: ShortenRequest, request: Request) -> ShortenResponse:
    settings = get_settings()
    if settings.rate_limit_enabled:
        limiter = get_rate_limiter()
        if not limiter.allow(_client_key(request)):
            raise HTTPException(status_code=429, detail="Rate limit exceeded. Slow down.")
    try:
        result = get_service().shorten(payload.url)
    except InvalidURL as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ShortenResponse(**result.__dict__)


@api_router.get("/stats/{code}", response_model=StatsResponse)
def stats(code: str) -> StatsResponse:
    data = get_service().stats(code)
    if data is None:
        raise HTTPException(status_code=404, detail="Short code not found")
    return StatsResponse(**data)


@redirect_router.get("/{code}", include_in_schema=False)
def redirect(code: str, request: Request) -> RedirectResponse:
    if code in _RESERVED:
        raise HTTPException(status_code=404, detail="Not found")
    long_url = get_service().resolve(
        code,
        referer=request.headers.get("referer"),
        user_agent=request.headers.get("user-agent"),
    )
    if long_url is None:
        raise HTTPException(status_code=404, detail="Short link not found")
    # 302 so analytics capture every click instead of browsers caching a 301.
    return RedirectResponse(url=long_url, status_code=302)
