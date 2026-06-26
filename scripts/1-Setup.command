#!/bin/bash
# Double-click this file in Finder to set up the agent (first time only).
cd "$(dirname "$0")"

echo "Setting up Lawn Shopper Customer Service Agent..."
echo ""

if ! command -v python3 &>/dev/null; then
    echo "Python 3 is not installed."
    echo "Install it from https://www.python.org/downloads/ then run this again."
    read -p "Press Enter to close..."
    exit 1
fi

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install -r requirements.txt

echo ""
echo "Setup complete!"
echo "Next: double-click 'Connect Gmail.command'"
read -p "Press Enter to close..."
