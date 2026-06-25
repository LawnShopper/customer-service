import uuid
from datetime import datetime, timezone

from app.config import load_business_config

_tickets: dict[str, dict] = {}


def search_faqs(query: str) -> str:
    config = load_business_config()
    faqs = config.get("faqs", [])
    query_lower = query.lower()

    matches = [
        faq
        for faq in faqs
        if query_lower in faq["question"].lower()
        or query_lower in faq["answer"].lower()
    ]

    if not matches:
        return "No matching FAQs found. Offer to help directly or escalate to a human agent."

    return "\n\n".join(
        f"Q: {faq['question']}\nA: {faq['answer']}" for faq in matches[:3]
    )


def get_business_hours() -> str:
    config = load_business_config()
    hours = dict(config.get("hours", {}))
    timezone_name = hours.pop("timezone", "UTC")

    lines = [f"{day.title()}: {time}" for day, time in hours.items()]
    return f"Business hours ({timezone_name}):\n" + "\n".join(lines)


def get_products() -> str:
    config = load_business_config()
    products = config.get("products", [])

    if not products:
        return "No product information is configured."

    return "\n\n".join(
        f"- {product['name']} ({product['price']}): {product['description']}"
        for product in products
    )


def get_policies() -> str:
    config = load_business_config()
    policies = config.get("policies", {})

    if not policies:
        return "No policy information is configured."

    return "\n".join(
        f"{name.replace('_', ' ').title()}: {value}"
        for name, value in policies.items()
    )


def get_contact_info() -> str:
    config = load_business_config()
    business = config.get("business", {})

    return (
        f"Business: {business.get('name', 'N/A')}\n"
        f"Email: {business.get('email', 'N/A')}\n"
        f"Phone: {business.get('phone', 'N/A')}\n"
        f"Website: {business.get('website', 'N/A')}"
    )


def create_support_ticket(customer_message: str, customer_email: str = "") -> str:
    ticket_id = f"TKT-{uuid.uuid4().hex[:8].upper()}"
    _tickets[ticket_id] = {
        "id": ticket_id,
        "message": customer_message,
        "email": customer_email,
        "status": "open",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    return ticket_id


def get_ticket(ticket_id: str) -> dict | None:
    return _tickets.get(ticket_id)


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "search_faqs",
            "description": "Search frequently asked questions for answers to common customer inquiries.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Keywords or topic to search for in FAQs.",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_business_hours",
            "description": "Get the business operating hours.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_products",
            "description": "List products or services offered by the business.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_policies",
            "description": "Get business policies such as shipping, returns, refunds, and warranty.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_contact_info",
            "description": "Get business contact information including email, phone, and website.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_support_ticket",
            "description": "Create a support ticket to escalate the conversation to a human agent.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_message": {
                        "type": "string",
                        "description": "Summary of the customer's issue or request.",
                    },
                    "customer_email": {
                        "type": "string",
                        "description": "Customer email address if provided.",
                    },
                },
                "required": ["customer_message"],
            },
        },
    },
]

TOOL_HANDLERS = {
    "search_faqs": lambda args: search_faqs(args["query"]),
    "get_business_hours": lambda args: get_business_hours(),
    "get_products": lambda args: get_products(),
    "get_policies": lambda args: get_policies(),
    "get_contact_info": lambda args: get_contact_info(),
    "create_support_ticket": lambda args: create_support_ticket(
        args["customer_message"], args.get("customer_email", "")
    ),
}
