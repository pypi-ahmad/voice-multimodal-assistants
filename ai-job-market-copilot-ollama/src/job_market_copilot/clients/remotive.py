"""Remotive API client."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from job_market_copilot.config import Settings

REMOTIVE_URL = "https://remotive.com/api/remote-jobs"


@retry(wait=wait_exponential(min=1, max=8), stop=stop_after_attempt(3), reraise=True)
async def _fetch_json(url: str, timeout: float, user_agent: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=timeout, headers={"User-Agent": user_agent}) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()


async def fetch_remotive_jobs(settings: Settings) -> list[dict[str, Any]]:
    """Fetch live jobs from Remotive.

    Args:
        settings: Runtime settings.

    Returns:
        Raw Remotive job dictionaries.
    """
    payload = await _fetch_json(
        url=REMOTIVE_URL,
        timeout=settings.request_timeout_seconds,
        user_agent=settings.user_agent,
    )
    jobs = payload.get("jobs", [])
    return jobs[: settings.max_jobs_per_source]


def save_raw_payload(path: Path, payload: list[dict[str, Any]]) -> None:
    """Persist raw API payload for reproducibility."""
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
