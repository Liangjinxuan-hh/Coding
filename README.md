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