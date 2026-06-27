"""
Gmail CLI commands.

Usage:
    python -m agent.gmail auth              # Connect your Gmail account
    python -m agent.gmail inbox             # Triage unread inbox messages
    python -m agent.gmail scan-outbox         # Pull sent-mail tone examples
"""

import argparse
import sys
from typing import List, Optional

from agent.gmail_client import (
    GmailError,
    fetch_inbox_messages,
    fetch_sent_messages,
    get_account_email,
    get_credentials,
)
from agent.config import get_settings, resolve_path
from agent.output_writer import save_results
from agent.tone_examples import save_tone_examples
from agent.triage import triage_messages


def cmd_auth() -> int:
    """Run OAuth flow and save token."""
    try:
        get_credentials()
        email = get_account_email()
        print(f"Gmail connected successfully: {email}")
        print("Token saved. You can now run inbox triage and outbox scanning.")
        return 0
    except GmailError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def cmd_inbox(args: argparse.Namespace) -> int:
    """Fetch inbox messages and run triage."""
    try:
        email = get_account_email()
        print(f"Connected as {email}")
        print(
            f"Fetching inbox messages "
            f"(unread_only={args.unread_only}, max={args.max}, "
            f"newer_than={args.days}d)..."
        )

        messages = fetch_inbox_messages(
            max_results=args.max,
            unread_only=args.unread_only,
            newer_than_days=args.days,
        )

        if not messages:
            print("No messages found matching your filters.")
            print("Tip: your inbox may have no unread mail. Try:")
            print("  python3 -m agent.gmail inbox --all")
            return 0

        print(f"Found {len(messages)} message(s). Running triage...\n")

        output_path = resolve_path(args.output)
        print(f"Results will be saved to: {output_path}\n", flush=True)

        if not get_settings().openai_api_key:
            print(
                "Note: Using rule-based classification (no OPENAI_API_KEY set).\n"
                "Add your API key to .env for smarter triage.\n"
            )

        results = triage_messages(messages)
        paths = save_results(results, args.output)

        from datetime import datetime

        csv_mtime = datetime.fromtimestamp(paths["csv"].stat().st_mtime)
        print(f"\nCSV file updated on disk at: {csv_mtime}", flush=True)

        needs_response = sum(1 for r in results if r.classification == "Needs Response")
        print(f"Processed {len(results)} message(s) — {needs_response} need a response\n")

        for result in results:
            print(f"[{result.urgency}] {result.classification} — {result.category}")
            print(f"  From: {result.sender}")
            print(f"  Summary: {result.summary}")
            if result.draft_reply:
                preview = result.draft_reply.replace("\n", " ")
                print(f"  Draft: {preview[:120]}{'...' if len(preview) > 120 else ''}")
            print()

        print("Output saved to:")
        print(f"  CSV:  {paths['csv']}")
        print(f"  JSON: {paths['json']}")
        if paths.get("stamped_csv"):
            print(f"  New copy: {paths['stamped_csv']}")
        return 0

    except GmailError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"\nRun failed before saving results: {exc}", file=sys.stderr)
        print("Scroll up for the full error message.", file=sys.stderr)
        return 1


def cmd_scan_outbox(args: argparse.Namespace) -> int:
    """Scan sent mail and save tone examples."""
    try:
        email = get_account_email()
        print(f"Connected as {email}")
        print(f"Scanning sent mail (max={args.max})...")
        if args.after or args.before or args.days:
            print(
                f"Date filter: after={args.after or 'any'}, "
                f"before={args.before or 'any'}, days={args.days or 'n/a'}"
            )

        sent = fetch_sent_messages(
            max_results=args.max,
            after_date=args.after,
            before_date=args.before,
            newer_than_days=args.days,
        )
        if not sent:
            print("No suitable sent messages found.")
            return 0

        payload = save_tone_examples(sent, path=args.output, account_email=email)
        print(f"Saved {payload['example_count']} tone example(s) to {args.output}")
        print("\nSample snippets:")
        for example in sent[:3]:
            preview = example["body"][:120].replace("\n", " ")
            print(f"  - {preview}{'...' if len(example['body']) > 120 else ''}")

        print(
            "\nThese examples will be used automatically the next time you run triage."
        )
        return 0

    except GmailError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def main(argv: Optional[List[str]] = None) -> int:
    from agent.config import get_settings

    settings = get_settings()

    parser = argparse.ArgumentParser(description="Lawn Shopper Gmail integration")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("auth", help="Connect Gmail via OAuth (run this first)")

    inbox_parser = subparsers.add_parser("inbox", help="Triage inbox messages")
    inbox_parser.add_argument(
        "--max", type=int, default=20, help="Max messages to fetch (default: 20)"
    )
    inbox_parser.add_argument(
        "--days", type=int, default=7, help="Only messages newer than N days (default: 7)"
    )
    inbox_parser.add_argument(
        "--all",
        action="store_true",
        help="Include read messages, not just unread",
    )
    inbox_parser.add_argument(
        "--output",
        default=settings.output_dir,
        help="Output directory for triage results",
    )

    outbox_parser = subparsers.add_parser(
        "scan-outbox", help="Scan sent mail for tone examples"
    )
    outbox_parser.add_argument(
        "--max", type=int, default=50, help="Max sent messages to scan (default: 50)"
    )
    outbox_parser.add_argument(
        "--after",
        help="Only sent mail on or after this date (YYYY-MM-DD, e.g. 2024-01-01)",
    )
    outbox_parser.add_argument(
        "--before",
        help="Only sent mail before this date (YYYY-MM-DD, e.g. 2025-01-01)",
    )
    outbox_parser.add_argument(
        "--days",
        type=int,
        help="Only sent mail from the last N days (alternative to --after)",
    )
    outbox_parser.add_argument(
        "--output",
        default=settings.tone_examples_path,
        help="Path to save tone examples JSON",
    )

    args = parser.parse_args(argv)

    if args.command == "auth":
        return cmd_auth()
    if args.command == "inbox":
        args.unread_only = not args.all
        return cmd_inbox(args)
    if args.command == "scan-outbox":
        return cmd_scan_outbox(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
