"""
Gmail API client (read-only).

Handles OAuth authentication, inbox fetching, and sent-mail scanning.
Uses gmail.readonly scope — cannot send, delete, or modify messages.
"""

import base64
import re
from email.utils import parseaddr
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from agent.config import get_settings, resolve_path
from agent.models import IncomingMessage

# Read-only access only — safety requirement from project brief.
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


class GmailError(Exception):
    """Raised when Gmail is not configured or a request fails."""


def get_credentials() -> Credentials:
    """
    Load saved OAuth credentials or run the browser login flow.

    On first run, opens a browser window for Google sign-in and saves
    the token to data/gmail_token.json for future runs.
    """
    settings = get_settings()
    token_path = resolve_path(settings.gmail_token_path)
    credentials_path = resolve_path(settings.gmail_credentials_path)

    if not credentials_path.exists():
        raise GmailError(
            f"Gmail credentials not found at {credentials_path}.\n"
            "Download OAuth client credentials from Google Cloud Console "
            "and save them there. See docs/GMAIL_SETUP.md for steps."
        )

    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(credentials_path), SCOPES
            )
            creds = flow.run_local_server(port=0)

        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(creds.to_json(), encoding="utf-8")

    return creds


def get_gmail_service():
    """Return an authenticated Gmail API service."""
    creds = get_credentials()
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def _header(headers: list[dict], name: str) -> str:
    for header in headers:
        if header.get("name", "").lower() == name.lower():
            return header.get("value", "")
    return ""


def _decode_body_data(data: str) -> str:
    if not data:
        return ""
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded).decode("utf-8", errors="replace")


def _extract_text_from_payload(payload: dict) -> str:
    """Pull plain-text content from a Gmail message payload."""
    mime_type = payload.get("mimeType", "")
    body = payload.get("body", {})
    data = body.get("data")

    if mime_type == "text/plain" and data:
        return _decode_body_data(data).strip()

    parts = payload.get("parts", [])
    for part in parts:
        text = _extract_text_from_payload(part)
        if text:
            return text

    for part in parts:
        if part.get("mimeType") == "text/html":
            html = _decode_body_data(part.get("body", {}).get("data", ""))
            return _html_to_text(html)

    if mime_type == "text/html" and data:
        return _html_to_text(_decode_body_data(data))

    return ""


def _html_to_text(html: str) -> str:
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.I | re.S)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</p>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _clean_reply_body(body: str) -> str:
    """Remove quoted reply chains and signatures when possible."""
    lines = body.splitlines()
    cleaned = []
    for line in lines:
        if line.strip().startswith(">"):
            break
        if re.match(r"^On .+ wrote:$", line.strip()):
            break
        if line.strip() == "--":
            break
        cleaned.append(line)
    return "\n".join(cleaned).strip()


def _parse_sender(from_header: str) -> tuple[str, str]:
    name, email = parseaddr(from_header)
    return name, email


def _get_thread_context(service, thread_id: str, current_message_id: str) -> str:
    """Fetch prior messages in the thread for context."""
    if not thread_id:
        return ""

    try:
        thread = (
            service.users()
            .threads()
            .get(userId="me", id=thread_id, format="metadata")
            .execute()
        )
    except Exception:
        return ""

    snippets = []
    for message in thread.get("messages", []):
        if message.get("id") == current_message_id:
            continue
        headers = message.get("payload", {}).get("headers", [])
        sender = _header(headers, "From")
        snippet = message.get("snippet", "")
        if snippet:
            snippets.append(f"{sender}: {snippet}")

    return "\n".join(snippets[-3:])


def _gmail_message_to_incoming(service, message: dict) -> Optional[IncomingMessage]:
    """Convert a Gmail API message into our IncomingMessage model."""
    message_id = message.get("id", "")
    thread_id = message.get("threadId", "")
    payload = message.get("payload", {})
    headers = payload.get("headers", [])

    from_header = _header(headers, "From")
    from_name, from_email = _parse_sender(from_header)
    subject = _header(headers, "Subject")
    received_at = _header(headers, "Date")

    body = _clean_reply_body(_extract_text_from_payload(payload))
    if not body:
        body = message.get("snippet", "")

    # Skip messages with no meaningful content.
    if not body and not subject:
        return None

    thread_context = _get_thread_context(service, thread_id, message_id)

    return IncomingMessage(
        id=f"gmail-{message_id}",
        channel="email",
        from_name=from_name,
        from_email=from_email,
        subject=subject,
        body=body,
        received_at=received_at,
        thread_context=thread_context,
    )


