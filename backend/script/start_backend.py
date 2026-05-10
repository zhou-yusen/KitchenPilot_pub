from __future__ import annotations

import argparse
import sys
from pathlib import Path

import uvicorn


def main() -> None:
    """Start the KitchenPilot API in the foreground with clean Ctrl+C shutdown."""
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
    print("Press Ctrl+C to stop.", flush=True)
    print()

    try:
        uvicorn.run(
            "kitchenpilot.main:app",
            host=args.host,
            port=args.port,
            reload=False,
            log_level="info",
        )
    except KeyboardInterrupt:
        print("\nStopping KitchenPilot backend.", flush=True)


if __name__ == "__main__":
    main()
