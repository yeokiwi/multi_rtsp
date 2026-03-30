"""YAML configuration manager for stream definitions and app settings."""

import os
import re
import threading
from typing import Optional

import yaml
from pydantic import BaseModel


class StreamConfig(BaseModel):
    name: str
    url: str


class AppConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    go2rtc_port: int = 1984


class ConfigManager:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self._lock = threading.Lock()
        self._config: dict = {}
        self.load()

    def load(self) -> dict:
        if os.path.exists(self.config_path):
            with open(self.config_path) as f:
                self._config = yaml.safe_load(f) or {}
        else:
            self._config = {"app": {}, "streams": {}}
        # Ensure sections exist
        self._config.setdefault("app", {})
        self._config.setdefault("streams", {})
        # Normalize: if streams is None (empty YAML section), make it a dict
        if self._config["streams"] is None:
            self._config["streams"] = {}
        return self._config

    def save(self):
        with self._lock:
            with open(self.config_path, "w") as f:
                yaml.dump(self._config, f, default_flow_style=False, sort_keys=False)

    def get_app_config(self) -> AppConfig:
        return AppConfig(**self._config.get("app", {}))

    def get_streams(self) -> dict[str, StreamConfig]:
        raw = self._config.get("streams", {}) or {}
        return {sid: StreamConfig(**data) for sid, data in raw.items()}

    def add_stream(self, stream_id: Optional[str], name: str, url: str) -> str:
        if not stream_id:
            stream_id = self._slugify(name)
        # Ensure unique ID
        base_id = stream_id
        counter = 1
        while stream_id in (self._config.get("streams") or {}):
            stream_id = f"{base_id}_{counter}"
            counter += 1
        if self._config["streams"] is None:
            self._config["streams"] = {}
        self._config["streams"][stream_id] = {"name": name, "url": url}
        self.save()
        return stream_id

    def update_stream(self, stream_id: str, name: Optional[str] = None, url: Optional[str] = None):
        streams = self._config.get("streams", {}) or {}
        if stream_id not in streams:
            raise KeyError(f"Stream '{stream_id}' not found")
        if name is not None:
            streams[stream_id]["name"] = name
        if url is not None:
            streams[stream_id]["url"] = url
        self.save()

    def remove_stream(self, stream_id: str):
        streams = self._config.get("streams", {}) or {}
        if stream_id not in streams:
            raise KeyError(f"Stream '{stream_id}' not found")
        del streams[stream_id]
        self.save()

    @staticmethod
    def _slugify(text: str) -> str:
        text = text.lower().strip()
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"[\s-]+", "_", text)
        return text or "stream"
