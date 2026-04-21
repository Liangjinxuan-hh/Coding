# 滴动仪智能交互系统

面向滴定实验的人机协同控制项目，融合手势识别、面部识别、语音交互与 Web 可视化控制，支持通过统一事件中枢将多模态输入映射为设备动作。

## 功能概览

| 模块 | 功能 | 入口 |
| --- | --- | --- |
| Hand | MediaPipe 手势识别与事件上报 | Hand/main2.py |
| Face | 面部识别与表情交互 | Face/PythonProject/main.py |
| Voice | 语音识别、意图解析、串口/事件联动 | Voice/PythonProject/voice_module.py |
| Bridge | HTTP + WebSocket 事件中枢 | bridge/server.py |
| Web | Three.js 控制面板 | web/index.html |
| Unity（可选） | 仿真可视化脚本 | Unity/README_UnitySetup.md |

## 架构与文档

- 系统架构图与流程图：docs/architecture_design.md
- 语音模型训练与评测：Voice/PythonProject/voice_llm/README.md
- 语音实验结果：docs/results/voice_llm_paper_results.md
- 系统联调脚本：scripts/start_dripmotion.ps1

## 目录结构

```text
.
├─Hand/
├─Face/
├─Voice/
│  └─PythonProject/
│     ├─voice_module.py
│     └─voice_llm/
├─bridge/
├─web/
├─Unity/
├─scripts/
└─README.md
```

## 环境要求

- Windows 10/11
- Python 3.10+
- Node.js 18+（用于前端依赖）
- 可选：Unity 2021+

## 快速开始

1. 创建并激活虚拟环境

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. 安装依赖

```powershell
pip install -r Hand/requirements.txt
pip install -r Face/PythonProject/requirements.txt
pip install -r Voice/PythonProject/requirements.txt
pip install -r bridge/requirements.txt
```

3. 启动事件中枢

```powershell
Set-Location bridge
python server.py
```

4. 启动手势与面部模块（可选）

```powershell
Set-Location ../Hand
python main2.py
```

```powershell
Set-Location ../Face/PythonProject
python main.py
```

5. 启动语音模块

```powershell
Set-Location ../../Voice/PythonProject
python voice_module.py
```

6. 打开 Web 控制面板

- 直接在浏览器打开 web/index.html
- 或参考 web/README.md 配置本地服务

## 语音模块说明（已迁移到 Voice）

语音相关实现已统一迁移到 Voice/PythonProject：

- 语音主入口：Voice/PythonProject/voice_module.py
- 语音识别与命令分发：Voice/PythonProject/voice_control.py
- 运行时意图模型：Voice/PythonProject/voice_llm/runtime_intent.py
- 默认模型目录：Voice/PythonProject/voice_llm/models/v3

可通过环境变量控制语义解析：

- DRIP_VOICE_LLM_ENABLE
- DRIP_VOICE_LLM_MODEL_DIR
- DRIP_VOICE_LLM_MIN_CONFIDENCE
- DRIP_VOICE_LLM_MAX_NEW_TOKENS
- DRIP_VOICE_LLM_CPU_INT8

语音识别稳定模式（推荐离线）可通过 Vosk 本地模型启用：

- 安装依赖：`pip install -r Voice/PythonProject/requirements.txt`
- 下载并解压中文模型到 `Voice/PythonProject/models/`（如 `vosk-model-small-cn-0.22`）
- 可选环境变量：`DRIP_VOSK_MODEL_DIR` 指向模型目录
- 可选环境变量：`DRIP_VOICE_ONLINE_FALLBACK=1` 可在离线无结果时启用在线识别回退（默认关闭）

默认优先纯离线：Vosk 离线 -> PocketSphinx 离线；仅在显式开启 `DRIP_VOICE_ONLINE_FALLBACK=1` 时才回退 Google 在线识别。

## 标准动作命令

- moveUp
- moveDown
- rotateLeft
- rotateRight
- stop

## 相关说明

- 若语音模型不可用，系统将回退到关键词规则匹配。
- 即使串口暂不可用，语音/手势事件仍会通过桥接服务广播到前端，便于调试与联调。
