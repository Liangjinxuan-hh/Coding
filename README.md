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

### 表情识别故障排除

如果表情识别一直显示"平静"或无法正确识别表情，请使用诊断工具排查。

#### 快速诊断

1. **激活虚拟环境**
   ```powershell
   cd C:\Users\acer\Desktop\BS\Coding
   .\.venv312\Scripts\Activate.ps1
   ```

2. **运行诊断脚本**
   ```powershell
   python scripts/diagnose_expression.py
   ```

3. **观察输出**
   - 脚本每 10 帧输出一次诊断数据
   - 在摄像头前做出不同表情，观察参数变化
   - 关键参数：**MAR**（嘴部开合比）、**嘴宽比**、**嘴角抬升度**

#### 常见问题与解决方案

| 症状 | 原因 | 解决方案 |
|------|------|--------|
| 所有表情参数都很低 | 摄像头距离过远或光线不足 | 靠近摄像头 20-40cm，改善光线 |
| MAR 很高但嘴宽比很低 | 只做纵向张嘴，没有横向张开 | 做出更"夸张"的表情 |
| 参数正常变化但仍显示"平静" | 识别阈值设置过严格 | 调整 config.py 中的 MOUTH_THRESHOLD |

#### 调整灵敏度

编辑 `Face/PythonProject/config.py`，修改全局灵敏度：

```python
# 原值
'MOUTH_THRESHOLD': 0.13,

# 降低以提高灵敏度（更容易触发表情识别）
'MOUTH_THRESHOLD': 0.10,
```

修改后需要重启 Face 模块才能生效。

#### 启用实时诊断日志

编辑 `Face/PythonProject/face_analysis.py`，找到 `detect_face_expression` 函数内的这一行（约第 92 行）：

```python
# 诊断输出（临时用于调试）
# print(f"[表情诊断] MAR={mar:.4f} 嘴宽比={mouth_width_ratio:.4f} 嘴角抬升={corner_lift:.6f}")
```

移除注释符号以启用实时输出：

```python
print(f"[表情诊断] MAR={mar:.4f} 嘴宽比={mouth_width_ratio:.4f} 嘴角抬升={corner_lift:.6f}")
```

重启 Face 模块后，工作窗口将每帧输出诊断数据。

#### 详细诊断指南

详见 `scripts/DIAGNOSE_EXPRESSION_GUIDE.md` 获取完整的诊断流程和参数解释。

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

## 3D 模型接入与运动控制方案

目标：将真实滴动仪 3D 模型接入当前系统，并让 Web 页面或 Unity 场景中的模型跟随面部、手势、语音或按钮指令运动。

### 1. 模型拆分规则

建议将模型拆成至少两个可独立控制的节点：

- `Base`：底座、机身、固定支架，保持不动。
- `TopPart`：上表面核心运动部件，负责上移、下移、左转、右转。

如果后续需要更细粒度动作，可以继续拆分：

- `PipetteHead`：滴定头或执行头。
- `ArmJointA` / `ArmJointB`：多段机械臂关节。
- `Indicator`：灯环、状态灯、提示组件。

命名建议统一使用英文节点名，避免 Web 和 Unity 两边各写一套映射。

### 2. 推荐文件格式

- Web 端优先使用 glTF / GLB。
   原因：Three.js 原生支持好、材质和层级保留更完整、加载成本低。
- Unity 端优先使用 FBX 或 GLB。
   原因：便于在 Inspector 中直接挂脚本和绑定子节点。

推荐输出：

- `web/models/dripmotion.glb`
- Unity 工程内导入同一份 FBX 或 GLB

### 3. Web 端接入方案

当前 Web 页面中的 3D 模型是代码内生成的简化几何体，入口在 `web/client-main.js`。

当前仓库已经落地了基础加载逻辑：页面启动时会自动尝试加载 `web/models/dripmotion.glb`，如果文件不存在或找不到 `TopPart` 节点，就自动回退到内置演示模型，不会影响整页运行。

建议改造方式：

1. 保留当前控制状态机：
    - `applyCommand`
    - `stepPhysics`
    - `motionState`

2. 将“程序生成的简化模型”替换为“加载外部 GLB 模型”：
    - 用 `GLTFLoader` 加载 `web/models/dripmotion.glb`
    - 加载完成后通过名称找到 `TopPart`
    - 将 `TopPart` 赋给当前控制对象引用

