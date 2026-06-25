"""
CLI entry point for the Lawn Shopper triage agent.

Run from the project root:
    python -m agent.main                         # Triage sample messages
    python -m agent.gmail auth                   # Connect Gmail (one-time)
    python -m agent.gmail inbox                  # Triage live inbox
    python -m agent.gmail scan-outbox            # Learn tone from sent mail

Optional flags:
    --input path/to/messages.json
    --output path/to/output/dir
"""

import argparse
import json
import sys
from pathlib import Path

from agent.config import get_settings, resolve_path
from agent.models import IncomingMessage
from agent.output_writer import save_results
from agent.triage import triage_messages


def load_messages(path: Path) -> list[IncomingMessage]:
    """Read sample messages from a JSON file."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return [IncomingMessage(**item) for item in data]


def print_summary(results) -> None:
    """Print a quick human-readable summary to the terminal."""
    needs_response = [r for r in results if r.classification == "Needs Response"]
    no_response = [r for r in results if r.classification == "Does Not Need Response"]

    print(f"\nProcessed {len(results)} message(s)")
    print(f"  Needs Response: {len(needs_response)}")
    print(f"  Does Not Need Response: {len(no_response)}\n")

    for result in results:
        print(f"[{result.urgency}] {result.classification} — {result.category}")
        print(f"  From: {result.sender}")
        print(f"  Summary: {result.summary}")
        if result.draft_reply:
            preview = result.draft_reply.replace("\n", " ")
            print(f"  Draft: {preview[:120]}{'...' if len(preview) > 120 else ''}")
        print()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Lawn Shopper message triage and draft reply agent"
    )
    parser.add_argument(
        "--input",
        help="Path to sample messages JSON (default: data/sample_messages.json)",
    )
    parser.add_argument(
        "--output",
        help="Directory for output files (default: data/output)",
    )
    args = parser.parse_args(argv)

    settings = get_settings()
    input_path = resolve_path(args.input or settings.sample_messages_path)
    output_dir = args.output or settings.output_dir

    if not input_path.exists():
        print(f"Error: input file not found: {input_path}", file=sys.stderr)
        return 1

    messages = load_messages(input_path)
    print(f"Loading {len(messages)} message(s) from {input_path}")

    results = triage_messages(messages)
    paths = save_results(results, output_dir)

    print_summary(results)
    print("Output saved to:")
    print(f"  JSON: {paths['json']}")
    print(f"  CSV:  {paths['csv']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
