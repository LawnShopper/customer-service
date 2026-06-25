from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None
    history: list[ChatMessage] = Field(default_factory=list)


class ChatResponse(BaseModel):
    reply: str
    conversation_id: str
    escalated: bool = False
    ticket_id: str | None = None


class BusinessInfoResponse(BaseModel):
    name: str
    greeting: str
    description: str
