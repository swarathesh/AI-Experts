# 🚀 Quick Start Guide - StockPicker Dashboard

## The Issue
Your frontend is showing "API Disconnected" because the backend server is not running.

## Solution: Start the Backend

### Option 1: Simple Backend (Mock Data) - **RECOMMENDED FOR TESTING**

This starts a lightweight backend with mock data to test the UI:

```bash
cd /workspaces/AI-Experts/StockPicker
chmod +x start_backend_simple.sh
./start_backend_simple.sh
```

**What you'll see:**
- Mock stock prices and charts
- Simulated trading signals
- Portfolio data
- All UI features working

### Option 2: Full Backend (Real Data)

This requires installing all dependencies and may take longer:

```bash
cd /workspaces/AI-Experts/StockPicker
chmod +x start_services.sh
./start_services.sh
```

## Verify It's Working

### 1. Check Backend is Running
Open http://localhost:8000 in your browser. You should see:
```json
{
  "message": "StockPicker API",
  "version": "1.0.0",
  "status": "running"
}
```

### 2. Check API Documentation
Visit http://localhost:8000/docs to see all available endpoints.

### 3. Check Frontend Connection
- Look at the top-right corner of the dashboard
- Should show "API Connected" (green) instead of "API Disconnected" (red)
- Stock data should start appearing

## Troubleshooting

### Backend Won't Start

**Error: "ModuleNotFoundError"**
```bash
# Install missing dependencies
python3 -m pip install --break-system-packages fastapi uvicorn pydantic loguru
```

**Error: "Port 8000 already in use"**
```bash
# Kill the process using port 8000
sudo lsof -ti:8000 | xargs kill -9
```

### Frontend Shows No Data

1. **Open browser console** (F12)
2. Look for errors in the Console tab
3. Check Network tab for failed API calls
4. Errors will show the exact issue

### Check Logs

Backend logs are saved to: `logs/api.log`

```bash
tail -f logs/api.log
```

## What the Frontend Expects

The frontend makes these API calls:
- `GET /api/health` - Check if backend is alive
- `GET /api/stocks` - Get stock list for dashboard
- `GET /api/hot-stocks` - Get buy/sell signals
- `GET /api/stock/{symbol}` - Get detailed stock data
- `GET /api/portfolio` - Get portfolio information

## Current Setup

Based on your terminals:
- ✅ **Frontend**: Running on http://localhost:3001 (npm terminal)
- ❌ **Backend**: Not running (exited with error)

## Next Steps

1. **In a new terminal**, run:
   ```bash
   cd /workspaces/AI-Experts/StockPicker
   chmod +x start_backend_simple.sh
   ./start_backend_simple.sh
   ```

2. **Wait for this message:**
   ```
   🚀 StockPicker API Started!
   🌐 Listening on: http://0.0.0.0:8000
   ```

3. **Refresh your browser** - The dashboard should now show data!

## Console Logging

The backend now logs everything:
- 📥 Every incoming request
- 📊 What data it's fetching
- ✅ Success messages
- ❌ Error messages with full details
- ⏱️  Request duration

Example output:
```
15:30:45 | INFO | 📊 Fetching stocks (mock data)
15:30:45 | INFO | ✅ Returning 8 stocks
15:30:45 | INFO | 📤 Response: GET /api/stocks - Status: 200 - Duration: 0.003s
```

## Still Having Issues?

Check the browser's JavaScript console for frontend errors:
1. Press F12
2. Go to Console tab
3. Look for red error messages
4. Share those errors for help