def _gmail_date(date_str: str) -> str:
    """Convert YYYY-MM-DD to Gmail search format (YYYY/MM/DD)."""
    from datetime import datetime

    try:
        parsed = datetime.strptime(date_str.strip(), "%Y-%m-%d")
    except ValueError as exc:
        raise GmailError(
            f"Invalid date '{date_str}'. Use YYYY-MM-DD (example: 2024-06-01)."
        ) from exc
    return f"{parsed.year}/{parsed.month}/{parsed.day}"


def _build_sent_query(
    after_date: Optional[str] = None,
    before_date: Optional[str] = None,
    newer_than_days: Optional[int] = None,
) -> str:
    """Build a Gmail search query for sent mail with optional date filters."""
    query_parts = ["in:sent"]

    if after_date:
        query_parts.append(f"after:{_gmail_date(after_date)}")
    if before_date:
        query_parts.append(f"before:{_gmail_date(before_date)}")
    if newer_than_days and not after_date:
        query_parts.append(f"newer_than:{newer_than_days}d")

    return " ".join(query_parts)


def list_messages(
    query: str,
    max_results: int = 20,
) -> list[dict]:
    """List Gmail message metadata matching a search query."""
    service = get_gmail_service()
    response = (
        service.users()
        .messages()
        .list(userId="me", q=query, maxResults=max_results)
        .execute()
    )
    return response.get("messages", [])


def fetch_inbox_messages(
    max_results: int = 20,
    unread_only: bool = True,
    newer_than_days: int = 7,
) -> list[IncomingMessage]:
    """
    Fetch recent inbox messages for triage.

    Defaults to unread messages from the last 7 days in the inbox.
    """
    query_parts = ["in:inbox", f"newer_than:{newer_than_days}d"]
    if unread_only:
        query_parts.append("is:unread")

    query = " ".join(query_parts)
    service = get_gmail_service()
    listed = list_messages(query=query, max_results=max_results)

    messages: list[IncomingMessage] = []
    for item in listed:
        full = (
            service.users()
            .messages()
            .get(userId="me", id=item["id"], format="full")
            .execute()
        )
        incoming = _gmail_message_to_incoming(service, full)
        if incoming:
            messages.append(incoming)

    return messages


def fetch_sent_messages(
    max_results: int = 50,
    after_date: Optional[str] = None,
    before_date: Optional[str] = None,
    newer_than_days: Optional[int] = None,
) -> list[dict]:
    """
    Fetch sent messages from the outbox for tone-example scanning.

    Date filters (optional):
      - after_date: YYYY-MM-DD, emails sent on or after this date
      - before_date: YYYY-MM-DD, emails sent before this date
      - newer_than_days: shorthand for recent mail (e.g. 90 = last 90 days)

    Returns lightweight dicts with subject, body, and sent date.
    """
    service = get_gmail_service()
    query = _build_sent_query(after_date, before_date, newer_than_days)
    listed = list_messages(query=query, max_results=max_results)

    sent_messages = []
    for item in listed:
        full = (
            service.users()
            .messages()
            .get(userId="me", id=item["id"], format="full")
            .execute()
        )
        payload = full.get("payload", {})
        headers = payload.get("headers", [])
        body = _clean_reply_body(_extract_text_from_payload(payload))
        subject = _header(headers, "Subject")
        sent_at = _header(headers, "Date")

        if not body or len(body) < 20:
            continue

        # Skip likely automated or bulk messages.
        lower = f"{subject} {body}".lower()
        if any(
            phrase in lower
            for phrase in [
                "unsubscribe",
                "do not reply",
                "automated message",
                "mail delivery subsystem",
            ]
        ):
            continue

        sent_messages.append(
            {
                "gmail_id": item["id"],
                "subject": subject,
                "body": body,
                "sent_at": sent_at,
            }
        )

    return sent_messages


def get_account_email() -> str:
    """Return the authenticated Gmail address."""
    service = get_gmail_service()
    profile = service.users().getProfile(userId="me").execute()
    return profile.get("emailAddress", "")
