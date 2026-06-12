"""Typed models for voice sessions, retrieval, telemetry, and evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeDoc(BaseModel):
    """Knowledge base source document."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    source: str
    title: str
    text: str


@dataclass(frozen=True)
class RetrievedDoc:
    """Retrieved doc with lexical score."""

    doc: KnowledgeDoc
    score: float


class ChatResult(BaseModel):
    """LLM output metadata."""

    model_config = ConfigDict(extra="forbid")

    text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_duration_ns: int = 0
    done_reason: str = ""
    fallback_used: bool = False

    @property
    def latency_ms(self) -> float:
        return self.total_duration_ns / 1_000_000 if self.total_duration_ns else 0.0


class TranscriptResult(BaseModel):
    """Speech-to-text output."""

    model_config = ConfigDict(extra="forbid")

    transcript: str
    method: Literal["sidecar", "empty_fallback"]


class SessionResult(BaseModel):
    """One full study-coaching session output."""

    model_config = ConfigDict(extra="forbid")

    trace_id: str
    input_mode: Literal["audio", "text"]
    question_text: str
    retrieved: list[dict[str, Any]]
    tutor_response_text: str
    quiz_question_text: str
    tutor_audio_path: str
    quiz_audio_path: str
    tutor_audio_seconds: float
    quiz_audio_seconds: float
    tutor_fallback_used: bool
    quiz_fallback_used: bool
    total_latency_ms: float


class EvalTask(BaseModel):
    """Evaluation task item."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    task_id: str
    question: str
    reference_answer: str
    expected_source: str
    required_keywords: list[str] = Field(default_factory=list)


class EvalPrediction(BaseModel):
    """Per-task evaluation row."""

    model_config = ConfigDict(extra="forbid")

    task_id: str
    question: str
    expected_source: str
    baseline_answer: str
    tutor_answer: str
    baseline_keyword_recall: float
    tutor_keyword_recall: float
    keyword_gain: float
    retrieval_hit: bool
    source_cited: bool
    tutor_fallback_used: bool
    quiz_fallback_used: bool
    tutor_audio_seconds: float
    total_latency_ms: float


class EvalSummary(BaseModel):
    """Aggregate evaluation metrics."""

    model_config = ConfigDict(extra="forbid")

    n_tasks: int
    baseline_keyword_recall_mean: float
    tutor_keyword_recall_mean: float
    keyword_recall_gain: float
    retrieval_hit_rate: float
    source_citation_rate: float
    tutor_fallback_rate: float
    quiz_fallback_rate: float
    avg_tutor_audio_seconds: float
    avg_total_latency_ms: float


class TraceSpanRecord(BaseModel):
    """One telemetry span persisted in JSONL."""

    model_config = ConfigDict(extra="forbid")

    trace_id: str
    span_name: str
    status: Literal["ok", "error"]
    start_time_utc: str
    end_time_utc: str
    latency_ms: float
    attributes: dict[str, Any] = Field(default_factory=dict)
