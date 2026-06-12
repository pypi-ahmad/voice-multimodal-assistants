from __future__ import annotations

from pathlib import Path

from voice_study_coach.audio.synthesizer import ProceduralVoiceSynthesizer


def test_synthesizer_writes_wav(tmp_path: Path) -> None:
    synth = ProceduralVoiceSynthesizer(sample_rate=16000, amplitude=0.3, word_seconds=0.1, pause_seconds=0.02)
    out = tmp_path / "out.wav"
    duration = synth.synthesize("hello study coach", out)

    assert out.exists()
    assert duration > 0.0
