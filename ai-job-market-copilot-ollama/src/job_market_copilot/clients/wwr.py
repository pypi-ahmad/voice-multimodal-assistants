"""We Work Remotely RSS client."""

from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from job_market_copilot.config import Settings

WWR_RSS_URL = "https://weworkremotely.com/remote-jobs.rss"


@retry(wait=wait_exponential(min=1, max=8), stop=stop_after_attempt(3), reraise=True)
async def _fetch_text(url: str, timeout: float, user_agent: str) -> str:
    async with httpx.AsyncClient(timeout=timeout, headers={"User-Agent": user_agent}) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.text


def _strip_html(raw_html: str) -> str:
    clean = re.sub(r"<[^>]+>", " ", raw_html)
    clean = html.unescape(clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def _parse_item(item: ET.Element) -> dict[str, Any]:
    title_raw = item.findtext("title", default="").strip()
    if ":" in title_raw:
        company, title = [x.strip() for x in title_raw.split(":", maxsplit=1)]
    else:
        company, title = "Unknown", title_raw

    description_html = item.findtext("description", default="")
    description = _strip_html(description_html)

    skills_text = item.findtext("skills", default="")
    tags = [s.strip() for s in skills_text.split(",") if s.strip()]

    return {
        "id": item.findtext("guid", default="") or item.findtext("link", default=""),
        "company": company or "Unknown",
        "title": title or "Unknown",
        "url": item.findtext("link", default=""),
        "published": item.findtext("pubDate", default=""),
        "location": item.findtext("region", default=""),
        "category": item.findtext("category", default=""),
        "employment_type": item.findtext("type", default=""),
        "description": description,
        "tags": tags,
    }


async def fetch_wwr_jobs(settings: Settings) -> list[dict[str, Any]]:
    """Fetch and parse We Work Remotely RSS jobs."""
    xml_text = await _fetch_text(
        url=WWR_RSS_URL,
        timeout=settings.request_timeout_seconds,
        user_agent=settings.user_agent,
    )
    root = ET.fromstring(xml_text)
    items = root.findall("./channel/item")
    jobs = [_parse_item(item) for item in items]
    return jobs[: settings.max_jobs_per_source]


def save_raw_payload(path: Path, payload: list[dict[str, Any]]) -> None:
    """Persist parsed RSS payload."""
    import json

    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
