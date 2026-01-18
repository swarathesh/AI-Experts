#!/bin/bash
# Emergency Backend Starter - Absolutely Minimal
# Run this if nothing else works

echo "🚀 Starting Emergency Backend..."

cd /workspaces/AI-Experts/StockPicker || exit 1

# Install ONLY what we absolutely need
python3 -m pip install --break-system-packages --quiet fastapi uvicorn pydantic 2>&1 | grep -i "error" || true

# Create logs directory
mkdir -p logs

# Start the simple backend
echo ""
echo "✅ Starting API on http://localhost:8000"
echo "   Press Ctrl+C to stop"
echo ""

python3 -m uvicorn api.simple_main:app --host 0.0.0.0 --port 8000
