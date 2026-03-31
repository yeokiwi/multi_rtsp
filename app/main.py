"""FastAPI application factory and lifespan management."""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import ConfigManager
from .go2rtc_manager import Go2RTCManager
from .routers import streams, webrtc

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("multi_rtsp")

PROJECT_ROOT = Path(__file__).parent.parent
STATIC_DIR = PROJECT_ROOT / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    config_path = os.environ.get("MULTI_RTSP_CONFIG", "config.yaml")
    config_mgr = ConfigManager(config_path)
    app_config = config_mgr.get_app_config()

    # Locate go2rtc binary
    binary_path = PROJECT_ROOT / "bin" / "go2rtc"
    if not binary_path.exists():
        # Try Windows path
        binary_path = PROJECT_ROOT / "bin" / "go2rtc.exe"

    go2rtc_mgr = Go2RTCManager(str(binary_path), api_port=app_config.go2rtc_port)

    # Start go2rtc with streams baked into its config file
    configured_streams = config_mgr.get_streams()
    stream_urls = {sid: s.url for sid, s in configured_streams.items()}

    try:
        await go2rtc_mgr.start(stream_urls)
    except FileNotFoundError as e:
        logger.error(str(e))
        logger.error("Please run: python setup_go2rtc.py")
        raise SystemExit(1)

    logger.info("Started with %d stream(s)", len(stream_urls))

    # Store managers in app state
    app.state.config_mgr = config_mgr
    app.state.go2rtc_mgr = go2rtc_mgr

    yield

    # Shutdown
    await go2rtc_mgr.cleanup()
    logger.info("Shutdown complete")


app = FastAPI(title="Multi-RTSP Viewer", lifespan=lifespan)

# Include API routers
app.include_router(streams.router, prefix="/api")
app.include_router(webrtc.router, prefix="/api")

# Serve static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def index():
    return FileResponse(str(STATIC_DIR / "index.html"))
