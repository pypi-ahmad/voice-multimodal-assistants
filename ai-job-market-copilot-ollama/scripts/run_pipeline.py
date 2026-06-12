"""Convenience runner for notebook users.

Usage:
    uv run python scripts/run_pipeline.py
"""

from __future__ import annotations

import asyncio

from job_market_copilot.config import get_settings
from job_market_copilot.logging_utils import configure_logging
from job_market_copilot.pipeline import run_all


def main() -> None:
    configure_logging()
    settings = get_settings()
    asyncio.run(run_all(settings))


if __name__ == "__main__":
    main()
