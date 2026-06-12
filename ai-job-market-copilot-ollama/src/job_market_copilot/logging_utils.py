"""Logging helpers."""

from __future__ import annotations

import sys

from loguru import logger


def configure_logging() -> None:
    """Configure application logging once per process."""
    logger.remove()
    logger.add(
        sys.stderr,
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <cyan>{name}</cyan> | <level>{message}</level>",
    )
