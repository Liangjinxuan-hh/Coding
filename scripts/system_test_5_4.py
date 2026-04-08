from __future__ import annotations

import asyncio
import csv
import json
import math
import time
from pathlib import Path
from statistics import mean, median
from typing import Any
from urllib import error, request

import matplotlib.pyplot as plt
import websockets


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "scripts" / "output" / "system_test_5_4"
BASE_URL = "http://127.0.0.1:5051"
WS_URL = "ws://127.0.0.1:5051/ws"


def ensure_out_dir() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)


def now_ms() -> float:
    return time.perf_counter() * 1000.0


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    k = (len(ordered) - 1) * p
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return float(ordered[int(k)])
    d0 = ordered[f] * (c - k)
    d1 = ordered[c] * (k - f)
    return float(d0 + d1)


def http_json(method: str, path: str, payload: dict[str, Any] | None = None, timeout: float = 5.0) -> tuple[int, dict[str, Any] | str, float]:
    url = f"{BASE_URL}{path}"
    data = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = request.Request(url=url, method=method, data=data, headers=headers)
    t0 = now_ms()
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            elapsed = now_ms() - t0
            try:
                body = json.loads(raw)
            except json.JSONDecodeError:
                body = raw
            return resp.status, body, elapsed
    except error.HTTPError as ex:
        raw = ex.read().decode("utf-8", errors="replace")
        elapsed = now_ms() - t0
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            body = raw
        return ex.code, body, elapsed


def run_endpoint_latency_suite() -> list[dict[str, Any]]:
    tests = [
        ("health", "GET", "/health", None, 50),
        ("control_status", "GET", "/api/control/status", None, 50),
        (
            "ingest_event",
            "POST",
            "/api/events",
            {"channel": "test", "type": "status", "payload": {"ok": True}},
            100,
        ),
        (
            "voice_plan",
            "POST",
            "/api/ai/voice-plan",
            {"text": "山风江月花夜"},
            30,
        ),
    ]

    rows: list[dict[str, Any]] = []
    for name, method, path, payload, n in tests:
        for i in range(1, n + 1):
            status, body, elapsed = http_json(method, path, payload)
            rows.append(
                {
                    "suite": "endpoint_latency",
                    "test": name,
                    "iter": i,
                    "status": status,
                    "ok": 200 <= status < 300,
                    "latency_ms": round(elapsed, 3),
                    "body": json.dumps(body, ensure_ascii=True),
                }
            )
    return rows


async def run_ws_relay_suite(iterations: int = 30) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    async with websockets.connect(WS_URL, open_timeout=5) as ws:
        for i in range(1, iterations + 1):
            marker = f"m{i}"
            status, _, _ = http_json(
                "POST",
                "/api/events",
                {
                    "channel": "relay_test",
                    "type": "command",
                    "payload": {"marker": marker, "cmd": "moveUp"},
                },
            )
            t0 = now_ms()
            recv_ok = False
            recv_latency = -1.0
            recv_channel = ""
            recv_type = ""
            recv_marker = ""
            if 200 <= status < 300:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=3)
                    recv_latency = now_ms() - t0
                    obj = json.loads(msg)
                    recv_channel = str(obj.get("channel", ""))
                    recv_type = str(obj.get("type", ""))
                    recv_marker = str(obj.get("payload", {}).get("marker", ""))
                    recv_ok = recv_channel == "relay_test" and recv_type == "command" and recv_marker == marker
                except Exception:
                    recv_ok = False

            rows.append(
                {
                    "suite": "ws_relay",
                    "test": "event_to_ws",
                    "iter": i,
                    "status": status,
                    "ok": recv_ok,
                    "latency_ms": round(recv_latency, 3),
                    "channel": recv_channel,
                    "type": recv_type,
                    "marker": recv_marker,
                }
            )
    return rows


def run_robustness_suite() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    # Invalid payload tests
    invalid_cases = [
        ("invalid_control_target", "POST", "/api/control", {"target": "bad", "action": "start"}, 422),
        ("invalid_control_action", "POST", "/api/control", {"target": "voice", "action": "bad"}, 422),
        ("empty_voice_text", "POST", "/api/ai/voice-plan", {"text": " "}, 422),
        ("invalid_event_schema", "POST", "/api/events", {"channel": "x"}, 422),
    ]
    for name, method, path, payload, expect in invalid_cases:
        status, body, elapsed = http_json(method, path, payload)
        rows.append(
            {
                "suite": "robustness",
                "test": name,
                "iter": 1,
                "status": status,
                "ok": status == expect,
                "latency_ms": round(elapsed, 3),
                "body": json.dumps(body, ensure_ascii=True),
            }
        )

    # Repeated start/stop for voice module to observe control path stability
    for i in range(1, 11):
        start_status, start_body, t_start = http_json("POST", "/api/control", {"target": "voice", "action": "start"})
        time.sleep(0.25)
        st_status, st_body, t_state = http_json("GET", "/api/control/status")
        stop_status, stop_body, t_stop = http_json("POST", "/api/control", {"target": "voice", "action": "stop"})

        start_ok = 200 <= start_status < 300
        status_ok = 200 <= st_status < 300
        stop_ok = 200 <= stop_status < 300

        running_flag = None
        if isinstance(st_body, dict):
            running_flag = bool(st_body.get("modules", {}).get("voice", False))

        rows.extend(
            [
                {
                    "suite": "robustness",
                    "test": "voice_start",
                    "iter": i,
                    "status": start_status,
                    "ok": start_ok,
                    "latency_ms": round(t_start, 3),
                    "body": json.dumps(start_body, ensure_ascii=True),
                },
                {
                    "suite": "robustness",
                    "test": "voice_running_probe",
                    "iter": i,
                    "status": st_status,
                    "ok": status_ok,
                    "latency_ms": round(t_state, 3),
                    "body": json.dumps({"voice_running": running_flag}, ensure_ascii=True),
                },
                {
                    "suite": "robustness",
                    "test": "voice_stop",
                    "iter": i,
                    "status": stop_status,
                    "ok": stop_ok,
                    "latency_ms": round(t_stop, 3),
                    "body": json.dumps(stop_body, ensure_ascii=True),
                },
            ]
        )

    # Final safeguard: ensure voice is stopped.
    http_json("POST", "/api/control", {"target": "voice", "action": "stop"})
    return rows


