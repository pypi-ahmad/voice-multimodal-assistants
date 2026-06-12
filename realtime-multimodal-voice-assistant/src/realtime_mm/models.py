"""Core data models used across the pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


StageStatus = Literal["ok", "timeout", "error", "skipped", "dropped"]
PipelineMode = Literal["normal", "degraded"]


@dataclass(slots=True)
class StageResult:
    """Observed performance for one stage of a single request."""

    stage: str
    status: StageStatus
    latency_ms: float
    target_ms: int
    timeout_ms: int
    detail: str = ""


@dataclass(slots=True)
class RequestEnvelope:
    """One incoming voice request entering the pipeline."""

    request_id: str
    user_text: str
    created_at: float


@dataclass(slots=True)
class RequestContext:
    """Mutable processing context that travels between stages."""

    envelope: RequestEnvelope
    mode_at_ingress: PipelineMode
    transcript: str | None = None
    reply_text: str | None = None
    audio_payload: bytes | None = None
    degraded_reasons: list[str] = field(default_factory=list)
    stage_results: dict[str, StageResult] = field(default_factory=dict)


@dataclass(slots=True)
class PipelineResult:
    """Final output for one request."""

    request_id: str
    transcript: str
    reply_text: str
    audio_rendered: bool
    degraded_reasons: list[str]
    stage_results: dict[str, StageResult]
    end_to_end_ms: float
    deadline_met: bool
    mode_at_ingress: PipelineMode
