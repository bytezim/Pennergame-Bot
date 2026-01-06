"""
Simple HTTP server with API proxy for PennerBot web frontend.
Serves static files from dist/ and proxies /api requests to backend.

Usage:
    python serve.py [--port PORT] [--backend-url URL]

Example:
    python serve.py --port 1420 --backend-url http://127.0.0.1:8000
"""

import argparse
import asyncio
from pathlib import Path

from aiohttp import ClientSession, web


class ProxyServer:
    def __init__(self, backend_url: str = "http://127.0.0.1:8000"):
        self.backend_url = backend_url.rstrip("/")
        self.dist_path = Path(__file__).parent / "dist"

        if not self.dist_path.exists():
            raise FileNotFoundError(
                f"Build directory not found: {self.dist_path}\n"
                "Please run 'npm run build' first!"
            )

    async def proxy_handler(self, request):
        """Proxy /api requests to backend server"""
        async with ClientSession() as session:
            # Build target URL
            url = f"{self.backend_url}{request.path}"
            if request.query_string:
                url += f"?{request.query_string}"

            # Forward request to backend
            async with session.request(
                method=request.method,
                url=url,
                headers={
                    k: v for k, v in request.headers.items() if k.lower() != "host"
                },
                data=await request.read() if request.can_read_body else None,
            ) as resp:
                # Forward response back to client
                headers = {
                    k: v
                    for k, v in resp.headers.items()
                    if k.lower() not in ("transfer-encoding", "connection")
                }

                return web.Response(
                    body=await resp.read(), status=resp.status, headers=headers
                )

    async def index_handler(self, request):
        """Serve index.html for root path"""
        index_path = self.dist_path / "index.html"
        return web.FileResponse(index_path)

    async def spa_handler(self, request):
        """
        SPA (Single Page Application) handler
        Serves index.html for all routes except API and static assets
        This enables client-side routing (React Router)
        """
        index_path = self.dist_path / "index.html"
        return web.FileResponse(index_path)

    async def create_app(self):
        """Create and configure the web application"""
        app = web.Application()

        # 1. Proxy API requests (highest priority)
        app.router.add_route("*", "/api/{tail:.*}", self.proxy_handler)

        # 2. Serve static assets (js, css, images, etc.)
        app.router.add_static("/assets", self.dist_path / "assets", name="assets")
        
        # 3. Root and all other routes serve index.html (SPA fallback)
        app.router.add_get("/", self.spa_handler)
        app.router.add_get("/{path:.*}", self.spa_handler)

        return app


async def main():
    parser = argparse.ArgumentParser(description="PennerBot Web Server")
    parser.add_argument(
        "--port", type=int, default=1420, help="Port to serve on (default: 1420)"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--backend-url",
        type=str,
        default="http://127.0.0.1:8000",
        help="Backend API URL (default: http://127.0.0.1:8000)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("PennerBot Web Server")
    print("=" * 60)
    print(f"Frontend URL:  http://{args.host}:{args.port}")
    print(f"Backend URL:   {args.backend_url}")
    print(f"Serving from:  {Path(__file__).parent / 'dist'}")
    print("=" * 60)
    print("\nPress Ctrl+C to stop the server\n")

    try:
        server = ProxyServer(backend_url=args.backend_url)
        app = await server.create_app()
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, args.host, args.port)
        await site.start()

        print(f"[OK] Server running on http://{args.host}:{args.port}")
        print(f"[OK] API proxy active: /api/* -> {args.backend_url}/api/*\n")

        # Keep running
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        print("\n\nShutting down server...")
    except FileNotFoundError as e:
        print(f"\n[ERROR] Error: {e}")
        return 1
    except Exception as e:
        print(f"\n[ERROR] Error starting server: {e}")
        return 1

    return 0


def run_server(port: int = 1420, host: str = "127.0.0.1", backend_url: str = "http://127.0.0.1:8000"):
    """
    Run the web server (synchronous wrapper for use in threads).
    
    Args:
        port: Port to serve on (default: 1420)
        host: Host to bind to (default: 127.0.0.1)
        backend_url: Backend API URL (default: http://127.0.0.1:8000)
    """
    import sys
    
    # Create a modified version of sys.argv for the parser
    old_argv = sys.argv
    sys.argv = ['serve.py', '--port', str(port), '--host', host, '--backend-url', backend_url]
    
    try:
        return asyncio.run(main())
    finally:
        sys.argv = old_argv


if __name__ == "__main__":
    try:
        exit(asyncio.run(main()))
    except KeyboardInterrupt:
        print("\n\nServer stopped.")
