from typing import Literal

from pydantic import BaseModel, Field


Classification = Literal["Needs Response", "Does Not Need Response"]
Urgency = Literal["High", "Medium", "Low"]

CATEGORIES = [
    "New customer inquiry",
    "Existing customer question",
    "Quote request",
    "Scheduling",
    "Service change",
    "Service issue / complaint",
    "Billing / payment",
    "Photos received",
    "Crew coordination",
    "Seasonal service",
    "Cancellation / pause",
    "Thank-you / no action",
    "Spam / solicitation",
    "System notification",
    "Other / unclear",
]


class IncomingMessage(BaseModel):
    """A single incoming customer message from the sample file."""

    id: str
    channel: Literal["email", "sms"] = "email"
    from_name: str = ""
    from_email: str = ""
    subject: str = ""
    body: str
    received_at: str = ""
    thread_context: str = ""


class TriageResult(BaseModel):
    """Structured output for one triaged message."""

    message_id: str
    sender: str
    classification: Classification
    category: str
    urgency: Urgency
    summary: str
    reasoning: str
    missing_info: list[str] = Field(default_factory=list)
    draft_reply: str = ""
    recommended_human_action: str


class TriageBatch(BaseModel):
    """Full output for a triage run."""

    processed_at: str
    message_count: int
    needs_response_count: int
    results: list[TriageResult]
