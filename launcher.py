"""
PennerBot Launcher - Single EXE Entry Point
Starts both FastAPI backend and serves frontend
"""

import os
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

# Handle Unicode output on Windows
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())


def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


def start_backend():
    """Start FastAPI backend server"""
    print("🐍 Starting Backend Server..." if sys.platform != "win32" else "Starting Backend Server...")

    # Add resource path to sys.path
    sys.path.insert(0, get_resource_path("."))

    # Import and run FastAPI app
    import uvicorn

    from server import app

    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info", access_log=False)


def start_frontend():
    """Start Frontend server (aiohttp)"""
    print("🌐 Starting Frontend Server..." if sys.platform != "win32" else "Starting Frontend Server...")
    time.sleep(2)  # Wait for backend to start

    import asyncio

    from aiohttp import ClientSession, web

    # Get the dist folder path
    dist_path = get_resource_path("web/dist")

    if not os.path.exists(dist_path):
        print(f"❌ Frontend build not found at: {dist_path}" if sys.platform != "win32" else f"Frontend build not found at: {dist_path}")
        print("Please build the frontend first with: npm run build")
        sys.exit(1)

    async def proxy_handler(request):
        """Proxy API requests to backend"""
        path = request.path.replace("/api", "", 1)
        url = f"http://127.0.0.1:8000/api{path}"

        async with ClientSession() as session:
            try:
                async with session.request(
                    method=request.method,
                    url=url,
                    headers=request.headers,
                    data=await request.read(),
                ) as resp:
                    body = await resp.read()
                    return web.Response(
                        body=body, status=resp.status, headers=resp.headers
                    )
            except Exception as e:
                print(f"❌ Proxy error: {e}" if sys.platform != "win32" else f"Proxy error: {e}")
                return web.Response(text=f"Backend connection error: {e}", status=502)

    async def index_handler(request):
        """Serve index.html for root path"""
        index_path = os.path.join(dist_path, "index.html")
        return web.FileResponse(index_path)

    app = web.Application()

    # Proxy API requests (must be first)
    app.router.add_route("*", "/api/{tail:.*}", proxy_handler)

    # Root path serves index.html (before static handler)
    app.router.add_get("/", index_handler)

    # Serve static files (assets, js, css) - must be last
    app.router.add_static("/", dist_path, name="static", show_index=False)

    print("✅ Backend Server ready at http://127.0.0.1:8000" if sys.platform != "win32" else "Backend Server ready at http://127.0.0.1:8000")
    print("✅ Frontend Server ready at http://127.0.0.1:1420" if sys.platform != "win32" else "Frontend Server ready at http://127.0.0.1:1420")
    print("🌐 Opening browser..." if sys.platform != "win32" else "Opening browser...")

    # Open browser after 1 second
    threading.Timer(1.0, lambda: webbrowser.open("http://127.0.0.1:1420")).start()

    web.run_app(app, host="127.0.0.1", port=1420, print=None)


def main():
    """Main launcher function"""
    print("=" * 60)
    print("🤖 PennerBot - Windows Binary Edition" if sys.platform != "win32" else "PennerBot - Windows Binary Edition")
    print("=" * 60)
    print()

    # Start backend in separate thread
    backend_thread = threading.Thread(target=start_backend, daemon=True)
    backend_thread.start()

    # Start frontend (blocking)
    try:
        start_frontend()
    except KeyboardInterrupt:
        print("\n👋 Shutting down..." if sys.platform != "win32" else "\nShutting down...")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}" if sys.platform != "win32" else f"\nError: {e}")
        input("\nPress Enter to exit...")
        sys.exit(1)


if __name__ == "__main__":
    main()
