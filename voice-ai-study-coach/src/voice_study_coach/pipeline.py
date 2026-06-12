"""End-to-end pipeline for voice study coach."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from voice_study_coach.agents.quiz import QuizAgent
from voice_study_coach.agents.tutor import TutorAgent
from voice_study_coach.audio.synthesizer import ProceduralVoiceSynthesizer
from voice_study_coach.audio.transcriber import SidecarTranscriber
from voice_study_coach.config import Settings
from voice_study_coach.eval.evaluator import evaluate, load_tasks
from voice_study_coach.ollama_client import AsyncOllamaGateway
from voice_study_coach.orchestration.session import VoiceStudySession
from voice_study_coach.reporting.reporting import (
    render_report,
    save_demo_runs,
    save_predictions,
    save_summary,
)
from voice_study_coach.telemetry.tracer import JsonlTelemetryTracer, summarize_traces
from voice_study_coach.tools.knowledge_base import load_docs


def _make_synth(settings: Settings) -> ProceduralVoiceSynthesizer:
    return ProceduralVoiceSynthesizer(
        sample_rate=settings.audio_sample_rate,
        amplitude=settings.audio_amplitude,
        word_seconds=settings.word_seconds,
        pause_seconds=settings.pause_seconds,
    )


def _build_session(settings: Settings, tracer: JsonlTelemetryTracer) -> VoiceStudySession:
    docs = load_docs(settings.resolved_knowledge_dir)
    gateway = AsyncOllamaGateway(settings.ollama_host)

    tutor = TutorAgent(settings=settings, gateway=gateway)
    quiz = QuizAgent(settings=settings, gateway=gateway)
    transcriber = SidecarTranscriber()
    synth = _make_synth(settings)

    return VoiceStudySession(
        tutor=tutor,
        quiz=quiz,
        transcriber=transcriber,
        synthesizer=synth,
        docs=docs,
        top_k=settings.retrieval_top_k,
        audio_output_dir=settings.resolved_audio_dir,
        tracer=tracer,
    )


def _prepare_demo_audio(settings: Settings) -> dict[str, str]:
    synth = _make_synth(settings)

    q1_audio = settings.resolved_demo_audio_dir / "student_question_1.wav"
    q1_text = "Can you explain when emergency rollback is mandatory for API incidents?"
    synth.synthesize(q1_text, q1_audio)
    q1_audio.with_suffix(".txt").write_text(q1_text, encoding="utf-8")

    q2_audio = settings.resolved_demo_audio_dir / "student_question_2.wav"
    q2_text = "What is the enterprise first response SLA and where do escalations go?"
    synth.synthesize(q2_text, q2_audio)
    q2_audio.with_suffix(".txt").write_text(q2_text, encoding="utf-8")

    return {
        "question_1_audio": q1_audio.as_posix(),
        "question_2_audio": q2_audio.as_posix(),
    }


async def run_demo(settings: Settings) -> list[dict[str, Any]]:
    """Run demo sessions (audio and text)."""
    demo_audio = _prepare_demo_audio(settings)

    tracer = JsonlTelemetryTracer(settings.traces_file)
    session = _build_session(settings, tracer)

    runs = []
    runs.append(
        json.loads(
            (
                await session.run(
                    trace_id="demo-audio-001",
                    question_audio_path=Path(demo_audio["question_1_audio"]),
                )
            ).model_dump_json()
        )
    )
    runs.append(
        json.loads(
            (
                await session.run(
                    trace_id="demo-audio-002",
                    question_audio_path=Path(demo_audio["question_2_audio"]),
                )
            ).model_dump_json()
        )
    )
    runs.append(
        json.loads(
            (
                await session.run(
                    trace_id="demo-text-001",
                    question_text="What canary traffic percentage is used at release start?",
                )
            ).model_dump_json()
        )
    )

    save_demo_runs(runs, settings.demo_runs_file)
    return runs


async def run_evaluation(settings: Settings, reset_traces: bool = False) -> dict[str, Any]:
    """Run baseline-vs-tutor evaluation and save artifacts."""
    if reset_traces and settings.traces_file.exists():
        settings.traces_file.unlink()

    tracer = JsonlTelemetryTracer(settings.traces_file)
    session = _build_session(settings, tracer)

    tasks = load_tasks(settings.resolved_evaluation_file.as_posix())
    rows, summary = await evaluate(session, tasks)

    save_predictions(rows, settings.predictions_file)
    save_summary(summary, settings.summary_file)

    telemetry_summary = summarize_traces(settings.traces_file, settings.telemetry_summary_file)
    render_report(
        summary=summary,
        rows=rows,
        tutor_model=settings.tutor_model,
        quiz_model=settings.quiz_model,
        telemetry_summary=telemetry_summary,
        output_path=settings.report_file,
    )

    return {
        "summary": json.loads(summary.model_dump_json()),
        "predictions_path": settings.predictions_file.as_posix(),
        "summary_path": settings.summary_file.as_posix(),
        "report_path": settings.report_file.as_posix(),
        "trace_path": settings.traces_file.as_posix(),
        "telemetry_summary_path": settings.telemetry_summary_file.as_posix(),
    }


async def run_all(settings: Settings) -> dict[str, Any]:
    """Run demo sessions, evaluation, and save run summary."""
    if settings.traces_file.exists():
        settings.traces_file.unlink()

    demo_runs = await run_demo(settings)
    eval_payload = await run_evaluation(settings, reset_traces=False)

    payload = {
        "tutor_model": settings.tutor_model,
        "quiz_model": settings.quiz_model,
        "demo_runs_path": settings.demo_runs_file.as_posix(),
        "demo_count": len(demo_runs),
        "evaluation": eval_payload,
        "run_summary_path": settings.run_summary_file.as_posix(),
    }

    settings.run_summary_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload
