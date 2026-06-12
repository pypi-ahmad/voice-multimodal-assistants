"""Tests for timeout handling, graceful degradation, and latency accounting."""

from __future__ import annotations

import asyncio

from realtime_mm.config import PipelineSettings
from realtime_mm.pipeline import RealTimePipeline
from realtime_mm.services import SimulatedServices


class SlowAsrServices(SimulatedServices):
    """Forces ASR timeout to test fallback behavior."""

    async def transcribe_primary(self, text: str) -> str:
        await asyncio.sleep(0.2)
        return text


class SlowLlmAndTtsServices(SimulatedServices):
    """Forces LLM/TTS timeouts to test layered degradation."""

    async def generate_reply_primary(self, transcript: str) -> str:
        await asyncio.sleep(0.2)
        return transcript

    async def synthesize_primary(self, reply_text: str) -> bytes:
        await asyncio.sleep(0.2)
        return reply_text.encode("utf-8")


async def test_asr_timeout_uses_fallback() -> None:
    settings = PipelineSettings(
        request_count=1,
        asr={"target_ms": 20, "timeout_ms": 40},
        llm={"target_ms": 20, "timeout_ms": 60},
        tts={"target_ms": 20, "timeout_ms": 60},
    )
    pipeline = RealTimePipeline(settings=settings, services=SlowAsrServices(settings))

    results = await pipeline.run(["Please summarize this request for me in one sentence"])

    assert len(results) == 1
    result = results[0]
    assert "asr_timeout_fallback" in result.degraded_reasons
    assert result.stage_results["asr"].status == "timeout"
    assert result.transcript.endswith("...")


async def test_llm_and_tts_timeout_graceful_degradation() -> None:
    settings = PipelineSettings(
        request_count=1,
        asr={"target_ms": 15, "timeout_ms": 40},
        llm={"target_ms": 15, "timeout_ms": 40},
        tts={"target_ms": 15, "timeout_ms": 40},
    )
    pipeline = RealTimePipeline(settings=settings, services=SlowLlmAndTtsServices(settings))

    results = await pipeline.run(["Explain the deployment checklist quickly"])

    assert len(results) == 1
    result = results[0]
    assert "llm_timeout_fallback" in result.degraded_reasons
    assert "tts_timeout_text_only" in result.degraded_reasons
    assert result.audio_rendered is False
    assert result.stage_results["llm"].status == "timeout"
    assert result.stage_results["tts"].status == "timeout"


async def test_end_to_end_deadline_can_miss() -> None:
    settings = PipelineSettings(
        request_count=1,
        end_to_end_budget_ms=100,
        ingress={"target_ms": 20, "timeout_ms": 50},
        asr={"target_ms": 20, "timeout_ms": 70},
        llm={"target_ms": 20, "timeout_ms": 70},
        tts={"target_ms": 20, "timeout_ms": 70},
        output={"target_ms": 20, "timeout_ms": 70},
    )
    pipeline = RealTimePipeline(settings=settings)

    results = await pipeline.run(["Quick request"])

    assert len(results) == 1
    assert results[0].deadline_met is False
