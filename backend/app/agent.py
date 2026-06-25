import json
import uuid

from openai import OpenAI

from app.config import get_settings, load_business_config
from app.models import ChatMessage, ChatResponse
from app.tools import TOOL_DEFINITIONS, TOOL_HANDLERS, get_ticket


def build_system_prompt() -> str:
    config = load_business_config()
    business = config.get("business", {})
    agent = config.get("agent", {})

    return f"""You are a customer service agent for {business.get("name", "the business")}.

Business description: {business.get("description", "")}

Your tone should be {agent.get("tone", "friendly and professional")}.

Guidelines:
- Answer questions accurately using the available tools.
- If you don't know something, say so honestly and offer to escalate.
- For complex issues, billing disputes, or when a customer asks for a human, use create_support_ticket.
- Keep responses concise and helpful.
- Never make up information about products, policies, or order status.
- If a customer provides an order number you cannot look up, offer to create a support ticket.
"""


def run_tool(name: str, arguments: str) -> tuple[str, str | None]:
    handler = TOOL_HANDLERS.get(name)
    if not handler:
        return f"Unknown tool: {name}", None

    args = json.loads(arguments) if arguments else {}
    result = handler(args)

    ticket_id = result if name == "create_support_ticket" else None
    return str(result), ticket_id


def chat(
    message: str,
    history: list[ChatMessage],
    conversation_id: str | None = None,
) -> ChatResponse:
    settings = get_settings()
    config = load_business_config()
    agent_config = config.get("agent", {})
    conversation_id = conversation_id or str(uuid.uuid4())

    if not settings.openai_api_key:
        return ChatResponse(
            reply=(
                "The AI agent is not configured yet. Please set OPENAI_API_KEY in your "
                ".env file to enable intelligent responses."
            ),
            conversation_id=conversation_id,
        )

    client = OpenAI(api_key=settings.openai_api_key)
    messages = [{"role": "system", "content": build_system_prompt()}]
    messages.extend({"role": msg.role, "content": msg.content} for msg in history)
    messages.append({"role": "user", "content": message})

    escalated = False
    ticket_id = None

    for _ in range(5):
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=messages,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto",
        )

        choice = response.choices[0]
        assistant_message = choice.message

        if not assistant_message.tool_calls:
            reply = assistant_message.content or "I'm sorry, I couldn't generate a response."
            if escalated and ticket_id:
                escalation_msg = agent_config.get(
                    "escalation_message",
                    "A team member will follow up with you shortly.",
                )
                reply = f"{reply}\n\n{escalation_msg} (Ticket: {ticket_id})"
            return ChatResponse(
                reply=reply,
                conversation_id=conversation_id,
                escalated=escalated,
                ticket_id=ticket_id,
            )

        messages.append(
            {
                "role": "assistant",
                "content": assistant_message.content,
                "tool_calls": [
                    {
                        "id": tool_call.id,
                        "type": "function",
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments,
                        },
                    }
                    for tool_call in assistant_message.tool_calls
                ],
            }
        )

        for tool_call in assistant_message.tool_calls:
            result, new_ticket_id = run_tool(
                tool_call.function.name,
                tool_call.function.arguments,
            )
            if new_ticket_id:
                escalated = True
                ticket_id = new_ticket_id
                get_ticket(ticket_id)

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                }
            )

    return ChatResponse(
        reply="I'm having trouble processing your request. Please try again or ask for a human agent.",
        conversation_id=conversation_id,
        escalated=escalated,
        ticket_id=ticket_id,
    )
