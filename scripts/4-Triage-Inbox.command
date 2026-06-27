#!/bin/bash
# Double-click to triage unread inbox messages.
cd "$(dirname "$0")/.."

if [ ! -d "venv" ]; then
    echo "Run '1-Setup.command' first."
    read -p "Press Enter to close..."
    exit 1
fi

source venv/bin/activate
python -m agent.gmail inbox

echo ""
read -p "Press Enter to close..."
