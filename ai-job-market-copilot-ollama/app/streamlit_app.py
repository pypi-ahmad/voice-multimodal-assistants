"""Streamlit dashboard for AI job market insights."""

from __future__ import annotations

import json
from pathlib import Path

import plotly.express as px
import polars as pl
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = PROJECT_ROOT / "artifacts"

st.set_page_config(page_title="AI Job Market Copilot", layout="wide")
st.title("AI Job Market Copilot")
st.caption("Notebook-first pipeline artifacts visualized as an interactive dashboard.")

metrics_path = ARTIFACTS / "metrics.json"
enriched_path = ARTIFACTS / "ai_jobs_enriched.parquet"

if not metrics_path.exists() or not enriched_path.exists():
    st.warning("Artifacts not found. Run `uv run job-market-copilot run-all` first.")
    st.stop()

metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
df = pl.read_parquet(enriched_path)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Jobs", metrics.get("total_jobs", 0))
col2.metric("AI/ML Jobs", metrics.get("ai_jobs", 0))
col3.metric("AI Share", f"{metrics.get('ai_share', 0)}%")
col4.metric("Salary Coverage", f"{metrics.get('salary_coverage_ai', 0)}%")

sources = sorted(df.get_column("source").unique().to_list())
selected_sources = st.multiselect("Source", sources, default=sources)

seniority = sorted(df.get_column("seniority").unique().to_list())
selected_seniority = st.multiselect("Seniority", seniority, default=seniority)

filtered = df.filter(
    pl.col("source").is_in(selected_sources) & pl.col("seniority").is_in(selected_seniority)
)

st.subheader("Role Family Mix")
role_df = filtered.group_by("role_family").len(name="count").sort("count", descending=True).to_pandas()
if not role_df.empty:
    st.plotly_chart(px.pie(role_df, names="role_family", values="count"), use_container_width=True)

st.subheader("Top Skills")
skills_df = (
    filtered.explode("core_skills")
    .drop_nulls("core_skills")
    .group_by("core_skills")
    .len(name="count")
    .sort("count", descending=True)
    .head(20)
    .to_pandas()
)
if not skills_df.empty:
    st.plotly_chart(
        px.bar(skills_df, x="core_skills", y="count", title="Top Skills", labels={"core_skills": "Skill"}),
        use_container_width=True,
    )

st.subheader("AI Job Explorer")
preview = filtered.select(
    [
        "source",
        "title",
        "company",
        "location",
        "role_family",
        "seniority",
        "salary_text",
        "url",
    ]
).to_pandas()
st.dataframe(preview, use_container_width=True, hide_index=True)
