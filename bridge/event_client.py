"""Tiny HTTP client that pushes events into the FastAPI bridge server.

Designed to be imported from the Face / Hand detection scripts without adding
heavy dependencies. Events are queued and delivered in a background thread to
avoid blocking the real-time computer-vision loop.
"""
from __future__ import annotations

import json
import os
import queue
import threading
import time
from typing import Any, Dict
from urllib import error, request

DEFAULT_ENDPOINT = os.getenv("DRIP_EVENT_ENDPOINT", "http://127.0.0.1:5051/api/events")
ENABLED = os.getenv("DRIP_EVENT_ENABLED", "1") != "0"


class EventClient:
    def __init__(self, channel: str, endpoint: str | None = None) -> None:
        self.channel = channel
        self.endpoint = endpoint or DEFAULT_ENDPOINT
        self.enabled = ENABLED
        self._queue: "queue.Queue[Dict[str, Any]]" = queue.Queue(maxsize=256)
        self._worker = threading.Thread(target=self._loop, daemon=True)
        self._worker.start()

    def publish(self, event_type: str, payload: Dict[str, Any]) -> None:
        if not self.enabled:
            return
        envelope = {
            "channel": self.channel,
            "type": event_type,
            "payload": payload,
            "timestamp": time.time(),
        }
        try:
            self._queue.put_nowait(envelope)
        except queue.Full:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                pass
            self._queue.put_nowait(envelope)

    def _loop(self) -> None:
        while True:
            event = self._queue.get()
            data = json.dumps(event).encode("utf-8")
            try:
                req = request.Request(
                    self.endpoint,
                    data=data,
                    headers={"Content-Type": "application/json", "User-Agent": "DripEventClient/1.0"},
                    method="POST",
                )
                request.urlopen(req, timeout=1.0)
            except (error.HTTPError, error.URLError, TimeoutError):
                # Connection not ready yet; retry shortly.
                time.sleep(1.0)
            except Exception:
                time.sleep(1.0)
