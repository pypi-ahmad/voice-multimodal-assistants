"""Async Ollama wrapper for tutor/quiz generation."""

from __future__ import annotations

import asyncio
from typing import Any

from ollama import AsyncClient

from voice_study_coach.schemas import ChatResult


class AsyncOllamaGateway:
    """Thin async wrapper around Ollama chat API."""

    def __init__(self, host: str) -> None:
        self._client = AsyncClient(host=host)

    async def list_model_names(self) -> set[str]:
        """List local model names."""
        response = await self._client.list()
        return {model.model for model in response.models if model.model}

    async def ensure_required_models(self, tutor_model: str, quiz_model: str) -> None:
        """Validate required models are installed locally."""
        available = await self.list_model_names()
        missing = [m for m in [tutor_model, quiz_model] if m not in available]
        if missing:
            raise RuntimeError(
                f"Missing required model(s): {', '.join(missing)}. Pull with `ollama pull <model>`"
            )

    async def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
        timeout_seconds: float,
    ) -> ChatResult:
        """Execute one non-streaming chat request."""
        options: dict[str, Any] = {
            "temperature": temperature,
            "num_predict": max_tokens,
        }

        response = await asyncio.wait_for(
            self._client.chat(model=model, messages=messages, options=options),
            timeout=timeout_seconds,
        )

        message = getattr(response, "message", None)
        text = ""
        if message is not None:
            text = (getattr(message, "content", "") or "").strip()

        return ChatResult(
            text=text,
            prompt_tokens=int(getattr(response, "prompt_eval_count", 0) or 0),
            completion_tokens=int(getattr(response, "eval_count", 0) or 0),
            total_duration_ns=int(getattr(response, "total_duration", 0) or 0),
            done_reason=str(getattr(response, "done_reason", "") or ""),
            fallback_used=False,
        )
