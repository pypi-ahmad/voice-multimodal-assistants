"""Latency accounting and report helpers for the pipeline."""

from __future__ import annotations

import math
import statistics
from collections import defaultdict

from realtime_mm.config import PipelineSettings
from realtime_mm.models import PipelineResult, StageResult


def _percentile(values: list[float], p: float) -> float:
    """Return percentile using linear interpolation for small samples."""
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]

    ordered = sorted(values)
    idx = (len(ordered) - 1) * p
    lo = math.floor(idx)
    hi = math.ceil(idx)
    if lo == hi:
        return ordered[lo]
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (idx - lo)


def _format_table(rows: list[list[str]], headers: list[str]) -> str:
    """Format an ASCII table without external dependencies."""
    all_rows = [headers, *rows]
    widths = [max(len(row[i]) for row in all_rows) for i in range(len(headers))]

    def render_row(row: list[str]) -> str:
        return " | ".join(cell.ljust(widths[i]) for i, cell in enumerate(row))

    divider = "-+-".join("-" * width for width in widths)
    rendered = [render_row(headers), divider]
    rendered.extend(render_row(row) for row in rows)
    return "\n".join(rendered)


class LatencyReport:
    """Collect and summarize observed pipeline behavior."""

    def __init__(self) -> None:
        self._results: list[PipelineResult] = []

    @property
    def results(self) -> list[PipelineResult]:
        """Return all captured request results."""
        return self._results

    def add(self, result: PipelineResult) -> None:
        """Store one completed request result."""
        self._results.append(result)

    def stage_summary(self) -> dict[str, dict[str, float]]:
        """Aggregate per-stage latency and reliability metrics."""
        grouped: dict[str, list[StageResult]] = defaultdict(list)
        for result in self._results:
            for stage_name, stage_result in result.stage_results.items():
                grouped[stage_name].append(stage_result)

        summary: dict[str, dict[str, float]] = {}
        for stage_name, entries in grouped.items():
            latencies = [entry.latency_ms for entry in entries]
            timeouts = sum(1 for entry in entries if entry.status == "timeout")
            errors = sum(1 for entry in entries if entry.status == "error")
            dropped = sum(1 for entry in entries if entry.status == "dropped")
            skipped = sum(1 for entry in entries if entry.status == "skipped")
            summary[stage_name] = {
                "count": float(len(entries)),
                "p50_ms": _percentile(latencies, 0.50),
                "p95_ms": _percentile(latencies, 0.95),
                "mean_ms": statistics.fmean(latencies) if latencies else 0.0,
                "timeouts": float(timeouts),
                "errors": float(errors),
                "skipped": float(skipped),
                "dropped": float(dropped),
            }
        return summary

    def end_to_end_summary(self) -> dict[str, float]:
        """Aggregate end-to-end latency and deadline adherence."""
        latencies = [r.end_to_end_ms for r in self._results]
        deadline_misses = sum(1 for r in self._results if not r.deadline_met)
        degraded = sum(1 for r in self._results if r.degraded_reasons)

        return {
            "count": float(len(self._results)),
            "p50_ms": _percentile(latencies, 0.50),
            "p95_ms": _percentile(latencies, 0.95),
            "mean_ms": statistics.fmean(latencies) if latencies else 0.0,
            "deadline_miss_count": float(deadline_misses),
            "deadline_miss_ratio": (deadline_misses / len(self._results)) if self._results else 0.0,
            "degraded_count": float(degraded),
        }

    def render_budget_table(self, settings: PipelineSettings) -> str:
        """Render configured latency budget decomposition."""
        stage_target_sum = (
            settings.ingress.target_ms
            + settings.asr.target_ms
            + settings.llm.target_ms
            + settings.tts.target_ms
            + settings.output.target_ms
        )
        queueing_slack = max(0, settings.end_to_end_budget_ms - stage_target_sum)
        rows = [
            ["ingress", str(settings.ingress.target_ms), str(settings.ingress.timeout_ms), "capture + VAD + enqueue"],
            ["asr", str(settings.asr.target_ms), str(settings.asr.timeout_ms), "speech-to-text"],
            ["llm", str(settings.llm.target_ms), str(settings.llm.timeout_ms), "response generation"],
            ["tts", str(settings.tts.target_ms), str(settings.tts.timeout_ms), "text-to-speech"],
            ["output", str(settings.output.target_ms), str(settings.output.timeout_ms), "stream/send result"],
            ["queueing_slack", str(queueing_slack), "-", "queue wait + scheduling jitter reserve"],
            ["end_to_end", str(settings.end_to_end_budget_ms), "-", "global deadline"],
        ]
        return _format_table(rows, headers=["Stage", "Target (ms)", "Timeout (ms)", "Notes"])

    def render_runtime_summary(self) -> str:
        """Render concise runtime metrics table."""
        stage_data = self.stage_summary()
        critical_stages = ["ingress", "asr", "llm", "tts", "output"]
        rows: list[list[str]] = []
        for stage in critical_stages:
            metrics = stage_data.get(stage)
            if metrics is None:
                continue
            rows.append(
                [
                    stage,
                    str(int(metrics["count"])),
                    f"{metrics['p50_ms']:.1f}",
                    f"{metrics['p95_ms']:.1f}",
                    str(int(metrics["timeouts"])),
                    str(int(metrics["errors"])),
                    str(int(metrics["skipped"])),
                    str(int(metrics["dropped"])),
                ]
            )

        queue_overheads: list[float] = []
        for result in self._results:
            stage_sum = sum(
                result.stage_results[stage].latency_ms
                for stage in critical_stages
                if stage in result.stage_results
            )
            queue_overheads.append(max(0.0, result.end_to_end_ms - stage_sum))
        rows.append(
            [
                "queueing_overhead",
                str(len(queue_overheads)),
                f"{_percentile(queue_overheads, 0.50):.1f}",
                f"{_percentile(queue_overheads, 0.95):.1f}",
                "-",
                "-",
                "-",
                "-",
            ]
        )

        e2e = self.end_to_end_summary()
        rows.append(
            [
                "end_to_end",
                str(int(e2e["count"])),
                f"{e2e['p50_ms']:.1f}",
                f"{e2e['p95_ms']:.1f}",
                str(int(e2e["deadline_miss_count"])),
                "-",
                str(int(e2e["degraded_count"])),
                "-",
            ]
        )
        return _format_table(
            rows,
            headers=["Metric", "N", "P50 ms", "P95 ms", "Timeout/Miss", "Errors", "Skipped/Degraded", "Dropped"],
        )
