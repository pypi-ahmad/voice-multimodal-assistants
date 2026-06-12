"""Pipeline orchestration."""

from __future__ import annotations

import asyncio

import polars as pl
from loguru import logger

from job_market_copilot.analysis.metrics import compute_metrics, save_charts, save_metrics
from job_market_copilot.clients import remotive, wwr
from job_market_copilot.config import Settings
from job_market_copilot.processing.enrich import JobEnricher
from job_market_copilot.processing.normalize import deduplicate_records, normalize_records
from job_market_copilot.processing.relevance import score_relevance
from job_market_copilot.reporting.report import render_report


async def run_ingestion(settings: Settings) -> pl.DataFrame:
    """Fetch raw jobs and return normalized, deduplicated dataframe."""
    settings.ensure_directories()

    logger.info("Fetching live job feeds...")
    remotive_jobs, wwr_jobs = await asyncio.gather(
        remotive.fetch_remotive_jobs(settings),
        wwr.fetch_wwr_jobs(settings),
    )

    remotive.save_raw_payload(settings.resolved_raw_dir / "remotive_jobs.json", remotive_jobs)
    wwr.save_raw_payload(settings.resolved_raw_dir / "wwr_jobs.json", wwr_jobs)

    logger.info("Normalizing and deduplicating records...")
    normalized = normalize_records(remotive_jobs, wwr_jobs)
    deduped = deduplicate_records(normalized)
    deduped.write_parquet(settings.resolved_artifacts_dir / "jobs_normalized.parquet")

    logger.info("Ingestion complete: {} jobs after deduplication", deduped.height)
    return deduped


def run_relevance_filter(df: pl.DataFrame, settings: Settings) -> pl.DataFrame:
    """Apply rule-based relevance scoring and persist candidates."""
    scored = score_relevance(df, threshold=settings.ai_keyword_threshold)
    scored.write_parquet(settings.resolved_artifacts_dir / "jobs_scored.parquet")

    ai_candidates = scored.filter(pl.col("is_ai_role_rule"))
    ai_candidates.write_parquet(settings.resolved_artifacts_dir / "jobs_ai_candidates.parquet")
    logger.info("AI candidate jobs identified: {}", ai_candidates.height)
    return ai_candidates


def run_enrichment(ai_df: pl.DataFrame, settings: Settings) -> pl.DataFrame:
    """Enrich AI candidate jobs with Ollama metadata."""
    logger.info("Running Ollama enrichment with model {}", settings.ollama_model)
    enricher = JobEnricher(settings)
    enriched = enricher.enrich_dataframe(ai_df)
    enriched.write_parquet(settings.resolved_artifacts_dir / "ai_jobs_enriched.parquet")
    logger.info("Enrichment complete: {} rows", enriched.height)
    return enriched


def run_analytics(df_all: pl.DataFrame, df_ai: pl.DataFrame, settings: Settings) -> dict[str, object]:
    """Generate metrics, plots, and markdown report."""
    metrics = compute_metrics(df_all, df_ai)
    save_metrics(metrics, settings.resolved_artifacts_dir / "metrics.json")
    save_charts(df_ai, settings.resolved_artifacts_dir / "charts")

    report_path = settings.resolved_artifacts_dir / "reports" / "job_market_report.md"
    render_report(metrics, settings.ollama_model, report_path)

    # Export table snapshots for quick inspection (flatten list columns for CSV compatibility).
    preview_df = df_ai.head(200).with_columns(
        pl.col("core_skills").list.join(", ").alias("core_skills"),
        pl.col("tooling").list.join(", ").alias("tooling"),
        pl.col("tags").list.join(", ").alias("tags"),
    )
    preview_df.write_csv(settings.resolved_artifacts_dir / "tables" / "ai_jobs_preview.csv")
    logger.info("Analytics artifacts generated under {}", settings.resolved_artifacts_dir)
    return metrics


async def run_all(settings: Settings) -> dict[str, object]:
    """Run the full end-to-end pipeline."""
    df_all = await run_ingestion(settings)
    ai_candidates = run_relevance_filter(df_all, settings)
    enriched = run_enrichment(ai_candidates, settings)
    return run_analytics(df_all, enriched, settings)
