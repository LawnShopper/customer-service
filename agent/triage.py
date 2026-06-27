"""
Core triage logic.

This module sends each incoming message to OpenAI with Lawn Shopper's
classification rules and tone guidance, then returns structured results.
"""

import json
from datetime import datetime, timezone

from openai import OpenAI
from pydantic import ValidationError

from agent.config import get_settings, load_business_config
from agent.heuristics import triage_with_rules
from agent.models import CATEGORIES, IncomingMessage, TriageResult
from agent.tone_examples import load_tone_examples


def build_system_prompt() -> str:
    """Build the instructions the model follows for every message."""
    config = load_business_config()
    business = config.get("business", {})
    tone = config.get("tone", {})
    safety = config.get("safety_rules", [])

    good_examples = "\n".join(f'- "{line}"' for line in tone.get("good_examples", []))
    scanned_examples = load_tone_examples()
    if scanned_examples:
        scanned_block = "\n".join(f'- "{line}"' for line in scanned_examples[:8])
        good_examples = (
            f"{good_examples}\n\nReal sent-email examples from your outbox:\n{scanned_block}"
            if good_examples
            else f"Real sent-email examples from your outbox:\n{scanned_block}"
        )
    avoid = "\n".join(f"- {line}" for line in tone.get("avoid", []))
    safety_rules = "\n".join(f"- {rule}" for rule in safety)

    return f"""You are an internal message triage assistant for {business.get("name", "Lawn Shopper")}.

{business.get("description", "")}

Your job is to review incoming customer messages and prepare them for human review.
You do NOT send replies. You only classify, summarize, and draft suggested replies.

## Classification

Assign exactly one classification:
- "Needs Response" — customer asked a question, made a request, reported an issue, followed up, or sent anything ambiguous that may need human judgment.
- "Does Not Need Response" — simple thank-you with no ask, auto-reply, bounce, spam, duplicate, payment notification, system alert, or FYI with no action needed.

When uncertain, default to "Needs Response".

### Needs Response examples
Direct questions, quote requests, scheduling, service issues, service changes, billing, photos for a job, project inquiries, complaints, clarifications, follow-ups, start/stop/pause requests, crew timing, damage/missed service/quality issues, recommendations.

### Does Not Need Response examples
Simple thank-you with no ask, auto-replies, bounces, spam, notifications requiring no action, duplicates already handled, completed payment notifications, system alerts to log only, FYI messages clearly needing no reply.

**Important distinctions:**
- "You received a $175 payment" from HubSpot/Stripe = Does Not Need Response (log the payment, no reply)
- "I was charged twice" from a customer = Needs Response, High urgency
- GitHub/Cursor/Zapier/Resend deployment or webhook alerts = Does Not Need Response
- Customer says "dissatisfied", "disappointed", "poor quality" = Needs Response, High urgency (complaint)

## Categories (pick exactly one)
{json.dumps(CATEGORIES)}

## Urgency
- High: angry or dissatisfied customer, complaints about quality, missed service, damage claim, customer billing dispute or question, same-day scheduling, cancellation threat, storm-related urgent request, reputation-sensitive items.
- Medium: quote requests, scheduling questions, service changes, follow-ups, photos for active jobs, general customer questions.
- Low: general questions, future project ideas, thank-you messages, non-urgent seasonal requests.

**Do NOT assign High urgency to automated payment-received notifications or system alerts. Those should be Does Not Need Response with Low urgency.**

## Draft Reply Rules (only when classification is "Needs Response")
- Be concise, warm but not chatty.
- Sound like a practical local business owner/operator.
- Acknowledge the request clearly and state the next step.
- Ask for missing information if needed.
- Do not promise exact timing unless provided.
- Do not quote prices unless given.
- Do not apologize excessively unless there is a real issue.
- Leave draft_reply empty when classification is "Does Not Need Response".

## Tone
Style: {tone.get("style", "practical, friendly, direct")}
Good examples:
{good_examples}

Avoid:
{avoid}

## Safety Rules
{safety_rules}

Return valid JSON only with these fields:
- sender (customer name or email if known)
- classification ("Needs Response" or "Does Not Need Response")
- category (one from the list above)
- urgency ("High", "Medium", or "Low")
- summary (one sentence)
- reasoning (why you classified it this way)
- missing_info (array of strings; empty if none)
- draft_reply (string; empty if no response needed)
- recommended_human_action (what a human should do next)
"""


def format_message_for_model(message: IncomingMessage) -> str:
    """Turn a message record into plain text for the model."""
    parts = [
        f"Channel: {message.channel}",
        f"From: {message.from_name} <{message.from_email}>",
        f"Subject: {message.subject}",
        f"Received: {message.received_at}",
    ]

    if message.thread_context:
        parts.append(f"Prior thread context:\n{message.thread_context}")

    parts.append(f"Message body:\n{message.body}")
    return "\n".join(parts)


def triage_message(message: IncomingMessage) -> TriageResult:
    """
    Classify one message and draft a reply if needed.

    Falls back to rules if the API key is missing or the API call fails.
    """
    settings = get_settings()
    sender_label = message.from_name or message.from_email or "Unknown sender"

    if not settings.openai_api_key:
        return triage_with_rules(message)

    try:
        client = OpenAI(api_key=settings.openai_api_key)
        response = client.chat.completions.create(
            model=settings.openai_model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": build_system_prompt()},
                {
                    "role": "user",
                    "content": format_message_for_model(message),
                },
            ],
            temperature=0.2,
        )
    except Exception as exc:
        print(f"  OpenAI error for {message.id}, using rules: {exc}", flush=True)
        return triage_with_rules(message)

    raw = response.choices[0].message.content or "{}"

    try:
        payload = json.loads(raw)
        return TriageResult(
            message_id=message.id,
            sender=payload.get("sender", sender_label),
            classification=payload.get("classification", "Needs Response"),
            category=payload.get("category", "Other / unclear"),
            urgency=payload.get("urgency", "Medium"),
            summary=payload.get("summary", ""),
            reasoning=payload.get("reasoning", ""),
            missing_info=payload.get("missing_info", []),
            draft_reply=payload.get("draft_reply", ""),
            recommended_human_action=payload.get(
                "recommended_human_action", "Review and send reply."
            ),
        )
    except (json.JSONDecodeError, ValidationError):
        return TriageResult(
            message_id=message.id,
            sender=sender_label,
            classification="Needs Response",
            category="Other / unclear",
            urgency="Medium",
            summary="Model returned an invalid response.",
            reasoning="Could not parse model output — flagged for human review.",
            missing_info=[],
            draft_reply="",
            recommended_human_action="Review the original message manually.",
        )


def triage_messages(messages: list[IncomingMessage]) -> list[TriageResult]:
    """Process a list of messages in order, with progress output."""
    results = []
    total = len(messages)
    for index, message in enumerate(messages, start=1):
        subject = (message.subject or message.body or "")[:60]
        print(f"  [{index}/{total}] {subject}...", flush=True)
        results.append(triage_message(message))
    return results


def count_needs_response(results: list[TriageResult]) -> int:
    return sum(1 for result in results if result.classification == "Needs Response")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
