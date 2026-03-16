# 滴动仪智能交互系统

面向滴定实验的人机协同控制项目，融合手势/人脸识别、语音交互、Web 控制台、Unity 机械臂可视化以及硬件串口桥接，旨在通过多模态输入实现滴定仪的智能操控。

## 功能概览

| 模块 | 功能 | 入口 |
| --- | --- | --- |
| Hand | MediaPipe 手势识别、事件桥接 | `Hand/main2.py` |
| Face | 人脸/语音分析、串口命令发送、UI 反馈 | `Face/PythonProject/main.py` |
| Web | Three.js 交互面板、CommandHub 集成 | `web/index.html` (`web/README.md`) |
| Unity | 机械臂仿真控制脚本 | `Unity/*.cs` (`Unity/README_UnitySetup.md`) |
| Bridge | WebSocket/UDP/串口事件中枢 | `bridge/server.py` |
| Scripts | 组合启动脚本等 | `scripts/start_dripmotion.ps1` |

## 目录结构

```
.
├─web/                 # 前端控制面板（含 README）
├─Unity/               # Unity 场景脚本与配置说明
├─Hand/                # 手势识别 & Web 桥接
├─Face/                # 人脸/语音 & 硬件串口
├─bridge/              # 事件桥接服务
├─scripts/             # Powershell/批处理脚本
└─README.md            # 当前文件
```

## 环境要求

- Windows 10/11，PowerShell 7+
- Python 3.10+
- Node.js 18+（用于前端依赖）
- Unity 2021+（参见 `Unity/README_UnitySetup.md`）
- 可选：Arduino/串口控制硬件

## 快速开始

1. **克隆项目并创建虚拟环境**

   ```powershell
   git clone <repo-url> C:\Users\acer\Desktop\BS\Coding
   cd C:\Users\acer\Desktop\BS\Coding
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. **安装依赖**

   ```powershell
   pip install -r Hand/requirements.txt
   pip install -r Face/PythonProject/requirements.txt
   pip install -r bridge/requirements.txt
   ```

3. **启动事件桥接**

   ```powershell
   cd bridge
   python server.py
   ```

4. **启动手势识别**

   ```powershell
   cd ..\Hand
   python main2.py
   ```

5. **启动人脸/语音模块**

   ```powershell
   cd ..\Face\PythonProject
   python main.py
   ```

6. **打开控制界面**

   - Web：`cd ..\..\web` 后直接在浏览器打开 `index.html`，或按 `web/README.md` 配置 `DRIP_EVENT_ENDPOINT`、`DRIP_SERIAL_ENDPOINT` 后部署。
   - Unity：按照 `Unity/README_UnitySetup.md` 将 `CameraOrbit.cs`、`TopPartController.cs` 等脚本挂载到对应对象，运行场景并确认串口/UDP 设置与 Bridge 一致。

7. **可选自动化**：执行 `scripts/start_dripmotion.ps1` 按顺序拉起上述进程。

## 运行顺序建议

1. Bridge（统一事件总线）
2. Hand（手势事件 → Bridge）
3. Face（语音/表情/串口 → Bridge/硬件）
4. Web 或 Unity 前端（接收 Bridge 事件、发送控制指令）

## 配置项

- `web/README.md` 中描述的 `DRIP_EVENT_ENDPOINT`、`DRIP_SERIAL_ENDPOINT`
- `Face/PythonProject/config.json` / `config.py`：相机索引、串口号、语音关键词
- `Hand/web_bridge.py` 与 `Face/web_bridge.py`：统一的 WebSocket/HTTP 地址需与 Bridge 保持一致
- `Unity/GestureCommandBridge.cs`、`SerialCommandBridge.cs`：串口名、波特率、UDP 端口需同步

## 相关文档

- `web/README.md`：Three.js 控制面板说明
- `Unity/README_UnitySetup.md`：Unity 场景搭建与测试
- `bridge/README.md`：事件服务器协议与参数

## 待办

- 编写统一的 `.env` 或配置模板，避免多处硬编码
- 增加自动化测试/仿真脚本
- 将 Face 模块内重复的 `PythonProject/` 目录整合
- 在 README 中补充硬件接线示意与安全事项