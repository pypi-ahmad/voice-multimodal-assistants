"""Configuration for the real-time multimodal pipeline."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class StageBudget(BaseModel):
    """Latency budget and timeout for one pipeline stage."""

    target_ms: int = Field(gt=0)
    timeout_ms: int = Field(gt=0)

    @field_validator("timeout_ms")
    @classmethod
    def timeout_must_cover_target(cls, value: int, info) -> int:
        """Ensure the timeout is not tighter than target latency."""
        target_ms = info.data.get("target_ms")
        if target_ms is not None and value < target_ms:
            raise ValueError("timeout_ms must be >= target_ms")
        return value


class PipelineSettings(BaseSettings):
    """Application settings loaded from env vars or defaults."""

    model_config = SettingsConfigDict(
        env_prefix="RTMA_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    random_seed: int = 7
    profile: Literal["normal", "stress"] = "normal"
    request_count: int = 8

    end_to_end_budget_ms: int = 1400

    ingress: StageBudget = StageBudget(target_ms=180, timeout_ms=260)
    asr: StageBudget = StageBudget(target_ms=280, timeout_ms=380)
    llm: StageBudget = StageBudget(target_ms=520, timeout_ms=760)
    tts: StageBudget = StageBudget(target_ms=260, timeout_ms=420)
    output: StageBudget = StageBudget(target_ms=90, timeout_ms=140)

    queue_maxsize: int = 32
    enqueue_timeout_ms: int = 80

    overload_window: int = 8
    overload_fail_ratio: float = 0.35
    degrade_cooldown_requests: int = 5

    @field_validator("overload_fail_ratio")
    @classmethod
    def ratio_between_zero_and_one(cls, value: float) -> float:
        """Keep adaptive threshold valid."""
        if value <= 0 or value >= 1:
            raise ValueError("overload_fail_ratio must be in (0, 1)")
        return value
