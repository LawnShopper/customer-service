from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agent import chat
from app.config import get_settings, load_business_config
from app.models import BusinessInfoResponse, ChatRequest, ChatResponse

app = FastAPI(title="Customer Service Agent", version="1.0.0")

settings = get_settings()
origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/business", response_model=BusinessInfoResponse)
def get_business_info() -> BusinessInfoResponse:
    config = load_business_config()
    business = config.get("business", {})
    agent = config.get("agent", {})
    greeting_template = agent.get(
        "greeting",
        "Hi! I'm the customer service assistant for {business_name}. How can I help you today?",
    )

    return BusinessInfoResponse(
        name=business.get("name", "Your Business"),
        greeting=greeting_template.format(business_name=business.get("name", "Your Business")),
        description=business.get("description", ""),
    )


@app.post("/api/chat", response_model=ChatResponse)
def post_chat(request: ChatRequest) -> ChatResponse:
    return chat(
        message=request.message,
        history=request.history,
        conversation_id=request.conversation_id,
    )
