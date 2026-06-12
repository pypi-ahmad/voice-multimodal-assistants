# Real-Time Multimodal Voice Assistant (Streaming Pipeline)

This project is a **production-style simulation** of a real-time multimodal assistant pipeline.
It focuses on the hard parts that matter in real systems:

- end-to-end latency budgeting,
- queueing and bounded waits,
- timeout handling with fallbacks,
- graceful degradation under overload,
- observability via per-stage and end-to-end metrics.

The implementation runs fully local (no API keys required), but the design maps directly to real ASR/LLM/TTS backends.

## 1. What You Will Build

A streaming pipeline with 5 stages:

1. `ingress`: microphone capture + VAD simulation.
2. `asr`: speech-to-text.
3. `llm`: response generation.
4. `tts`: text-to-speech (skippable in degraded mode).
5. `output`: final stream/send to client.

Each stage has:

- target latency budget,
- hard timeout,
- fallback behavior.

## 2. Real-Time Design Choices

### Latency decomposition (configured budget)

The default target budget is:

- ingress: 180 ms (timeout 260 ms)
- asr: 280 ms (timeout 380 ms)
- llm: 520 ms (timeout 760 ms)
- tts: 260 ms (timeout 420 ms)
- output: 90 ms (timeout 140 ms)
- queueing slack reserve: 70 ms (for queue wait + scheduler jitter)
- end-to-end deadline: 1400 ms

### Graceful degradation policy

- `ASR timeout/error` -> use compact fallback transcript.
- `LLM timeout/error` -> use deterministic fallback answer.
- `TTS timeout/error` -> text-only response.
- Under sustained stress (deadline misses/timeouts), global mode shifts to `degraded`, proactively skipping TTS to preserve responsiveness.
- Enqueue operations are bounded; if a queue push times out, request is dropped with explicit status.

### Why this is real-time-safe

- Bounded queue waits prevent unbounded tail latency.
- Every stage is wrapped in timeout guards.
- Backpressure decisions are explicit and measurable.
- End-to-end deadline is tracked per request, not inferred from averages.

## 3. Project Structure

```text
realtime-multimodal-voice-assistant/
  src/realtime_mm/
    cli.py            # CLI demo entrypoint
    config.py         # Pydantic settings + stage budgets
    demo_inputs.py    # deterministic demo utterances
    latency.py        # metrics aggregation and ASCII reports
    models.py         # dataclasses for request/result lifecycle
    pipeline.py       # async worker pipeline + degradation controller
    services.py       # simulated ASR/LLM/TTS services with spikes
  tests/
    test_pipeline.py  # timeout/degradation/deadline tests
  README.md
  pyproject.toml
```

## 4. Quick Start (`uv`)

From project root:

```bash
uv sync --dev
uv run rtma-demo --requests 8 --profile normal
```

To force overload-like behavior:

```bash
uv run rtma-demo --requests 12 --profile stress --show-responses
```

### Tutorial Notebook

A step-by-step notebook version is included at:

- `notebooks/realtime_multimodal_tutorial.ipynb`

It contains executable cells with explanations and captured real outputs.
You can open it in Jupyter and rerun cells safely; it does not modify core source files.

## 5. How the Code Works (Tutorial Walkthrough)

### `config.py`
- `PipelineSettings` defines all budgets, queue limits, and adaptive degradation thresholds.
- Configuration can be overridden via env vars with prefix `RTMA_`.

### `services.py`
- `SimulatedServices` mimics real backend calls with random jitter/spikes.
- Primary methods are async and can exceed budgets.
- Fallback methods are deterministic and fast.

### `pipeline.py`
- Uses `asyncio.Queue` to model stage boundaries.
- Worker chain: ASR worker -> LLM worker -> TTS worker -> Output worker.
- `_run_stage` wraps each stage with `asyncio.wait_for()` and fallback logic.
- `DegradationController` monitors recent failures and toggles degraded mode.

### `latency.py`
- Aggregates per-stage metrics: `P50`, `P95`, timeout/error counts.
- Estimates `queueing_overhead = end_to_end - sum(stage latencies)` to expose backlog pressure.
- Reports end-to-end deadline misses and degraded request counts.
- Produces human-readable ASCII tables for CLI output.

### `tests/test_pipeline.py`
- Validates ASR timeout fallback.
- Validates layered degradation for LLM/TTS timeout.
- Validates deadline miss detection.

## 6. Example Output

From a sample run (`uv run rtma-demo --requests 8 --profile normal`):

```text
=== Runtime Summary ===
Metric            | N | P50 ms | P95 ms | Timeout/Miss | Errors | Skipped/Degraded | Dropped
------------------+---+--------+--------+--------------+--------+------------------+--------
ingress           | 8 | 150.6  | 161.7  | 0            | 0      | 0                | 0
asr               | 8 | 159.1  | 245.5  | 0            | 0      | 0                | 0
llm               | 8 | 331.0  | 371.1  | 0            | 0      | 0                | 0
tts               | 8 | 0.0    | 174.6  | 0            | 0      | 5                | 0
output            | 8 | 43.2   | 58.4   | 0            | 0      | 0                | 0
queueing_overhead | 8 | 638.0  | 1204.9 | -            | -      | -                | -
end_to_end        | 8 | 1301.4 | 1932.2 | 3            | -      | 5                | -
```

Interpretation:
- Core stage latencies are healthy.
- Queueing overhead dominates tail latency, which is typical in bursty real-time workloads.
- TTS gets skipped on late requests to protect user-perceived responsiveness.

## 7. Moving to Production Backends

Replace simulated stage calls in `services.py` with real providers:

- ASR provider (streaming preferred),
- LLM provider with incremental token streaming,
- TTS provider with chunked synthesis.

Keep the same interface and timeout wrappers in `pipeline.py`; this preserves behavior under stress with minimal code churn.

## 8. Key Tradeoff

This implementation chooses **deadline protection over full-fidelity output**:

- During stress, audio can be skipped (text-only fallback) to keep response time predictable.
- Tradeoff: lower UX richness under load, but better SLA reliability and fewer catastrophic tail-latency spikes.

## Setup

```bash
git clone https://github.com/pypi-ahmad/realtime-multimodal-voice-assistant.git
cd realtime-multimodal-voice-assistant
```
