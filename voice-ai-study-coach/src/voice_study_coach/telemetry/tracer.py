"""JSONL telemetry tracer and summarizer."""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any

import numpy as np

from voice_study_coach.schemas import TraceSpanRecord

JsonScalar = str | int | float | bool | None


class JsonlTelemetryTracer:
    """Persist span telemetry as JSONL."""

    def __init__(self, trace_path: Path) -> None:
        self._trace_path = trace_path
        self._trace_path.parent.mkdir(parents=True, exist_ok=True)
        if not self._trace_path.exists():
            self._trace_path.touch()

    @contextmanager
    def span(
        self,
        trace_id: str,
        span_name: str,
        attributes: dict[str, JsonScalar] | None = None,
    ) -> Iterator[dict[str, JsonScalar]]:
        """Record one span with start/end timestamps and attributes."""
        start_wall = datetime.now(tz=UTC)
        start_perf = perf_counter()
        attrs = dict(attributes or {})
        status = "ok"

        try:
            yield attrs
        except Exception as exc:
            status = "error"
            attrs["error"] = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            end_wall = datetime.now(tz=UTC)
            latency_ms = (perf_counter() - start_perf) * 1000.0
            row = TraceSpanRecord(
                trace_id=trace_id,
                span_name=span_name,
                status="error" if status == "error" else "ok",
                start_time_utc=start_wall.isoformat(timespec="milliseconds"),
                end_time_utc=end_wall.isoformat(timespec="milliseconds"),
                latency_ms=round(latency_ms, 3),
                attributes={k: _safe_json(v) for k, v in attrs.items()},
            )
            with self._trace_path.open("a", encoding="utf-8") as handle:
                handle.write(row.model_dump_json())
                handle.write("\n")


def _safe_json(value: JsonScalar) -> JsonScalar:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _safe_mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return float(sum(values) / len(values))


def _safe_percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    return float(np.quantile(np.asarray(values, dtype=np.float64), q))


def summarize_traces(trace_path: Path, output_path: Path) -> dict[str, Any]:
    """Aggregate traces into per-stage stats."""
    rows: list[TraceSpanRecord] = []
    if trace_path.exists():
        for line in trace_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(TraceSpanRecord.model_validate_json(line))

    buckets: dict[str, list[TraceSpanRecord]] = {}
    for row in rows:
        buckets.setdefault(row.span_name, []).append(row)

    by_span: list[dict[str, Any]] = []
    for span_name in sorted(buckets):
        items = buckets[span_name]
        latencies = [item.latency_ms for item in items]
        by_span.append(
            {
                "span_name": span_name,
                "count": len(items),
                "error_count": sum(1 for item in items if item.status == "error"),
                "latency_ms_mean": round(_safe_mean(latencies), 3),
                "latency_ms_p50": round(_safe_percentile(latencies, 0.5), 3),
                "latency_ms_p95": round(_safe_percentile(latencies, 0.95), 3),
                "latency_ms_max": round(max(latencies) if latencies else 0.0, 3),
            }
        )

    payload: dict[str, Any] = {
        "generated_at_utc": datetime.now(tz=UTC).isoformat(timespec="seconds"),
        "trace_file": trace_path.as_posix(),
        "n_spans": len(rows),
        "n_unique_traces": len({row.trace_id for row in rows}),
        "by_span": by_span,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload
