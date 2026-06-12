# Project 7: Voice AI Study Coach

Notebook-based voice tutoring system with local Ollama agents, audio I/O adapters, telemetry traces, and quantitative evals.

- Tutor model: `phi3.5:3.8b`
- Quiz model: `functiongemma:270m`
- Python: `3.12.10`
- Env/package manager: `uv`

## What this project demonstrates

- Multi-agent coaching workflow (`TutorAgent`, `QuizAgent`).
- Voice pipeline with audio input adapter and generated `.wav` outputs.
- Fallback-safe execution under local model timeouts.
- Evaluation + telemetry artifacts for reproducible measurement.

## Setup

```bash
git clone https://github.com/pypi-ahmad/voice-ai-study-coach.git
cd voice-ai-study-coach
uv python pin 3.12.10
uv sync --dev
cp .env.example .env
```

## Pull required models

```bash
ollama pull phi3.5:3.8b
ollama pull functiongemma:270m
```

## Run end-to-end

```bash
uv run voice-study-coach run-all
```

## Notebook tutorial flow

```bash
uv run python scripts/execute_notebooks.py
```

Notebook order:

1. `notebooks/01_setup_and_backend_check.ipynb`
2. `notebooks/02_voice_io_tutorial.ipynb`
3. `notebooks/03_single_session_walkthrough.ipynb`
4. `notebooks/04_evaluation.ipynb`
5. `notebooks/05_telemetry_and_report.ipynb`
6. `notebooks/06_full_tutorial_voice_ai_study_coach.ipynb`

## Real results (executed on June 12, 2026)

From `artifacts/evals/summary.json`:

- `n_tasks`: `6`
- `baseline_keyword_recall_mean`: `0.0`
- `tutor_keyword_recall_mean`: `1.0`
- `keyword_recall_gain`: `+1.0`
- `retrieval_hit_rate`: `1.0`
- `source_citation_rate`: `1.0`
- `tutor_fallback_rate`: `1.0`
- `quiz_fallback_rate`: `1.0`
- `avg_tutor_audio_seconds`: `6.0232`
- `avg_total_latency_ms`: `7026.85`

From `artifacts/telemetry/summary.json`:

- `n_spans`: `175`
- `n_unique_traces`: `10`
- highest mean-latency stage: `tutor_answer` (`3005.98 ms`)

Generated outputs include:

- `artifacts/runs/demo_sessions.json`
- `artifacts/audio/*.wav`
- `artifacts/evals/predictions.csv`
- `artifacts/evals/summary.json`
- `artifacts/telemetry/traces.jsonl`
- `artifacts/telemetry/summary.json`
- `artifacts/reports/voice_study_coach_report.md`
- `artifacts/run_summary.json`

## CLI examples

```bash
uv run voice-study-coach check-backends
uv run voice-study-coach run-demo
uv run voice-study-coach evaluate
uv run voice-study-coach summarize-telemetry
```
