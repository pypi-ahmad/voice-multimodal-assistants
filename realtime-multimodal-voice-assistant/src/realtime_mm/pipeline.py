"""Async streaming pipeline with latency budgets and graceful degradation."""

from __future__ import annotations

import asyncio
import time
from collections import deque
from typing import Awaitable, Callable, TypeVar

from loguru import logger

from realtime_mm.config import PipelineSettings, StageBudget
from realtime_mm.latency import LatencyReport
from realtime_mm.models import PipelineResult, RequestContext, RequestEnvelope, StageResult
from realtime_mm.services import SimulatedServices

_SENTINEL = object()
T = TypeVar("T")


class DegradationController:
    """Adaptive controller that toggles degraded mode under sustained stress."""

    def __init__(self, settings: PipelineSettings) -> None:
        self.settings = settings
        self._recent_failures: deque[int] = deque(maxlen=settings.overload_window)
        self._mode: str = "normal"
        self._cooldown_remaining = 0

    @property
    def mode(self) -> str:
        """Current global operating mode."""
        return "degraded" if self._mode == "degraded" else "normal"

    def should_skip_tts(self, remaining_budget_ms: float, tts_backlog: int) -> bool:
        """Decide whether to skip TTS to protect deadline."""
        if self.mode == "degraded":
            return True

        required = self.settings.tts.target_ms + self.settings.output.target_ms
        return remaining_budget_ms < required or tts_backlog >= 3

    def observe(self, result: PipelineResult) -> None:
        """Update mode using recent deadline misses/timeouts."""
        has_timeout_or_error = any(
            stage.status in {"timeout", "error", "dropped"} for stage in result.stage_results.values()
        )
        failed = (not result.deadline_met) or has_timeout_or_error

        self._recent_failures.append(1 if failed else 0)

        if len(self._recent_failures) == self.settings.overload_window:
            ratio = sum(self._recent_failures) / len(self._recent_failures)
            if ratio >= self.settings.overload_fail_ratio:
                self._mode = "degraded"
                self._cooldown_remaining = self.settings.degrade_cooldown_requests

        if self._mode == "degraded":
            self._cooldown_remaining -= 1
            if self._cooldown_remaining <= 0:
                self._mode = "normal"
                self._recent_failures.clear()


