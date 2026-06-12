"""Tutor agent for explanation generation."""

from __future__ import annotations

from voice_study_coach.config import Settings
from voice_study_coach.ollama_client import AsyncOllamaGateway
from voice_study_coach.schemas import ChatResult, RetrievedDoc


class TutorAgent:
    """Generate concise tutor explanations with fallback."""

    def __init__(self, settings: Settings, gateway: AsyncOllamaGateway) -> None:
        self._settings = settings
        self._gateway = gateway

    async def baseline_answer(self, question: str) -> ChatResult:
        """Baseline answer without retrieval context."""
        try:
            result = await self._gateway.chat(
                model=self._settings.tutor_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a tutor with no notes. If unsure, say you don't know.",
                    },
                    {"role": "user", "content": question},
                ],
                temperature=self._settings.generation_temperature,
                max_tokens=min(self._settings.generation_max_tokens, 100),
                timeout_seconds=min(self._settings.generation_timeout_seconds, 2.0),
            )
            if result.text.strip():
                return result
        except Exception:
            pass

        return ChatResult(
            text="I do not know from the question alone.",
            done_reason="baseline_fallback",
            fallback_used=True,
        )

    async def explain(self, question: str, retrieved: list[RetrievedDoc]) -> ChatResult:
        """Generate tutoring response from retrieved context."""
        context = self._build_context(retrieved)
        user_prompt = (
            f"Student question: {question}\n\n"
            f"Study notes:\n{context}\n\n"
            "Give a concise explanation in 3-5 bullets and cite source filenames."
        )

        try:
            result = await self._gateway.chat(
                model=self._settings.tutor_model,
                messages=[
                    {"role": "system", "content": "You are a clear study coach."},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=self._settings.generation_temperature,
                max_tokens=self._settings.generation_max_tokens,
                timeout_seconds=self._settings.generation_timeout_seconds,
            )
            if result.text.strip():
                return result
        except Exception:
            pass

        return ChatResult(
            text=self._fallback(question=question, retrieved=retrieved),
            done_reason="tutor_fallback",
            fallback_used=True,
        )

    @staticmethod
    def _build_context(retrieved: list[RetrievedDoc]) -> str:
        if not retrieved:
            return "(no context retrieved)"
        lines: list[str] = []
        for idx, hit in enumerate(retrieved, start=1):
            lines.append(f"[{idx}] source={hit.doc.source} text={hit.doc.text}")
        return "\n".join(lines)

    @staticmethod
    def _fallback(question: str, retrieved: list[RetrievedDoc]) -> str:
        if not retrieved:
            return (
                f"I could not retrieve study notes for '{question}'. "
                "Please provide more specific course context."
            )
        top = retrieved[0].doc
        return (
            f"From {top.source}: {top.text}\n"
            "This fallback summary was produced because live model generation timed out."
        )
