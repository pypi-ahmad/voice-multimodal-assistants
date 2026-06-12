"""Artifact writers and markdown report generator."""

from __future__ import annotations

import csv
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jinja2 import Template

from voice_study_coach.schemas import EvalPrediction, EvalSummary

_REPORT_TEMPLATE = """# Voice AI Study Coach Report

Generated at: `{{ generated_at }}`

## Setup

- Tutor model: `{{ tutor_model }}`
- Quiz model: `{{ quiz_model }}`
- Tasks evaluated: **{{ n_tasks }}**

## Metrics

- Baseline keyword recall mean: **{{ baseline_recall }}**
- Tutor keyword recall mean: **{{ tutor_recall }}**
- Keyword recall gain: **{{ gain }}**
- Retrieval hit rate: **{{ retrieval_hit_rate }}**
- Source citation rate: **{{ source_citation_rate }}**
- Tutor fallback rate: **{{ tutor_fallback_rate }}**
- Quiz fallback rate: **{{ quiz_fallback_rate }}**
- Avg tutor audio duration (s): **{{ audio_seconds }}**
- Avg total latency (ms): **{{ latency_ms }}**

## Telemetry

- Total spans: **{{ telemetry_spans }}**
- Unique traces: **{{ telemetry_traces }}**

| Span | Count | Mean ms | P95 ms | Errors |
|---|---:|---:|---:|---:|
{% for row in telemetry_rows %}| {{ row.span_name }} | {{ row.count }} | {{ row.latency_ms_mean }} | {{ row.latency_ms_p95 }} | {{ row.error_count }} |
{% endfor %}

## Per-task Scores

| Task ID | Baseline Recall | Tutor Recall | Gain | Retrieval Hit |
|---|---:|---:|---:|---:|
{% for row in rows %}| {{ row.task_id }} | {{ "%.3f"|format(row.baseline_keyword_recall) }} | {{ "%.3f"|format(row.tutor_keyword_recall) }} | {{ "%.3f"|format(row.keyword_gain) }} | {{ 1 if row.retrieval_hit else 0 }} |
{% endfor %}
"""


def save_predictions(rows: list[EvalPrediction], output_path: Path) -> None:
    """Persist per-task predictions CSV."""
    records = [row.model_dump() for row in rows]
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not records:
        output_path.write_text("", encoding="utf-8")
        return

    fieldnames = list(records[0].keys())
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)


def save_summary(summary: EvalSummary, output_path: Path) -> None:
    """Persist summary JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(summary.model_dump_json(indent=2), encoding="utf-8")


def save_demo_runs(runs: list[dict[str, Any]], output_path: Path) -> None:
    """Persist demo session runs."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(runs, indent=2), encoding="utf-8")


def render_report(
    summary: EvalSummary,
    rows: list[EvalPrediction],
    tutor_model: str,
    quiz_model: str,
    telemetry_summary: dict[str, Any],
    output_path: Path,
) -> str:
    """Render markdown report and save to disk."""
    text = Template(_REPORT_TEMPLATE).render(
        generated_at=datetime.now(tz=UTC).isoformat(timespec="seconds"),
        tutor_model=tutor_model,
        quiz_model=quiz_model,
        n_tasks=summary.n_tasks,
        baseline_recall=f"{summary.baseline_keyword_recall_mean:.4f}",
        tutor_recall=f"{summary.tutor_keyword_recall_mean:.4f}",
        gain=f"{summary.keyword_recall_gain:.4f}",
        retrieval_hit_rate=f"{summary.retrieval_hit_rate:.4f}",
        source_citation_rate=f"{summary.source_citation_rate:.4f}",
        tutor_fallback_rate=f"{summary.tutor_fallback_rate:.4f}",
        quiz_fallback_rate=f"{summary.quiz_fallback_rate:.4f}",
        audio_seconds=f"{summary.avg_tutor_audio_seconds:.3f}",
        latency_ms=f"{summary.avg_total_latency_ms:.2f}",
        telemetry_spans=telemetry_summary.get("n_spans", 0),
        telemetry_traces=telemetry_summary.get("n_unique_traces", 0),
        telemetry_rows=telemetry_summary.get("by_span", []),
        rows=[json.loads(row.model_dump_json()) for row in rows],
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8")
    return text
