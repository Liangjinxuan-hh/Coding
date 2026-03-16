# 滴动仪 Web 基础交互面板说明

该页面用于快速在浏览器端演示“模型展示 + 按钮控制 + 语音/手势指令”三大核心功能，逻辑与 Unity 版本一致，可直接在 PC 上打开 `index.html` 进行体验。

## 功能概览

1. **模型展示区**：Three.js 渲染的简化滴动仪模型，支持鼠标拖拽旋转、滚轮缩放。
2. **控制按钮区**：底部五个按钮对应上移 / 下移 / 左转 / 右转 / 停止。
3. **状态反馈区**：右上角实时同步高度（cm）与角度（度），并输出中文状态文案。
4. **语音/手势桥接**：`window.DripCommandHub` 对外暴露 `send(command)` 和 `getState()`，可被语音模块、手势识别或 Python/硬件桥接调用。

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
3. 打开 Web 页面或 Unity WebView。页面会通过 `ws://127.0.0.1:5050/ws` 接收事件，更新“面部交互 / 手势交互”卡片，并把命令映射到 `DripCommandHub`。

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

### 3. Python 串口/语音桥接（示例）

```python
import serial
import time
import websocket

ser = serial.Serial("COM5", 9600)
ws = websocket.create_connection("ws://127.0.0.1:12345")

while True:
    cmd = ser.readline().decode("utf-8").strip()
    ws.send(cmd)  # 服务端收到后调用 window.DripCommandHub.send(cmd)
    time.sleep(0.05)
```

## 语音 / 手势指令映射

| 外部指令 | 页面动作 |
|----------|----------|
| 上移 / 上 / UP | moveUp |
| 下移 / 下 / DOWN | moveDown |
| 左转 / 左 / LEFT | rotateLeft |
| 右转 / 右 / RIGHT | rotateRight |
| 停止 / STOP / S | stop |

## 文件列表

- `index.html`：骨架结构与语音/手势说明区。
- `styles.css`：配色、布局、动效。
- `app.js`：Three.js 场景、运动逻辑、CommandHub。

如需将该页面嵌入现有 Python/Unity 流程，可通过 WebView2、Electron 或三方面板加载 `index.html`，同时把硬件指令转发到 `window.DripCommandHub`。需要进一步扩展（如真实 glTF 模型、串口直连、WebSocket 网桥）请告诉我。