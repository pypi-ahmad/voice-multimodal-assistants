"""Analytics and visualization helpers."""

from __future__ import annotations

import json
from pathlib import Path

import plotly.express as px
import polars as pl


def _explode_list_column(df: pl.DataFrame, col_name: str) -> pl.DataFrame:
    if df.is_empty() or col_name not in df.columns:
        return pl.DataFrame({col_name: [], "count": []})
    return (
        df.explode(col_name)
        .drop_nulls(col_name)
        .filter(pl.col(col_name).str.len_chars() > 0)
        .group_by(col_name)
        .len(name="count")
        .sort("count", descending=True)
    )


def compute_metrics(df_all: pl.DataFrame, df_ai: pl.DataFrame) -> dict[str, object]:
    """Compute summary metrics used by the report and app."""
    total_jobs = df_all.height
    ai_jobs = df_ai.height
    salary_present = df_ai.filter(pl.col("salary_text").str.len_chars() > 0).height

    source_counts = df_ai.group_by("source").len(name="count").sort("count", descending=True)
    role_counts = df_ai.group_by("role_family").len(name="count").sort("count", descending=True)
    seniority_counts = df_ai.group_by("seniority").len(name="count").sort("count", descending=True)

    top_skills = _explode_list_column(df_ai, "core_skills").head(20)
    top_tools = _explode_list_column(df_ai, "tooling").head(20)
    top_companies = df_ai.group_by("company").len(name="count").sort("count", descending=True).head(20)

    return {
        "total_jobs": total_jobs,
        "ai_jobs": ai_jobs,
        "ai_share": round((ai_jobs / total_jobs) * 100, 2) if total_jobs else 0.0,
        "salary_coverage_ai": round((salary_present / ai_jobs) * 100, 2) if ai_jobs else 0.0,
        "source_counts": source_counts.to_dicts(),
        "role_counts": role_counts.to_dicts(),
        "seniority_counts": seniority_counts.to_dicts(),
        "top_skills": top_skills.to_dicts(),
        "top_tools": top_tools.to_dicts(),
        "top_companies": top_companies.to_dicts(),
    }


def save_metrics(metrics: dict[str, object], output_path: Path) -> None:
    output_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")


def save_charts(df_ai: pl.DataFrame, chart_dir: Path) -> None:
    """Generate Plotly charts for notebooks, app, and README assets."""
    if df_ai.is_empty():
        return

    chart_dir.mkdir(parents=True, exist_ok=True)

    skills = _explode_list_column(df_ai, "core_skills").head(12).to_pandas()
    if not skills.empty:
        fig_skills = px.bar(
            skills,
            x="core_skills",
            y="count",
            title="Top AI/ML Skills in Remote Roles",
            labels={"core_skills": "Skill", "count": "Count"},
        )
        fig_skills.update_layout(xaxis_tickangle=-35)
        fig_skills.write_html(chart_dir / "top_skills.html", include_plotlyjs="cdn")

    roles = (
        df_ai.group_by("role_family")
        .len(name="count")
        .sort("count", descending=True)
        .to_pandas()
    )
    if not roles.empty:
        fig_roles = px.pie(roles, names="role_family", values="count", title="Role Family Mix")
        fig_roles.write_html(chart_dir / "role_family_mix.html", include_plotlyjs="cdn")

    sources = df_ai.group_by("source").len(name="count").sort("count", descending=True).to_pandas()
    if not sources.empty:
        fig_sources = px.bar(sources, x="source", y="count", title="AI Roles by Source")
        fig_sources.write_html(chart_dir / "ai_roles_by_source.html", include_plotlyjs="cdn")
