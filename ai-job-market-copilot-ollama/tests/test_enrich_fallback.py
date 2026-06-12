from __future__ import annotations

from job_market_copilot.config import Settings
from job_market_copilot.processing.enrich import JobEnricher


def test_heuristic_fallback_assigns_role_family() -> None:
    settings = Settings(enable_hf_fallback=False)
    enricher = JobEnricher(settings)

    row = {
        "title": "Senior Data Scientist",
        "raw_description": "Build machine learning models in python and pytorch",
        "salary_text": "$100k",
    }

    enriched = enricher._heuristic_fallback(row)

    assert enriched.role_family == "data scientist"
    assert enriched.seniority in {"senior", "staff+"}
    assert enriched.compensation_signal == "provided"
