"""Demo utterances to simulate incoming voice requests."""

from __future__ import annotations


DEFAULT_UTTERANCES: list[str] = [
    "What's the weather in Mumbai this evening and should I carry an umbrella?",
    "Summarize the top three priorities from my calendar for today.",
    "Draft a polite follow-up message for the client meeting notes.",
    "Give me a quick status from the model training run and validation score trend.",
    "Set a reminder to review production logs in thirty minutes.",
    "What's a concise explanation of retrieval augmented generation?",
    "Help me compare two cloud GPU options for fine-tuning a small model.",
    "Convert this spoken request into an action plan with next steps.",
    "Give me a short definition of concept drift with a practical example.",
    "Generate a checklist for shipping a real-time inference service safely.",
]


def get_demo_utterances(count: int) -> list[str]:
    """Return a deterministic slice/repeat of demo utterances."""
    if count <= len(DEFAULT_UTTERANCES):
        return DEFAULT_UTTERANCES[:count]

    extended: list[str] = []
    while len(extended) < count:
        extended.extend(DEFAULT_UTTERANCES)
    return extended[:count]
