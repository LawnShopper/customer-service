# Lawn Shopper Message Triage + Draft Reply Agent

An internal tool that reads incoming customer messages, classifies whether they need a response, and drafts replies in Lawn Shopper's voice — all for human review. Nothing is sent automatically.

## What this does

For each incoming message, the agent:

1. Reads the message (from a local sample file in v1)
2. Identifies the sender, if possible
3. Summarizes what the customer is asking or saying
4. Classifies as **Needs Response** or **Does Not Need Response**
5. Assigns a category and urgency level
6. Drafts a reply when a response is needed
7. Explains its reasoning
8. Saves results to `data/output/triage_results.json` and `.csv`

**First version uses mock/sample data only.** No Gmail or SMS integration yet.

## Folder structure

```
customer-service/
├── agent/                    # Python triage agent
│   ├── main.py               # CLI entry point — run this
│   ├── triage.py             # Classification + draft reply logic
│   ├── models.py             # Input/output data shapes
│   ├── config.py             # Settings and business config loader
│   └── output_writer.py      # Saves JSON and CSV results
├── config/
│   └── lawn_shopper.yaml     # Business context, tone, safety rules
├── data/
│   ├── sample_messages.json  # Mock incoming emails for testing
│   └── output/               # Generated triage results (gitignored)
├── requirements.txt
├── .env.example
└── README.md
```

## Quick start

### 1. Install dependencies

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Set your OpenAI API key

```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

Without an API key, the agent uses built-in rule-based classification so you can test the full pipeline locally. Add your key for AI-powered triage and draft replies.

### 3. Run the agent

```bash
python -m agent.main
```

This reads `data/sample_messages.json`, triages each message, prints a summary, and saves output to `data/output/`.

### Optional flags

```bash
python -m agent.main --input data/sample_messages.json --output data/output
```

## Sample output

Each message produces structured output like this:

```json
{
  "message_id": "msg-001",
  "sender": "Sarah Mitchell",
  "classification": "Needs Response",
  "category": "Scheduling",
  "urgency": "Medium",
  "summary": "Customer is asking whether mowing is still happening this week due to rain.",
  "reasoning": "The customer asked a direct scheduling question and needs a reply.",
  "missing_info": [],
  "draft_reply": "Thanks — we're watching the weather and crew schedule now. If anything shifts, we'll let you know. Otherwise, we're still planning to get the service completed this week.",
  "recommended_human_action": "Review and send reply."
}
```

Full batch results are saved to:

- `data/output/triage_results.json` — complete structured output
- `data/output/triage_results.csv` — easy to scan in a spreadsheet

## Sample messages included

The mock file covers common Lawn Shopper scenarios:

| ID | Scenario |
|----|----------|
| msg-001 | Scheduling question (rain/week) |
| msg-002 | Thank-you with no ask |
| msg-003 | Missed service / complaint |
| msg-004 | New quote request |
| msg-005 | Auto-reply / out of office |
| msg-006 | Pause service request |
| msg-007 | Spam / solicitation |
| msg-008 | Photos received for project |
| msg-009 | Billing / double charge |
| msg-010 | Delivery failure / bounce |
| msg-011 | Crew arrival timing (same-day) |
| msg-012 | New customer inquiry |

## Classification rules

**Needs Response** — questions, quotes, scheduling, issues, changes, billing, photos, complaints, follow-ups, ambiguous messages. When uncertain, defaults to Needs Response.

**Does Not Need Response** — simple thank-yous, auto-replies, bounces, spam, system notifications, FYI messages with no action needed.

See `config/lawn_shopper.yaml` for full business context, tone guidance, and safety rules.

## Lawn Shopper voice

Drafts should sound like a responsive local operator — practical, direct, and helpful. Not corporate, not salesy.

Good: *"Thanks — we can take a look. Please send over your address and a couple photos of the area, and we'll let you know the best next step."*

Avoid: *"Dear valued customer, we sincerely apologize for any inconvenience..."*

## Safety

The agent will **not**:

- Send emails or texts automatically
- Delete or archive messages
- Promise specific dates or quote prices without human approval
- Admit fault or offer refunds autonomously

All replies are drafts for human review.

## Future scope

Planned expansions (not in v1):

- Gmail inbox monitoring and draft creation
- SMS ingestion via Twilio
- Daily digest of messages needing response
- High-priority Slack/email alerts
- Customer lookup from CRM
- Crew status lookup before drafting
- Tone matching from prior sent emails

## How the code works

1. **`agent/main.py`** — loads messages from JSON, calls the triage logic, saves output.
2. **`agent/triage.py`** — sends each message to OpenAI with Lawn Shopper's rules and tone. Returns structured JSON.
3. **`agent/models.py`** — defines the shape of incoming messages and triage results.
4. **`agent/output_writer.py`** — writes results to JSON and CSV files.
5. **`config/lawn_shopper.yaml`** — business context the model uses for classification and tone.

## License

MIT
