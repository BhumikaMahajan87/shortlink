"""Pydantic request/response models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ShortenRequest(BaseModel):
    url: str = Field(..., examples=["https://example.com/some/very/long/path?with=query"])


class ShortenResponse(BaseModel):
    code: str
    short_url: str
    long_url: str
    created: bool = Field(..., description="False if an existing short code was reused")


class ClickModel(BaseModel):
    timestamp: str
    referer: str | None = None
    user_agent: str | None = None


class StatsResponse(BaseModel):
    code: str
    short_url: str
    long_url: str
    created_at: str
    clicks: int
    recent_clicks: list[ClickModel]
