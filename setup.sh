#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Setting up onshape-featurescript-tools..."

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

echo "Activating virtual environment..."
source .venv/bin/activate

echo "Installing package and dependencies..."
pip install -e . --quiet

echo ""
echo "Setup complete."
echo ""
echo "To activate the environment:"
echo "  source .venv/bin/activate"
echo ""

# Check for API config
if [ ! -f "$HOME/.onshape_client_config.yaml" ]; then
    echo "NOTE: Onshape API credentials not found."
    echo "  Copy the example config and add your API keys:"
    echo "    cp onshape_client_config.example.yaml ~/.onshape_client_config.yaml"
    echo "    chmod 600 ~/.onshape_client_config.yaml"
    echo ""
    echo "  Get API keys at: https://cad.onshape.com (My Account > Developer)"
else
    echo "Onshape API credentials found at ~/.onshape_client_config.yaml"
fi
