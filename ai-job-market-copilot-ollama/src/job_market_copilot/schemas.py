"""Typed schema definitions."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CanonicalJob(BaseModel):
    """Canonical normalized job record."""

    source_job_id: str
    source: str
    title: str
    company: str
    url: str
    published_at: datetime | None = None
    location: str | None = None
    category: str | None = None
    raw_description: str
    salary_text: str | None = None
    employment_type: str | None = None
    tags: list[str] = Field(default_factory=list)


class EnrichmentResult(BaseModel):
    """LLM-enriched role metadata."""

    role_family: str
    seniority: str
    core_skills: list[str] = Field(default_factory=list)
    tooling: list[str] = Field(default_factory=list)
    summary: str
    compensation_signal: str
    model_source: str
