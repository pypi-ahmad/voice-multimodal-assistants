"""Procedural text-to-audio synthesizer using pure NumPy + WAV output."""

from __future__ import annotations

import wave
from pathlib import Path
from typing import cast

import numpy as np
from numpy.typing import NDArray


class ProceduralVoiceSynthesizer:
    """Generate speech-like procedural audio for text outputs."""

    def __init__(self, sample_rate: int, amplitude: float, word_seconds: float, pause_seconds: float) -> None:
        self.sample_rate = sample_rate
        self.amplitude = amplitude
        self.word_seconds = word_seconds
        self.pause_seconds = pause_seconds

    def synthesize(self, text: str, output_path: Path) -> float:
        """Synthesize text to WAV file and return duration in seconds."""
        words = [w for w in text.split() if w.strip()]
        if not words:
            words = ["silence"]

        chunks: list[np.ndarray] = []
        for idx, word in enumerate(words):
            duration = self.word_seconds * (0.8 + min(len(word), 12) / 20)
            tone = self._word_tone(word=word, duration=duration, phase_offset=idx)
            chunks.append(tone)

            pause_samples = int(self.pause_seconds * self.sample_rate)
            if pause_samples > 0:
                chunks.append(np.zeros(pause_samples, dtype=np.float32))

        audio = np.concatenate(chunks).astype(np.float32)
        audio = np.clip(audio, -1.0, 1.0)
        pcm = (audio * 32767).astype(np.int16)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(output_path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(self.sample_rate)
            wav.writeframes(pcm.tobytes())

        return len(audio) / self.sample_rate

    def _word_tone(self, word: str, duration: float, phase_offset: int) -> NDArray[np.float32]:
        n_samples = max(1, int(duration * self.sample_rate))
        t = np.linspace(0.0, duration, n_samples, endpoint=False, dtype=np.float32)

        base = 170 + (sum(ord(c) for c in word) % 110)
        f1 = base
        f2 = base * 1.9
        f3 = base * 2.7

        envelope = np.minimum(1.0, t / 0.02) * np.minimum(1.0, (duration - t) / 0.03)
        envelope = np.clip(envelope, 0.0, 1.0)

        phase = phase_offset * 0.19
        wave1 = np.sin(2 * np.pi * f1 * t + phase)
        wave2 = 0.35 * np.sin(2 * np.pi * f2 * t + phase * 0.7)
        wave3 = 0.22 * np.sin(2 * np.pi * f3 * t + phase * 1.3)

        signal = (wave1 + wave2 + wave3) * envelope * self.amplitude
        return cast(NDArray[np.float32], signal.astype(np.float32))
