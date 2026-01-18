#!/bin/bash

echo "🔍 StockPicker Diagnostic Tool"
echo "=============================="
echo ""

# 1. Check if backend is responding
echo "1️⃣  Checking Backend (Port 8000)..."
if curl -s --max-time 3 http://localhost:8000/api/health > /dev/null 2>&1; then
    echo "   ✅ Backend is RUNNING and responding"
    echo "   Response:"
    curl -s http://localhost:8000/api/health | python3 -m json.tool 2>/dev/null || echo "   (API up but response not JSON)"
else
    echo "   ❌ Backend is NOT responding"
    echo ""
    echo "   Possible issues:"
    echo "   • Backend crashed during startup"
    echo "   • Missing Python dependencies"
    echo "   • Port 8000 is blocked"
    echo ""
    echo "   To fix: Run this command in a NEW terminal:"
    echo "   cd /workspaces/AI-Experts/StockPicker && chmod +x emergency_start.sh && ./emergency_start.sh"
fi

echo ""

# 2. Check if frontend is running
echo "2️⃣  Checking Frontend (Port 3001)..."
if curl -s --max-time 3 http://localhost:3001 > /dev/null 2>&1; then
    echo "   ✅ Frontend is RUNNING"
else
    echo "   ❌ Frontend is NOT running"
    echo "   To start: cd /workspaces/AI-Experts/StockPicker/dashboard && npm run dev"
fi

echo ""

# 3. Check what's using the ports
echo "3️⃣  Port Usage:"
PORT_8000=$(lsof -ti:8000 2>/dev/null)
PORT_3001=$(lsof -ti:3001 2>/dev/null)

if [ -n "$PORT_8000" ]; then
    echo "   Port 8000: ✅ In use by PID $PORT_8000"
    ps -p $PORT_8000 -o comm= 2>/dev/null | head -1 | xargs echo "   Process:"
else
    echo "   Port 8000: ❌ NOT in use (backend not running)"
fi

if [ -n "$PORT_3001" ]; then
    echo "   Port 3001: ✅ In use by PID $PORT_3001"
else
    echo "   Port 3001: ❌ NOT in use (frontend not running)"
fi

echo ""

# 4. Check Python dependencies
echo "4️⃣  Checking Python Dependencies..."
python3 -c "import fastapi; print('   ✅ fastapi installed')" 2>/dev/null || echo "   ❌ fastapi NOT installed"
python3 -c "import uvicorn; print('   ✅ uvicorn installed')" 2>/dev/null || echo "   ❌ uvicorn NOT installed"
python3 -c "import pydantic; print('   ✅ pydantic installed')" 2>/dev/null || echo "   ❌ pydantic NOT installed"

echo ""

# 5. Test API endpoints
echo "5️⃣  Testing API Endpoints..."
if curl -s --max-time 3 http://localhost:8000/api/health > /dev/null 2>&1; then
    echo "   Testing /api/stocks..."
    if curl -s --max-time 5 http://localhost:8000/api/stocks > /dev/null 2>&1; then
        STOCK_COUNT=$(curl -s http://localhost:8000/api/stocks | python3 -c "import sys, json; data=json.load(sys.stdin); print(len(data.get('stocks', [])))" 2>/dev/null)
        echo "   ✅ /api/stocks working (${STOCK_COUNT:-0} stocks)"
    else
        echo "   ❌ /api/stocks failed"
    fi
    
    echo "   Testing /api/hot-stocks..."
    if curl -s --max-time 5 http://localhost:8000/api/hot-stocks > /dev/null 2>&1; then
        echo "   ✅ /api/hot-stocks working"
    else
        echo "   ❌ /api/hot-stocks failed"
    fi
else
    echo "   ⏭️  Skipped (backend not running)"
fi

echo ""
echo "=============================="
echo "📊 Summary:"
echo ""

# Final verdict
BACKEND_OK=$(curl -s --max-time 3 http://localhost:8000/api/health > /dev/null 2>&1 && echo "yes" || echo "no")
FRONTEND_OK=$(curl -s --max-time 3 http://localhost:3001 > /dev/null 2>&1 && echo "yes" || echo "no")

if [ "$BACKEND_OK" = "yes" ] && [ "$FRONTEND_OK" = "yes" ]; then
    echo "✅ Both services are running!"
    echo "   Open http://localhost:3001 in your browser"
    echo "   Check browser console (F12) for any frontend errors"
elif [ "$BACKEND_OK" = "no" ] && [ "$FRONTEND_OK" = "yes" ]; then
    echo "⚠️  Frontend is running but Backend is NOT"
    echo "   This is why you see 'API Disconnected'"
    echo ""
    echo "   🔧 Fix: Run in a NEW terminal:"
    echo "   cd /workspaces/AI-Experts/StockPicker"
    echo "   chmod +x emergency_start.sh"
    echo "   ./emergency_start.sh"
elif [ "$BACKEND_OK" = "yes" ] && [ "$FRONTEND_OK" = "no" ]; then
    echo "⚠️  Backend is running but Frontend is NOT"
    echo "   Start frontend with: cd dashboard && npm run dev"
else
    echo "❌ Neither service is running"
    echo "   Start backend: ./emergency_start.sh"
    echo "   Start frontend: cd dashboard && npm run dev"
fi

echo ""
echo "=============================="
