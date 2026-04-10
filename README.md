# 滴动仪智能交互系统

面向滴定实验的人机协同控制项目，融合手势/人脸识别、语音交互与 Web 控制台（可选扩展 Unity 可视化），旨在通过多模态输入实现滴定仪的智能操控。

## 功能概览

| 模块 | 功能 | 入口 |
| --- | --- | --- |
| Hand | MediaPipe 手势识别、事件桥接 | `Hand/main2.py` |
| Face | 人脸/语音分析、交互状态反馈 | `Face/PythonProject/main.py` |
| Web | Three.js 交互面板、CommandHub 集成 | `web/index.html` (`web/README.md`) |
| Unity（可选） | 机械臂仿真控制脚本 | `Unity/*.cs` (`Unity/README_UnitySetup.md`) |
| Bridge | HTTP/WebSocket 事件中枢 | `bridge/server.py` |
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

### 特殊手势模式（新增）

Web 页面“手势交互”卡片新增按钮：**特殊手势：关闭/开启**。

- 仅在 Hand 模块运行中可点击。
- 关闭时：沿用原有“选环 + 方向动作”控制链路。
- 开启时：进入“特殊手势节奏模式”，**禁用选环与方向动作**，改为“一个手势对应一段节奏（全环联动）”。

#### 特殊手势识别条件（当前实现）

以下规则来自 `Hand/main2.py` 的当前判定逻辑（含防抖与冷却）：

- 发布策略：同一特殊手势连续稳定检测 2 帧后触发事件，触发冷却约 0.7 秒。
- **✌（VICTORY）**：食指与中指伸直，无名指和小拇指弯曲。
- **6（SIX）**：拇指与小拇指伸直，食指/中指/无名指弯曲（类似 shaka）。
- **8（EIGHT）**：拇指与食指伸直，中指/无名指/小拇指弯曲（手枪形态）。
- **OK**：拇指与食指捏合，且中指/无名指/小拇指伸直。
- **比心（LOVE_HEART）**：拇指与食指靠拢，且其余三指收拢。
- **爱心（HEART）**：
   - 主规则：拇指与食指靠拢，食指/中指伸直，无名指/小拇指弯曲；
   - 兜底规则：拇指与小拇指明显接近，且食指与中指不同时伸直。

> 说明：特殊手势判定使用归一化距离与手指伸展状态组合，阈值已在代码中按手掌尺度归一化，适配不同手大小和拍摄距离。

#### 特殊手势节奏编排（当前实现）

特殊手势模式开启后，系统根据识别到的特殊手势切换全环节奏。每种手势对应一套参数：

- `speed`：节奏时间缩放（越大越快）
- `amp`：上下振幅系数
- `rotateDeg`：基础旋转角速度（度/秒）
- `phases`：RingA/B/C/D 相位差
- `spinDir`：各环旋转方向（1 左转 / -1 右转）
- `pairWeight`：AC 与 BD 对向耦合权重

实现上的公共规则：

- 四个环始终联动，不再接受单环选中。
- 每帧将高度偏移与旋转偏移直接写入 RingA~D 的运动状态。
- 轨迹由“基波 + 脉冲 + 成对反相波”混合形成，不同手势主要通过参数差异体现风格。

当前参数集（简表）：

| 手势 | speed | amp | rotateDeg | 编排特征 |
| --- | --- | --- | --- | --- |
| OK | 1.55 | 0.50 | 24 | AB 同向、CD 反向，节奏中速偏稳 |
| ✌ | 2.10 | 0.62 | 34 | AB 与 CD 两组强对向，节奏更强烈 |
| 比心 | 1.35 | 0.48 | 16 | 旋转较柔和，相位错开明显 |
| 爱心 | 1.25 | 0.46 | 14 | 四环同向为主，连贯平滑 |
| 6 | 1.95 | 0.56 | 32 | 对向耦合较高，起伏明显 |
| 8 | 2.35 | 0.64 | 38 | 速度与幅度最高，表现最激进 |

#### 手势卡片状态展示

手势卡片中会同步显示：

- 当前模式（选环动作模式 / 特殊手势节奏模式）
- 当前特殊手势
- 当前行为
- 左手选环手势、左手当前环、左手特殊手势、右手食指标向等明细

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
├─Unity/               # Unity 场景脚本与配置说明（可选扩展）
├─Hand/                # 手势识别 & Web 桥接
├─Face/                # 人脸/语音交互模块
├─bridge/              # 事件桥接服务
├─scripts/             # Powershell/批处理脚本
└─README.md            # 当前文件
```

## 环境要求

- Windows 10/11，PowerShell 7+
- Python 3.10+
- Node.js 18+（用于前端依赖）
- 可选：Unity 2021+（参见 `Unity/README_UnitySetup.md`）

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

   - Web（默认）：`cd ..\..\web` 后直接在浏览器打开 `index.html`，或按 `web/README.md` 配置 `DRIP_EVENT_ENDPOINT`、`DRIP_SERIAL_ENDPOINT` 后部署。
   - Unity（可选）：按照 `Unity/README_UnitySetup.md` 将 `CameraOrbit.cs`、`TopPartController.cs` 等脚本挂载到对应对象，运行场景并确认串口/UDP 设置与 Bridge 一致。

7. **可选自动化**：执行 `scripts/start_dripmotion.ps1` 按顺序拉起上述进程。

## 运行顺序建议

1. Bridge（统一事件总线）
2. Hand（手势事件 → Bridge）
3. Face（语音/表情 → Bridge）
4. Web 前端（默认，接收 Bridge 事件、发送控制指令）
5. 可选：Unity 前端联调（作为扩展可视化终端）

## 配置项

- `web/README.md` 中描述的 `DRIP_EVENT_ENDPOINT`、`DRIP_SERIAL_ENDPOINT`
- `Face/PythonProject/config.json` / `config.py`：相机索引、语音关键词
- `Hand/web_bridge.py` 与 `Face/web_bridge.py`：统一的 WebSocket/HTTP 地址需与 Bridge 保持一致
- 可选：`Unity/GestureCommandBridge.cs`、`SerialCommandBridge.cs`：串口名、波特率、UDP 端口需同步

## 3D 模型与控制现状

### Web 端

- 入口：`web/client-main.js`
- 页面：`web/index.html`
- 模型：优先加载 `web/models/dripmotion.glb`
- 回退机制：当模型文件缺失或未找到目标节点时，自动回退到内置演示模型

### Unity 端（可选）

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
3. Web 前端接收事件并映射标准指令（可选扩展到 Unity）
4. 模型节点执行运动

## 相关文档

- `web/README.md`：Three.js 控制面板说明
- `Unity/README_UnitySetup.md`：Unity 场景搭建与测试（可选）
- `bridge/README.md`：事件服务器协议与参数