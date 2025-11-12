#!/bin/bash
# Linux/Mac shell script to setup and run the ChatGPT Retrieval Plugin
# Run: chmod +x setup_and_run.sh && ./setup_and_run.sh

set -e  # Exit on error

echo "============================================================"
echo "  ChatGPT Retrieval Plugin - Setup & Launch"
echo "============================================================"
echo ""

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed"
    echo ""
    echo "Please install Python 3.10 or 3.11:"
    echo "  macOS: brew install python@3.11"
    echo "  Ubuntu/Debian: sudo apt install python3.11"
    echo "  Other: https://www.python.org/downloads/"
    exit 1
fi

echo "✓ Python found: $(python3 --version)"
echo ""

# Run the Python setup script
python3 setup_and_run.py
