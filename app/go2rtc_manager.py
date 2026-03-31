"""Manages the go2rtc subprocess lifecycle via config file."""

import asyncio
import logging
import os
import sys
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
        self._client = httpx.AsyncClient(timeout=30.0)

    def _write_config(self, streams: dict[str, str]):
        """Write go2rtc YAML config with ports and stream definitions."""
        go2rtc_config = {
            "api": {"listen": f":{self.api_port}"},
            "webrtc": {"listen": ":8555"},
        }
        if streams:
            go2rtc_config["streams"] = streams

        if self._config_file and os.path.exists(self._config_file):
            # Reuse existing temp file
            with open(self._config_file, "w") as f:
                yaml.dump(go2rtc_config, f, default_flow_style=False)
        else:
            fd, self._config_file = tempfile.mkstemp(suffix=".yaml", prefix="go2rtc_")
            with os.fdopen(fd, "w") as f:
                yaml.dump(go2rtc_config, f, default_flow_style=False)

        logger.info("Wrote go2rtc config with %d stream(s): %s",
                     len(streams), list(streams.keys()))

    async def start(self, streams: dict[str, str] | None = None):
        """Start go2rtc with the given streams baked into the config."""
        if not os.path.exists(self.binary_path):
            raise FileNotFoundError(
                f"go2rtc binary not found at {self.binary_path}. "
                "Run 'python setup_go2rtc.py' to download it."
            )

        self._write_config(streams or {})

        self._process = await asyncio.create_subprocess_exec(
            self.binary_path, "-config", self._config_file,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        logger.info("go2rtc started (PID: %d)", self._process.pid)

        self._log_tasks = [
            asyncio.create_task(self._pipe_log(self._process.stdout, "go2rtc")),
            asyncio.create_task(self._pipe_log(self._process.stderr, "go2rtc")),
        ]

        await self._wait_ready()

    async def stop(self):
        """Stop the go2rtc process."""
        if self._process and self._process.returncode is None:
            # Use terminate() for cross-platform compatibility (Windows + Unix)
            self._process.terminate()
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self._process.kill()
                await self._process.wait()
            logger.info("go2rtc stopped")

        for task in self._log_tasks:
            task.cancel()
        self._log_tasks.clear()

    async def restart(self, streams: dict[str, str]):
        """Restart go2rtc with updated stream definitions."""
        logger.info("Restarting go2rtc with %d stream(s)...", len(streams))
        await self.stop()
        await self.start(streams)

    async def cleanup(self):
        """Stop go2rtc and clean up temp files."""
        await self.stop()
        if self._config_file and os.path.exists(self._config_file):
            os.unlink(self._config_file)
            self._config_file = None
        await self._client.aclose()

    async def _wait_ready(self, timeout: float = 15.0):
        elapsed = 0.0
        interval = 0.3
        while elapsed < timeout:
            try:
                resp = await self._client.get(f"{self.base_url}/api/streams")
                if resp.status_code == 200:
                    logger.info("go2rtc is ready (streams: %s)", list(resp.json().keys()))
                    return
            except (httpx.ConnectError, httpx.ReadError, httpx.RemoteProtocolError):
                # ConnectError: go2rtc not listening yet
                # ReadError/RemoteProtocolError: stale connection from before restart
                pass
            await asyncio.sleep(interval)
            elapsed += interval
        raise TimeoutError("go2rtc did not become ready in time")

    async def get_streams_status(self) -> dict:
        try:
            resp = await self._client.get(f"{self.base_url}/api/streams")
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return {}

    async def webrtc_offer(self, stream_id: str, sdp_offer: str) -> httpx.Response:
        """Proxy WebRTC SDP offer to go2rtc."""
        return await self._client.post(
            f"{self.base_url}/api/webrtc",
            params={"src": stream_id},
            content=sdp_offer,
            headers={"Content-Type": "application/sdp"},
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
