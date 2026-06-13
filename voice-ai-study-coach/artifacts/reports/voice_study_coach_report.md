# Voice AI Study Coach Report

Generated at: `2026-06-12T11:44:32+00:00`

## Setup

- Tutor model: `phi3.5:3.8b`
- Quiz model: `functiongemma:270m`
- Tasks evaluated: **6**

## Metrics

- Baseline keyword recall mean: **0.0000**
- Tutor keyword recall mean: **1.0000**
- Keyword recall gain: **1.0000**
- Retrieval hit rate: **1.0000**
- Source citation rate: **1.0000**
- Tutor fallback rate: **1.0000**
- Quiz fallback rate: **1.0000**
- Avg tutor audio duration (s): **6.023**
- Avg total latency (ms): **7026.85**

## Telemetry

- Total spans: **175**
- Unique traces: **10**

| Span | Count | Mean ms | P95 ms | Errors |
|---|---:|---:|---:|---:|
| baseline_answer | 28 | 2007.853 | 2015.986 | 0 |
| quiz_generation | 28 | 2004.269 | 2008.116 | 0 |
| retrieve_context | 28 | 0.061 | 0.073 | 0 |
| synthesize_quiz_audio | 28 | 1.884 | 5.943 | 0 |
| synthesize_tutor_audio | 28 | 8.86 | 15.146 | 0 |
| transcribe_audio | 7 | 0.085 | 0.104 | 0 |
| tutor_answer | 28 | 3005.983 | 3012.842 | 0 |


## Per-task Scores

| Task ID | Baseline Recall | Tutor Recall | Gain | Retrieval Hit |
|---|---:|---:|---:|---:|
| q1 | 0.000 | 1.000 | 1.000 | 1 |
| q2 | 0.000 | 1.000 | 1.000 | 1 |
| q3 | 0.000 | 1.000 | 1.000 | 1 |
| q4 | 0.000 | 1.000 | 1.000 | 1 |
| q5 | 0.000 | 1.000 | 1.000 | 1 |
| q6 | 0.000 | 1.000 | 1.000 | 1 |
