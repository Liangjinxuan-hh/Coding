"""
将 GLB 中错误命名的 Part_11~15_RingPatternA~E 改为 Part_11~15_BodyPatternA~E
圆环真正的组成节点只有 Part_09_RingBand / Part_10_RingDiscInner / Part_16_RingDiscOuter
"""
import json, struct, shutil, os

SRC = r"web/models/dripmotion.glb"
DST = r"web/models/dripmotion.glb"
BACKUP = r"web/models/dripmotion.named3.bak.glb"

RENAME_MAP = {
    "Part_11_RingPatternA": "Part_11_BodyPatternA",
    "Part_12_RingPatternB": "Part_12_BodyPatternB",
    "Part_13_RingPatternC": "Part_13_BodyPatternC",
    "Part_14_RingPatternD": "Part_14_BodyPatternD",
    "Part_15_RingPatternE": "Part_15_BodyPatternE",
}

with open(SRC, "rb") as f:
    raw = f.read()

# parse header
magic = raw[:4]
version = struct.unpack_from("<I", raw, 4)[0]
length = struct.unpack_from("<I", raw, 8)[0]
json_chunk_len = struct.unpack_from("<I", raw, 12)[0]
json_chunk_type = struct.unpack_from("<I", raw, 16)[0]

json_start = 20
json_bytes = raw[json_start:json_start + json_chunk_len]
rest = raw[json_start + json_chunk_len:]

gltf = json.loads(json_bytes.decode("utf-8"))

changes = 0
for node in gltf.get("nodes", []):
    old_name = node.get("name", "")
    if old_name in RENAME_MAP:
        node["name"] = RENAME_MAP[old_name]
        print(f"  {old_name}  →  {RENAME_MAP[old_name]}")
        changes += 1

for mesh in gltf.get("meshes", []):
    old_name = mesh.get("name", "")
    if old_name in RENAME_MAP:
        mesh["name"] = RENAME_MAP[old_name]
        changes += 1

if changes == 0:
    print("未找到需要重命名的节点，请检查当前节点名称")
else:
    print(f"\n共修改 {changes} 处")
    shutil.copy2(SRC, BACKUP)
    print(f"备份: {BACKUP}")

    new_json_bytes = json.dumps(gltf, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    # GLB JSON chunk must be 4-byte aligned, pad with spaces
    pad = (4 - len(new_json_bytes) % 4) % 4
    new_json_bytes += b" " * pad

    new_json_chunk_len = struct.pack("<I", len(new_json_bytes))
    new_json_chunk_type = struct.pack("<I", json_chunk_type)
    new_total_len = struct.pack("<I", 12 + 8 + len(new_json_bytes) + len(rest))

    new_raw = (
        raw[:8]
        + new_total_len
        + new_json_chunk_len
        + new_json_chunk_type
        + new_json_bytes
        + rest
    )

    with open(DST, "wb") as f:
        f.write(new_raw)
    print(f"保存: {DST}")
