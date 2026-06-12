"""Generate notebook tutorial files."""

from __future__ import annotations

from pathlib import Path

import nbformat as nbf


def _write(path: Path, cells: list[nbf.NotebookNode]) -> None:
    nb = nbf.v4.new_notebook()
    nb["cells"] = cells
    path.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(nb, path)


def main() -> None:
    base = Path("notebooks")

    _write(
        base / "01_setup_and_backend_check.ipynb",
        [
            nbf.v4.new_markdown_cell(
                "# 01 - Setup and Backend Check\n"
                "Validate configuration, local models, and voice pipeline backends."
            ),
            nbf.v4.new_code_cell(
                "from voice_study_coach.config import get_settings\n"
                "from voice_study_coach.ollama_client import AsyncOllamaGateway\n"
                "settings = get_settings()\n"
                "settings"
            ),
            nbf.v4.new_code_cell(
                "gateway = AsyncOllamaGateway(settings.ollama_host)\n"
                "models = await gateway.list_model_names()\n"
                "{'configured': [settings.tutor_model, settings.quiz_model], 'available_subset': [m for m in [settings.tutor_model, settings.quiz_model] if m in models], 'n_local_models': len(models)}"
            ),
        ],
    )

    _write(
        base / "02_voice_io_tutorial.ipynb",
        [
            nbf.v4.new_markdown_cell(
                "# 02 - Voice I/O Tutorial\n"
                "Generate demo student audio, attach sidecar transcript, and inspect transcription."
            ),
            nbf.v4.new_code_cell(
                "from pathlib import Path\n"
                "from voice_study_coach.config import get_settings\n"
                "from voice_study_coach.audio.synthesizer import ProceduralVoiceSynthesizer\n"
                "from voice_study_coach.audio.transcriber import SidecarTranscriber\n"
                "settings = get_settings()\n"
                "synth = ProceduralVoiceSynthesizer(settings.audio_sample_rate, settings.audio_amplitude, settings.word_seconds, settings.pause_seconds)\n"
                "transcriber = SidecarTranscriber()"
            ),
            nbf.v4.new_code_cell(
                "audio_path = settings.resolved_demo_audio_dir / 'notebook_student_question.wav'\n"
                "text = 'Explain the rollback threshold for API incidents.'\n"
                "seconds = synth.synthesize(text, audio_path)\n"
                "audio_path.with_suffix('.txt').write_text(text, encoding='utf-8')\n"
                "{'audio_path': audio_path.as_posix(), 'seconds': round(seconds, 3)}"
            ),
            nbf.v4.new_code_cell(
                "transcript = transcriber.transcribe(audio_path)\n"
                "transcript"
            ),
        ],
    )

    _write(
        base / "03_single_session_walkthrough.ipynb",
        [
            nbf.v4.new_markdown_cell(
                "# 03 - Single Study Session\n"
                "Run one full audio-based coaching turn and inspect outputs."
            ),
            nbf.v4.new_code_cell(
                "from voice_study_coach.config import get_settings\n"
                "from voice_study_coach.pipeline import run_demo\n"
                "settings = get_settings()"
            ),
            nbf.v4.new_code_cell(
                "runs = await run_demo(settings)\n"
                "runs[0]"
            ),
        ],
    )

    _write(
        base / "04_evaluation.ipynb",
        [
            nbf.v4.new_markdown_cell(
                "# 04 - Evaluation\n"
                "Run baseline-vs-tutor evaluation and inspect metric summary."
            ),
            nbf.v4.new_code_cell(
                "from voice_study_coach.config import get_settings\n"
                "from voice_study_coach.pipeline import run_evaluation\n"
                "settings = get_settings()"
            ),
            nbf.v4.new_code_cell(
                "payload = await run_evaluation(settings, reset_traces=False)\n"
                "payload['summary']"
            ),
        ],
    )

    _write(
        base / "05_telemetry_and_report.ipynb",
        [
            nbf.v4.new_markdown_cell(
                "# 05 - Telemetry and Report\n"
                "Inspect trace summary and generated markdown report."
            ),
            nbf.v4.new_code_cell(
                "from pathlib import Path\n"
                "import json\n"
                "from voice_study_coach.config import get_settings\n"
                "settings = get_settings()"
            ),
            nbf.v4.new_code_cell(
                "telemetry = json.loads(Path(settings.telemetry_summary_file).read_text(encoding='utf-8'))\n"
                "telemetry"
            ),
            nbf.v4.new_code_cell(
                "report = Path(settings.report_file).read_text(encoding='utf-8')\n"
                "print(report[:1500])"
            ),
        ],
    )

    _write(
        base / "06_full_tutorial_voice_ai_study_coach.ipynb",
        [
            nbf.v4.new_markdown_cell(
                "# 06 - Full Tutorial: Voice AI Study Coach\n"
                "This notebook is a step-by-step, end-to-end tutorial version of the project.\n\n"
                "You will learn and run:\n"
                "1. Configuration and local backend checks\n"
                "2. Knowledge loading and retrieval\n"
                "3. Voice I/O (procedural synthesis + sidecar transcript)\n"
                "4. A full tutoring session orchestration\n"
                "5. Batch demo runs, evaluation, telemetry, and report inspection"
            ),
            nbf.v4.new_markdown_cell(
                "## Step 1 - Imports and Project Settings\n"
                "Load all key modules used by the voice tutoring system."
            ),
            nbf.v4.new_code_cell(
                "from pathlib import Path\n"
                "import csv\n"
                "import json\n\n"
                "from voice_study_coach.config import get_settings\n"
                "from voice_study_coach.ollama_client import AsyncOllamaGateway\n"
                "from voice_study_coach.tools.knowledge_base import load_docs, retrieve\n"
                "from voice_study_coach.audio.synthesizer import ProceduralVoiceSynthesizer\n"
                "from voice_study_coach.audio.transcriber import SidecarTranscriber\n"
                "from voice_study_coach.agents.tutor import TutorAgent\n"
                "from voice_study_coach.agents.quiz import QuizAgent\n"
                "from voice_study_coach.orchestration.session import VoiceStudySession\n"
                "from voice_study_coach.telemetry.tracer import JsonlTelemetryTracer, summarize_traces\n"
                "from voice_study_coach.pipeline import run_demo, run_evaluation\n\n"
                "settings = get_settings()\n"
                "settings"
            ),
            nbf.v4.new_markdown_cell(
                "## Step 2 - Runtime Configuration Snapshot\n"
                "Print the practical runtime knobs that affect behavior, latency, and outputs."
            ),
            nbf.v4.new_code_cell(
                "config_view = {\n"
                "    'ollama_host': settings.ollama_host,\n"
                "    'tutor_model': settings.tutor_model,\n"
                "    'quiz_model': settings.quiz_model,\n"
                "    'retrieval_top_k': settings.retrieval_top_k,\n"
                "    'generation_timeout_seconds': settings.generation_timeout_seconds,\n"
                "    'audio_sample_rate': settings.audio_sample_rate,\n"
                "    'audio_amplitude': settings.audio_amplitude,\n"
                "}\n"
                "config_view"
            ),
            nbf.v4.new_markdown_cell(
                "## Step 3 - Check Local Model Availability\n"
                "This confirms whether the configured Ollama models are locally available."
            ),
            nbf.v4.new_code_cell(
                "gateway = AsyncOllamaGateway(settings.ollama_host)\n"
                "local_models = await gateway.list_model_names()\n"
                "{\n"
                "    'configured_models': [settings.tutor_model, settings.quiz_model],\n"
                "    'available_subset': [m for m in [settings.tutor_model, settings.quiz_model] if m in local_models],\n"
                "    'n_local_models': len(local_models),\n"
                "}"
            ),
            nbf.v4.new_markdown_cell(
                "## Step 4 - Load Knowledge Base Documents\n"
                "The study coach retrieves from these local markdown files."
            ),
            nbf.v4.new_code_cell(
                "docs = load_docs(settings.resolved_knowledge_dir)\n"
                "{\n"
                "    'n_docs': len(docs),\n"
                "    'sources': [doc.source for doc in docs],\n"
                "}"
            ),
            nbf.v4.new_markdown_cell(
                "## Step 5 - Retrieval Demonstration\n"
                "Run lexical retrieval for one question and inspect ranked sources."
            ),
            nbf.v4.new_code_cell(
                "sample_question = 'When is emergency rollback mandatory for API incidents?'\n"
                "hits = retrieve(sample_question, docs, top_k=settings.retrieval_top_k)\n"
                "[\n"
                "    {'source': item.doc.source, 'score': round(item.score, 4)}\n"
                "    for item in hits\n"
                "]"
            ),
            nbf.v4.new_markdown_cell(
                "## Step 6 - Build Voice Input Example\n"
                "Create a WAV question and sidecar transcript (`.txt`) so the transcriber can decode it."
            ),
            nbf.v4.new_code_cell(
                "synth = ProceduralVoiceSynthesizer(\n"
                "    sample_rate=settings.audio_sample_rate,\n"
                "    amplitude=settings.audio_amplitude,\n"
                "    word_seconds=settings.word_seconds,\n"
                "    pause_seconds=settings.pause_seconds,\n"
                ")\n"
                "transcriber = SidecarTranscriber()\n\n"
                "tutorial_audio = settings.resolved_demo_audio_dir / 'tutorial_student_question.wav'\n"
                "tutorial_text = 'Can you teach me the rollback threshold and duration for API incidents?'\n"
                "duration = synth.synthesize(tutorial_text, tutorial_audio)\n"
                "tutorial_audio.with_suffix('.txt').write_text(tutorial_text, encoding='utf-8')\n\n"
                "{'audio_path': tutorial_audio.as_posix(), 'duration_seconds': round(duration, 3)}"
            ),
            nbf.v4.new_markdown_cell(
                "## Step 7 - Verify Transcription\n"
                "Transcriber reads the sidecar transcript associated with the WAV input."
            ),
            nbf.v4.new_code_cell(
                "transcript_result = transcriber.transcribe(tutorial_audio)\n"
                "transcript_result"
            ),
            nbf.v4.new_markdown_cell(
                "## Step 8 - Build and Run One Full Session Manually\n"
                "Here we instantiate agents + orchestrator directly to make the flow explicit."
            ),
            nbf.v4.new_code_cell(
                "tutor = TutorAgent(settings=settings, gateway=gateway)\n"
                "quiz = QuizAgent(settings=settings, gateway=gateway)\n"
                "tracer = JsonlTelemetryTracer(settings.traces_file)\n"
                "session = VoiceStudySession(\n"
                "    tutor=tutor,\n"
                "    quiz=quiz,\n"
                "    transcriber=transcriber,\n"
                "    synthesizer=synth,\n"
                "    docs=docs,\n"
                "    top_k=settings.retrieval_top_k,\n"
                "    audio_output_dir=settings.resolved_audio_dir,\n"
                "    tracer=tracer,\n"
                ")\n\n"
                "single_run = await session.run(trace_id='tutorial-single-audio', question_audio_path=tutorial_audio)\n"
                "{\n"
                "    'question_text': single_run.question_text,\n"
                "    'top_retrieved': single_run.retrieved[:2],\n"
                "    'tutor_audio_seconds': single_run.tutor_audio_seconds,\n"
                "    'quiz_audio_seconds': single_run.quiz_audio_seconds,\n"
                "    'tutor_fallback_used': single_run.tutor_fallback_used,\n"
                "    'quiz_fallback_used': single_run.quiz_fallback_used,\n"
                "}"
            ),
            nbf.v4.new_markdown_cell(
                "## Step 9 - Inspect Generated Audio Files\n"
                "Confirm that tutor/quiz audio artifacts were produced by this session."
            ),
            nbf.v4.new_code_cell(
                "audio_files = sorted(settings.resolved_audio_dir.glob('tutorial-single-audio*.wav'))\n"
                "[{'file': p.name, 'size_kb': round(p.stat().st_size / 1024, 2)} for p in audio_files]"
            ),
            nbf.v4.new_markdown_cell(
                "## Step 10 - Run Batch Demo Sessions (Pipeline Helper)\n"
                "This executes the project's predefined demo sessions and stores them."
            ),
            nbf.v4.new_code_cell(
                "demo_runs = await run_demo(settings)\n"
                "{\n"
                "    'demo_count': len(demo_runs),\n"
                "    'demo_runs_file': settings.demo_runs_file.as_posix(),\n"
                "    'first_demo_trace_id': demo_runs[0]['trace_id'],\n"
                "}"
            ),
            nbf.v4.new_markdown_cell(
                "## Step 11 - Run Evaluation\n"
                "Compare baseline vs tutor answer quality across the task set."
            ),
            nbf.v4.new_code_cell(
                "eval_payload = await run_evaluation(settings, reset_traces=False)\n"
                "eval_payload['summary']"
            ),
            nbf.v4.new_markdown_cell(
                "## Step 12 - Inspect Prediction Rows\n"
                "Read a few rows from the evaluation CSV artifact."
            ),
            nbf.v4.new_code_cell(
                "rows = []\n"
                "with open(settings.predictions_file, encoding='utf-8') as handle:\n"
                "    reader = csv.DictReader(handle)\n"
                "    for idx, row in enumerate(reader):\n"
                "        rows.append(row)\n"
                "        if idx >= 2:\n"
                "            break\n"
                "rows"
            ),
            nbf.v4.new_markdown_cell(
                "## Step 13 - Telemetry Summary\n"
                "Aggregate trace spans and examine latency by stage."
            ),
            nbf.v4.new_code_cell(
                "telemetry = summarize_traces(settings.traces_file, settings.telemetry_summary_file)\n"
                "{\n"
                "    'n_spans': telemetry['n_spans'],\n"
                "    'n_unique_traces': telemetry['n_unique_traces'],\n"
                "    'first_3_spans': telemetry['by_span'][:3],\n"
                "}"
            ),
            nbf.v4.new_markdown_cell(
                "## Step 14 - Report Preview\n"
                "Load the generated markdown report and preview the first section."
            ),
            nbf.v4.new_code_cell(
                "report_text = Path(settings.report_file).read_text(encoding='utf-8')\n"
                "print(report_text[:1800])"
            ),
            nbf.v4.new_markdown_cell(
                "## Tutorial Complete\n"
                "You now have an end-to-end, executable walkthrough with real outputs saved to disk."
            ),
        ],
    )


if __name__ == "__main__":
    main()
