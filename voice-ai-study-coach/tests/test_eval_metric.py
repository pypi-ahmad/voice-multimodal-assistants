from __future__ import annotations

from voice_study_coach.eval.evaluator import keyword_recall


def test_keyword_recall() -> None:
    score = keyword_recall("Tuesday 16:00 UTC", ["tuesday", "16:00", "utc", "canary"])
    assert round(score, 4) == 0.75
