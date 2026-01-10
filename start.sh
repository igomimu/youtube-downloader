#!/bin/bash

# Function to kill all background jobs on exit
cleanup() {
    echo "Stopping servers..."
    kill $(jobs -p) 2>/dev/null
}
trap cleanup EXIT

# Ensure backend venv exists
if [ ! -d "backend/.venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv backend/.venv
    backend/.venv/bin/pip install -r backend/requirements.txt
fi

echo "Starting Backend (FastAPI)..."
cd backend
.venv/bin/uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!
cd ..

echo "Starting Frontend (Vite)..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo "Servers running. Press Ctrl+C to stop."
wait
