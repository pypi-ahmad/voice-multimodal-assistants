"""Convenience script for full pipeline execution."""

from __future__ import annotations

import asyncio
import json

from voice_study_coach.config import get_settings
from voice_study_coach.logging_utils import configure_logging
from voice_study_coach.pipeline import run_all


async def _main() -> None:
    settings = get_settings()
    configure_logging()
    payload = await run_all(settings)
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    asyncio.run(_main())
