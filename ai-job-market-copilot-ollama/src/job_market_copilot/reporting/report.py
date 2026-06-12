"""Markdown report generation."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from jinja2 import Template

_REPORT_TEMPLATE = """# AI Job Market Copilot Report

Generated at: `{{ generated_at }}`

## Executive Summary

- Total jobs ingested: **{{ metrics.total_jobs }}**
- AI/ML jobs identified: **{{ metrics.ai_jobs }}**
- AI/ML share: **{{ metrics.ai_share }}%**
- Salary coverage in AI/ML jobs: **{{ metrics.salary_coverage_ai }}%**

## Top Role Families

| Role Family | Count |
|---|---:|
{% for row in metrics.role_counts[:10] %}| {{ row.role_family }} | {{ row.count }} |
{% endfor %}

## Seniority Distribution

| Seniority | Count |
|---|---:|
{% for row in metrics.seniority_counts[:10] %}| {{ row.seniority }} | {{ row.count }} |
{% endfor %}

## Top Skills

| Skill | Count |
|---|---:|
{% for row in metrics.top_skills[:15] %}| {{ row.core_skills }} | {{ row.count }} |
{% endfor %}

## Top Companies Hiring AI/ML

| Company | Count |
|---|---:|
{% for row in metrics.top_companies[:15] %}| {{ row.company }} | {{ row.count }} |
{% endfor %}

## Notes

- This report is generated from live public job feeds at run time.
- Enrichment is Ollama-first (`{{ ollama_model }}`), with optional Hugging Face fallback if enabled.
"""


def render_report(metrics: dict[str, Any], ollama_model: str, output_path: Path) -> str:
    """Render and save a markdown report."""
    template = Template(_REPORT_TEMPLATE)
    markdown = template.render(
        metrics=metrics,
        generated_at=datetime.now().isoformat(timespec="seconds"),
        ollama_model=ollama_model,
    )
    output_path.write_text(markdown, encoding="utf-8")
    return markdown
