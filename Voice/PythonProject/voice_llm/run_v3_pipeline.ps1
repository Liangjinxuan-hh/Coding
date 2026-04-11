param(
    [string]$BaseModel = "Qwen/Qwen2.5-0.5B-Instruct",
    [int]$AugPerSeed = 40,
    [double]$Epochs = 1.0
)

$ErrorActionPreference = "Stop"

Write-Host "[1/4] Build v3 augmented dataset"
python voice_llm/augment_data.py --input voice_llm/data/train_sample.jsonl --train-out voice_llm/data/train_augmented_v3.jsonl --test-out voice_llm/data/test_augmented_v3.jsonl --aug-per-seed $AugPerSeed

Write-Host "[2/4] Train v3 LoRA model"
python voice_llm/train_lora.py --model $BaseModel --train-file voice_llm/data/train_augmented_v3.jsonl --output-dir voice_llm/models/v3 --epochs $Epochs --batch-size 2 --grad-accum 8 --max-seq-len 384

Write-Host "[3/4] Evaluate v3"
$env:DRIP_VOICE_LLM_ENABLE = "1"
$env:DRIP_VOICE_LLM_MODEL_DIR = (Resolve-Path "voice_llm/models/v3").Path
$env:DRIP_VOICE_LLM_MIN_CONFIDENCE = "0.30"
$env:DRIP_VOICE_LLM_MAX_NEW_TOKENS = "8"
python -m voice_llm.evaluate_intent --dataset voice_llm/data/test_augmented_v3.jsonl

Write-Host "[4/4] Benchmark v3"
python -m voice_llm.benchmark_infer --loops 30 --warmup 3

Write-Host "V3 pipeline completed."
