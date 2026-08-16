#!/usr/bin/env bash
# Fashion-2 AI Stylist & Recommendation Engine Launcher
# Starts FastAPI backend (port 8000) and React frontend (port 5173)

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "=========================================================="
echo " Starting Fashion-2 AI Stylist & Recommendation Engine"
echo "=========================================================="

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Ensure output directories exist
mkdir -p crops data clothes

# Start FastAPI backend in the background
echo "[1/2] Launching FastAPI backend on http://localhost:8000..."
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Trap SIGINT/SIGTERM to kill backend when frontend exits
cleanup() {
    echo ""
    echo "Stopping Fashion-2 backend (PID: $BACKEND_PID)..."
    kill $BACKEND_PID 2>/dev/null
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# Give backend a moment to start
sleep 2

# Start Vite frontend
echo "[2/2] Launching React frontend on http://localhost:5173..."
cd "$DIR/frontend"
npm run dev

# Wait for backend
wait $BACKEND_PID
