#!/usr/bin/env python3
"""
Docker startup script for PennerBot.
Starts both backend and frontend servers with 0.0.0.0 binding for Docker containers.
"""

import signal
import subprocess
import sys
import time


processes = []


def signal_handler(sig, frame):
    """Handle shutdown signals gracefully."""
    print("\n👋 Shutting down...")
    for p in processes:
        try:
            p.terminate()
            p.wait(timeout=5)
        except:
            p.kill()
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

print("=" * 60)
print("🤖 PennerBot - Docker Edition")
print("=" * 60)
print()

# Start Backend
print("🐍 Starting Backend Server on 0.0.0.0:8000...")
backend = subprocess.Popen(
    [
        "python",
        "-m",
        "uvicorn",
        "server:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8000",
        "--log-level",
        "info",
    ],
    cwd="/app"
)
processes.append(backend)

# Wait for backend to start
print("⏳ Waiting for backend to start...")
time.sleep(5)

# Start Frontend
print("🌐 Starting Frontend Server on 0.0.0.0:1420...")
frontend = subprocess.Popen(
    [
        "python",
        "serve.py",
        "--host",
        "0.0.0.0",
        "--port",
        "1420",
        "--backend-url",
        "http://127.0.0.1:8000",
    ],
    cwd="/app/web"
)
processes.append(frontend)

print()
print("=" * 60)
print("✅ Servers are running!")
print("=" * 60)
print("  Backend:  http://0.0.0.0:8000")
print("  Frontend: http://0.0.0.0:1420")
print("  API Docs: http://0.0.0.0:8000/docs")
print()
print("Access from host:")
print("  Frontend: http://localhost:1420")
print("  Backend:  http://localhost:8000")
print("=" * 60)
print()

# Wait for processes
try:
    while True:
        # Check if any process has died
        for p in processes:
            if p.poll() is not None:
                print(f"\n❌ Process {p.pid} terminated unexpectedly")
                signal_handler(None, None)
        time.sleep(1)
except KeyboardInterrupt:
    signal_handler(None, None)
