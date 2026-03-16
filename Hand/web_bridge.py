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
except Exception:  # pragma: no cover - optional dependency
    EventClient = None

hand_client = EventClient(channel="hand") if EventClient else None
_last_snapshot_at = 0.0


def publish_hand_snapshot(payload: Dict[str, Any], throttle: float = 0.15) -> None:
    global _last_snapshot_at
    if not hand_client:
        return
    now = time.time()
    if now - _last_snapshot_at < throttle:
        return
    _last_snapshot_at = now
    hand_client.publish("status", payload)


def publish_hand_command(action: str, meta: Dict[str, Any] | None = None) -> None:
    if not hand_client:
        return
    hand_client.publish("command", {"action": action, "meta": meta or {}})


def publish_hand_frame(jpeg_base64: str) -> None:
    if not hand_client:
        return
    hand_client.publish("frame", {"data": jpeg_base64, "format": "jpeg"})
