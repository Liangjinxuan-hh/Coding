import json
import struct
import sys

path = sys.argv[1] if len(sys.argv) > 1 else r"web/models/ImageToStl.com_999.glb"

with open(path, "rb") as f:
    magic = f.read(4)
    if magic != b"glTF":
        raise SystemExit("not glb")
    version = struct.unpack("<I", f.read(4))[0]
    _length = struct.unpack("<I", f.read(4))[0]
    jlen = struct.unpack("<I", f.read(4))[0]
    jtype = struct.unpack("<I", f.read(4))[0]
    jdata = f.read(jlen)

doc = json.loads(jdata.decode("utf-8"))

print("version", version)
print("asset", doc.get("asset"))
print("scene", doc.get("scene"))
print("scenes", len(doc.get("scenes", [])))
print("nodes", len(doc.get("nodes", [])))
print("meshes", len(doc.get("meshes", [])))
print("materials", len(doc.get("materials", [])))
print("extensionsUsed", doc.get("extensionsUsed", []))
print("extensionsRequired", doc.get("extensionsRequired", []))

nodes = doc.get("nodes", [])
meshes = doc.get("meshes", [])
print("\nfirst 20 node names:")
for i, n in enumerate(nodes[:20]):
    print(i, n.get("name"), "mesh=" + str(n.get("mesh")), "children=" + str(n.get("children")))

print("\nfirst 10 mesh names:")
for i, m in enumerate(meshes[:10]):
    print(i, m.get("name"), "prims=" + str(len(m.get("primitives", []))))
