#!/usr/bin/env bash
set -e

# Unified starter for StockPicker backend + dashboard
# Usage:
#   ./start_all.sh [--api-url URL] [--mode minimal|full]
# Examples:
#   ./start_all.sh --api-url http://localhost:8000
#   ./start_all.sh --api-url https://your-forwarded-8000-url.app.github.dev --mode minimal

API_URL="http://localhost:8000"
MODE="minimal"  # or 'full'

while [[ $# -gt 0 ]]; do
  case "$1" in
    --api-url)
      API_URL="$2"; shift 2 ;;
    --mode)
      MODE="$2"; shift 2 ;;
    *)
      echo "Unknown arg: $1"; exit 1 ;;
  esac
done

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

# Update dashboard env
DASHBOARD_DIR="$ROOT_DIR/dashboard"
mkdir -p "$DASHBOARD_DIR"
# Strip trailing slash from API_URL
API_URL_NOSLASH="${API_URL%/}"
cat > "$DASHBOARD_DIR/.env.local" <<EOF
NEXT_PUBLIC_API_URL=$API_URL_NOSLASH
EOF

echo "[INFO] NEXT_PUBLIC_API_URL set to: $API_URL_NOSLASH"

# Start backend
if [[ "$MODE" == "minimal" ]]; then
  echo "[INFO] Starting minimal backend (mock data) at $API_URL_NOSLASH"
  # Relax CORS handled in simple_main.py
  python3 -m uvicorn api.simple_main:app --reload --host 0.0.0.0 --port 8000 &
else
  echo "[INFO] Starting full backend at $API_URL_NOSLASH"
  # Allow all origins by default; override with ALLOWED_ORIGINS
  ALLOWED_ORIGINS=${ALLOWED_ORIGINS:-*} python3 -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000 &
fi
BACKEND_PID=$!

# Start dashboard (port 3001)
cd "$DASHBOARD_DIR"
if [[ ! -d node_modules ]]; then
  echo "[INFO] Installing dashboard dependencies..."
  npm install --no-audit --no-fund
fi

echo "[INFO] Starting dashboard on port 3001"
# Use nohup to keep running after terminal closes
nohup npm run dev >/dev/null 2>&1 &
DASHBOARD_PID=$!

echo "=============================================="
echo "✅ Started services"
echo "   Backend: $API_URL_NOSLASH (docs at $API_URL_NOSLASH/docs)"
echo "   Dashboard: http://localhost:3001 (or forwarded 3001 URL)"
echo "   PIDs -> backend: $BACKEND_PID, dashboard: $DASHBOARD_PID"
echo "----------------------------------------------"
echo "To stop: kill $BACKEND_PID $DASHBOARD_PID"
echo "=============================================="
