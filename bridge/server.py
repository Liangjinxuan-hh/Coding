"""Event bridge server.

Expose a lightweight FastAPI application that accepts HTTP POST events from
Python producers (face / hand detectors) and pushes them to any connected
WebSocket consumers (the web control panel, Unity editor, etc.).

Run with:
    uvicorn bridge.server:app --reload --port 5050
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import time
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
