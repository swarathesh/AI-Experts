#!/bin/bash

# StockPicker - Start Both Services
# This script starts the backend API and frontend dashboard

echo "🚀 Starting StockPicker Services"
echo "=================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}❌ Error: Please run this script from the StockPicker directory${NC}"
    exit 1
fi

# Create logs directory if it doesn't exist
mkdir -p logs

echo ""
echo -e "${YELLOW}📦 Installing Python dependencies...${NC}"
python3 -m pip install --break-system-packages fastapi uvicorn yfinance pandas numpy python-dotenv loguru pydantic 2>&1 | grep -E "(Successfully|Requirement already|error|ERROR)" || true

echo ""
echo -e "${YELLOW}📦 Installing Node.js dependencies...${NC}"
cd dashboard
npm install 2>&1 | grep -E "(added|up to date|error|ERROR)" || true
cd ..

echo ""
echo -e "${GREEN}✅ Dependencies installed${NC}"
echo ""
echo "=================================="
echo -e "${GREEN}Starting Services:${NC}"
echo ""
echo -e "  ${YELLOW}Backend API:${NC} http://localhost:8000"
echo -e "  ${YELLOW}API Docs:${NC}    http://localhost:8000/docs"
echo -e "  ${YELLOW}Frontend:${NC}    http://localhost:3001"
echo ""
echo "=================================="
echo ""
echo -e "${YELLOW}ℹ️  Logs will be saved to:${NC}"
echo "  - Backend: logs/api.log"
echo "  - Terminal output below"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
echo ""
echo "=================================="

# Trap Ctrl+C to kill both processes
trap 'echo ""; echo "🛑 Stopping services..."; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit' INT TERM

# Start backend in background
echo ""
echo -e "${GREEN}🔧 Starting Backend API...${NC}"
python3 -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

# Wait a bit for backend to start
sleep 3

# Start frontend in background
echo ""
echo -e "${GREEN}🎨 Starting Frontend Dashboard...${NC}"
cd dashboard
npm run dev &
FRONTEND_PID=$!
cd ..
echo "Frontend PID: $FRONTEND_PID"

echo ""
echo "=================================="
echo -e "${GREEN}✅ Both services started!${NC}"
echo "=================================="
echo ""

# Wait for both processes
wait