class RealTimePipeline:
    """Voice-assistant style streaming pipeline with stage workers.

    Stages:
    1. ingress (capture + VAD simulation)
    2. asr
    3. llm
    4. tts (optional, can be skipped in degraded mode)
    5. output
    """

    def __init__(self, settings: PipelineSettings, services: SimulatedServices | None = None) -> None:
        self.settings = settings
        self.services = services or SimulatedServices(settings)
        self.report = LatencyReport()
        self._degradation = DegradationController(settings)
        self._results: list[PipelineResult] = []

    async def run(self, utterances: list[str]) -> list[PipelineResult]:
        """Run utterances through the streaming pipeline.

        Args:
            utterances: Simulated incoming spoken requests.

        Returns:
            Completed pipeline results in completion order.
        """
        asr_queue: asyncio.Queue[RequestContext | object] = asyncio.Queue(maxsize=self.settings.queue_maxsize)
        llm_queue: asyncio.Queue[RequestContext | object] = asyncio.Queue(maxsize=self.settings.queue_maxsize)
        tts_queue: asyncio.Queue[RequestContext | object] = asyncio.Queue(maxsize=self.settings.queue_maxsize)
        output_queue: asyncio.Queue[RequestContext | object] = asyncio.Queue(maxsize=self.settings.queue_maxsize)

        workers = [
            asyncio.create_task(self._asr_worker(asr_queue, llm_queue)),
            asyncio.create_task(self._llm_worker(llm_queue, tts_queue)),
            asyncio.create_task(self._tts_worker(tts_queue, output_queue)),
            asyncio.create_task(self._output_worker(output_queue)),
        ]

        for idx, utterance in enumerate(utterances, start=1):
            ctx = RequestContext(
                envelope=RequestEnvelope(
                    request_id=f"req-{idx:03d}",
                    user_text=utterance,
                    created_at=time.perf_counter(),
                ),
                mode_at_ingress=self._degradation.mode,
            )

            await self._run_stage(
                ctx=ctx,
                stage="ingress",
                budget=self.settings.ingress,
                primary=lambda text=utterance: self.services.ingest_capture(text),
                fallback=None,
                timeout_reason="ingress_timeout",
                error_reason="ingress_error",
            )

            enqueued = await self._safe_put(asr_queue, ctx)
            if not enqueued:
                ctx.degraded_reasons.append("asr_queue_drop")
                self._mark_stage(
                    ctx,
                    stage="asr",
                    status="dropped",
                    latency_ms=0.0,
                    budget=self.settings.asr,
                    detail="queue put timed out; request dropped before ASR",
                )
                self._mark_stage(
                    ctx,
                    stage="llm",
                    status="dropped",
                    latency_ms=0.0,
                    budget=self.settings.llm,
                    detail="upstream dropped",
                )
                self._mark_stage(
                    ctx,
                    stage="tts",
                    status="dropped",
                    latency_ms=0.0,
                    budget=self.settings.tts,
                    detail="upstream dropped",
                )
                self._mark_stage(
                    ctx,
                    stage="output",
                    status="dropped",
                    latency_ms=0.0,
                    budget=self.settings.output,
                    detail="upstream dropped",
                )
                self._finalize(ctx)

        await asr_queue.put(_SENTINEL)
        await asyncio.gather(*workers)
        return self._results

    async def _asr_worker(
        self,
        in_queue: asyncio.Queue[RequestContext | object],
        out_queue: asyncio.Queue[RequestContext | object],
    ) -> None:
        while True:
            item = await in_queue.get()
            if item is _SENTINEL:
                in_queue.task_done()
                await out_queue.put(_SENTINEL)
                break

            ctx = item
            transcript = await self._run_stage(
                ctx=ctx,
                stage="asr",
                budget=self.settings.asr,
                primary=lambda text=ctx.envelope.user_text: self.services.transcribe_primary(text),
                fallback=lambda text=ctx.envelope.user_text: self.services.transcribe_fallback(text),
                timeout_reason="asr_timeout_fallback",
                error_reason="asr_error_fallback",
            )
            ctx.transcript = str(transcript) if transcript is not None else ""

            queued = await self._safe_put(out_queue, ctx)
            if not queued:
                ctx.degraded_reasons.append("llm_queue_drop")
                self._mark_stage(
                    ctx,
                    stage="llm",
                    status="dropped",
                    latency_ms=0.0,
                    budget=self.settings.llm,
                    detail="queue put timed out before LLM",
                )
                self._mark_stage(
                    ctx,
                    stage="tts",
                    status="dropped",
                    latency_ms=0.0,
                    budget=self.settings.tts,
                    detail="upstream dropped",
                )
                self._mark_stage(
                    ctx,
                    stage="output",
                    status="dropped",
                    latency_ms=0.0,
                    budget=self.settings.output,
                    detail="upstream dropped",
                )
                self._finalize(ctx)

            in_queue.task_done()

    async def _llm_worker(
        self,
        in_queue: asyncio.Queue[RequestContext | object],
        out_queue: asyncio.Queue[RequestContext | object],
    ) -> None:
        while True:
            item = await in_queue.get()
            if item is _SENTINEL:
                in_queue.task_done()
                await out_queue.put(_SENTINEL)
                break

            ctx = item
            transcript = ctx.transcript or ""
            reply = await self._run_stage(
                ctx=ctx,
                stage="llm",
                budget=self.settings.llm,
                primary=lambda text=transcript: self.services.generate_reply_primary(text),
                fallback=lambda text=transcript: self.services.generate_reply_fallback(text),
                timeout_reason="llm_timeout_fallback",
                error_reason="llm_error_fallback",
            )
            ctx.reply_text = str(reply) if reply is not None else ""

            queued = await self._safe_put(out_queue, ctx)
            if not queued:
                ctx.degraded_reasons.append("tts_queue_drop")
                self._mark_stage(
                    ctx,
                    stage="tts",
                    status="dropped",
                    latency_ms=0.0,
                    budget=self.settings.tts,
                    detail="queue put timed out before TTS",
                )
                self._mark_stage(
                    ctx,
                    stage="output",
                    status="dropped",
                    latency_ms=0.0,
                    budget=self.settings.output,
                    detail="upstream dropped",
                )
                self._finalize(ctx)

            in_queue.task_done()

    async def _tts_worker(
        self,
        in_queue: asyncio.Queue[RequestContext | object],
        out_queue: asyncio.Queue[RequestContext | object],
    ) -> None:
        while True:
            item = await in_queue.get()
            if item is _SENTINEL:
                in_queue.task_done()
                await out_queue.put(_SENTINEL)
                break

            ctx = item
            remaining_budget = self.settings.end_to_end_budget_ms - self._elapsed_ms(ctx.envelope.created_at)
            if self._degradation.should_skip_tts(
                remaining_budget_ms=remaining_budget,
                tts_backlog=in_queue.qsize(),
            ):
                ctx.degraded_reasons.append("tts_skipped_for_latency")
                self._mark_stage(
                    ctx,
                    stage="tts",
                    status="skipped",
                    latency_ms=0.0,
                    budget=self.settings.tts,
                    detail="skipped to protect end-to-end deadline",
                )
                ctx.audio_payload = None
            else:
                reply_text = ctx.reply_text or ""
                audio = await self._run_stage(
                    ctx=ctx,
                    stage="tts",
                    budget=self.settings.tts,
                    primary=lambda text=reply_text: self.services.synthesize_primary(text),
                    fallback=lambda: None,
                    timeout_reason="tts_timeout_text_only",
                    error_reason="tts_error_text_only",
                )
                ctx.audio_payload = audio if isinstance(audio, bytes) else None

            queued = await self._safe_put(out_queue, ctx)
            if not queued:
                ctx.degraded_reasons.append("output_queue_drop")
                self._mark_stage(
                    ctx,
                    stage="output",
                    status="dropped",
                    latency_ms=0.0,
                    budget=self.settings.output,
                    detail="queue put timed out before output",
                )
                self._finalize(ctx)

            in_queue.task_done()

    async def _output_worker(self, in_queue: asyncio.Queue[RequestContext | object]) -> None:
        while True:
            item = await in_queue.get()
            if item is _SENTINEL:
                in_queue.task_done()
                break

            ctx = item
            await self._run_stage(
                ctx=ctx,
                stage="output",
                budget=self.settings.output,
                primary=self.services.output_stream,
                fallback=None,
                timeout_reason="output_timeout",
                error_reason="output_error",
            )
            self._finalize(ctx)
            in_queue.task_done()

    async def _safe_put(self, queue: asyncio.Queue[RequestContext | object], ctx: RequestContext) -> bool:
        """Bound enqueue wait to avoid unlimited queueing delay."""
        try:
            await asyncio.wait_for(queue.put(ctx), timeout=self.settings.enqueue_timeout_ms / 1000.0)
            return True
        except asyncio.TimeoutError:
            return False

    async def _run_stage(
        self,
        ctx: RequestContext,
        stage: str,
        budget: StageBudget,
        primary: Callable[[], Awaitable[T]],
        fallback: Callable[[], T] | None,
        timeout_reason: str,
        error_reason: str,
    ) -> T | None:
        """Execute one stage with timeout and optional fallback."""
        started = time.perf_counter()
        status = "ok"
        detail = "primary"
        value: T | None = None

        try:
            value = await asyncio.wait_for(primary(), timeout=budget.timeout_ms / 1000.0)
        except asyncio.TimeoutError:
            status = "timeout"
            detail = "primary timeout"
            ctx.degraded_reasons.append(timeout_reason)
            if fallback is not None:
                value = fallback()
                detail += "; fallback used"
        except Exception as exc:  # noqa: BLE001
            status = "error"
            detail = f"{type(exc).__name__}: {exc}"
            ctx.degraded_reasons.append(error_reason)
            if fallback is not None:
                value = fallback()
                detail += "; fallback used"

        latency_ms = self._elapsed_ms(started)
        self._mark_stage(ctx, stage, status, latency_ms, budget, detail)
        return value

    def _mark_stage(
        self,
        ctx: RequestContext,
        stage: str,
        status: str,
        latency_ms: float,
        budget: StageBudget,
        detail: str,
    ) -> None:
        ctx.stage_results[stage] = StageResult(
            stage=stage,
            status=status,
            latency_ms=latency_ms,
            target_ms=budget.target_ms,
            timeout_ms=budget.timeout_ms,
            detail=detail,
        )

    def _finalize(self, ctx: RequestContext) -> None:
        transcript = ctx.transcript or self.services.transcribe_fallback(ctx.envelope.user_text)
        reply_text = ctx.reply_text or self.services.generate_reply_fallback(transcript)
        end_to_end_ms = self._elapsed_ms(ctx.envelope.created_at)
        deadline_met = end_to_end_ms <= self.settings.end_to_end_budget_ms

        result = PipelineResult(
            request_id=ctx.envelope.request_id,
            transcript=transcript,
            reply_text=reply_text,
            audio_rendered=ctx.audio_payload is not None,
            degraded_reasons=sorted(set(ctx.degraded_reasons)),
            stage_results=ctx.stage_results,
            end_to_end_ms=end_to_end_ms,
            deadline_met=deadline_met,
            mode_at_ingress=ctx.mode_at_ingress,
        )

        self._results.append(result)
        self.report.add(result)
        self._degradation.observe(result)

        status = "OK" if result.deadline_met else "MISS"
        logger.info(
            "{request_id} | mode={mode} | e2e={e2e:.1f}ms | deadline={status} | audio={audio} | degraded={degraded}",
            request_id=result.request_id,
            mode=result.mode_at_ingress,
            e2e=result.end_to_end_ms,
            status=status,
            audio=result.audio_rendered,
            degraded=",".join(result.degraded_reasons) if result.degraded_reasons else "none",
        )

    @staticmethod
    def _elapsed_ms(started: float) -> float:
        return (time.perf_counter() - started) * 1000.0
