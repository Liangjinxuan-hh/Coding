import json
import struct
import sys

path = sys.argv[1] if len(sys.argv) > 1 else r"web/models/model_999.glb"
with open(path, "rb") as f:
    magic = f.read(4)
    if magic != b"glTF":
        raise SystemExit("not glb")
    _version = struct.unpack("<I", f.read(4))[0]
    _len = struct.unpack("<I", f.read(4))[0]
    jlen = struct.unpack("<I", f.read(4))[0]
    _jtype = struct.unpack("<I", f.read(4))[0]
    jdoc = json.loads(f.read(jlen).decode("utf-8"))

accessors = jdoc.get("accessors", [])
mode_name = {
    0: "POINTS",
    1: "LINES",
    2: "LINE_LOOP",
    3: "LINE_STRIP",
    4: "TRIANGLES",
    5: "TRIANGLE_STRIP",
    6: "TRIANGLE_FAN",
}

print("meshes:", len(jdoc.get("meshes", [])))
for mi, mesh in enumerate(jdoc.get("meshes", [])):
    prims = mesh.get("primitives", [])
    print(f"mesh[{mi}] name={mesh.get('name')} prims={len(prims)}")
    for pi, prim in enumerate(prims):
        mode = prim.get("mode", 4)
        attrs = prim.get("attributes", {})
        pos_acc = attrs.get("POSITION")
        pos_cnt = accessors[pos_acc]["count"] if pos_acc is not None else None
        idx_acc = prim.get("indices")
        idx_cnt = accessors[idx_acc]["count"] if idx_acc is not None else None
        print(f"  prim[{pi}] mode={mode}({mode_name.get(mode,'?')}) pos_count={pos_cnt} idx_count={idx_cnt} attrs={list(attrs.keys())}")
