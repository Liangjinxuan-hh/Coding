# 滴动仪 Web 基础交互面板说明

该页面用于快速在浏览器端演示“模型展示 + 按钮控制 + 语音/手势指令”三大核心功能，可直接在 PC 上打开 `index.html` 进行体验。

## 功能概览

1. **模型展示区**：Three.js 渲染的 chaifen.fbx 模型，支持鼠标拖拽旋转、滚轮缩放。
2. **控制按钮区**：底部按钮对应圆环上移 / 下移 / 左转 / 右转 / 花朵打开 / 花朵闭合 / 停止。
3. **状态反馈区**：右上角实时同步高度（cm）与角度（度），并输出中文状态文案。
4. **手势/语音桥接**：`window.DripCommandHub` 对外暴露 `send(command)` 和 `getState()`，可被语音模块、手势识别或 Python 事件桥接调用。

## 模型分层架构

模型分为 **6 个模块**，统一用 chaifen.fbx 加载：

| 模块 | 功能 | 可控性 |
|------|------|--------|
| **RingA** | 内环 | 上下移动 + 左右旋转 |
| **RingB** | 次内环 | 上下移动 + 左右旋转 |
| **RingC** | 次外环 | 上下移动 + 左右旋转 |
| **RingD** | 外环 | 上下移动 + 左右旋转 |
| **Flower** | 中心花朵 | 打开/闭合（缩放） |
| **Component** | 配件 | 不参与运动 |

### 圆环运动特性

- **同步控制**：RingA ~ RingD 作为一个运动组，同时响应相同指令
- **上下移动**：竖向平移 0 ~ 0.55 单位，速度 0.25 单位/秒
- **左右旋转**：水平旋转，速度 60°/秒
- **并行执行**：上下移动和左右旋转可同时进行（不互斥）
- **行程限制**：到达上下限时仅停止升降，旋转可继续

### 花朵特性

- **原地动作**：花朵保持中心位置不变
- **开合方式**：打开时缩放放大，闭合时恢复原大小（目前禁用中，待完善）

## 按钮指令映射

| 按钮文案 | 指令代码 | 作用 |
|----------|----------|------|
| 上移 | `moveUp` | RingA~D 向上平移 |
| 下移 | `moveDown` | RingA~D 向下平移 |
| 左转 | `rotateLeft` | RingA~D 逆时针旋转 |
| 右转 | `rotateRight` | RingA~D 顺时针旋转 |
| 花朵打开 | `flowerOpen` | Flower 放大 |
| 花朵闭合 | `flowerClose` | Flower 缩小 |
| 停止 | `stop` | 将所有圆环复位到初始位置（双手五指张开） |

## 手势指令映射

**Hand 模块** 可识别以下手势并自动转换为控制指令：

| 手势 | 转换指令 | 对应动作 |
|------|----------|----------|
| (moveUp) | `moveUp` | 圆环上升 |
| (moveDown) | `moveDown` | 圆环下降 |
| (rotateLeft) | `rotateLeft` | 圆环左转 |
| (rotateRight) | `rotateRight` | 圆环右转 |
| (flowerOpen/openFlower) | `flowerOpen` | 花朵打开 |
| (flowerClose/closeFlower) | `flowerClose` | 花朵闭合 |
| (stop) | `stop` | 复位所有圆环（双手五指张开） |

> 手势识别使用 MediaPipe Hand，具体手势定义见 `Hand/main2.py`

## 面部识别指令映射

**Face 模块** 可识别以下表情并自动转换为控制指令：

| 面部状态 | 转换指令 | 对应动作 |
|----------|----------|----------|
| 向左看（LOOK_LEFT） | `rotateLeft` | 圆环左转 |
| 向右看（LOOK_RIGHT） | `rotateRight` | 圆环右转 |
| 睁眼（OPEN_EYES） | `moveUp` | 圆环上升 |
| 闭眼（CLOSE_EYES） | `moveDown` | 圆环下降 |
| 张嘴（OPEN_MOUTH） | `moveUp` | 圆环上升 |
| 闭嘴/默认状态 | `stop` | 停止 |

> 面部识别使用 MediaPipe Face Mesh，具体状态检测见 `Face/PythonProject/main.py`

## 运行方式

无需构建工具，直接在桌面双击 `web/index.html` 即可。如果需要本地 Web 服务器（解决某些浏览器对 module 的限制），可在 VS Code 中运行：

```bash
# 任选开发服务器
npx serve web
# 或
python -m http.server 8080 --directory web
```

## 与 Hand / Face 模块联动

1. 安装桥接依赖并启动 FastAPI 事件桥：

    ```bash
    pip install -r bridge/requirements.txt
    uvicorn bridge.server:app --reload --port 5050
    ```

2. 运行面部和手势脚本（同原来流程）。它们会自动把状态、命令推送到 `http://127.0.0.1:5050/api/events`。
3. 打开 Web 页面。页面会通过 `ws://127.0.0.1:5050/ws` 接收事件，更新“面部交互 / 手势交互”卡片，并把命令映射到 `DripCommandHub`。

> 如果桥接端口或地址需要修改，可设置 `DRIP_EVENT_ENDPOINT` 环境变量再运行 Python 检测脚本。

## CommandHub 接入示例

### 1. 浏览器控制台

```javascript
window.DripCommandHub.send("上移");
window.DripCommandHub.send("停止");
```

### 2. postMessage（适用于 WebView 或嵌入式壳）

```javascript
window.postMessage({ type: "dd-command", payload: "左转" });
```

### 3. Python 事件桥接（示例）

```python
import time
import websocket

ws = websocket.create_connection("ws://127.0.0.1:5050/ws")

commands = ["moveUp", "rotateLeft", "stop"]

for cmd in commands:
    ws.send(cmd)
    time.sleep(0.05)

ws.close()
```

## 文件列表

- `index.html`：骨架结构与交互面板。
- `styles.css`：配色、布局、动效。
- `client-main.js`：Three.js 场景、运动逻辑、命令桥接。
- `models/chaifen.fbx`：当前加载的 3D 模型（可替换为其他 FBX/GLB）。

## 常见问题

### Q: 如何快速测试按钮和控制逻辑？
A: 刷新页面打开 `http://127.0.0.1:8081`，直接点击底部按钮即可测试圆环和花朵动作。

### Q: 如何替换模型？
A: 将新模型（FBX 或 GLB）放入 `web/models/` 目录，修改 `client-main.js` 中的 `MODEL_CANDIDATES` 列表，把新模型文件名加入即可自动加载。

### Q: 为什么手势/面部识别没有响应？
A: 确保 Bridge 服务（`bridge.server`）正在运行，且 Hand/Face 模块已启动。检查浏览器控制台是否有连接错误。

如需进一步扩展（如自定义手势、新增动作），请参考 Hand 和 Face 模块的文档。