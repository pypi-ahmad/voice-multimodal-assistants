from __future__ import annotations

import json
from pathlib import Path

from voice_study_coach.telemetry.tracer import JsonlTelemetryTracer, summarize_traces


def test_summarize_traces(tmp_path: Path) -> None:
    traces = tmp_path / "traces.jsonl"
    summary = tmp_path / "summary.json"

    tracer = JsonlTelemetryTracer(traces)
    with tracer.span("x1", "retrieve", {"top_k": 3}):
        pass
    with tracer.span("x1", "tutor_answer", {"model": "phi3.5"}):
        pass

    payload = summarize_traces(traces, summary)

    assert payload["n_spans"] == 2
    loaded = json.loads(summary.read_text(encoding="utf-8"))
    assert loaded["n_unique_traces"] == 1
