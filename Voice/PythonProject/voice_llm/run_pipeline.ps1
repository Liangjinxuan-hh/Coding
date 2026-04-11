param(
    [string]$BaseModel = "Qwen/Qwen2.5-1.5B-Instruct",
    [int]$AugPerSeed = 20,
    [double]$Epochs = 3.0
)

$ErrorActionPreference = "Stop"

Write-Host "[1/5] Install training dependencies"
pip install -r voice_llm/requirements-train.txt

Write-Host "[2/5] Build augmented dataset"
python voice_llm/augment_data.py --input voice_llm/data/train_sample.jsonl --train-out voice_llm/data/train_augmented.jsonl --test-out voice_llm/data/test_augmented.jsonl --aug-per-seed $AugPerSeed

Write-Host "[3/5] Train LoRA model"
python voice_llm/train_lora.py --model $BaseModel --train-file voice_llm/data/train_augmented.jsonl --output-dir voice_llm/models/latest --epochs $Epochs

Write-Host "[4/5] Evaluate intent accuracy"
$env:DRIP_VOICE_LLM_ENABLE = "1"
$env:DRIP_VOICE_LLM_MODEL_DIR = (Resolve-Path "voice_llm/models/latest").Path
python -m voice_llm.evaluate_intent --dataset voice_llm/data/test_augmented.jsonl

Write-Host "[5/5] Benchmark inference latency"
python -m voice_llm.benchmark_infer --loops 60 --warmup 5

Write-Host "Pipeline completed."
