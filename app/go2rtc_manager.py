"""Manages the go2rtc subprocess lifecycle and its REST API."""

import asyncio
import logging
import os
import signal
import tempfile

import httpx
import yaml

logger = logging.getLogger("go2rtc_manager")


class Go2RTCManager:
    def __init__(self, binary_path: str, api_port: int = 1984):
        self.binary_path = binary_path
        self.api_port = api_port
        self.base_url = f"http://127.0.0.1:{api_port}"
        self._process: asyncio.subprocess.Process | None = None
        self._config_file: str | None = None
        self._log_tasks: list[asyncio.Task] = []
        self._client = httpx.AsyncClient(timeout=10.0)

    async def start(self):
        if not os.path.exists(self.binary_path):
            raise FileNotFoundError(
                f"go2rtc binary not found at {self.binary_path}. "
                "Run 'python setup_go2rtc.py' to download it."
            )

        # Generate minimal config for go2rtc (ports only, streams via API)
        go2rtc_config = {
            "api": {"listen": f":{self.api_port}"},
            "webrtc": {"listen": ":8555"},
        }
        fd, self._config_file = tempfile.mkstemp(suffix=".yaml", prefix="go2rtc_")
        with os.fdopen(fd, "w") as f:
            yaml.dump(go2rtc_config, f)

        self._process = await asyncio.create_subprocess_exec(
            self.binary_path, "-config", self._config_file,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        logger.info("go2rtc started (PID: %d)", self._process.pid)

        # Background tasks to log go2rtc output
        self._log_tasks = [
            asyncio.create_task(self._pipe_log(self._process.stdout, "go2rtc")),
            asyncio.create_task(self._pipe_log(self._process.stderr, "go2rtc")),
        ]

        await self._wait_ready()

    async def _wait_ready(self, timeout: float = 15.0):
        elapsed = 0.0
        interval = 0.3
        while elapsed < timeout:
            try:
                resp = await self._client.get(f"{self.base_url}/api/streams")
                if resp.status_code == 200:
                    logger.info("go2rtc is ready")
                    return
            except httpx.ConnectError:
                pass
            await asyncio.sleep(interval)
            elapsed += interval
        raise TimeoutError("go2rtc did not become ready in time")

    async def stop(self):
        if self._process and self._process.returncode is None:
            self._process.send_signal(signal.SIGTERM)
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self._process.kill()
                await self._process.wait()
            logger.info("go2rtc stopped")

        for task in self._log_tasks:
            task.cancel()
        self._log_tasks.clear()

        if self._config_file and os.path.exists(self._config_file):
            os.unlink(self._config_file)
            self._config_file = None

        await self._client.aclose()

    async def sync_streams(self, streams: dict[str, str]):
        """Sync stream definitions to go2rtc. streams = {id: rtsp_url}."""
        # Get current streams in go2rtc
        try:
            resp = await self._client.get(f"{self.base_url}/api/streams")
            current = set(resp.json().keys()) if resp.status_code == 200 else set()
        except Exception:
            current = set()

        desired = set(streams.keys())

        # Remove streams no longer in config
        for sid in current - desired:
            await self.remove_stream(sid)

        # Add/update streams
        for sid, url in streams.items():
            await self.add_stream(sid, url)

    async def add_stream(self, stream_id: str, url: str):
        try:
            await self._client.put(
                f"{self.base_url}/api/streams",
                params={"name": stream_id, "src": url},
            )
        except Exception as e:
            logger.error("Failed to add stream %s: %s", stream_id, e)

    async def remove_stream(self, stream_id: str):
        try:
            await self._client.delete(
                f"{self.base_url}/api/streams",
                params={"name": stream_id},
            )
        except Exception as e:
            logger.error("Failed to remove stream %s: %s", stream_id, e)

    async def get_streams_status(self) -> dict:
        try:
            resp = await self._client.get(f"{self.base_url}/api/streams")
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return {}

    async def webrtc_offer(self, stream_id: str, offer: str, content_type: str) -> httpx.Response:
        return await self._client.post(
            f"{self.base_url}/api/webrtc",
            params={"src": stream_id},
            content=offer,
            headers={"Content-Type": content_type},
        )

    def is_running(self) -> bool:
        return self._process is not None and self._process.returncode is None

    @staticmethod
    async def _pipe_log(stream, prefix: str):
        try:
            async for line in stream:
                text = line.decode("utf-8", errors="replace").rstrip()
                if text:
                    logger.info("[%s] %s", prefix, text)
        except asyncio.CancelledError:
            pass
