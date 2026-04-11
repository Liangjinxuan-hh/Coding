from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Optional

try:
    from .runtime_intent import predict_command as predict_llm_command
except ImportError:
    from runtime_intent import predict_command as predict_llm_command


KEYWORD_TO_COMMAND: Dict[str, str] = {
    "打开眼睛": "OPEN_EYES",
    "关闭眼睛": "CLOSE_EYES",
    "打开嘴巴": "OPEN_MOUTH",
    "张嘴": "OPEN_MOUTH",
    "关闭嘴巴": "CLOSE_MOUTH",
    "左眼": "LEFT_ONLY",
    "右眼": "RIGHT_ONLY",
    "默认": "DEFAULT",
    "恢复默认": "DEFAULT",
    "所有灯光": "ALL_ON",
    "全部点亮": "ALL_ON",
    "关闭灯光": "ALL_OFF",
    "彩虹": "RAINBOW",
    "七彩": "RAINBOW",
    "闪烁": "BLINK",
    "闪光": "BLINK",
    "天黑请闭眼": "ALL_OFF",
    "请睁眼": "ALL_ON",
    "请断案": "RAINBOW",
    "关闭": "DEFAULT",
}


def load_jsonl(path: Path) -> List[dict]:
    rows: List[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def keyword_predict(text: str) -> Optional[str]:
    if len(text) >= 80:
        return None
    for kw, cmd in KEYWORD_TO_COMMAND.items():
        if kw in text:
            return cmd
    return None


def final_predict(text: str) -> str:
    llm = predict_llm_command(text)
    if llm:
        return llm
    return keyword_predict(text) or "DEFAULT"


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate voice intent accuracy")
    parser.add_argument("--dataset", default="voice_llm/data/test_augmented.jsonl")
    parser.add_argument("--max-print-errors", type=int, default=20)
    args = parser.parse_args()

    samples = load_jsonl(Path(args.dataset))
    if not samples:
        print("No samples found.")
        return

    total = len(samples)
    correct = 0
    errors: List[dict] = []

    for row in samples:
        transcript = str(row.get("transcript", ""))
        expected = str(row.get("command", "DEFAULT"))
        pred = final_predict(transcript)
        if pred == expected:
            correct += 1
        else:
            errors.append({"text": transcript, "expected": expected, "pred": pred})

    acc = correct / total
    print(f"Total: {total}")
    print(f"Correct: {correct}")
    print(f"Accuracy: {acc:.4f}")

    if errors:
        print("\nTop mistakes:")
        for item in errors[: args.max_print_errors]:
            print(json.dumps(item, ensure_ascii=False))


if __name__ == "__main__":
    main()
