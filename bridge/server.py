"""Event bridge server.

Expose a lightweight FastAPI application that accepts HTTP POST events from
Python producers (face / hand detectors) and pushes them to any connected
WebSocket consumers (the web control panel, Unity editor, etc.).

Run with:
    uvicorn bridge.server:app --reload --port 5050
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import time
from urllib import error as url_error
from urllib import request as url_request
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

ROOT_DIR = Path(__file__).resolve().parents[1]
BRIDGE_PORT = int(os.getenv("DRIP_BRIDGE_PORT", "5051"))
MODULE_CONFIG = {
    "face": {
        "cwd": ROOT_DIR / "Face" / "PythonProject",
        "cmd": [sys.executable, "main.py"],
    },
    "hand": {
        "cwd": ROOT_DIR / "Hand",
        "cmd": [sys.executable, "main2.py"],
    },
    "voice": {
        "cwd": ROOT_DIR / "Face" / "PythonProject",
        "cmd": [sys.executable, "voice_module.py"],
    },
}
CREATE_NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


class Event(BaseModel):
    channel: str = Field(..., description="Source channel, e.g. 'face' or 'hand'")
    type: str = Field(..., description="Logical event type, e.g. 'status', 'command'")
    payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: float | None = Field(default=None)


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(websocket)

    async def broadcast(self, message: Dict[str, Any]) -> None:
        stale: List[WebSocket] = []
        async with self._lock:
            targets = list(self._connections)
        for ws in targets:
            try:
                await ws.send_json(message)
            except Exception:
                stale.append(ws)
        if stale:
            async with self._lock:
                for ws in stale:
                    self._connections.discard(ws)


class ModuleProcessManager:
    def __init__(self) -> None:
        self._procs: Dict[str, subprocess.Popen | None] = {key: None for key in MODULE_CONFIG}
        self._lock = Lock()

    def _start_sync(self, key: str) -> bool:
        if key not in MODULE_CONFIG:
            raise ValueError(f"Unknown module: {key}")
        with self._lock:
            proc = self._procs.get(key)
            if proc and proc.poll() is None:
                return False
            cfg = MODULE_CONFIG[key]
            env = os.environ.copy()
            env.setdefault("PYTHONPATH", str(ROOT_DIR))
            env.setdefault("DRIP_EVENT_ENDPOINT", f"http://127.0.0.1:{BRIDGE_PORT}/api/events")
            proc = subprocess.Popen(
                cfg["cmd"],
                cwd=str(cfg["cwd"]),
                env=env,
                creationflags=0,
            )
            self._procs[key] = proc
            return True

    def _stop_sync(self, key: str) -> bool:
        with self._lock:
            proc = self._procs.get(key)
            if not proc or proc.poll() is not None:
                self._procs[key] = None
                return False
            proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        finally:
            with self._lock:
                self._procs[key] = None
        return True

    def status(self) -> Dict[str, bool]:
        with self._lock:
            return {key: (proc is not None and proc.poll() is None) for key, proc in self._procs.items()}

    async def start(self, key: str) -> bool:
        return await asyncio.to_thread(self._start_sync, key)

    async def stop(self, key: str) -> bool:
        return await asyncio.to_thread(self._stop_sync, key)


app = FastAPI(title="DripMotion Bridge", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
ws_manager = ConnectionManager()
module_manager = ModuleProcessManager()


@app.get("/health")
async def healthcheck() -> Dict[str, Any]:
    return {
        "status": "ok",
        "connections": len(ws_manager._connections),
        "modules": module_manager.status(),
    }


@app.post("/api/events")
async def ingest_event(event: Event) -> Dict[str, Any]:
    payload = event.dict()
    payload["timestamp"] = payload.get("timestamp") or time.time()
    await ws_manager.broadcast(payload)
    return {"status": "ok"}


class ControlRequest(BaseModel):
    target: str = Field(..., pattern="^(face|hand|voice)$")
    action: str = Field(..., pattern="^(start|stop)$")


class VoicePlanRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=200)


def _normalize_action(action: str) -> str:
    allowed = {"moveUp", "moveDown", "rotateLeft", "rotateRight", "stop"}
    return action if action in allowed else "stop"


def _normalize_ring(ring: str | None) -> str | None:
    if ring in {"A", "B", "C", "D"}:
        return ring
    return None


def _normalize_duration(duration_ms: int | None) -> int:
    if duration_ms is None:
        return 900
    return max(250, min(int(duration_ms), 5000))


def _build_fallback_plan(text: str) -> Dict[str, Any]:
    rings = ["A", "B", "C", "D"]
    keywords = [
        ("山", "moveUp"),
        ("江", "moveDown"),
        ("风", "rotateLeft"),
        ("月", "rotateRight"),
        ("花", "moveUp"),
        ("夜", "rotateRight"),
    ]
    actions: List[str] = []
    for kw, action in keywords:
        if kw in text:
            actions.append(action)
    if not actions:
        actions = ["rotateLeft", "moveUp", "rotateRight", "moveDown"]

    steps: List[Dict[str, Any]] = []
    chars = [ch for ch in text if not ch.isspace()]
    length_factor = max(1, min(len(chars), 12))
    base_duration = 700 + min(700, length_factor * 40)
    for idx, action in enumerate(actions[:8]):
        steps.append(
            {
                "ring": rings[idx % 4],
                "action": action,
                "durationMs": _normalize_duration(base_duration + idx * 80),
            }
        )
    steps.append({"ring": None, "action": "stop", "durationMs": 350})
    return {
        "summary": "规则引擎已生成动作序列",
        "steps": steps,
    }


def _parse_json_from_text(raw: str) -> Dict[str, Any] | None:
    cleaned = (raw or "").strip()
    if not cleaned:
        return None
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if len(lines) >= 3:
            cleaned = "\n".join(lines[1:-1]).strip()
    try:
        return json.loads(cleaned)
    except Exception:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(cleaned[start : end + 1])
            except Exception:
                return None
    return None


def _call_llm_voice_plan(text: str) -> Dict[str, Any] | None:
    api_key = os.getenv("DRIP_AI_API_KEY", "").strip()
    if not api_key:
        return None

    model = os.getenv("DRIP_AI_MODEL", "gpt-4o-mini")
    endpoint = os.getenv("DRIP_AI_BASE_URL", "https://api.openai.com/v1/chat/completions")
    timeout_sec = float(os.getenv("DRIP_AI_TIMEOUT_SEC", "10"))

    sys_prompt = (
        "你是动作编排器。把中文诗句转换为机械环运动步骤。"
        "仅输出 JSON，不要解释。JSON 结构必须是："
        '{"summary":"...","steps":[{"ring":"A|B|C|D|null","action":"moveUp|moveDown|rotateLeft|rotateRight|stop","durationMs":900}]}'
        "steps 最多 8 个。"
    )
    body = {
        "model": model,
        "temperature": 0.4,
        "messages": [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": f"诗句：{text}"},
        ],
        "response_format": {"type": "json_object"},
    }
    req = url_request.Request(
        endpoint,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with url_request.urlopen(req, timeout=timeout_sec) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (url_error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
        return None

    content = (
        payload.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
    )
    parsed = _parse_json_from_text(content)
    if not parsed or not isinstance(parsed, dict):
        return None
    return parsed


def _normalize_plan(plan: Dict[str, Any] | None, source_text: str) -> Dict[str, Any]:
    raw = plan if isinstance(plan, dict) else _build_fallback_plan(source_text)
    steps_in = raw.get("steps") if isinstance(raw.get("steps"), list) else []
    steps_out: List[Dict[str, Any]] = []
    for step in steps_in[:8]:
        if not isinstance(step, dict):
            continue
        action = _normalize_action(str(step.get("action", "stop")))
        ring = _normalize_ring(step.get("ring"))
        duration_ms = _normalize_duration(step.get("durationMs"))
        steps_out.append({"ring": ring, "action": action, "durationMs": duration_ms})

    if not steps_out:
        steps_out = _build_fallback_plan(source_text)["steps"]

    summary = str(raw.get("summary") or "已生成动作序列")
    return {"summary": summary[:80], "steps": steps_out}


@app.get("/api/control/status")
async def control_status() -> Dict[str, Any]:
    return {"status": "ok", "modules": module_manager.status()}


@app.post("/api/control")
async def control_module(req: ControlRequest) -> Dict[str, Any]:
    stopped: List[str] = []
    if req.action == "start":
        # Face and hand modules both use the same camera; keep only these mutually exclusive.
        if req.target in {"face", "hand"}:
            for key, is_running in module_manager.status().items():
                if key in {"face", "hand"} and key != req.target and is_running:
                    await module_manager.stop(key)
                    stopped.append(key)
        changed = await module_manager.start(req.target)
    else:
        changed = await module_manager.stop(req.target)

    states = module_manager.status()
    await ws_manager.broadcast(
        {
            "channel": "system",
            "type": "module",
            "payload": {"target": req.target, "running": states.get(req.target, False), "states": states},
        }
    )
    return {"status": "ok", "changed": changed, "stopped": stopped, "modules": states}


@app.post("/api/ai/voice-plan")
async def ai_voice_plan(req: VoicePlanRequest) -> Dict[str, Any]:
    text = req.text.strip()
    if not text:
        return {"status": "error", "message": "empty_text"}

    llm_plan = await asyncio.to_thread(_call_llm_voice_plan, text)
    normalized = _normalize_plan(llm_plan, text)
    engine = "llm" if llm_plan else "fallback"
    return {
        "status": "ok",
        "engine": engine,
        "plan": normalized,
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await ws_manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("bridge.server:app", host="0.0.0.0", port=BRIDGE_PORT, reload=False)
