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
except Exception:  # pragma: no cover - fallback when dependency missing
    EventClient = None

action_client = EventClient(channel="face") if EventClient else None
_last_status_at = 0.0


def publish_face_snapshot(payload: Dict[str, Any], throttle: float = 0.2) -> None:
    global _last_status_at
    if not action_client:
        return
    now = time.time()
    if now - _last_status_at < throttle:
        return
    _last_status_at = now
    action_client.publish("status", payload)


def publish_face_command(command: str, meta: Dict[str, Any] | None = None) -> None:
    if not action_client:
        return
    action_client.publish("command", {"command": command, "meta": meta or {}})


def publish_voice_state(status: str, transcript: str) -> None:
    if not action_client:
        return
    action_client.publish("voice", {"status": status, "transcript": transcript})


def publish_face_frame(jpeg_base64: str) -> None:
    if not action_client:
        return
    action_client.publish("frame", {"data": jpeg_base64, "format": "jpeg"})
