from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
from typing import Any
from urllib import error, request


def _http_json(method: str, url: str, payload: dict[str, Any] | None = None, timeout: float = 3.0) -> tuple[int, dict[str, Any] | str]:
    data = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = request.Request(url=url, method=method, data=data, headers=headers)

    try:
        with request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            try:
                return resp.status, json.loads(raw)
            except json.JSONDecodeError:
                return resp.status, raw
    except error.HTTPError as ex:
        raw = ex.read().decode("utf-8", errors="replace")
        try:
            return ex.code, json.loads(raw)
        except json.JSONDecodeError:
            return ex.code, raw


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_ready(base_url: str, timeout_sec: float = 15.0) -> bool:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        try:
            status, body = _http_json("GET", f"{base_url}/health", None, timeout=1.0)
            if status == 200 and isinstance(body, dict) and body.get("status") == "ok":
                return True
        except Exception:
            pass
        time.sleep(0.25)
    return False


def run_check(host: str, port: int) -> int:
    base_url = f"http://{host}:{port}"
    cmd = [sys.executable, "-m", "uvicorn", "bridge.server:app", "--host", host, "--port", str(port)]

    env = os.environ.copy()
    env["DRIP_BRIDGE_PORT"] = str(port)

    proc = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=(subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0),
    )

    try:
        if not _wait_ready(base_url):
            print("[FAIL] bridge startup timeout")
            return 2

        # Regression case: whitespace-only text must fail at validation layer with 422.
        status, body = _http_json("POST", f"{base_url}/api/ai/voice-plan", {"text": "   "})
        if status != 422:
            print(f"[FAIL] expected 422 for empty text, got {status}; body={body}")
            return 1

        # Sanity case: non-empty text should still be accepted.
        ok_status, ok_body = _http_json("POST", f"{base_url}/api/ai/voice-plan", {"text": "山风江月"})
        if ok_status != 200:
            print(f"[FAIL] expected 200 for valid text, got {ok_status}; body={ok_body}")
            return 1

        print("[PASS] /api/ai/voice-plan validation regression check")
        return 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def main() -> int:
    parser = argparse.ArgumentParser(description="CI regression check for /api/ai/voice-plan empty-text validation")
    parser.add_argument("--host", default="127.0.0.1", help="Bridge host")
    parser.add_argument("--port", type=int, default=0, help="Bridge port (0 = auto free port)")
    args = parser.parse_args()

    port = args.port if args.port > 0 else _find_free_port()
    return run_check(args.host, port)


if __name__ == "__main__":
    raise SystemExit(main())