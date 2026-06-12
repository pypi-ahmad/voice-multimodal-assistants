from __future__ import annotations

import polars as pl

from job_market_copilot.processing.relevance import score_relevance


def test_relevance_scores_ai_jobs() -> None:
    df = pl.DataFrame(
        {
            "title": ["Senior ML Engineer", "Customer Success Specialist"],
            "category": ["Data and Analytics", "Support"],
            "raw_description": ["Build LLM and NLP pipelines", "Resolve customer tickets"],
            "tags": [["python", "ml"], ["crm"]],
        }
    )

    scored = score_relevance(df, threshold=2)

    assert scored[0, "is_ai_role_rule"] is True
    assert scored[1, "is_ai_role_rule"] is False
    assert scored[0, "ai_relevance_score"] > scored[1, "ai_relevance_score"]
