from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class FrontendServer(ThreadingHTTPServer):
    """HTTP server tuned for clean Ctrl+C shutdown on Windows terminals."""

    allow_reuse_address = True
    daemon_threads = True


def main() -> None:
    """Run the zero-build KitchenPilot frontend with a visible local URL."""
    parser = argparse.ArgumentParser(description="Start the KitchenPilot frontend demo.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5173)
    args = parser.parse_args()

    frontend_dir = Path(__file__).resolve().parent
    handler = partial(SimpleHTTPRequestHandler, directory=str(frontend_dir))
    server = FrontendServer((args.host, args.port), handler)
    server.timeout = 0.5
    url = f"http://{args.host}:{args.port}"

    print("KitchenPilot frontend running:", flush=True)
    print(f"  {url}", flush=True)
    print(flush=True)
    print("Press Ctrl+C to stop.", flush=True)
    print(flush=True)

    try:
        while True:
            server.handle_request()
    except KeyboardInterrupt:
        print("\nStopping KitchenPilot frontend.", flush=True)
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
