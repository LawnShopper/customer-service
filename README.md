# Customer Service Agent

An AI-powered customer service agent you can customize for your business. It answers FAQs, shares business hours and policies, and escalates complex issues to your team.

## Features

- **Configurable knowledge base** — Edit `config/business.yaml` with your business name, hours, products, policies, and FAQs
- **AI agent with tools** — Uses OpenAI to understand questions and look up the right information
- **Human escalation** — Creates support tickets when customers need a real person
- **Chat widget UI** — Clean, responsive interface ready to embed or deploy

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- An [OpenAI API key](https://platform.openai.com/api-keys)

### 1. Configure your business

Edit `config/business.yaml` with your business details:

```yaml
business:
  name: "Acme Coffee Co."
  description: "Specialty coffee roasters since 2010."
  email: "hello@acmecoffee.com"
  # ...
```

### 2. Set up environment

```bash
cp .env.example .env
# Add your OpenAI API key to .env
```

### 3. Start the backend

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 4. Start the frontend

In a new terminal:

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) to chat with your agent.

### Docker

```bash
cp .env.example .env
# Add your OpenAI API key
docker compose up
```

## How It Works

```
Customer → Chat UI → FastAPI → OpenAI Agent → Tools (FAQs, hours, policies, tickets)
```

The agent has access to these tools:

| Tool | Purpose |
|------|---------|
| `search_faqs` | Find answers in your FAQ list |
| `get_business_hours` | Return operating hours |
| `get_products` | List products/services and pricing |
| `get_policies` | Shipping, returns, refunds, warranty |
| `get_contact_info` | Email, phone, website |
| `create_support_ticket` | Escalate to a human agent |

## Customization

### Add more FAQs

```yaml
faqs:
  - question: "Do you offer gift cards?"
    answer: "Yes! Gift cards are available in $25, $50, and $100 denominations."
```

### Change the agent's tone

```yaml
agent:
  tone: "warm, casual, and enthusiastic"
  greeting: "Hey there! Welcome to {business_name}. What can I help you with?"
```

### Use a different model

Set `OPENAI_MODEL` in `.env` (e.g. `gpt-4o` for higher quality).

## API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/business` | GET | Business name and greeting |
| `/api/chat` | POST | Send a message and get a reply |

### Chat request example

```json
{
  "message": "What are your return policies?",
  "conversation_id": "optional-uuid",
  "history": [
    { "role": "user", "content": "Hi" },
    { "role": "assistant", "content": "Hello! How can I help?" }
  ]
}
```

## Next Steps

- **Embed the widget** on your website by building the frontend and serving it from your domain
- **Persist tickets** by connecting `create_support_ticket` to your helpdesk (Zendesk, Freshdesk, email)
- **Add order lookup** by integrating with your e-commerce platform's API
- **Deploy** to Railway, Render, Fly.io, or any cloud provider

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── agent.py      # AI agent logic
│   │   ├── tools.py      # Tool definitions and handlers
│   │   ├── main.py       # FastAPI routes
│   │   └── config.py     # Settings and business config loader
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── ChatWidget.jsx
│       └── App.jsx
├── config/
│   └── business.yaml     # Your business knowledge base
└── docker-compose.yml
```

## License

MIT
