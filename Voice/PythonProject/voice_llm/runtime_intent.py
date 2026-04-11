from __future__ import annotations

import json
import importlib
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


_ALLOWED_COMMANDS = {
    "OPEN_EYES",
    "CLOSE_EYES",
    "OPEN_MOUTH",
    "CLOSE_MOUTH",
    "LEFT_ONLY",
    "RIGHT_ONLY",
    "DEFAULT",
    "ALL_ON",
    "ALL_OFF",
    "RAINBOW",
    "BLINK",
}

_ZH_HINT_TO_COMMAND = {
    "打开眼睛": "OPEN_EYES",
    "睁开眼睛": "OPEN_EYES",
    "闭眼": "CLOSE_EYES",
    "关闭眼睛": "CLOSE_EYES",
    "打开嘴巴": "OPEN_MOUTH",
    "张嘴": "OPEN_MOUTH",
    "闭嘴": "CLOSE_MOUTH",
    "关闭嘴巴": "CLOSE_MOUTH",
    "左眼": "LEFT_ONLY",
    "右眼": "RIGHT_ONLY",
    "默认": "DEFAULT",
    "全亮": "ALL_ON",
    "所有灯光": "ALL_ON",
    "关灯": "ALL_OFF",
    "灯全灭": "ALL_OFF",
    "彩虹": "RAINBOW",
    "七彩": "RAINBOW",
    "闪烁": "BLINK",
}

_PROMPT_TEMPLATE = (
    "你是滴动仪语音控制的意图识别器。"
    "只输出JSON，不要解释。"
    "JSON格式严格为: {{\"command\":\"...\",\"confidence\":0.0}}。"
    "command必须是以下之一: OPEN_EYES,CLOSE_EYES,OPEN_MOUTH,CLOSE_MOUTH,"
    "LEFT_ONLY,RIGHT_ONLY,DEFAULT,ALL_ON,ALL_OFF,RAINBOW,BLINK。"
    "如果无法判断，command输出DEFAULT，confidence<=0.4。\n"
    "用户语音: {text}\n"
    "输出:"
)


@dataclass
class IntentResult:
    command: str
    confidence: float


class _IntentRuntime:
    def __init__(self) -> None:
        self.enabled = os.getenv("DRIP_VOICE_LLM_ENABLE", "0") == "1"
        self.model_dir = os.getenv(
            "DRIP_VOICE_LLM_MODEL_DIR",
            os.path.join(os.path.dirname(__file__), "models", "v3"),
        )
        self.max_new_tokens = int(os.getenv("DRIP_VOICE_LLM_MAX_NEW_TOKENS", "48"))
        self.min_confidence = float(os.getenv("DRIP_VOICE_LLM_MIN_CONFIDENCE", "0.35"))
        self.cpu_int8 = os.getenv("DRIP_VOICE_LLM_CPU_INT8", "0") == "1"
        self._ready = False
        self._disabled_reason = ""
        self._tokenizer = None
        self._model = None

    def _lazy_load(self) -> bool:
        if self._ready:
            return True
        if not self.enabled:
            self._disabled_reason = "disabled"
            return False

        try:
            torch = importlib.import_module("torch")
            transformers = importlib.import_module("transformers")
            AutoModelForCausalLM = transformers.AutoModelForCausalLM
            AutoTokenizer = transformers.AutoTokenizer
            peft_mod = None
            try:
                peft_mod = importlib.import_module("peft")
            except Exception:
                peft_mod = None

            model_path = Path(self.model_dir)
            is_adapter = (model_path / "adapter_config.json").exists()

            self._tokenizer = AutoTokenizer.from_pretrained(self.model_dir, trust_remote_code=True)
            if is_adapter and peft_mod is not None:
                PeftConfig = peft_mod.PeftConfig
                PeftModel = peft_mod.PeftModel
                peft_cfg = PeftConfig.from_pretrained(self.model_dir)
                base_model = AutoModelForCausalLM.from_pretrained(
                    peft_cfg.base_model_name_or_path,
                    trust_remote_code=True,
                    torch_dtype=(torch.float16 if torch.cuda.is_available() else torch.float32),
                    device_map="auto" if torch.cuda.is_available() else None,
                )
                self._model = PeftModel.from_pretrained(base_model, self.model_dir)
            else:
                self._model = AutoModelForCausalLM.from_pretrained(
                    self.model_dir,
                    trust_remote_code=True,
                    torch_dtype=(torch.float16 if torch.cuda.is_available() else torch.float32),
                    device_map="auto" if torch.cuda.is_available() else None,
                )
            if not torch.cuda.is_available():
                self._model = self._model.to("cpu")
                if self.cpu_int8:
                    try:
                        self._model = torch.quantization.quantize_dynamic(
                            self._model, {torch.nn.Linear}, dtype=torch.qint8
                        )
                    except Exception:
                        pass
            self._ready = True
            return True
        except Exception as exc:
            self._disabled_reason = str(exc)
            return False

    @staticmethod
    def _parse_json(raw: str) -> Optional[IntentResult]:
        text = (raw or "").strip()
        if not text:
            return None

        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            return None

        try:
            data = json.loads(text[start : end + 1])
        except Exception:
            return None

        command = str(data.get("command", "")).strip().upper()
        if command not in _ALLOWED_COMMANDS:
            return None

        try:
            confidence = float(data.get("confidence", 0.0))
        except Exception:
            confidence = 0.0
        confidence = max(0.0, min(1.0, confidence))
        return IntentResult(command=command, confidence=confidence)

    @staticmethod
    def _parse_loose(raw: str) -> Optional[IntentResult]:
        text = (raw or "").upper()
        for cmd in _ALLOWED_COMMANDS:
            if cmd in text:
                return IntentResult(command=cmd, confidence=0.60)

        text_zh = raw or ""
        for zh, cmd in _ZH_HINT_TO_COMMAND.items():
            if zh in text_zh:
                return IntentResult(command=cmd, confidence=0.55)

        m = re.search(r'"confidence"\s*:\s*([0-9]+(?:\.[0-9]+)?)', raw or "")
        if m:
            conf = max(0.0, min(1.0, float(m.group(1))))
            for cmd in _ALLOWED_COMMANDS:
                if cmd in text:
                    return IntentResult(command=cmd, confidence=conf)
        return None

    def predict(self, text: str) -> Optional[IntentResult]:
        if not self._lazy_load():
            return None

        prompt = _PROMPT_TEMPLATE.format(text=text)
        try:
            torch = importlib.import_module("torch")

            inputs = self._tokenizer(prompt, return_tensors="pt")
            if torch.cuda.is_available():
                inputs = {k: v.to("cuda") for k, v in inputs.items()}

            with torch.no_grad():
                outputs = self._model.generate(
                    **inputs,
                    max_new_tokens=self.max_new_tokens,
                    do_sample=False,
                    temperature=0.0,
                    eos_token_id=self._tokenizer.eos_token_id,
                )
            input_len = int(inputs["input_ids"].shape[1])
            gen_tokens = outputs[0][input_len:]
            generated = self._tokenizer.decode(gen_tokens, skip_special_tokens=True)
            parsed = self._parse_json(generated)
            if parsed:
                return parsed
            return self._parse_loose(generated)
        except Exception:
            return None


_runtime = _IntentRuntime()


def predict_command(text: str, min_confidence: float = 0.55) -> Optional[str]:
    """Return a command inferred by local fine-tuned LLM, or None when unavailable."""
    result = _runtime.predict(text)
    if not result:
        return None
    threshold = min(min_confidence, _runtime.min_confidence)
    if result.confidence < threshold:
        return None
    return result.command
