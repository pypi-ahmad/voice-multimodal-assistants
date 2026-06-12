"""Quiz-generation agent."""

from __future__ import annotations

from voice_study_coach.config import Settings
from voice_study_coach.ollama_client import AsyncOllamaGateway
from voice_study_coach.schemas import ChatResult, RetrievedDoc


class QuizAgent:
    """Generate one short quiz question from tutor context."""

    def __init__(self, settings: Settings, gateway: AsyncOllamaGateway) -> None:
        self._settings = settings
        self._gateway = gateway

    async def generate_quiz(self, question: str, tutor_answer: str, retrieved: list[RetrievedDoc]) -> ChatResult:
        """Create one short recall question."""
        context = self._context(retrieved)
        prompt = (
            f"Original question: {question}\n"
            f"Tutor explanation: {tutor_answer}\n"
            f"Context: {context}\n\n"
            "Generate one short quiz question that checks retention of the key fact."
        )

        try:
            result = await self._gateway.chat(
                model=self._settings.quiz_model,
                messages=[
                    {"role": "system", "content": "You create concise quiz prompts."},
                    {"role": "user", "content": prompt},
                ],
                temperature=self._settings.generation_temperature,
                max_tokens=min(self._settings.generation_max_tokens, 80),
                timeout_seconds=min(self._settings.generation_timeout_seconds, 2.0),
            )
            if result.text.strip():
                return result
        except Exception:
            pass

        return ChatResult(
            text=self._fallback(retrieved),
            done_reason="quiz_fallback",
            fallback_used=True,
        )

    @staticmethod
    def _context(retrieved: list[RetrievedDoc]) -> str:
        if not retrieved:
            return "(none)"
        return " | ".join(f"{item.doc.source}: {item.doc.text}" for item in retrieved[:2])

    @staticmethod
    def _fallback(retrieved: list[RetrievedDoc]) -> str:
        if not retrieved:
            return "What is one key concept from the previous explanation?"
        return f"From {retrieved[0].doc.source}, what is the most important threshold or value to remember?"
