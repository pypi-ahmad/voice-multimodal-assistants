"""LLM enrichment pipeline."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

import polars as pl
from huggingface_hub import InferenceClient
from loguru import logger
from ollama import Client

from job_market_copilot.config import Settings

_ALLOWED_ROLE_FAMILIES = {
    "ml engineer",
    "ai engineer",
    "data scientist",
    "data engineer",
    "research scientist",
    "data analyst",
    "software engineer",
    "other",
}
_ALLOWED_SENIORITY = {"intern", "junior", "mid", "senior", "staff+", "unknown"}

_SKILL_LEXICON = [
    "python",
    "sql",
    "pytorch",
    "tensorflow",
    "scikit-learn",
    "spark",
    "airflow",
    "kubernetes",
    "docker",
    "aws",
    "gcp",
    "azure",
    "llm",
    "rag",
    "nlp",
    "computer vision",
    "xgboost",
    "lightgbm",
    "mlflow",
    "langchain",
    "llamaindex",
]


@dataclass
class EnrichmentOutput:
    role_family: str
    seniority: str
    core_skills: list[str]
    tooling: list[str]
    summary: str
    compensation_signal: str
    model_source: str


class JobEnricher:
    """Enrich AI job posts using Ollama with safe fallbacks."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.ollama_client = Client(
            host=settings.ollama_base_url,
            timeout=max(60.0, settings.request_timeout_seconds * 4),
        )
        self.hf_client = InferenceClient(model=settings.hf_model, token=settings.hf_token)
        self.ollama_enabled = True

    def enrich_dataframe(self, df: pl.DataFrame) -> pl.DataFrame:
        """Enrich rows with model-derived metadata."""
        if df.is_empty():
            return df

        enrich_limit = min(df.height, self.settings.max_jobs_for_enrichment)
        subset = df.head(enrich_limit)
        outputs: list[dict[str, object]] = []

        for idx, row in enumerate(subset.iter_rows(named=True), start=1):
            if idx % 10 == 0 or idx == enrich_limit:
                logger.info("Enrichment progress: {}/{}", idx, enrich_limit)
            outputs.append(self._enrich_row(row).__dict__)

        enriched_subset = subset.hstack(pl.from_dicts(outputs))

        if enrich_limit == df.height:
            return enriched_subset

        # Preserve non-enriched rows with heuristic defaults if the limit truncates.
        tail = df.slice(enrich_limit).with_columns(
            pl.lit("other").alias("role_family"),
            pl.lit("unknown").alias("seniority"),
            pl.lit([]).alias("core_skills"),
            pl.lit([]).alias("tooling"),
            pl.lit("Not enriched due to configured max_jobs_for_enrichment limit.").alias("summary"),
            pl.lit("unclear").alias("compensation_signal"),
            pl.lit("fallback_limit").alias("model_source"),
        )
        return pl.concat([enriched_subset, tail], how="vertical")

    def _enrich_row(self, row: dict[str, object]) -> EnrichmentOutput:
        prompt = self._build_prompt(row)
        ollama_payload = self._try_ollama(prompt)
        if ollama_payload:
            parsed = self._validate_payload(ollama_payload)
            if parsed:
                return parsed

        if self.settings.enable_hf_fallback and self.settings.hf_token:
            hf_payload = self._try_hf(prompt)
            if hf_payload:
                parsed = self._validate_payload(hf_payload)
                if parsed:
                    parsed.model_source = "hf_fallback"
                    return parsed

        return self._heuristic_fallback(row)

    def _build_prompt(self, row: dict[str, object]) -> str:
        description = str(row.get("raw_description", ""))[:1600]
        tags = row.get("tags", []) if isinstance(row.get("tags"), list) else []
        tags_text = ", ".join(str(t) for t in tags)

        return (
            "You are classifying an AI/ML job posting. "
            "Return strict JSON with keys: role_family, seniority, core_skills, tooling, summary, compensation_signal. "
            "Allowed role_family: ml engineer, ai engineer, data scientist, data engineer, research scientist, data analyst, software engineer, other. "
            "Allowed seniority: intern, junior, mid, senior, staff+, unknown. "
            "compensation_signal must be one of provided, missing, unclear. "
            "core_skills/tooling should be lowercase arrays with max 8 items each.\n\n"
            f"TITLE: {row.get('title', '')}\n"
            f"COMPANY: {row.get('company', '')}\n"
            f"CATEGORY: {row.get('category', '')}\n"
            f"LOCATION: {row.get('location', '')}\n"
            f"SALARY TEXT: {row.get('salary_text', '')}\n"
            f"TAGS: {tags_text}\n"
            f"DESCRIPTION: {description}\n"
        )

    def _try_ollama(self, prompt: str) -> dict[str, object] | None:
        if not self.ollama_enabled:
            return None
        try:
            response = self.ollama_client.generate(
                model=self.settings.ollama_model,
                prompt=prompt,
                options={"temperature": self.settings.ollama_temperature},
                format="json",
            )
            text = str(response.get("response", "")).strip()
            return json.loads(text)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Ollama enrichment failed: {}", exc)
            self.ollama_enabled = False
            logger.warning("Disabling Ollama for this run; using fallback path for remaining rows.")
            return None

    def _try_hf(self, prompt: str) -> dict[str, object] | None:
        try:
            completion = self.hf_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                response_format={"type": "json_object"},
            )
            content = completion.choices[0].message.content
            if not content:
                return None
            return json.loads(content)
        except Exception as exc:  # noqa: BLE001
            logger.warning("HF fallback enrichment failed: {}", exc)
            return None

    def _validate_payload(self, payload: dict[str, object]) -> EnrichmentOutput | None:
        try:
            role_family = str(payload.get("role_family", "other")).lower().strip()
            if role_family not in _ALLOWED_ROLE_FAMILIES:
                role_family = "other"

            seniority = str(payload.get("seniority", "unknown")).lower().strip()
            if seniority not in _ALLOWED_SENIORITY:
                seniority = "unknown"

            compensation = str(payload.get("compensation_signal", "unclear")).lower().strip()
            if compensation not in {"provided", "missing", "unclear"}:
                compensation = "unclear"

            core_skills = [str(v).lower().strip() for v in payload.get("core_skills", [])][:8]
            tooling = [str(v).lower().strip() for v in payload.get("tooling", [])][:8]
            summary = str(payload.get("summary", "")).strip() or "No summary generated."

            return EnrichmentOutput(
                role_family=role_family,
                seniority=seniority,
                core_skills=[s for s in core_skills if s],
                tooling=[t for t in tooling if t],
                summary=summary,
                compensation_signal=compensation,
                model_source="ollama",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Payload validation failed: {}", exc)
            return None

    def _heuristic_fallback(self, row: dict[str, object]) -> EnrichmentOutput:
        text = f"{row.get('title', '')} {row.get('raw_description', '')}".lower()

        role_family = "other"
        if "data scientist" in text:
            role_family = "data scientist"
        elif "data engineer" in text:
            role_family = "data engineer"
        elif "machine learning" in text or re.search(r"\bml engineer\b", text):
            role_family = "ml engineer"
        elif "ai engineer" in text:
            role_family = "ai engineer"
        elif "research" in text:
            role_family = "research scientist"
        elif "analyst" in text:
            role_family = "data analyst"
        elif "software engineer" in text or "developer" in text:
            role_family = "software engineer"

        seniority = "unknown"
        if re.search(r"\b(staff|principal|lead)\b", text):
            seniority = "staff+"
        elif "senior" in text:
            seniority = "senior"
        elif re.search(r"\b(mid|intermediate)\b", text):
            seniority = "mid"
        elif re.search(r"\b(junior|entry)\b", text):
            seniority = "junior"
        elif "intern" in text:
            seniority = "intern"

        skills = [skill for skill in _SKILL_LEXICON if skill in text]
        compensation_signal = "provided" if str(row.get("salary_text", "")).strip() else "missing"

        return EnrichmentOutput(
            role_family=role_family,
            seniority=seniority,
            core_skills=skills[:8],
            tooling=skills[:8],
            summary="Heuristic fallback classification generated because model output was unavailable.",
            compensation_signal=compensation_signal,
            model_source="heuristic_fallback",
        )
