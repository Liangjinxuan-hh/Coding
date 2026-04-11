# Voice LLM (LoRA) for 语音交互

这个目录提供“可训练的大模型意图识别”能力，用于替代纯关键词匹配。

## 1. 安装训练依赖

在 `Voice/PythonProject` 目录执行：

```powershell
pip install -r voice_llm/requirements-train.txt
```


## 2. 准备训练数据

默认样例数据：`voice_llm/data/train_sample.jsonl`

每行一个 JSON，字段：

- `transcript`: 用户语音文本
- `command`: 系统命令（OPEN_EYES / CLOSE_EYES / ...）
- `tts`: 可选，执行反馈文本

可先做自动扩增，再训练：

```powershell
python voice_llm/augment_data.py --input voice_llm/data/train_sample.jsonl --train-out voice_llm/data/train_augmented.jsonl --test-out voice_llm/data/test_augmented.jsonl --aug-per-seed 20
```

## 3. 启动 LoRA 微调

```powershell
python voice_llm/train_lora.py --model Qwen/Qwen2.5-1.5B-Instruct --train-file voice_llm/data/train_augmented.jsonl --output-dir voice_llm/models/latest
```

说明：

- 推荐 NVIDIA GPU（>=12GB 显存）。
- 如果仅 CPU，可训练但会很慢。

## 4. 评估准确率

```powershell
$env:DRIP_VOICE_LLM_ENABLE = "1"
$env:DRIP_VOICE_LLM_MODEL_DIR = "C:\Users\acer\Desktop\BS\Coding\Voice\PythonProject\voice_llm\models\v3"
python voice_llm/evaluate_intent.py --dataset voice_llm/data/test_augmented.jsonl
```

## 5. 压测推理延迟

```powershell
python voice_llm/benchmark_infer.py --loops 100 --warmup 5
```

## 6. 一键流水线

```powershell
./voice_llm/run_pipeline.ps1 -BaseModel Qwen/Qwen2.5-1.5B-Instruct -AugPerSeed 20 -Epochs 3
```

## 7. 在语音模块启用推理

设置环境变量后启动 `voice_module.py`：

```powershell
$env:DRIP_VOICE_LLM_ENABLE = "1"
$env:DRIP_VOICE_LLM_MODEL_DIR = "C:\Users\acer\Desktop\BS\Coding\Voice\PythonProject\voice_llm\models\v3"
python voice_module.py
```

运行时策略：

- 优先使用本地微调模型识别命令；
- 若模型不可用或置信度不足，自动回退到原关键词规则；
- 因此不会破坏现有功能。

## 8. 当前推荐部署参数（v3）

在 CPU 环境下，建议使用以下参数：

```powershell
$env:DRIP_VOICE_LLM_ENABLE = "1"
$env:DRIP_VOICE_LLM_MODEL_DIR = "C:\Users\acer\Desktop\BS\Coding\Voice\PythonProject\voice_llm\models\v3"
$env:DRIP_VOICE_LLM_MIN_CONFIDENCE = "0.30"
$env:DRIP_VOICE_LLM_MAX_NEW_TOKENS = "8"
$env:DRIP_VOICE_LLM_CPU_INT8 = "0"
```

实测（test_augmented_v3，159 条）：

- 模型准确率：`92.45%`（147/159）
- 规则基线：`58.49%`（93/159）
- CPU 推理延迟：建议用同一脚本再跑一遍 `benchmark_infer` 记录

说明：

- 动态 INT8 在当前实现下会导致模型有效输出退化（结果接近回退规则），不建议开启。
