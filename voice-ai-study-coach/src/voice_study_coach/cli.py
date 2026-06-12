"""CLI entrypoint for voice study coach."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Coroutine
from typing import Any

import typer

from voice_study_coach.config import get_settings
from voice_study_coach.logging_utils import configure_logging
from voice_study_coach.ollama_client import AsyncOllamaGateway
from voice_study_coach.pipeline import run_all, run_demo, run_evaluation
from voice_study_coach.telemetry.tracer import summarize_traces

app = typer.Typer(help="Voice AI study coach")


def _run_async[T](coro: Coroutine[Any, Any, T]) -> T:
    return asyncio.run(coro)


@app.callback()
def callback() -> None:
    settings = get_settings()
    configure_logging()
    settings.ensure_dirs()


@app.command("check-backends")
def check_backends_cmd() -> None:
    settings = get_settings()
    gateway = AsyncOllamaGateway(settings.ollama_host)

    async def _run() -> dict[str, Any]:
        models = sorted(await gateway.list_model_names())
        configured = [settings.tutor_model, settings.quiz_model]
        return {
            "configured_models": configured,
            "available_subset": [m for m in configured if m in models],
            "n_local_models": len(models),
            "audio_backend": "procedural_numpy_wav",
            "stt_backend": "sidecar_txt_transcriber",
        }

    payload = _run_async(_run())
    typer.echo(json.dumps(payload, indent=2))


@app.command("run-demo")
def run_demo_cmd() -> None:
    settings = get_settings()
    payload = _run_async(run_demo(settings))
    typer.echo(json.dumps(payload, indent=2))


@app.command("evaluate")
def evaluate_cmd() -> None:
    settings = get_settings()
    payload = _run_async(run_evaluation(settings, reset_traces=False))
    typer.echo(json.dumps(payload["summary"], indent=2))


@app.command("run-all")
def run_all_cmd() -> None:
    settings = get_settings()
    payload = _run_async(run_all(settings))
    typer.echo(json.dumps(payload["evaluation"]["summary"], indent=2))


@app.command("summarize-telemetry")
def summarize_telemetry_cmd() -> None:
    settings = get_settings()
    payload = summarize_traces(settings.traces_file, settings.telemetry_summary_file)
    typer.echo(json.dumps(payload, indent=2))


if __name__ == "__main__":
    app()
