from __future__ import annotations

import argparse
import statistics
import time
from typing import List

try:
    from .runtime_intent import predict_command as predict_llm_command
except ImportError:
    from runtime_intent import predict_command as predict_llm_command

TEST_QUERIES = [
    "打开眼睛",
    "请把眼睛睁开",
    "闭眼",
    "打开嘴巴",
    "闭嘴",
    "左眼模式",
    "右眼模式",
    "恢复默认",
    "全部点亮",
    "关闭灯光",
    "彩虹模式",
    "闪烁",
    "请断案",
]


def run_once(text: str) -> str:
    cmd = predict_llm_command(text)
    return cmd or "DEFAULT"


def percentile(values: List[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    idx = min(len(s) - 1, max(0, int(round((p / 100.0) * (len(s) - 1)))))
    return s[idx]


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark local voice intent inference latency")
    parser.add_argument("--loops", type=int, default=100)
    parser.add_argument("--warmup", type=int, default=5)
    args = parser.parse_args()

    for _ in range(args.warmup):
        for text in TEST_QUERIES:
            run_once(text)

    lat_ms: List[float] = []
    start = time.perf_counter()
    for _ in range(args.loops):
        for text in TEST_QUERIES:
            t0 = time.perf_counter()
            run_once(text)
            t1 = time.perf_counter()
            lat_ms.append((t1 - t0) * 1000.0)
    end = time.perf_counter()

    total_calls = args.loops * len(TEST_QUERIES)
    elapsed = end - start
    qps = (total_calls / elapsed) if elapsed > 0 else 0.0

    print(f"Calls: {total_calls}")
    print(f"ElapsedSec: {elapsed:.3f}")
    print(f"QPS: {qps:.2f}")
    print(f"MeanMs: {statistics.mean(lat_ms):.2f}")
    print(f"P50Ms: {percentile(lat_ms, 50):.2f}")
    print(f"P95Ms: {percentile(lat_ms, 95):.2f}")
    print(f"P99Ms: {percentile(lat_ms, 99):.2f}")


if __name__ == "__main__":
    main()
