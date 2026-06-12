# AI Job Market Copilot (Ollama + Notebook-First)

An end-to-end, end-to-end project that ingests **live remote job market data**, filters for AI/ML roles, enriches postings with local LLM metadata via **Ollama**, and publishes analytics in both notebooks and a Streamlit dashboard.

This repository is built as a tutorial-style project first, but with production-minded structure (`src/`, typed settings, tests, CLI entrypoints, reproducible artifacts).

## Why This Project

- You get a real data engineering + LLM enrichment workflow, not toy CSV examples.
- You can learn each stage step-by-step in notebooks.
- You can demo a working app (`streamlit`) and explain tradeoffs in interviews.

## Tech Stack

- Python `3.12.10`
- Environment/package manager: `uv`
- Data: `polars`, `duckdb`
- LLM: local `Ollama` (`granite4.1:3b` by default)
- Optional fallback: Hugging Face Inference API via `HF_TOKEN`
- App: `streamlit`
- Testing: `pytest`

## Live Data Sources

- Remotive public API: `https://remotive.com/api/remote-jobs`
- We Work Remotely RSS: `https://weworkremotely.com/remote-jobs.rss`

## Architecture

```text
Live APIs/RSS
   -> Ingestion (async clients + retries)
   -> Normalization (canonical schema)
   -> Deduplication (canonical URL / title-company fallback)
   -> AI/ML Relevance Scoring (rule-based)
   -> LLM Enrichment (Ollama-first, HF fallback optional)
   -> Metrics + Charts + Markdown Report
   -> Streamlit Dashboard
```

## Repository Layout

```text
.
├── app/
│   └── streamlit_app.py
├── artifacts/
│   ├── charts/
│   ├── reports/
│   └── tables/
├── data/
│   └── raw/
├── notebooks/
│   ├── 01_data_ingestion.ipynb
│   ├── 02_cleaning_and_normalization.ipynb
│   ├── 03_ollama_enrichment.ipynb
│   └── 04_market_insights_report.ipynb
├── scripts/
│   └── run_pipeline.py
├── src/job_market_copilot/
│   ├── analysis/
│   ├── clients/
│   ├── processing/
│   ├── reporting/
│   ├── cli.py
│   ├── config.py
│   └── pipeline.py
└── tests/
```

## Quick Start

### 1) Create environment (project-local)

```bash
uv python pin 3.12.10
uv sync --dev
```

### 2) Configure environment

```bash
cp .env.example .env
# Optional: add HF_TOKEN in .env only if you want HF fallback
```

### 3) Run full pipeline

```bash
uv run job-market-copilot run-all
```

### 4) Run Streamlit app

```bash
uv run job-market-copilot serve-app --port 8501
```

### 5) Run tests

```bash
uv run pytest
```

## Notebook-First Learning Path

Execute notebooks in order:

1. `notebooks/01_data_ingestion.ipynb`
2. `notebooks/02_cleaning_and_normalization.ipynb`
3. `notebooks/03_ollama_enrichment.ipynb`
4. `notebooks/04_market_insights_report.ipynb`

They are already executed in this repo with real outputs from the current run.

## Results Snapshot

Run timestamp: **2026-06-12**

- Total jobs ingested: **128**
- AI/ML jobs identified: **40**
- AI share: **31.25%**
- Salary coverage in AI subset: **37.5%**
- Source split (AI subset): **WWR 23**, **Remotive 17**

Generated outputs:

- `artifacts/jobs_normalized.parquet`
- `artifacts/jobs_scored.parquet`
- `artifacts/jobs_ai_candidates.parquet`
- `artifacts/ai_jobs_enriched.parquet`
- `artifacts/metrics.json`
- `artifacts/reports/job_market_report.md`
- `artifacts/charts/*.html`
- `artifacts/tables/*.csv`

## Key Design Decisions

- **Ollama-first**: local inference by default for privacy/cost control.
- **Bounded enrichment**: only top `MAX_JOBS_FOR_ENRICHMENT` rows are LLM-enriched each run (default `12`) to keep runtime practical on laptop GPUs.
- **Fallback behavior**:
  - If Ollama call fails, run switches to fallback path for remaining rows.
  - HF fallback is optional and only used if enabled.
- **Typed + modular**: data clients, normalization, relevance scoring, enrichment, analytics, and reporting are separated for maintainability.

## Limitations and Next Improvements

- Public job feeds contain noisy tagging and many generic software roles; AI relevance quality can be improved with:
  - stricter title-only gating,
  - a small supervised classifier,
  - source-specific calibration.
- Current enrichment uses single-pass extraction. You can improve with:
  - two-stage extraction (classification then skill extraction),
  - confidence scores,
  - schema-constrained validation with retry policies.
- Add historical snapshots + trend deltas (daily/weekly) for stronger market trend analysis.

## Resume Talking Points

- Built an end-to-end AI analytics pipeline with live data ingestion, normalization, deduplication, LLM enrichment, and dashboarding.
- Implemented local LLM inference with Ollama and robust fallback strategy.
- Delivered tutorial notebooks plus reusable production-style Python package and CLI.
- Added tests for key pipeline logic and generated reproducible report artifacts from project runs.

## Setup

```bash
git clone https://github.com/pypi-ahmad/ai-job-market-copilot-ollama.git
cd ai-job-market-copilot-ollama
```
