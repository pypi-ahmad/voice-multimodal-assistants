"""Execute all tutorial notebooks to save real outputs."""

from __future__ import annotations

from pathlib import Path

import nbformat
from nbclient import NotebookClient

NOTEBOOKS = [
    "01_setup_and_backend_check.ipynb",
    "02_voice_io_tutorial.ipynb",
    "03_single_session_walkthrough.ipynb",
    "04_evaluation.ipynb",
    "05_telemetry_and_report.ipynb",
    "06_full_tutorial_voice_ai_study_coach.ipynb",
]


def execute(path: Path) -> None:
    nb = nbformat.read(path, as_version=4)
    client = NotebookClient(nb, timeout=1800, kernel_name="python3")
    client.execute()
    nbformat.write(nb, path)


def main() -> None:
    base = Path("notebooks")
    for item in NOTEBOOKS:
        execute(base / item)


if __name__ == "__main__":
    main()
