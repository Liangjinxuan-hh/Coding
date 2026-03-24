# web/models 使用说明

把你的 3D 模型文件放到这个目录下，文件名固定为：

- chaifen.fbx（当前默认加载）

也支持备用文件：

- dripmotion.glb

## 推荐格式

- Web 页面：GLB
- Unity：FBX 或 GLB

## 节点命名要求

模型里至少保留两个节点：

- Base：底座和固定结构
- TopPart：需要被页面控制上下移动和左右旋转的部件

页面会优先查找这些名字：

- TopPart
- top_part
- top-part
- top

如果找不到 TopPart，页面会自动回退到内置演示模型。

## 推荐建模/导出软件

- Blender：推荐，免费，导出 GLB 最方便
- 3ds Max：可用，导出 FBX 后再转 GLB
- Maya：可用，适合已有角色/机械建模流程
- Fusion 360 / SolidWorks：适合机械结构建模，通常先导出 FBX/OBJ，再进 Blender 整理后导出 GLB

## Blender 导出建议

1. 保证可动部件单独命名为 TopPart。
2. 统一应用缩放和旋转。
3. 原点尽量放在模型中心或底座中心。
4. 导出时选择 glTF 2.0，格式选 GLB。
5. 尽量勾选包含材质和纹理。

## 当前页面行为

- 页面启动时优先尝试加载 web/models/chaifen.fbx。
- 若失败，会继续尝试其他候选模型（包括 dripmotion.glb）。
- 加载成功后，按钮和 Face/Hand/Voice 指令会驱动 TopPart。
- 加载失败时，页面继续使用内置演示模型，不会白屏。
