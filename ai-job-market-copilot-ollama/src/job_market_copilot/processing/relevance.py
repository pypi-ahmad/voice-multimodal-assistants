"""Rule-based AI/ML relevance scoring."""

from __future__ import annotations

import re

import polars as pl

STRONG_AI_KEYWORDS = [
    "ai",
    "ml",
    "machine learning",
    "llm",
    "nlp",
    "genai",
    "deep learning",
    "generative ai",
    "computer vision",
    "mlops",
    "reinforcement learning",
]

SECONDARY_AI_KEYWORDS = [
    "data scientist",
    "data science",
    "data engineer",
    "applied scientist",
    "research scientist",
    "recommendation system",
    "rag",
]

TITLE_BONUS_PATTERNS = [
    r"\b(machine learning|ml|ai|llm|nlp|genai|data scientist|data engineer|mlops|computer vision)\b",
]

NON_AI_TITLE_EXCLUSIONS = [
    r"\bcustomer support\b",
    r"\bcustomer success\b",
    r"\bhuman resources\b",
    r"\brecruiter\b",
    r"\bmarketing\b",
    r"\bsales\b",
    r"\badministrative\b",
    r"\baccount manager\b",
    r"\boperations coordinator\b",
]


def _count_matches(text: str, patterns: list[str]) -> int:
    text_low = text.lower()
    return sum(1 for pattern in patterns if re.search(pattern, text_low))


def score_relevance(df: pl.DataFrame, threshold: int = 2) -> pl.DataFrame:
    """Compute a relevance score for AI/ML role filtering."""
    if df.is_empty():
        return df

    def compute_score(row: dict[str, object]) -> int:
        title = str(row.get("title", "")).lower()
        category = str(row.get("category", "")).lower()
        description = str(row.get("raw_description", "")).lower()
        tags = " ".join(row.get("tags", []) if isinstance(row.get("tags"), list) else []).lower()

        if any(re.search(pattern, title) for pattern in NON_AI_TITLE_EXCLUSIONS):
            return 0

        score = 0
        score += _count_matches(title, TITLE_BONUS_PATTERNS) * 2
        score += sum(3 for keyword in STRONG_AI_KEYWORDS if keyword in title)
        score += sum(2 for keyword in STRONG_AI_KEYWORDS if keyword in category)
        score += sum(2 for keyword in STRONG_AI_KEYWORDS if keyword in tags)
        score += sum(1 for keyword in STRONG_AI_KEYWORDS if keyword in description[:1600])
        score += sum(1 for keyword in SECONDARY_AI_KEYWORDS if keyword in title)
        score += sum(1 for keyword in SECONDARY_AI_KEYWORDS if keyword in category)
        score += sum(1 for keyword in SECONDARY_AI_KEYWORDS if keyword in description[:1600])
        return score

    scored = df.with_columns(
        pl.struct(df.columns)
        .map_elements(compute_score, return_dtype=pl.Int64)
        .alias("ai_relevance_score")
    )

    has_strong_signal = (
        pl.concat_str([pl.col("title"), pl.col("tags").list.join(" ")], separator=" ")
        .str.to_lowercase()
        .str.contains("|".join(re.escape(keyword) for keyword in STRONG_AI_KEYWORDS))
    )

    return scored.with_columns(
        ((pl.col("ai_relevance_score") >= threshold) & has_strong_signal).alias("is_ai_role_rule")
    )
