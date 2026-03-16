import json, struct

GLB_PATH = r"web/models/dripmotion.glb"

with open(GLB_PATH, "rb") as f:
    f.read(12)  # magic + version + length
    json_len = struct.unpack("<I", f.read(4))[0]
    f.read(4)   # chunk type
    json_data = json.loads(f.read(json_len))
    f.read(8)   # bin chunk header
    bin_data = f.read()

meshes = json_data.get("meshes", [])
nodes = json_data.get("nodes", [])
accessors = json_data.get("accessors", [])
buffer_views = json_data.get("bufferViews", [])

mesh_to_node = {}
for node in nodes:
    if "mesh" in node:
        mesh_to_node[node["mesh"]] = node.get("name", f"node_mesh{node['mesh']}")

print(f"{'#':<4} {'Node Name':<36} {'MinX':>8} {'MaxX':>8} {'MinY':>8} {'MaxY':>8} {'MinZ':>8} {'MaxZ':>8} | {'SzX':>7} {'SzY':>7} {'SzZ':>7}")
print("-"*130)

for mi, mesh in enumerate(meshes):
    node_name = mesh_to_node.get(mi, f"<unnamed {mi}>")
    primitives = mesh.get("primitives", [])
    if not primitives:
        continue
    prim = primitives[0]
    attrs = prim.get("attributes", {})
    if "POSITION" not in attrs:
        continue
    acc = accessors[attrs["POSITION"]]
    bv_idx = acc.get("bufferView")
    if bv_idx is None:
        continue
    bv = buffer_views[bv_idx]
    byte_offset = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
    count = acc["count"]
    xs, ys, zs = [], [], []
    for i in range(count):
        off = byte_offset + i * 12
        x, y, z = struct.unpack_from("<fff", bin_data, off)
        xs.append(x); ys.append(y); zs.append(z)
    mnx, mxx = min(xs), max(xs)
    mny, mxy = min(ys), max(ys)
    mnz, mxz = min(zs), max(zs)
    print(f"{mi:<4} {node_name:<36} {mnx:>8.1f} {mxx:>8.1f} {mny:>8.1f} {mxy:>8.1f} {mnz:>8.1f} {mxz:>8.1f} | {mxx-mnx:>7.1f} {mxy-mny:>7.1f} {mxz-mnz:>7.1f}")
