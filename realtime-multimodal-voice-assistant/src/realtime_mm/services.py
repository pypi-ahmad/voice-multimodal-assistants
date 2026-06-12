"""Simulated service backends for a real-time voice assistant."""

from __future__ import annotations

import asyncio
import random

from realtime_mm.config import PipelineSettings


class SimulatedServices:
    """Primary and fallback implementations for each stage.

    The primary implementations intentionally include random latency spikes,
    so timeout/degradation behavior can be observed in realistic conditions.
    """

    def __init__(self, settings: PipelineSettings) -> None:
        self.settings = settings
        self.rng = random.Random(settings.random_seed)

    async def ingest_capture(self, text: str) -> None:
        """Simulate microphone capture + VAD cost for an utterance."""
        words = max(1, len(text.split()))
        base = 70 + words * 7
        jitter = self.rng.uniform(-20, 35)
        await asyncio.sleep(max(0.01, (base + jitter) / 1000.0))

    async def transcribe_primary(self, text: str) -> str:
        """Simulate ASR latency and produce transcript."""
        await asyncio.sleep(self._sample_latency_ms("asr") / 1000.0)
        return " ".join(text.strip().split())

    def transcribe_fallback(self, text: str) -> str:
        """Provide a shorter transcript when ASR times out."""
        words = text.strip().split()
        return " ".join(words[: min(8, len(words))]) + (" ..." if len(words) > 8 else "")

    async def generate_reply_primary(self, transcript: str) -> str:
        """Simulate LLM response generation."""
        await asyncio.sleep(self._sample_latency_ms("llm") / 1000.0)
        short = transcript[:120]
        return f"Actionable summary: {short}. Recommended next step: confirm intent and execute safely."

    def generate_reply_fallback(self, transcript: str) -> str:
        """Return a compact fallback response under LLM timeout/error."""
        if not transcript.strip():
            return "I am running in fallback mode. Please repeat your request."
        return f"Fallback response: I heard '{transcript[:60]}'. I can provide a short answer now or retry."

    async def synthesize_primary(self, reply_text: str) -> bytes:
        """Simulate TTS synthesis."""
        await asyncio.sleep(self._sample_latency_ms("tts") / 1000.0)
        return f"AUDIO::{reply_text}".encode("utf-8")

    async def output_stream(self) -> None:
        """Simulate output transport latency."""
        await asyncio.sleep(self._sample_latency_ms("output") / 1000.0)

    def _sample_latency_ms(self, stage: str) -> float:
        """Sample stage latency from a profile with bursty spikes."""
        if self.settings.profile == "normal":
            profile = {
                "asr": (180, 45, 0.06, 130),
                "llm": (330, 90, 0.08, 170),
                "tts": (170, 60, 0.08, 150),
                "output": (45, 20, 0.02, 30),
            }
        else:
            profile = {
                "asr": (260, 90, 0.22, 200),
                "llm": (620, 180, 0.30, 320),
                "tts": (320, 110, 0.27, 260),
                "output": (70, 28, 0.08, 60),
            }

        mean, jitter, spike_prob, spike_ms = profile[stage]
        sampled = mean + self.rng.uniform(-jitter, jitter)
        if self.rng.random() < spike_prob:
            sampled += self.rng.uniform(spike_ms * 0.6, spike_ms)

        return max(8.0, sampled)
