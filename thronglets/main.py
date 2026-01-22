"""Main entry point for Thronglets ServiceBus."""

import argparse
import logging
import sys


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Thronglets - Multi-Agent ServiceBus",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind server (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for server (default: 8000)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log level (default: INFO)",
    )

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )

    print(f"Starting Thronglets ServiceBus on http://{args.host}:{args.port}")
    print(f"  HTTP API:    http://{args.host}:{args.port}/")
    print(f"  MCP Server:  http://{args.host}:{args.port}/bus")
    print(f"  Log Level:  {args.log_level}")

    import uvicorn

    from thronglets.http_api import app

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
