"""Simple transcription adapter using sidecar transcript files."""

from __future__ import annotations

from pathlib import Path

from voice_study_coach.schemas import TranscriptResult


class SidecarTranscriber:
    """Transcribe audio by reading <audio>.txt sidecar transcript."""

    def transcribe(self, audio_path: Path) -> TranscriptResult:
        sidecar = audio_path.with_suffix(".txt")
        if sidecar.exists():
            text = sidecar.read_text(encoding="utf-8").strip()
            if text:
                return TranscriptResult(transcript=text, method="sidecar")

        return TranscriptResult(
            transcript="I could not transcribe this audio automatically. Provide a sidecar .txt transcript.",
            method="empty_fallback",
        )
