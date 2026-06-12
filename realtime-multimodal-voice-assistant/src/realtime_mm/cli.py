"""CLI entrypoint for running the real-time multimodal demo."""

from __future__ import annotations

import argparse
import asyncio

from loguru import logger

from realtime_mm.config import PipelineSettings
from realtime_mm.demo_inputs import get_demo_utterances
from realtime_mm.pipeline import RealTimePipeline


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rtma-demo",
        description="Run a simulated real-time multimodal voice assistant pipeline.",
    )
    parser.add_argument("--requests", type=int, default=8, help="Number of simulated requests.")
    parser.add_argument(
        "--profile",
        type=str,
        choices=["normal", "stress"],
        default="normal",
        help="Latency profile: normal for healthy system, stress for overload behavior.",
    )
    parser.add_argument("--seed", type=int, default=7, help="Random seed for deterministic simulation.")
    parser.add_argument(
        "--show-responses",
        action="store_true",
        help="Print transcript + reply text for each request.",
    )
    return parser


async def _run_demo(args: argparse.Namespace) -> None:
    settings = PipelineSettings(
        request_count=args.requests,
        profile=args.profile,
        random_seed=args.seed,
    )
    pipeline = RealTimePipeline(settings=settings)

    logger.remove()
    logger.add(
        sink=lambda msg: print(msg, end=""),
        format="{time:HH:mm:ss} | {level} | {message}",
    )

    print("\n=== Configured Latency Budget ===")
    print(pipeline.report.render_budget_table(settings))

    utterances = get_demo_utterances(args.requests)
    print("\n=== Running Streaming Pipeline ===")
    results = await pipeline.run(utterances)

    if args.show_responses:
        print("\n=== Per-Request Content ===")
        for result in results:
            print(f"{result.request_id} transcript: {result.transcript}")
            print(f"{result.request_id} reply     : {result.reply_text}")
            print("-")

    print("\n=== Runtime Summary ===")
    print(pipeline.report.render_runtime_summary())



def main() -> None:
    """CLI main function.

    Example:
        uv run rtma-demo --requests 10 --profile stress --show-responses
    """
    parser = _build_parser()
    args = parser.parse_args()
    asyncio.run(_run_demo(args))


if __name__ == "__main__":
    main()
