from __future__ import annotations

import argparse
import msvcrt
import sys
import threading
import time
from pathlib import Path

import uvicorn


def main() -> None:
    """Start the KitchenPilot API in the foreground with Esc shutdown."""
    parser = argparse.ArgumentParser(description="Start the KitchenPilot backend API.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    src_dir = Path(__file__).resolve().parents[1] / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    base_url = f"http://{args.host}:{args.port}"
    print("KitchenPilot backend running:", flush=True)
    print(f"  API docs: {base_url}/docs", flush=True)
    print(f"  Health:   {base_url}/health", flush=True)
    print()
    print("Press Esc to stop.", flush=True)
    print()

    config = uvicorn.Config(
        "kitchenpilot.main:app",
        host=args.host,
        port=args.port,
        reload=False,
        log_level="info",
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)

    thread.start()
    while thread.is_alive():
        if msvcrt.kbhit() and msvcrt.getch() == b"\x1b":
            print("\nStopping KitchenPilot backend.", flush=True)
            server.should_exit = True
            break
        time.sleep(0.1)
    thread.join(timeout=5)


if __name__ == "__main__":
    main()
