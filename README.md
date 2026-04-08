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

## 架构与流程图

- [系统架构设计图与业务流程图](docs/architecture_design.md)

## 手势识别指南

### 手部手势 (Hand Gesture A/B/C/D)

摄像头前做出以下手势比划，系统自动识别并切换对应的环(Ring)进行控制：

| 手势 | 比划方式 | 含义 | 控制对象 |
| --- | --- | --- | --- |
| **A** | 大拇指竖起，其他四指握拳 | 选择/激活 RingA | 环A (Primary Ring A) |
| **B** | 大拇指握入拳内，其他四指展开 | 选择/激活 RingB | 环B (Primary Ring B) |
| **C** | 五指形成 C 字形开口，大拇指与食指间留有空隙 | 选择/激活 RingC | 环C (Primary Ring C) |
| **D** | 五指紧握成完全拳头状 | 选择/激活 RingD | 环D (Primary Ring D) |
| **✋ 停止** | 左右手食指同时竖起并靠近相触 | 停止当前环的所有动作 | 紧急停止 (Emergency Stop) |

选环后，配合以下手部动作控制选中的环：

| 手部动作 | 含义 | 模型反应 |
| --- | --- | --- |
| **手腕向上移动** | 垂直上升指令 | 模型上表面上升 |
| **手腕向下移动** | 垂直下降指令 | 模型上表面下降 |
| **手腕向左扫动** | 原地左旋指令 | 模型上表面左转 |
| **手腕向右扫动** | 原地右旋指令 | 模型上表面右转 |

### 左右眼组合识别 (Eye Pattern A/B/C/D)

面部模块同时支持通过左右眼开合状态选环，无需手势即可切换控制对象：

| 眼型 | 状态说明 | 含义 | 控制对象 |
| --- | --- | --- | --- |
| **A** | 左眼睁开，右眼闭合 | 选择/激活 RingA | 环A (Primary Ring A) |
| **B** | 左眼闭合，右眼睁开 | 选择/激活 RingB | 环B (Primary Ring B) |
| **C** | 双眼都睁开 | 选择/激活 RingC | 环C (Primary Ring C) |
| **D** | 双眼都闭合 | 选择/激活 RingD | 环D (Primary Ring D) |

眼型选环后，配合以下面部动作控制选中的环：

| 面部动作 | 含义 | 模型反应 |
| --- | --- | --- |
| **抬头** | 纵向上升指令 | 模型上表面上升 |
| **低头** | 纵向下降指令 | 模型上表面下降 |
| **左转头** | 原地左旋指令 | 模型上表面左转 |
| **右转头** | 原地右旋指令 | 模型上表面右转 |

> **说明**：手势和眼型识别相互独立，各有独立的识别状态机，可以切换使用。

## 面部交互设置与调试

### 表情控制功能

Web 页面上的"表情控制"按钮允许用户开启/关闭基于面部表情的节奏调制。启用此功能后，系统会根据识别的表情（微笑、惊讶、愤怒等）自动调整选中环的运动速度。

#### 表情识别映射

系统支持 5 种表情类型与节奏的映射：

| 表情 | 识别条件 | 节奏倍数 | 旋转倍数 |
|------|--------|--------|--------|
| 抿嘴微笑 | 嘴角上扬，嘴部轻微张开 | 0.65× | 0.75× |
| 咧嘴大笑 | 嘴部张开明显，嘴角横向扩张 | 1.5× | 1.8× |
| 惊讶 | 嘴部张开很大，嘴角不水平张开 | 1.8× | 2.0× |
| 愤怒 | 嘴角明显下垂，嘴部紧闭 | 0.4× | 0.6× |
| 平静 | 无上述明显特征 | 1.0× | 1.0× |

#### 圆环节奏编排（当前实现）

- 抿嘴微笑：AC 环左转，BD 环右转；上下节奏为 A→B→C→D 依次上移，再 D→C→B→A 依次下降（一个循环）。
- 咧嘴大笑：AC 环右转，BD 环左转；上下节奏为 AC 同时上移且 BD 同时下移，然后反向（一个循环）。
- 惊讶：AB 环左转，CD 环右转；上下节奏为 AD 同时上移且 BC 同时下移，然后反向（一个循环）。
- 愤怒：ABCD 环同时左转；上下节奏为 AC 同时上移且 BD 同时下移，然后反向（一个循环）。
- 旋转换向约束：每个环在表情模式下必须先累计完整旋转一圈（360°）后，才允许切换旋转方向。

#### 表情控制按钮状态

Web 页面上的"表情控制"按钮有以下三种状态：

- **灰色（禁用）**：Face 模块未启动，点击无效
- **暗红色**：Face 模块运行中，但表情控制已禁用（当前不使用表情调节速度）
- **绿色亮色**：表情控制已启用，系统正在使用识别的表情调节运动速度

### 表情识别诊断

如需排查表情识别准确性，请直接参考 `scripts/DIAGNOSE_EXPRESSION_GUIDE.md`。该文档包含诊断脚本使用方式、参数解释与阈值调优建议。

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

## 3D 模型与控制现状

### Web 端

- 入口：`web/client-main.js`
- 页面：`web/index.html`
- 模型：优先加载 `web/models/dripmotion.glb`
- 回退机制：当模型文件缺失或未找到目标节点时，自动回退到内置演示模型

### Unity 端

- 关键脚本：`Unity/TopPartController.cs`、`Unity/SerialCommandBridge.cs`、`Unity/GestureCommandBridge.cs`
- 负责接收同一套控制语义并驱动场景对象

### 标准控制指令

- `moveUp`
- `moveDown`
- `rotateLeft`
- `rotateRight`
- `stop`

### 系统链路

1. Face / Hand / Voice 识别输入
2. Bridge 统一广播事件
3. Web / Unity 前端接收事件并映射标准指令
4. 模型节点执行运动

## 相关文档

- `web/README.md`：Three.js 控制面板说明
- `Unity/README_UnitySetup.md`：Unity 场景搭建与测试
- `bridge/README.md`：事件服务器协议与参数