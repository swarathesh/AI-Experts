#!/bin/bash
# StockPicker Dashboard Setup Script

echo "🚀 StockPicker Dashboard Setup"
echo "=============================="

# Install backend dependencies
echo ""
echo "📦 Installing Python dependencies..."
pip install fastapi uvicorn --quiet

# Install frontend dependencies
echo ""
echo "📦 Installing Node.js dependencies..."
cd dashboard
npm install

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start the application:"
echo ""
echo "  Terminal 1 (API Backend):"
echo "    cd /workspaces/AI-Experts/StockPicker"
echo "    python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "  Terminal 2 (Frontend):"
echo "    cd /workspaces/AI-Experts/StockPicker/dashboard"
echo "    npm run dev"
echo ""
echo "Then open: http://localhost:3001"
