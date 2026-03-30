#!/usr/bin/env python3
"""Entry point for the Multi-RTSP Stream Viewer."""

import argparse
import uvicorn


def main():
    parser = argparse.ArgumentParser(description="Multi-RTSP Stream Viewer")
    parser.add_argument("--host", default=None, help="Host to bind to (overrides config)")
    parser.add_argument("--port", type=int, default=None, help="Port to bind to (overrides config)")
    parser.add_argument("--config", default="config.yaml", help="Path to config file")
    args = parser.parse_args()

    # Store config path for the app to pick up
    import os
    os.environ["MULTI_RTSP_CONFIG"] = args.config

    # Load config to get defaults
    import yaml
    try:
        with open(args.config) as f:
            config = yaml.safe_load(f) or {}
    except FileNotFoundError:
        config = {}

    app_config = config.get("app", {})
    host = args.host or app_config.get("host", "0.0.0.0")
    port = args.port or app_config.get("port", 8000)

    print(f"Starting Multi-RTSP Viewer on http://{host}:{port}")
    uvicorn.run("app.main:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
