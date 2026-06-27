# Gmail Setup

Connect Lawn Shopper's Gmail account for inbox monitoring and outbox tone scanning.

**Read-only access** — the agent can read messages but cannot send, delete, or modify anything.

## 1. Create Google Cloud credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select an existing one)
3. Enable the **Gmail API**:
   - APIs & Services → Library → search "Gmail API" → Enable
4. Configure the OAuth consent screen:
   - APIs & Services → OAuth consent screen
   - Choose **External** (or Internal if using Google Workspace)
   - Add your name and email
   - Add scope: `https://www.googleapis.com/auth/gmail.readonly`
   - Add your Gmail address as a test user (required while app is in testing mode)
5. Create OAuth credentials:
   - APIs & Services → Credentials → Create Credentials → **OAuth client ID**
   - Application type: **Desktop app**
   - Download the JSON file
6. Save the downloaded file as:
   ```
   credentials/google_credentials.json
   ```

## 2. Connect your account

From the project root:

```bash
source venv/bin/activate
pip install -r requirements.txt
python -m agent.gmail auth
```

This opens a browser window. Sign in with the Lawn Shopper Gmail account and approve read-only access.

Your token is saved to `data/gmail_token.json` (gitignored). You only need to auth once unless the token is revoked.

## 3. Triage your inbox

```bash
# Unread messages from the last 7 days (default)
python -m agent.gmail inbox

# Include read messages too
python -m agent.gmail inbox --all

# Fetch more messages or go back further
python -m agent.gmail inbox --max 50 --days 14
```

Results are saved to `data/output/triage_results.json` and `.csv`.

## 4. Scan your outbox for tone examples

After inbox monitoring is working, scan sent mail so draft replies match your real voice:

```bash
python -m agent.gmail scan-outbox
```

This saves examples to `data/tone_examples.json`. The triage agent uses these automatically when drafting replies.

```bash
# Scan more sent messages
python -m agent.gmail scan-outbox --max 100

# Sent mail from a date range
python -m agent.gmail scan-outbox --after 2024-01-01 --before 2025-01-01

# Sent mail from the last 90 days
python -m agent.gmail scan-outbox --days 90
```

## Recommended workflow

```bash
python -m agent.gmail auth           # One-time setup
python -m agent.gmail scan-outbox    # Learn your tone from sent mail
python -m agent.gmail inbox          # Triage new customer messages
```

## Troubleshooting

**"Gmail credentials not found"**
- Make sure `credentials/google_credentials.json` exists (see step 1)

**"Access blocked" or "App not verified"**
- Add your Gmail as a test user on the OAuth consent screen
- While in testing mode, only test users can authenticate

**"Token expired"**
- Delete `data/gmail_token.json` and run `python -m agent.gmail auth` again

**Running on a remote server**
- OAuth requires a browser. Run `auth` on your local machine first, then copy `data/gmail_token.json` to the server.

## Security notes

- `credentials/google_credentials.json` and `data/gmail_token.json` are gitignored
- Only `gmail.readonly` scope is requested — no send or modify permissions
- Tone examples and triage output stay local in `data/`
