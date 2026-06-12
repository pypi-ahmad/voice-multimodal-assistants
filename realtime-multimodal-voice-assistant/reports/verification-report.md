# Verification Report

Generated on: 2026-06-12 (local run)
Project: `realtime-multimodal-voice-assistant`

## 1. Scope

This report verifies that the project was run end-to-end and that output artifacts were captured as files.

## 2. Environment Snapshot

Source: `reports/environment.txt`

- Generated at: `2026-06-12T08:03:26+05:30`
- User: `ahmad`
- OS: `Linux 7.0.0-22-generic ... x86_64 GNU/Linux`
- Python: `3.14.5`
- uv: `0.11.19`

## 3. Executed Commands

1. `uv run rtma-demo --requests 8 --profile normal`
2. `uv run rtma-demo --requests 8 --profile stress`
3. `uv run pytest -q`

All three completed successfully (exit code 0).

## 4. Runtime Results Summary

### Normal Profile (`reports/run-normal.txt`)

- End-to-end P50: `1301.0 ms`
- End-to-end P95: `1932.5 ms`
- Deadline misses: `3/8`
- Degraded requests: `5/8`
- Queueing overhead P50/P95: `638.1 / 1203.8 ms`

### Stress Profile (`reports/run-stress.txt`)

- End-to-end P50: `2972.4 ms`
- End-to-end P95: `4914.1 ms`
- Deadline misses: `7/8`
- Degraded requests: `8/8`
- ASR timeouts: `3`
- LLM timeouts: `3`
- TTS skipped: `8`
- Queueing overhead P50/P95: `1828.3 / 3707.8 ms`

## 5. Test Results

Source: `reports/pytest.txt`

- `3 passed in 0.90s`

Validated behaviors:
- ASR timeout fallback
- LLM/TTS timeout degradation
- End-to-end deadline miss detection

## 6. Artifacts Produced

- `reports/environment.txt`
- `reports/run-normal.txt`
- `reports/run-stress.txt`
- `reports/pytest.txt`
- `reports/verification-report.md`

## 7. Verification Status

- Real runs performed: **Yes**
- Raw outputs captured to files: **Yes**
- Test suite executed and passed: **Yes**
- Documentation report produced: **Yes**

## 8. Notes

The pipeline uses simulated ASR/LLM/TTS services by design (deterministic, seed-based), so outputs are real execution results from simulation rather than external provider APIs.
