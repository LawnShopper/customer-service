"""
Rule-based triage fallback used when OPENAI_API_KEY is not set.

This lets you test the full pipeline locally without calling the API.
Once you add your API key, the OpenAI-powered triage in triage.py takes over.
"""

from agent.config import load_business_config
from agent.models import IncomingMessage, TriageResult


def _text(message: IncomingMessage) -> str:
    return f"{message.subject} {message.body} {message.from_email}".lower()


def _no_response_config() -> dict:
    return load_business_config().get("no_response", {})


def _is_automated_sender(message: IncomingMessage) -> bool:
    config = _no_response_config()
    email = message.from_email.lower()
    name = message.from_name.lower()

    for domain in config.get("sender_domains", []):
        if domain.lower() in email:
            return True

    for keyword in config.get("sender_keywords", []):
        if keyword.lower() in email or keyword.lower() in name:
            return True

    return False


def _is_payment_notification(text: str) -> bool:
    """Payment received alerts — not customer billing questions."""
    notification_phrases = [
        "you received a payment",
        "payment was successful",
        "payment has been processed",
        "invoice was paid",
        "payment of $",
        "payment received",
        "successfully charged",
    ]
    customer_question_phrases = [
        "charged twice",
        "wrong charge",
        "billing question",
        "why was i charged",
        "refund",
        "dispute",
        "can someone look",
        "what's going on",
    ]

    if any(phrase in text for phrase in customer_question_phrases):
        return False

    return any(phrase in text for phrase in notification_phrases)


def _looks_like_customer_request(text: str) -> bool:
    """True if the message reads like a person asking for help."""
    request_phrases = [
        "can you",
        "could you",
        "please",
        "question",
        "quote",
        "schedule",
        "mowing",
        "lawn",
        "help",
        "looking for",
        "interested in",
    ]
    return "?" in text or any(phrase in text for phrase in request_phrases)


def _is_no_response_message(message: IncomingMessage) -> tuple[bool, str]:
    """Return (True, category) if this message should not get a reply."""
    text = _text(message)
    config = _no_response_config()

    if _is_complaint(text) and not _is_automated_sender(message):
        return False, ""

    if _is_automated_sender(message):
        if _is_payment_notification(text):
            return True, "System notification"

        automated_phrases = [
            "notification",
            "alert",
            "webhook",
            "deploy",
            "build failed",
            "run succeeded",
            "verification",
            "confirm your email",
            "receipt for",
            "subscription",
            "new login",
            "security alert",
        ]
        if any(phrase in text for phrase in automated_phrases):
            return True, "System notification"

        if "?" not in message.body and not _looks_like_customer_request(text):
            return True, "System notification"

    for phrase in config.get("body_phrases", []):
        if phrase.lower() in text:
            if "unsubscribe" in phrase or "grow your" in phrase:
                return True, "Spam / solicitation"
            return True, "System notification"

    if "thanks" in text and "?" not in message.body and len(message.body.split()) < 30:
        return True, "Thank-you / no action"

    return False, ""


def _is_complaint(text: str) -> bool:
    config = _no_response_config()
    return any(phrase.lower() in text for phrase in config.get("complaint_phrases", []))


def triage_with_rules(message: IncomingMessage) -> TriageResult:
    """Classify a message using keyword and sender rules."""
    text = _text(message)
    sender = message.from_name or message.from_email or "Unknown sender"

    skip, category = _is_no_response_message(message)
    if skip:
        return TriageResult(
            message_id=message.id,
            sender=sender,
            classification="Does Not Need Response",
            category=category,
            urgency="Low",
            summary=_summarize_no_response(message, category),
            reasoning=_no_response_reasoning(message, category),
            missing_info=[],
            draft_reply="",
            recommended_human_action="No response needed. Log only.",
        )

    category, urgency = _categorize(text, message)
    missing = _missing_info(text, category)

    return TriageResult(
        message_id=message.id,
        sender=sender,
        classification="Needs Response",
        category=category,
        urgency=urgency,
        summary=_summarize_needs_response(message, category),
        reasoning=f"Customer message requires a human-reviewed reply ({category}, {urgency} urgency).",
        missing_info=missing,
        draft_reply=_draft_reply(message, category, missing),
        recommended_human_action="Review and send reply.",
    )


def _categorize(text: str, message: IncomingMessage) -> tuple[str, str]:
    # Complaints first — reputation-sensitive, always high
    if _is_complaint(text):
        return "Service issue / complaint", "High"

    if any(w in text for w in ["missed", "didn't show", "nobody showed", "second time"]):
        return "Service issue / complaint", "High"
    if any(w in text for w in ["damage", "broken", "ruined"]):
        return "Service issue / complaint", "High"

    # Customer-initiated billing issues only (not payment notifications)
    if any(
        w in text
        for w in [
            "charged twice",
            "wrong charge",
            "billing question",
            "why was i charged",
            "refund",
            "dispute",
        ]
    ):
        return "Billing / payment", "High"

    if any(w in text for w in ["cancel", "stop service", "threaten"]):
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

    # Generic billing word alone — only high if from a real person, not automated
    if any(w in text for w in ["billing", "payment", "invoice"]):
        if _is_automated_sender(message):
            return "System notification", "Low"
        return "Billing / payment", "Medium"

    return "Existing customer question", "Medium"


def _no_response_reasoning(message: IncomingMessage, category: str) -> str:
    if category == "Thank-you / no action":
        return "Simple thank-you with no ask — no reply needed."
    if category == "Spam / solicitation":
        return "Unsolicited or marketing message — no reply needed."
    if _is_automated_sender(message):
        return "Automated sender or system notification — log only, no reply needed."
    return "System or automated message requiring no reply."


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
    if _is_payment_notification(_text(message)):
        return "Automated payment received notification."
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
