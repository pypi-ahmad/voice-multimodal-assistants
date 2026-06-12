from __future__ import annotations

from pathlib import Path

from voice_study_coach.audio.transcriber import SidecarTranscriber


def test_sidecar_transcriber_reads_txt(tmp_path: Path) -> None:
    audio = tmp_path / "sample.wav"
    audio.write_bytes(b"RIFF")
    audio.with_suffix(".txt").write_text("test transcript", encoding="utf-8")

    result = SidecarTranscriber().transcribe(audio)

    assert result.method == "sidecar"
    assert "test transcript" in result.transcript