def write_csv(name: str, rows: list[dict[str, Any]]) -> Path:
    if not rows:
        raise ValueError(f"No rows for {name}")
    out = OUT_DIR / f"{name}.csv"
    fields = list(rows[0].keys())
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return out


def summarize_rows(rows: list[dict[str, Any]], group_key: str) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        buckets.setdefault(str(r[group_key]), []).append(r)

    summary: list[dict[str, Any]] = []
    for key, items in sorted(buckets.items()):
        lat = [float(i["latency_ms"]) for i in items if float(i["latency_ms"]) >= 0]
        ok_count = sum(1 for i in items if bool(i.get("ok")))
        total = len(items)
        summary.append(
            {
                "name": key,
                "total": total,
                "ok": ok_count,
                "success_rate": round(ok_count / total * 100.0, 2) if total else 0.0,
                "avg_latency_ms": round(mean(lat), 3) if lat else 0.0,
                "median_latency_ms": round(median(lat), 3) if lat else 0.0,
                "p95_latency_ms": round(percentile(lat, 0.95), 3) if lat else 0.0,
                "max_latency_ms": round(max(lat), 3) if lat else 0.0,
            }
        )
    return summary


def write_json(name: str, data: Any) -> Path:
    out = OUT_DIR / f"{name}.json"
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


def _bw_bar_style(count: int) -> list[str]:
    shades = ["#111111", "#555555", "#999999", "#DDDDDD"]
    return [shades[i % len(shades)] for i in range(count)]


def plot_endpoint_latency(summary: list[dict[str, Any]]) -> Path:
    labels = [x["name"] for x in summary]
    vals = [x["p95_latency_ms"] for x in summary]

    plt.figure(figsize=(8, 4.8))
    colors = _bw_bar_style(len(vals))
    bars = plt.bar(labels, vals, color=colors, edgecolor="black", linewidth=1.0)
    plt.title("Endpoint P95 Latency (ms)")
    plt.ylabel("Latency (ms)")
    plt.ylim(0, max(vals) * 1.25 if vals else 1)
    plt.grid(axis="y", linestyle="--", linewidth=0.6, color="black", alpha=0.3)
    for b, v in zip(bars, vals):
        plt.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.5, f"{v:.1f}", ha="center", va="bottom", fontsize=9)
    plt.tight_layout()
    out = OUT_DIR / "endpoint_p95_latency.png"
    plt.savefig(out, dpi=140)
    plt.close()
    return out


def plot_success_rate(summary: list[dict[str, Any]], title: str, out_name: str) -> Path:
    labels = [x["name"] for x in summary]
    vals = [x["success_rate"] for x in summary]

    plt.figure(figsize=(10, 5.2))
    colors = _bw_bar_style(len(vals))
    bars = plt.bar(labels, vals, color=colors, edgecolor="black", linewidth=1.0)
    plt.title(title)
    plt.ylabel("Success Rate (%)")
    plt.ylim(0, 105)
    plt.grid(axis="y", linestyle="--", linewidth=0.6, color="black", alpha=0.3)
    plt.xticks(rotation=25, ha="right")
    for b, v in zip(bars, vals):
        plt.text(b.get_x() + b.get_width() / 2, b.get_height() + 1, f"{v:.1f}%", ha="center", va="bottom", fontsize=8)
    plt.tight_layout()
    out = OUT_DIR / out_name
    plt.savefig(out, dpi=140)
    plt.close()
    return out


async def main() -> None:
    ensure_out_dir()

    endpoint_rows = run_endpoint_latency_suite()
    ws_rows = await run_ws_relay_suite(30)
    robust_rows = run_robustness_suite()

    write_csv("endpoint_latency_raw", endpoint_rows)
    write_csv("ws_relay_raw", ws_rows)
    write_csv("robustness_raw", robust_rows)

    endpoint_summary = summarize_rows(endpoint_rows, "test")
    ws_summary = summarize_rows(ws_rows, "test")
    robust_summary = summarize_rows(robust_rows, "test")

    plot_endpoint_latency(endpoint_summary)
    plot_success_rate(robust_summary, "Robustness Success Rate", "robustness_success_rate.png")

    all_summary = {
        "base_url": BASE_URL,
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "endpoint_summary": endpoint_summary,
        "ws_summary": ws_summary,
        "robustness_summary": robust_summary,
    }
    write_json("summary", all_summary)
    print(json.dumps(all_summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())