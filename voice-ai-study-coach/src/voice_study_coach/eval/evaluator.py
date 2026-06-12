"""Evaluation logic for baseline vs tutor responses."""

from __future__ import annotations

import json

from voice_study_coach.orchestration.session import VoiceStudySession
from voice_study_coach.schemas import EvalPrediction, EvalSummary, EvalTask


def load_tasks(path: str) -> list[EvalTask]:
    """Load evaluation tasks from JSON file."""
    with open(path, encoding="utf-8") as handle:
        payload = json.loads(handle.read())
    return [EvalTask.model_validate(item) for item in payload]


def keyword_recall(answer: str, required_keywords: list[str]) -> float:
    """Compute keyword recall in [0, 1]."""
    if not required_keywords:
        return 0.0
    norm = answer.lower()
    hits = sum(1 for kw in required_keywords if kw.lower() in norm)
    return hits / len(required_keywords)


def _safe_mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return float(sum(values) / len(values))


async def evaluate(session: VoiceStudySession, tasks: list[EvalTask]) -> tuple[list[EvalPrediction], EvalSummary]:
    """Run evaluation and aggregate metrics."""
    rows: list[EvalPrediction] = []

    for idx, task in enumerate(tasks, start=1):
        trace_id = f"eval-{idx:03d}-{task.task_id}"
        run = await session.run(trace_id=trace_id, question_text=task.question)

        baseline_answer = "I do not know from the question alone."
        baseline_score = keyword_recall(baseline_answer, task.required_keywords)
        tutor_score = keyword_recall(run.tutor_response_text, task.required_keywords)

        retrieval_hit = any(item["source"] == task.expected_source for item in run.retrieved)
        source_cited = task.expected_source.lower() in run.tutor_response_text.lower()

        rows.append(
            EvalPrediction(
                task_id=task.task_id,
                question=task.question,
                expected_source=task.expected_source,
                baseline_answer=baseline_answer,
                tutor_answer=run.tutor_response_text,
                baseline_keyword_recall=baseline_score,
                tutor_keyword_recall=tutor_score,
                keyword_gain=tutor_score - baseline_score,
                retrieval_hit=retrieval_hit,
                source_cited=source_cited,
                tutor_fallback_used=run.tutor_fallback_used,
                quiz_fallback_used=run.quiz_fallback_used,
                tutor_audio_seconds=run.tutor_audio_seconds,
                total_latency_ms=run.total_latency_ms,
            )
        )

    summary = EvalSummary(
        n_tasks=len(rows),
        baseline_keyword_recall_mean=_safe_mean([row.baseline_keyword_recall for row in rows]),
        tutor_keyword_recall_mean=_safe_mean([row.tutor_keyword_recall for row in rows]),
        keyword_recall_gain=_safe_mean([row.tutor_keyword_recall for row in rows])
        - _safe_mean([row.baseline_keyword_recall for row in rows]),
        retrieval_hit_rate=_safe_mean([1.0 if row.retrieval_hit else 0.0 for row in rows]),
        source_citation_rate=_safe_mean([1.0 if row.source_cited else 0.0 for row in rows]),
        tutor_fallback_rate=_safe_mean([1.0 if row.tutor_fallback_used else 0.0 for row in rows]),
        quiz_fallback_rate=_safe_mean([1.0 if row.quiz_fallback_used else 0.0 for row in rows]),
        avg_tutor_audio_seconds=_safe_mean([row.tutor_audio_seconds for row in rows]),
        avg_total_latency_ms=_safe_mean([row.total_latency_ms for row in rows]),
    )

    return rows, summary
