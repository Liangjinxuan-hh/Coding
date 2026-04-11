from __future__ import annotations

import argparse
import importlib
import json
import os

SYSTEM_PROMPT = (
    "你是滴动仪语音控制的意图识别器。"
    "只输出JSON，不要解释。"
    "JSON格式严格为: {\"command\":\"...\",\"confidence\":0.0,\"tts\":\"...\"}。"
    "command必须是以下之一: OPEN_EYES,CLOSE_EYES,OPEN_MOUTH,CLOSE_MOUTH,"
    "LEFT_ONLY,RIGHT_ONLY,DEFAULT,ALL_ON,ALL_OFF,RAINBOW,BLINK。"
)


def build_prompt(transcript: str) -> str:
    return f"{SYSTEM_PROMPT}\\n用户语音: {transcript}\\n输出:"


def build_chat_sample(tokenizer, transcript: str, answer_json: str) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"用户语音: {transcript}"},
        {"role": "assistant", "content": answer_json},
    ]
    if hasattr(tokenizer, "apply_chat_template"):
        return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
    return build_prompt(transcript) + answer_json


def main() -> None:
    parser = argparse.ArgumentParser(description="LoRA fine-tuning for voice command LLM")
    parser.add_argument("--model", default="Qwen/Qwen2.5-1.5B-Instruct", help="Base model ID or path")
    parser.add_argument("--resume-from-adapter", default="", help="Optional LoRA adapter directory to continue training from")
    parser.add_argument("--train-file", default="voice_llm/data/train_sample.jsonl", help="Training JSONL file")
    parser.add_argument("--output-dir", default="voice_llm/models/latest", help="Output model directory")
    parser.add_argument("--epochs", type=float, default=3.0, help="Training epochs")
    parser.add_argument("--lr", type=float, default=2e-4, help="Learning rate")
    parser.add_argument("--batch-size", type=int, default=2, help="Per-device train batch size")
    parser.add_argument("--grad-accum", type=int, default=8, help="Gradient accumulation steps")
    parser.add_argument("--max-seq-len", type=int, default=512, help="Max sequence length")
    args = parser.parse_args()

    load_dataset = importlib.import_module("datasets").load_dataset
    LoraConfig = importlib.import_module("peft").LoraConfig
    transformers = importlib.import_module("transformers")
    AutoModelForCausalLM = transformers.AutoModelForCausalLM
    AutoTokenizer = transformers.AutoTokenizer
    PeftModel = importlib.import_module("peft").PeftModel
    PeftConfig = importlib.import_module("peft").PeftConfig
    trl = importlib.import_module("trl")
    SFTConfig = trl.SFTConfig
    SFTTrainer = trl.SFTTrainer

    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(args.model, trust_remote_code=True)
    if args.resume_from_adapter:
        peft_cfg = PeftConfig.from_pretrained(args.resume_from_adapter)
        model = PeftModel.from_pretrained(model, args.resume_from_adapter).merge_and_unload()

    dataset = load_dataset("json", data_files=args.train_file, split="train")

    def _to_text(sample: dict) -> dict:
        answer = {
            "command": str(sample["command"]),
            "confidence": 0.95,
            "tts": str(sample.get("tts", "")),
        }
        answer_json = json.dumps(answer, ensure_ascii=False)
        chat_text = build_chat_sample(tokenizer, str(sample["transcript"]), answer_json)
        return {"text": chat_text + tokenizer.eos_token}

    train_dataset = dataset.map(_to_text, remove_columns=dataset.column_names)

    peft_config = LoraConfig(
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        task_type="CAUSAL_LM",
    )

    train_args = SFTConfig(
        output_dir=args.output_dir,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr,
        num_train_epochs=args.epochs,
        logging_steps=10,
        save_strategy="epoch",
        max_length=args.max_seq_len,
        lr_scheduler_type="cosine",
        warmup_ratio=0.03,
        bf16=False,
        fp16=False,
        report_to=[],
    )

    trainer = SFTTrainer(
        model=model,
        args=train_args,
        train_dataset=train_dataset,
        processing_class=tokenizer,
        peft_config=peft_config,
    )

    trainer.train()
    trainer.model.save_pretrained(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)

    print(f"Training finished. Model saved to: {os.path.abspath(args.output_dir)}")


if __name__ == "__main__":
    main()
