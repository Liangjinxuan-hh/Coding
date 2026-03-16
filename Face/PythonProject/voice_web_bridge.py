from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any, Dict

PROJECT_ROOT = None
_current = Path(__file__).resolve()
for parent in _current.parents:
    if (parent / "bridge").exists():
        PROJECT_ROOT = parent
        break
if PROJECT_ROOT and str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

try:
    from bridge.event_client import EventClient
except Exception:
    EventClient = None

voice_client = EventClient(channel="voice") if EventClient else None
_last_status_at = 0.0


def publish_voice_snapshot(payload: Dict[str, Any], throttle: float = 0.2) -> None:
    global _last_status_at
    if not voice_client:
        return
    now = time.time()
    if now - _last_status_at < throttle:
        return
    _last_status_at = now
    voice_client.publish("status", payload)


def publish_voice_command(command: str, meta: Dict[str, Any] | None = None) -> None:
    if not voice_client:
        return
    voice_client.publish("command", {"command": command, "meta": meta or {}})