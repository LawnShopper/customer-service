"""
Rule-based triage fallback used when OPENAI_API_KEY is not set.

This lets you test the full pipeline locally without calling the API.
Once you add your API key, the OpenAI-powered triage in triage.py takes over.
"""

from agent.models import IncomingMessage, TriageResult


def _text(message: IncomingMessage) -> str:
    return f"{message.subject} {message.body} {message.from_email}".lower()


def triage_with_rules(message: IncomingMessage) -> TriageResult:
    """Classify a message using simple keyword rules."""
    text = _text(message)
    sender = message.from_name or message.from_email or "Unknown sender"

    # Does Not Need Response patterns
    if any(
        phrase in text
        for phrase in [
            "out of office",
            "auto-reply",
            "delivery status notification",
            "mailer-daemon",
            "wasn't delivered",
            "grow your lawn care",
            "book a free demo",
            "seo package",
        ]
    ):
        category = (
            "Spam / solicitation"
            if "seo" in text or "demo" in text or "grow your" in text
            else "System notification"
        )
        if "mailer-daemon" in text or "wasn't delivered" in text:
            category = "System notification"
        return TriageResult(
            message_id=message.id,
            sender=sender,
            classification="Does Not Need Response",
            category=category,
            urgency="Low",
            summary=_summarize_no_response(message, category),
            reasoning="Matches a no-response pattern (auto-reply, bounce, spam, or system alert).",
            missing_info=[],
            draft_reply="",
            recommended_human_action="No response needed. Log only.",
        )

    if "thanks" in text and "?" not in message.body and len(message.body.split()) < 30:
        return TriageResult(
            message_id=message.id,
            sender=sender,
            classification="Does Not Need Response",
            category="Thank-you / no action",
            urgency="Low",
            summary="Customer sent a brief thank-you with no question or request.",
            reasoning="Simple thank-you with no ask — no reply needed.",
            missing_info=[],
            draft_reply="",
            recommended_human_action="No response needed. Log only.",
        )

    # Needs Response — determine category and urgency
    category, urgency = _categorize(text)
    missing = _missing_info(text, category)

    return TriageResult(
        message_id=message.id,
        sender=sender,
        classification="Needs Response",
        category=category,
        urgency=urgency,
        summary=_summarize_needs_response(message, category),
        reasoning=f"Customer message matches '{category}' and requires a human-reviewed reply.",
        missing_info=missing,
        draft_reply=_draft_reply(message, category, missing),
        recommended_human_action="Review and send reply.",
    )


def _categorize(text: str) -> tuple[str, str]:
    if any(w in text for w in ["charged twice", "billing", "payment", "invoice"]):
        return "Billing / payment", "High"
    if any(w in text for w in ["missed", "didn't show", "nobody showed", "second time"]):
        return "Service issue / complaint", "High"
    if any(w in text for w in ["damage", "broken", "ruined"]):
        return "Service issue / complaint", "High"
    if any(w in text for w in ["cancel", "stop service", "unhappy"]):
        return "Cancellation / pause", "High"
    if any(w in text for w in ["what time", "when will", "coming tomorrow", "arrival"]):
        return "Scheduling", "High"
    if any(w in text for w in ["pause", "hold", "pick back up"]):
        return "Cancellation / pause", "Medium"
    if any(w in text for w in ["quote", "how much", "pricing", "estimate"]):
        return "Quote request", "Medium"
    if any(w in text for w in ["photo", "attached", "pictures"]):
        return "Photos received", "Medium"
    if any(w in text for w in ["mowing this week", "schedule", "rain", "still happening"]):
        return "Scheduling", "Medium"
    if any(w in text for w in ["just moved", "new to", "do you service", "looking for"]):
        return "New customer inquiry", "Medium"
    if any(w in text for w in ["mulch", "cleanup", "fall", "spring", "seasonal"]):
        return "Seasonal service", "Low"
    return "Existing customer question", "Medium"


def _missing_info(text: str, category: str) -> list[str]:
    missing = []
    if category in {"Quote request", "New customer inquiry"} and "address" not in text:
        missing.append("property address")
    if category == "Quote request" and "photo" not in text:
        missing.append("photos of the work area")
    return missing


def _summarize_needs_response(message: IncomingMessage, category: str) -> str:
    preview = message.body.strip().replace("\n", " ")[:100]
    return f"{category}: {preview}{'...' if len(message.body) > 100 else ''}"


def _summarize_no_response(message: IncomingMessage, category: str) -> str:
    if category == "Thank-you / no action":
        return "Customer said thanks with no follow-up question."
    if category == "Spam / solicitation":
        return "Unsolicited marketing email."
    return "System or automated message requiring no reply."


def _draft_reply(message: IncomingMessage, category: str, missing: list[str]) -> str:
    name = message.from_name.split()[0] if message.from_name else "there"

    if category == "Scheduling":
        return (
            f"Hi {name} — thanks for checking in. We're watching the weather and crew "
            "schedule now. If anything shifts, we'll let you know. Otherwise we're still "
            "planning to get the service completed this week."
        )
    if category == "Service issue / complaint":
        return (
            f"Hi {name} — thanks for flagging this. I'm going to look into what happened "
            "and follow up as soon as I have an update."
        )
    if category == "Quote request":
        extra = ""
        if missing:
            extra = f" Please send over your {' and '.join(missing)}."
        return (
            f"Hi {name} — thanks for reaching out.{extra} We'll take a look and let you "
            "know the best next step."
        )
    if category == "Billing / payment":
        return (
            f"Hi {name} — thanks for letting us know. I'm going to pull up your account "
            "and check on the charges. I'll follow up shortly."
        )
    if category == "Cancellation / pause":
        return (
            f"Hi {name} — got it. I'll get this updated on our end and confirm once "
            "everything is set."
        )
    if category == "New customer inquiry":
        return (
            f"Hi {name} — thanks for reaching out. Yes, we service your area. Send over "
            "your address and let us know what you're looking for, and we'll go from there."
        )
    if category == "Photos received":
        return (
            f"Hi {name} — thanks for sending these over. We'll take a look and follow up "
            "with next steps."
        )
    return (
        f"Hi {name} — thanks for the message. I'll check on this and follow up as soon "
        "as I have an update."
    )
