from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Dict, List

FILLER_PREFIX = ["", "请", "麻烦", "帮我", "现在", "立刻", "马上", "直接"]
FILLER_SUFFIX = ["", "一下", "可以吗", "谢谢", "好吗", "吧"]

COMMAND_PARAPHRASES: Dict[str, List[str]] = {
    "OPEN_EYES": ["打开眼睛", "睁开眼睛", "请把眼睛睁开", "眼睛打开", "开眼", "现在睁开眼睛", "眼睛睁开一下", "睁眼", "睁开双眼", "把眼睛打开"],
    "CLOSE_EYES": ["关闭眼睛", "闭上眼睛", "闭眼", "眼睛关上", "把眼睛闭上", "闭眼一下", "立刻眼睛关上", "闭上双眼", "把眼睛闭起来", "合上眼睛"],
    "OPEN_MOUTH": ["打开嘴巴", "张嘴", "把嘴张开", "嘴巴打开", "张开嘴", "嘴巴打开一下", "现在张开嘴", "张口", "张开口", "嘴张开"],
    "CLOSE_MOUTH": ["关闭嘴巴", "闭嘴", "把嘴闭上", "嘴巴关上", "合上嘴", "现在闭嘴", "闭嘴一下", "合口", "闭上口", "把嘴合上"],
    "LEFT_ONLY": ["只亮左眼", "左眼模式", "切到左眼", "左眼", "保持左眼"],
    "RIGHT_ONLY": ["只亮右眼", "右眼模式", "切到右眼", "右眼", "保持右眼"],
    "DEFAULT": ["恢复默认", "默认模式", "回到默认", "重置", "关闭", "回到初始", "默认", "归位"],
    "ALL_ON": ["全部点亮", "所有灯光打开", "全亮", "开灯", "请睁眼", "把灯打开", "所有灯打开", "全部打开", "开全部灯", "打开所有灯"],
    "ALL_OFF": ["关闭灯光", "灯全灭", "全部关闭", "关灯", "天黑请闭眼", "请灯全灭一下", "把灯关掉", "灯关上", "所有灯关闭", "关闭所有灯"],
    "RAINBOW": ["彩虹模式", "七彩效果", "请断案", "切换彩虹", "七彩模式", "彩虹灯", "彩虹一下", "来点彩虹", "七彩灯效", "彩虹灯效"],
    "BLINK": ["闪烁", "闪光一下", "闪灯", "开始闪烁", "快速闪烁", "闪一下", "不停闪烁", "快速闪灯", "持续闪烁", "闪个灯"],
}


def load_jsonl(path: Path) -> List[dict]:
    items: List[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        items.append(json.loads(line))
    return items


def dump_jsonl(path: Path, items: List[dict]) -> None:
    lines = [json.dumps(item, ensure_ascii=False) for item in items]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def augment_one(record: dict, rng: random.Random, aug_per_seed: int) -> List[dict]:
    transcript = str(record.get("transcript", "")).strip()
    command = str(record.get("command", "")).strip()
    tts = str(record.get("tts", "")).strip()

    base = [{"transcript": transcript, "command": command, "tts": tts}]
    variants = COMMAND_PARAPHRASES.get(command, [transcript])

    for _ in range(aug_per_seed):
        core = rng.choice(variants)
        pref = rng.choice(FILLER_PREFIX)
        suff = rng.choice(FILLER_SUFFIX)
        text = f"{pref}{core}{suff}".strip()
        base.append({"transcript": text, "command": command, "tts": tts})

    return base


def build_dataset(seed_items: List[dict], aug_per_seed: int, seed: int) -> List[dict]:
    rng = random.Random(seed)
    out: List[dict] = []
    for item in seed_items:
        out.extend(augment_one(item, rng, aug_per_seed))
    rng.shuffle(out)
    return out


def split_train_test(items: List[dict], test_ratio: float, seed: int) -> tuple[List[dict], List[dict]]:
    rng = random.Random(seed)
    shuffled = list(items)
    rng.shuffle(shuffled)
    test_size = max(1, int(len(shuffled) * test_ratio))
    test_items = shuffled[:test_size]
    train_items = shuffled[test_size:]
    return train_items, test_items


def main() -> None:
    parser = argparse.ArgumentParser(description="Augment voice intent dataset from seed JSONL")
    parser.add_argument("--input", default="voice_llm/data/train_sample.jsonl")
    parser.add_argument("--train-out", default="voice_llm/data/train_augmented.jsonl")
    parser.add_argument("--test-out", default="voice_llm/data/test_augmented.jsonl")
    parser.add_argument("--aug-per-seed", type=int, default=20)
    parser.add_argument("--test-ratio", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    seed_items = load_jsonl(Path(args.input))
    all_items = build_dataset(seed_items, aug_per_seed=args.aug_per_seed, seed=args.seed)
    train_items, test_items = split_train_test(all_items, test_ratio=args.test_ratio, seed=args.seed)

    dump_jsonl(Path(args.train_out), train_items)
    dump_jsonl(Path(args.test_out), test_items)

    print(f"Seeds: {len(seed_items)}")
    print(f"Total after augmentation: {len(all_items)}")
    print(f"Train: {len(train_items)}")
    print(f"Test: {len(test_items)}")


if __name__ == "__main__":
    main()
