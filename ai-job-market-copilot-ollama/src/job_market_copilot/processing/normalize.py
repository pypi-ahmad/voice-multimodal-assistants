"""Normalization and deduplication logic."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import polars as pl
from dateutil import parser as date_parser


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = date_parser.parse(value)
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed
    except (ValueError, TypeError):
        return None


def _clean_text(value: str | None) -> str:
    if not value:
        return ""
    value = re.sub(r"\s+", " ", value).strip()
    return value


def _canonical_url(url: str) -> str:
    parsed = urlparse(url.strip())
    normalized_path = parsed.path.rstrip("/") or "/"
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{normalized_path}"


def _fallback_id(source: str, title: str, company: str, url: str) -> str:
    digest = hashlib.sha256(f"{source}|{title}|{company}|{url}".encode("utf-8")).hexdigest()[:16]
    return digest


def normalize_records(remotive_jobs: list[dict[str, Any]], wwr_jobs: list[dict[str, Any]]) -> pl.DataFrame:
    """Normalize jobs from both providers into one table."""
    records: list[dict[str, Any]] = []

    for job in remotive_jobs:
        title = _clean_text(job.get("title"))
        company = _clean_text(job.get("company_name")) or "Unknown"
        url = _clean_text(job.get("url"))
        records.append(
            {
                "source_job_id": str(job.get("id") or _fallback_id("remotive", title, company, url)),
                "source": "remotive",
                "title": title,
                "company": company,
                "url": url,
                "canonical_url": _canonical_url(url) if url else "",
                "published_at": _parse_date(job.get("publication_date")),
                "location": _clean_text(job.get("candidate_required_location")),
                "category": _clean_text(job.get("category")),
                "raw_description": _clean_text(job.get("description")),
                "salary_text": _clean_text(job.get("salary")),
                "employment_type": _clean_text(job.get("job_type")),
                "tags": job.get("tags") if isinstance(job.get("tags"), list) else [],
            }
        )

    for job in wwr_jobs:
        title = _clean_text(job.get("title"))
        company = _clean_text(job.get("company")) or "Unknown"
        url = _clean_text(job.get("url"))
        records.append(
            {
                "source_job_id": str(job.get("id") or _fallback_id("wwr", title, company, url)),
                "source": "wwr",
                "title": title,
                "company": company,
                "url": url,
                "canonical_url": _canonical_url(url) if url else "",
                "published_at": _parse_date(job.get("published")),
                "location": _clean_text(job.get("location")),
                "category": _clean_text(job.get("category")),
                "raw_description": _clean_text(job.get("description")),
                "salary_text": "",
                "employment_type": _clean_text(job.get("employment_type")),
                "tags": job.get("tags") if isinstance(job.get("tags"), list) else [],
            }
        )

    return pl.from_dicts(records)


def deduplicate_records(df: pl.DataFrame) -> pl.DataFrame:
    """Deduplicate records using canonical URL and title/company fallback."""
    if df.is_empty():
        return df

    dedup_key = pl.when(pl.col("canonical_url").str.len_chars() > 0).then(
        pl.col("canonical_url")
    ).otherwise(
        (pl.col("title").str.to_lowercase() + "|" + pl.col("company").str.to_lowercase())
    )

    ranked = df.with_columns(
        dedup_key.alias("dedup_key"),
        pl.col("published_at").fill_null(datetime(1970, 1, 1)).alias("published_rank"),
    ).sort(["dedup_key", "published_rank"], descending=[False, True])

    return ranked.unique(subset=["dedup_key"], keep="first").drop(["published_rank"])