3. 将运动逻辑继续绑定到 `TopPart`：
    - 上下移动：修改 `TopPart.position.y`
    - 左右旋转：修改 `TopPart.rotation.z` 或 `rotation.y`

4. 其余输入源不需要改：
    - 页面按钮仍然调用 `applyCommand`
    - Bridge 收到面部/手势/语音事件后，前端仍然映射到 `applyCommand`

也就是说，模型替换只影响“显示层”，不影响“控制层”。

### 4. Unity 端接入方案

Unity 端建议继续沿用现有脚本：

- `Unity/TopPartController.cs`
- `Unity/SerialCommandBridge.cs`
- `Unity/GestureCommandBridge.cs`
- `Unity/CameraOrbit.cs`

具体做法：

1. 将模型导入 Unity。
2. 找到模型中的 `TopPart` 节点。
3. 把 `TopPartController.cs` 挂到 `TopPart` 或它的父控制空物体上。
4. 把按钮、状态文本、串口桥、手势桥分别绑定到现有 Inspector 字段。

这样可以保证 Web 和 Unity 两边都围绕同一套动作语义：

- `moveUp`
- `moveDown`
- `rotateLeft`
- `rotateRight`
- `stop`

### 5. 运动映射建议

建议先实现一套最小动作映射：

| 指令 | 模型动作 | 建议实现 |
| --- | --- | --- |
| `moveUp` | 上表面部件上移 | `position.y += speed * dt` |
| `moveDown` | 上表面部件下移 | `position.y -= speed * dt` |
| `rotateLeft` | 上表面部件左转 | `rotation.z += speed * dt` |
| `rotateRight` | 上表面部件右转 | `rotation.z -= speed * dt` |
| `stop` | 停止当前动作 | 速度归零 |

参数建议：

- Web 演示层：
   - 位移范围：0.35 到 0.90
   - 旋转速度：60 度/秒
- Unity 演示层：
   - 用 Inspector 暴露 `moveSpeed` 和 `rotateSpeed`
   - 先做视觉联调，再按真实设备比例微调

### 6. 系统链路建议

推荐采用下面这条链路：

1. Face / Hand / Voice 模块识别用户动作。
2. Bridge 广播事件与模块状态。
3. Web 或 Unity 前端接收事件。
4. 前端把识别结果映射成标准动作命令。
5. 3D 模型中的 `TopPart` 根据命令执行运动。

这条链路的优点：

- 识别模块和 3D 渲染模块彻底解耦。
- 更换模型文件时，不需要改识别逻辑。
- 从 Web 切到 Unity 时，控制协议基本不变。

### 7. 落地实施顺序

推荐按以下顺序实施：

1. 用 Blender 或建模软件把模型整理成 `Base + TopPart` 两层结构。
2. 导出 `dripmotion.glb` 并放入 `web/models/`。
3. 在 `web/client-main.js` 中引入 `GLTFLoader`，替换当前简化几何体。
4. 验证页面按钮是否能驱动模型运动。
5. 验证 Face / Hand / Voice 模块的识别指令能否驱动同一个模型。
6. 将同一套节点命名迁移到 Unity，复用 `TopPartController.cs`。

### 8. 当前代码中最适合接入的位置

- Web 模型显示与运动：`web/client-main.js`
- Web 页面结构：`web/index.html`
- Unity 控制：`Unity/TopPartController.cs`
- 后端模块启停：`bridge/server.py`
- 面部识别事件：`Face/PythonProject/main.py`
- 手势识别事件：`Hand/main2.py`
- 语音识别事件：`Face/PythonProject/voice_module.py`

### 9. 建议的最终目标

建议最终形成两套前端表现层：

- Web 端：用于快速联调、演示、局域网控制。
- Unity 端：用于高保真模型展示、机械结构演示、答辩或汇报场景。

二者共用同一套指令语义和 Bridge 事件总线，这样后续无论换模型、换识别模块还是换硬件，都不会重写整套控制逻辑。

## 相关文档

- `web/README.md`：Three.js 控制面板说明
- `Unity/README_UnitySetup.md`：Unity 场景搭建与测试
- `bridge/README.md`：事件服务器协议与参数

## 待办

- 编写统一的 `.env` 或配置模板，避免多处硬编码
- 增加自动化测试/仿真脚本
- 将 Face 模块内重复的 `PythonProject/` 目录整合
- 在 README 中补充硬件接线示意与安全事项