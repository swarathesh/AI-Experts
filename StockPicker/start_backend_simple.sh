#!/bin/bash

# Quick Start - Backend Only (Minimal Version)
# This starts a simplified backend with mock data to test the connection

echo "🚀 Starting StockPicker Backend (Minimal Version)"
echo "================================================"

cd /workspaces/AI-Experts/StockPicker

# Create logs directory
mkdir -p logs

echo ""
echo "📦 Installing minimal dependencies..."
python3 -m pip install --break-system-packages fastapi uvicorn pydantic loguru python-dotenv -q 2>&1 | grep -E "(Successfully|already)" || echo "Done"

echo ""
echo "🔧 Starting API server..."
echo "   Backend: http://localhost:8000"
echo "   Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop"
echo "================================================"
echo ""

python3 -m uvicorn api.simple_main:app --reload --host 0.0.0.0 --port 8000
