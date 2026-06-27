#!/bin/bash
# Double-click to connect your Gmail account (one-time, or if token expires).
cd "$(dirname "$0")/.."

if [ ! -f "credentials/google_credentials.json" ]; then
    echo "Missing credentials/google_credentials.json"
    echo "Save your Google OAuth JSON file there first."
    read -p "Press Enter to close..."
    exit 1
fi

if [ ! -d "venv" ]; then
    echo "Run '1-Setup.command' first."
    read -p "Press Enter to close..."
    exit 1
fi

source venv/bin/activate
python -m agent.gmail auth

echo ""
read -p "Press Enter to close..."
