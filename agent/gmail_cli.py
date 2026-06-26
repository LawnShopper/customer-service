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
            return 0

        print(f"Found {len(messages)} message(s). Running triage...\n")
        results = triage_messages(messages)
        paths = save_results(results, args.output)

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
        print(f"  JSON: {paths['json']}")
        print(f"  CSV:  {paths['csv']}")
        return 0

    except GmailError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def cmd_scan_outbox(args: argparse.Namespace) -> int:
    """Scan sent mail and save tone examples."""
    try:
        email = get_account_email()
        print(f"Connected as {email}")
        print(f"Scanning sent mail (max={args.max})...")

        sent = fetch_sent_messages(max_results=args.max)
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
