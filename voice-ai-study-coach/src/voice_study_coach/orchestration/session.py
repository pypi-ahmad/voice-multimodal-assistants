"""Voice coaching session orchestrator."""

from __future__ import annotations

from pathlib import Path
from time import perf_counter
from typing import Literal

from voice_study_coach.agents.quiz import QuizAgent
from voice_study_coach.agents.tutor import TutorAgent
from voice_study_coach.audio.synthesizer import ProceduralVoiceSynthesizer
from voice_study_coach.audio.transcriber import SidecarTranscriber
from voice_study_coach.schemas import KnowledgeDoc, SessionResult
from voice_study_coach.telemetry.tracer import JsonlTelemetryTracer
from voice_study_coach.tools.knowledge_base import retrieve


class VoiceStudySession:
    """Run one voice or text study-coach interaction."""

    def __init__(
        self,
        tutor: TutorAgent,
        quiz: QuizAgent,
        transcriber: SidecarTranscriber,
        synthesizer: ProceduralVoiceSynthesizer,
        docs: list[KnowledgeDoc],
        top_k: int,
        audio_output_dir: Path,
        tracer: JsonlTelemetryTracer,
    ) -> None:
        self._tutor = tutor
        self._quiz = quiz
        self._transcriber = transcriber
        self._synthesizer = synthesizer
        self._docs = docs
        self._top_k = top_k
        self._audio_output_dir = audio_output_dir
        self._tracer = tracer

    async def run(
        self,
        trace_id: str,
        *,
        question_text: str | None = None,
        question_audio_path: Path | None = None,
    ) -> SessionResult:
        """Execute one study session and return structured outputs."""
        start = perf_counter()

        if question_audio_path is not None:
            with self._tracer.span(trace_id, "transcribe_audio"):
                transcript = self._transcriber.transcribe(question_audio_path)
                question = transcript.transcript
            input_mode: Literal["audio", "text"] = "audio"
        else:
            question = question_text or ""
            input_mode = "text"

        with self._tracer.span(trace_id, "retrieve_context", {"top_k": self._top_k}):
            hits = retrieve(query=question, docs=self._docs, top_k=self._top_k)

        with self._tracer.span(trace_id, "baseline_answer"):
            _ = await self._tutor.baseline_answer(question)

        with self._tracer.span(trace_id, "tutor_answer"):
            tutor_result = await self._tutor.explain(question=question, retrieved=hits)

        with self._tracer.span(trace_id, "quiz_generation"):
            quiz_result = await self._quiz.generate_quiz(
                question=question,
                tutor_answer=tutor_result.text,
                retrieved=hits,
            )

        tutor_audio = self._audio_output_dir / f"{trace_id}_tutor.wav"
        quiz_audio = self._audio_output_dir / f"{trace_id}_quiz.wav"

        with self._tracer.span(trace_id, "synthesize_tutor_audio"):
            tutor_seconds = self._synthesizer.synthesize(tutor_result.text, tutor_audio)

        with self._tracer.span(trace_id, "synthesize_quiz_audio"):
            quiz_seconds = self._synthesizer.synthesize(quiz_result.text, quiz_audio)

        total_ms = (perf_counter() - start) * 1000.0

        return SessionResult(
            trace_id=trace_id,
            input_mode=input_mode,
            question_text=question,
            retrieved=[
                {
                    "source": item.doc.source,
                    "title": item.doc.title,
                    "score": round(item.score, 4),
                    "text": item.doc.text,
                }
                for item in hits
            ],
            tutor_response_text=tutor_result.text,
            quiz_question_text=quiz_result.text,
            tutor_audio_path=tutor_audio.as_posix(),
            quiz_audio_path=quiz_audio.as_posix(),
            tutor_audio_seconds=round(tutor_seconds, 3),
            quiz_audio_seconds=round(quiz_seconds, 3),
            tutor_fallback_used=tutor_result.fallback_used,
            quiz_fallback_used=quiz_result.fallback_used,
            total_latency_ms=round(total_ms, 3),
        )
