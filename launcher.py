#!/usr/bin/env python3
"""
PennerBot Launcher - Single EXE Entry Point
Main launcher that provides both GUI and console modes
"""

import os
import sys
import argparse
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


def start_gui_launcher():
    """Start the modern GUI launcher"""
    try:
        print("Starting PennerBot Modern GUI Launcher...")
        from gui_launcher import main as gui_main
        gui_main()
    except ImportError as e:
        print(f"Error importing GUI launcher: {e}")
        print("Falling back to console mode...")
        start_console_launcher()
    except Exception as e:
        print(f"Error starting GUI launcher: {e}")
        import traceback
        traceback.print_exc()
        print("Falling back to console mode...")
        start_console_launcher()


def start_console_launcher():
    """Start the original console launcher"""
    print("Starting PennerBot Console Launcher...")
    
    # Add resource path to sys.path
    sys.path.insert(0, get_resource_path("."))

    try:
        import threading
        import time
        
        # Start backend in separate thread
        backend_thread = threading.Thread(target=start_backend, daemon=True)
        backend_thread.start()

        # Start frontend (blocking)
        try:
            start_frontend()
        except KeyboardInterrupt:
            print("\nShutting down...")
            sys.exit(0)
        except Exception as e:
            print(f"\nError: {e}")
            input("\nPress Enter to exit...")
            sys.exit(1)
            
    except Exception as e:
        print(f"Error in console launcher: {e}")
        input("\nPress Enter to exit...")
        sys.exit(1)


def start_backend():
    """Start FastAPI backend server"""
    print("Starting Backend Server..." if sys.platform != "win32" else "Starting Backend Server...")

    # Import and run FastAPI app
    import uvicorn

    from server import app

    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info", access_log=False)


def start_frontend():
    """Start Frontend server (aiohttp)"""
    print("Starting Frontend Server..." if sys.platform != "win32" else "Starting Frontend Server...")
    time.sleep(2)  # Wait for backend to start

    import asyncio
    from aiohttp import ClientSession, web

    # Get the dist folder path
    dist_path = get_resource_path("web/dist")

    if not os.path.exists(dist_path):
        print(f"Frontend build not found at: {dist_path}")
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
                print(f"Proxy error: {e}")
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

    print("Backend Server ready at http://127.0.0.1:8000" if sys.platform != "win32" else "Backend Server ready at http://127.0.0.1:8000")
    print("Frontend Server ready at http://127.0.0.1:1420" if sys.platform != "win32" else "Frontend Server ready at http://127.0.0.1:1420")
    print("Opening browser..." if sys.platform != "win32" else "Opening browser...")

    # Import webbrowser here to avoid issues
    import webbrowser
    import threading

    # Open browser after 1 second
    threading.Timer(1.0, lambda: webbrowser.open("http://127.0.0.1:1420")).start()

    web.run_app(app, host="127.0.0.1", port=1420, print=None)


def main():
    """Main launcher function"""
    print("=" * 60)
    print("PennerBot Launcher" if sys.platform != "win32" else "PennerBot Launcher")
    print("=" * 60)
    print()

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="PennerBot Launcher")
    parser.add_argument("--console", action="store_true", help="Force console mode")
    parser.add_argument("--gui", action="store_true", help="Force GUI mode (default)")
    args = parser.parse_args()

    # Determine mode
    if args.console:
        start_console_launcher()
    else:
        # Default to GUI mode
        start_gui_launcher()


if __name__ == "__main__":
    # Import required modules for console mode
    import threading
    import time
    main()
