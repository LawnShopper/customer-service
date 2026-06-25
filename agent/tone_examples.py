"""
Load and save tone examples scraped from Gmail sent mail.

These examples are injected into the triage prompt so draft replies
match Lawn Shopper's real voice.
"""

import json
from datetime import datetime, timezone

from agent.config import resolve_path

DEFAULT_TONE_PATH = "data/tone_examples.json"


def load_tone_examples(path: str | None = None) -> list[str]:
    """
    Return a list of example reply snippets for the triage prompt.

    Falls back to an empty list if no examples file exists yet.
    """
    file_path = resolve_path(path or DEFAULT_TONE_PATH)
    if not file_path.exists():
        return []

    data = json.loads(file_path.read_text(encoding="utf-8"))
    examples = data.get("examples", [])

    snippets = []
    for example in examples:
        body = example.get("body", "").strip()
        if body:
            # Use first ~300 chars as a tone snippet to keep prompts manageable.
            snippet = body[:300].strip()
            if len(body) > 300:
                snippet += "..."
            snippets.append(snippet)

    return snippets


def save_tone_examples(
    sent_messages: list[dict],
    path: str | None = None,
    account_email: str = "",
) -> dict:
    """
    Save scanned sent messages as tone examples.

    Returns the saved data dict.
    """
    file_path = resolve_path(path or DEFAULT_TONE_PATH)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "synced_at": datetime.now(timezone.utc).isoformat(),
        "account_email": account_email,
        "example_count": len(sent_messages),
        "examples": sent_messages,
    }

    file_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload
