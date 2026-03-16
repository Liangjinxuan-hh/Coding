"""
Blender --background 模式运行的转换脚本：
读取 model_999.glb，导出为 model_999.fbx
用法（自动调用，无需手动执行）：
  blender.exe --background --python scripts/glb_to_fbx.py
"""
import bpy
import sys
import os

# 路径相对于工作目录（由调用方传入 --）
argv = sys.argv
# 解析 -- 之后的参数（blender 占用前面的参数）
try:
    after_dash = argv[argv.index("--") + 1:]
    src = after_dash[0]
    dst = after_dash[1]
except (ValueError, IndexError):
    # 默认路径（从脚本所在目录推断）
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(script_dir)
    src = os.path.join(root, "web", "models", "model_999.glb")
    dst = os.path.join(root, "web", "models", "model_999.fbx")

print(f"[转换] 源文件: {src}")
print(f"[转换] 目标文件: {dst}")

# 清空默认场景
bpy.ops.wm.read_factory_settings(use_empty=True)

# 导入 GLB
bpy.ops.import_scene.gltf(filepath=src)
print(f"[转换] GLB 导入完成，场景对象数: {len(bpy.data.objects)}")

# 打印节点列表（供调试用）
for obj in bpy.data.objects:
    print(f"  对象: {obj.name}  类型: {obj.type}")

# 全选后导出 FBX
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.fbx(
    filepath=dst,
    use_selection=True,
    apply_scale_options='FBX_SCALE_NONE',
    axis_forward='-Z',
    axis_up='Y',
    use_mesh_modifiers=True,
    add_leaf_bones=False,
    path_mode='COPY',
    embed_textures=True,
)
print(f"[转换] FBX 导出完成: {dst}")
