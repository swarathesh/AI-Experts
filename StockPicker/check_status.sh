#!/bin/bash

# Status Check Script
# Checks if backend and frontend are running

echo "🔍 StockPicker Status Check"
echo "============================"
echo ""

# Check Backend
echo "Backend (Port 8000):"
if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
    echo "  ✅ RUNNING"
    curl -s http://localhost:8000/api/health | python3 -m json.tool 2>/dev/null || echo "  (API is up but not returning JSON)"
else
    echo "  ❌ NOT RUNNING"
    echo "  Start with: ./start_backend_simple.sh"
fi

echo ""

# Check Frontend  
echo "Frontend (Port 3001):"
if curl -s http://localhost:3001 > /dev/null 2>&1; then
    echo "  ✅ RUNNING"
    echo "  URL: http://localhost:3001"
else
    echo "  ❌ NOT RUNNING"
    echo "  Start with: cd dashboard && npm run dev"
fi

echo ""

# Check if ports are in use
echo "Port Usage:"
lsof -i :8000 2>/dev/null | grep LISTEN && echo "  Port 8000: ✅ In Use" || echo "  Port 8000: ❌ Free"
lsof -i :3001 2>/dev/null | grep LISTEN && echo "  Port 3001: ✅ In Use" || echo "  Port 3001: ❌ Free"

echo ""
echo "============================"
