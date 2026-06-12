"""Typer CLI for the job market copilot."""

from __future__ import annotations

import asyncio
import subprocess
import sys

import polars as pl
import typer
from loguru import logger

from job_market_copilot.config import get_settings
from job_market_copilot.logging_utils import configure_logging
from job_market_copilot.pipeline import run_all, run_analytics, run_enrichment, run_ingestion, run_relevance_filter

app = typer.Typer(help="AI Job Market Copilot CLI")


@app.callback()
def callback() -> None:
    """CLI entrypoint callback."""
    configure_logging()


@app.command("ingest")
def ingest_cmd() -> None:
    """Fetch and normalize raw data."""
    settings = get_settings()
    asyncio.run(run_ingestion(settings))


@app.command("enrich")
def enrich_cmd() -> None:
    """Run relevance + enrichment from normalized artifacts."""
    settings = get_settings()
    normalized_path = settings.resolved_artifacts_dir / "jobs_normalized.parquet"
    if not normalized_path.exists():
        raise typer.BadParameter("Run `job-market-copilot ingest` first.")

    normalized = pl.read_parquet(normalized_path)
    ai_candidates = run_relevance_filter(normalized, settings)
    run_enrichment(ai_candidates, settings)


@app.command("analyze")
def analyze_cmd() -> None:
    """Generate metrics and report from existing artifacts."""
    settings = get_settings()
    all_path = settings.resolved_artifacts_dir / "jobs_scored.parquet"
    ai_path = settings.resolved_artifacts_dir / "ai_jobs_enriched.parquet"

    if not all_path.exists() or not ai_path.exists():
        raise typer.BadParameter("Run `job-market-copilot enrich` first.")

    all_df = pl.read_parquet(all_path)
    ai_df = pl.read_parquet(ai_path)
    run_analytics(all_df, ai_df, settings)


@app.command("run-all")
def run_all_cmd() -> None:
    """Execute the full end-to-end pipeline."""
    settings = get_settings()
    metrics = asyncio.run(run_all(settings))
    logger.info(
        "Run complete | total_jobs={} ai_jobs={} ai_share={}%",
        metrics["total_jobs"],
        metrics["ai_jobs"],
        metrics["ai_share"],
    )


@app.command("serve-app")
def serve_app_cmd(port: int = 8501) -> None:
    """Serve Streamlit dashboard."""
    settings = get_settings()
    app_path = settings.resolve_path(settings.project_root / "app" / "streamlit_app.py")
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", str(app_path), "--server.port", str(port)],
        check=True,
    )


if __name__ == "__main__":
    app()
