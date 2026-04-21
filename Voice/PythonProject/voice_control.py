import threading
import time
import importlib.util
import json
import re
import difflib
from pathlib import Path
import speech_recognition as sr
import pygame
import os
import pyttsx3  # 新增TTS库导入
try:
    from .config import CONFIG, wake_word_detected, last_command_time
    from .serial_comms import send_command
except ImportError:
    from config import CONFIG, wake_word_detected, last_command_time
    from serial_comms import send_command

try:
    from .voice_llm.runtime_intent import predict_command as predict_llm_command
except Exception:
    try:
        from voice_llm.runtime_intent import predict_command as predict_llm_command
    except Exception:
        predict_llm_command = None

try:
    import vosk
except Exception:
    vosk = None

# 初始化音频系统
try:
    pygame.mixer.init()
except pygame.error as e:
    print(f"Pygame音频初始化失败: {e}。音效功能将禁用。")

# 加载提示音效
wake_sound = None
command_sound = None
try:
    # 假设音效文件名为 wake.wav 和 command.wav
    if os.path.exists("wake.wav"):
        wake_sound = pygame.mixer.Sound("wake.wav")
    if os.path.exists("command.wav"):
        command_sound = pygame.mixer.Sound("command.wav")
except pygame.error as e:
    print(f"音效加载失败: {e}")
    wake_sound = None
    command_sound = None

# 语音状态变量（使用列表实现引用传递）
V_WAKE_DETECTED = [wake_word_detected]
V_LAST_CMD_TIME = [last_command_time]
V_CURRENT_VOICE_STATUS = ["等待唤醒..."]
V_LAST_SPEECH = [""]  # 存储最后识别的文本
V_VOICE_AVAIL = [True]


def _resolve_vosk_model_dir() -> str | None:
    env_dir = os.getenv("DRIP_VOSK_MODEL_DIR", "").strip()
    candidates = []
    if env_dir:
        candidates.append(Path(env_dir))

    base_dir = Path(__file__).resolve().parent
    candidates.extend(
        [
            base_dir / "models" / "vosk-model-small-cn-0.22",
            base_dir / "models" / "vosk-model-cn-0.22",
            base_dir / "models" / "vosk-model-small-zh-cn",
            base_dir / "models" / "vosk-model-cn",
        ]
    )

    for model_dir in candidates:
        if model_dir.exists() and model_dir.is_dir():
            return str(model_dir)
    return None


def _normalize_text_for_match(text: str) -> str:
    # 仅保留中英文和数字，降低标点/空格对唤醒词匹配的影响。
    return re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]+", "", (text or "").lower())


def _wake_word_detected_in_text(text: str, wake_word: str) -> bool:
    normalized_text = _normalize_text_for_match(text)
    normalized_wake = _normalize_text_for_match(wake_word)
    if not normalized_text or not normalized_wake:
        return False
    if normalized_wake in normalized_text:
        return True

    # 对短文本做轻量模糊匹配，容忍少量识别误差。
    window = max(2, len(normalized_wake))
    for idx in range(0, max(1, len(normalized_text) - window + 1)):
        seg = normalized_text[idx : idx + window]
        if difflib.SequenceMatcher(a=seg, b=normalized_wake).ratio() >= 0.67:
            return True
    return False


def _normalize_transcript(text: str) -> str:
    return _normalize_text_for_match(text)


def _contains_like_keyword(text: str, keyword: str, threshold: float = 0.72) -> bool:
    norm_text = _normalize_text_for_match(text)
    norm_kw = _normalize_text_for_match(keyword)
    if not norm_text or not norm_kw:
        return False
    if norm_kw in norm_text:
        return True
    win = len(norm_kw)
    if win <= 1:
        return False
    for i in range(0, max(1, len(norm_text) - win + 1)):
        seg = norm_text[i : i + win]
        if difflib.SequenceMatcher(a=seg, b=norm_kw).ratio() >= threshold:
            return True
    return False


def _extract_latest_clause(text: str) -> str:
    if not text:
        return ""
    parts = [p.strip() for p in re.split(r"[，,。；;、\|]+|然后|再|并且|并|和", text) if p.strip()]
    return parts[-1] if parts else text.strip()


def _build_vosk_grammar() -> str:
    phrases = [
        "狄仁杰",
        "打开眼睛",
        "关闭眼睛",
        "打开嘴巴",
        "张嘴",
        "关闭嘴巴",
        "左眼",
        "右眼",
        "默认",
        "所有灯光",
        "全部点亮",
        "关闭灯光",
        "彩虹",
        "七彩",
        "闪烁",
        "闪光",
        "天黑请闭眼",
        "请睁眼",
        "请断案",
        "关闭",
        "A环上移",
        "A环下移",
        "A环左转",
        "A环右转",
        "A环停止",
        "B环上移",
        "B环下移",
        "B环左转",
        "B环右转",
        "B环停止",
        "C环上移",
        "C环下移",
        "C环左转",
        "C环右转",
        "C环停止",
        "D环上移",
        "D环下移",
        "D环左转",
        "D环右转",
        "D环停止",
        "[unk]",
    ]
    return json.dumps(phrases, ensure_ascii=False)


def speak_text(text):
    """独立的TTS语音播放函数（解决循环依赖）"""

    def run_tts():
        try:
            # 使用 pyttsx3 进行语音合成
            engine = pyttsx3.init()
            # 设置语速
            engine.setProperty('rate', 150)
            # 尝试设置中文语音
            voices = engine.getProperty('voices')
            chinese_voice = next((voice for voice in voices if 'chinese' in voice.name.lower()), None)
            if chinese_voice:
                engine.setProperty('voice', chinese_voice.id)

            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            print(f"TTS播放失败: {e}")

    # 避免阻塞主循环，在独立线程中运行 TTS
    threading.Thread(target=run_tts, daemon=True).start()


def voice_recognition_thread():
    """语音识别线程主函数"""
    global V_VOICE_AVAIL, V_CURRENT_VOICE_STATUS, V_LAST_SPEECH

    recognizer = sr.Recognizer()

    # 检查 PyAudio 与麦克风可用性，避免把所有错误都误报成“未安装PyAudio”。
    try:
        import pyaudio  # noqa: F401
    except Exception as e:
        V_VOICE_AVAIL[0] = False
        V_CURRENT_VOICE_STATUS[0] = "语音未启用（PyAudio不可用）"
        print(f"语音模块不可用（PyAudio）: {e}")
        return

    try:
        microphone = sr.Microphone()
        sr.Microphone.list_microphone_names()
        source = microphone
    except OSError as e:
        V_VOICE_AVAIL[0] = False
        V_CURRENT_VOICE_STATUS[0] = "语音未启用（麦克风不可用）"
        print(f"语音模块不可用（麦克风）: {e}")
        return
    except Exception as e:
        V_VOICE_AVAIL[0] = False
        V_CURRENT_VOICE_STATUS[0] = "语音未启用（音频初始化失败）"
        print(f"语音模块不可用（初始化）: {e}")
        return

    # 优化识别参数
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold = 0.35
    recognizer.non_speaking_duration = 0.2
    recognizer.phrase_threshold = 0.1
    CHINESE_LANGUAGE_MODEL = "zh-CN"
    online_error_log_cooldown_sec = 8.0
    last_online_error_log_at = 0.0
    online_fail_streak = 0
    network_status_latched = False
    vosk_recognizer = None
    last_processed_norm_text = ""
    last_processed_at = 0.0
    duplicate_cooldown_sec = 1.2
    min_text_len = 2
    idle_listen_timeout = 1.2
    idle_phrase_limit = 1.6
    awake_listen_timeout = 1.2
    awake_phrase_limit = 2.6
    online_fallback_when_offline_enabled = os.getenv("DRIP_VOICE_ONLINE_FALLBACK", "0").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    vosk_use_grammar = os.getenv("DRIP_VOSK_USE_GRAMMAR", "0").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    if vosk is not None:
        model_dir = _resolve_vosk_model_dir()
        if model_dir:
            try:
                vosk.SetLogLevel(-1)
                vosk_model = vosk.Model(model_dir)
                if vosk_use_grammar:
                    vosk_recognizer = vosk.KaldiRecognizer(vosk_model, 16000, _build_vosk_grammar())
                    print("Vosk语法约束已启用")
                else:
                    vosk_recognizer = vosk.KaldiRecognizer(vosk_model, 16000)
                print(f"Vosk离线识别已启用，模型目录: {model_dir}")
            except Exception as e:
                print(f"Vosk初始化失败，将回退其他识别方式: {e}")
        else:
            print("未找到Vosk中文模型目录，将回退其他识别方式。")
    else:
        print("未安装vosk，将回退其他识别方式。")

    sphinx_available = bool(importlib.util.find_spec("pocketsphinx"))
    if not sphinx_available:
        print("离线识别不可用（未安装 pocketsphinx），将尝试在线识别。")

    WAKE_WORD_RESPONSE = "我在"  # 唤醒反馈

    # 启动时做一次环境噪声校准，避免每轮校准带来显著延迟。
    try:
        with source as s:
            recognizer.adjust_for_ambient_noise(s, duration=0.3)
    except Exception as e:
        print(f"环境噪声校准失败，继续运行: {e}")

    print("语音识别线程启动")
    while V_VOICE_AVAIL[0]:
        try:
            with source as s:
                command_timeout_base = CONFIG['COMMAND_TIMEOUT']  # 基准超时时间
                # 实际超时时间为 60 秒 (1分钟)
                command_timeout_real = command_timeout_base * 6

                # 状态判断：当前是否处于唤醒状态
                is_awake = V_WAKE_DETECTED[0] and (time.time() - V_LAST_CMD_TIME[0] < command_timeout_real)

                audio = None

                # 根据唤醒状态调整监听策略
                if is_awake:
                    V_CURRENT_VOICE_STATUS[0] = f"已唤醒，等待命令...（{command_timeout_real}秒超时）"
                    audio = recognizer.listen(s, timeout=awake_listen_timeout, phrase_time_limit=awake_phrase_limit)
                else:
                    V_CURRENT_VOICE_STATUS[0] = f"等待唤醒词: {CONFIG['WAKE_WORD']}"
                    audio = recognizer.listen(s, timeout=idle_listen_timeout, phrase_time_limit=idle_phrase_limit)

                text = ""
                if audio:
                    # 优先使用 Vosk 离线识别，其次 PocketSphinx，最后在线识别。
                    if vosk_recognizer is not None:
                        try:
                            raw_pcm = audio.get_raw_data(convert_rate=16000, convert_width=2)
                            accepted = vosk_recognizer.AcceptWaveform(raw_pcm)
                            if accepted:
                                result_json = vosk_recognizer.Result()
                            else:
                                partial_json = vosk_recognizer.PartialResult()
                                partial_obj = json.loads(partial_json or "{}")
                                partial_text = (partial_obj.get("partial") or "").strip()
                                if partial_text:
                                    result_json = partial_json
                                else:
                                    result_json = vosk_recognizer.FinalResult()
                            result = json.loads(result_json or "{}")
                            text = (result.get("text") or result.get("partial") or "").strip()
                            if text:
                                print(f"Vosk离线识别结果: {text}")
                        except Exception as e:
                            print(f"Vosk识别失败，将回退其他识别方式: {e}")

                    if not text and sphinx_available:
                        try:
                            text = recognizer.recognize_sphinx(audio, language=CHINESE_LANGUAGE_MODEL)
                            print(f"离线识别结果: {text}")
                        except sr.UnknownValueError:
                            pass
                        except sr.RequestError as e:
                            print(f"PocketSphinx错误: {e}，尝试在线识别...")

                    allow_online_fallback = (vosk_recognizer is None and not sphinx_available) or online_fallback_when_offline_enabled
                    if not text and allow_online_fallback:
                        try:
                            text = recognizer.recognize_google(audio, language="zh-CN")
                            print(f"在线识别结果: {text}")
                            if online_fail_streak > 0:
                                online_fail_streak = 0
                                if network_status_latched:
                                    V_CURRENT_VOICE_STATUS[0] = "语音识别网络已恢复"
                                    network_status_latched = False
                        except sr.UnknownValueError:
                            pass
                        except sr.RequestError as online_err:
                            online_fail_streak += 1
                            now_ts = time.time()
                            if now_ts - last_online_error_log_at > online_error_log_cooldown_sec:
                                print(f"在线识别不可用（网络异常），继续监听: {online_err}")
                                # 降低状态抖动：仅连续失败时才更新为网络异常。
                                if online_fail_streak >= 2:
                                    V_CURRENT_VOICE_STATUS[0] = "语音识别网络不可用，请检查网络/代理"
                                    network_status_latched = True
                                last_online_error_log_at = now_ts

                    if text:
                        text = _extract_latest_clause(text.strip())
                        norm_text = _normalize_transcript(text)
                        if len(norm_text) < min_text_len:
                            continue

                        now_ts = time.time()
                        if norm_text == last_processed_norm_text and (now_ts - last_processed_at) < duplicate_cooldown_sec:
                            # 同一句短时间重复识别时忽略，避免界面闪烁和重复触发。
                            continue

                        last_processed_norm_text = norm_text
                        last_processed_at = now_ts
                        V_LAST_SPEECH[0] = text
                        print(f"最终识别内容: {text}")

                # 处理识别结果
                if not text:
                    continue  # 没有识别内容则跳过命令处理

                # 唤醒词检测
                if not is_awake:
                    if _wake_word_detected_in_text(text, CONFIG['WAKE_WORD']):
                        V_WAKE_DETECTED[0] = True
                        V_LAST_CMD_TIME[0] = time.time()
                        V_CURRENT_VOICE_STATUS[0] = "唤醒成功，请说命令"

                        # 唤醒反馈
                        speak_text(WAKE_WORD_RESPONSE)
                        if wake_sound:
                            wake_sound.play()
                else:
                    # 命令映射表
                    command_map = {
                        # 基础命令
                        "打开眼睛": {"cmd": "OPEN_EYES", "tts": "已执行打开眼睛"},
                        "关闭眼睛": {"cmd": "CLOSE_EYES", "tts": "已执行关闭眼睛"},
                        "打开嘴巴": {"cmd": "OPEN_MOUTH", "tts": "已执行打开嘴巴"},
                        "张嘴": {"cmd": "OPEN_MOUTH", "tts": "已执行打开嘴巴"},
                        "关闭嘴巴": {"cmd": "CLOSE_MOUTH", "tts": "已执行关闭嘴巴"},
                        "左眼": {"cmd": "LEFT_ONLY", "tts": "已执行左眼"},
                        "右眼": {"cmd": "RIGHT_ONLY", "tts": "已执行右眼"},
                        "默认": {"cmd": "DEFAULT", "tts": "已执行默认"},

                        # 特殊命令 (灯光/模式)
                        "所有灯光": {"cmd": "ALL_ON", "tts": "已执行所有灯光"},
                        "全部点亮": {"cmd": "ALL_ON", "tts": "已执行全部点亮"},
                        "关闭灯光": {"cmd": "ALL_OFF", "tts": "已执行关闭灯光"},
                        "彩虹": {"cmd": "RAINBOW", "tts": "已执行彩虹"},
                        "七彩": {"cmd": "RAINBOW", "tts": "已执行彩虹"},
                        "闪烁": {"cmd": "BLINK", "tts": "已执行闪烁"},
                        "闪光": {"cmd": "BLINK", "tts": "已执行闪光"},

                        # 新增的狄仁杰命令
                        "天黑请闭眼": {"cmd": "ALL_OFF", "tts": "系统关灯"},
                        "请睁眼": {"cmd": "ALL_ON", "tts": "系统开灯"},
                        "请断案": {"cmd": "RAINBOW", "tts": "系统思考"},
                        "关闭": {"cmd": "DEFAULT", "tts": "系统停止", "action": "RESET_WAKE"}  # 切换到表情交互状态
                    }

                    command_by_id = {
                        "OPEN_EYES": {"cmd": "OPEN_EYES", "tts": "已执行打开眼睛"},
                        "CLOSE_EYES": {"cmd": "CLOSE_EYES", "tts": "已执行关闭眼睛"},
                        "OPEN_MOUTH": {"cmd": "OPEN_MOUTH", "tts": "已执行打开嘴巴"},
                        "CLOSE_MOUTH": {"cmd": "CLOSE_MOUTH", "tts": "已执行关闭嘴巴"},
                        "LEFT_ONLY": {"cmd": "LEFT_ONLY", "tts": "已执行左眼"},
                        "RIGHT_ONLY": {"cmd": "RIGHT_ONLY", "tts": "已执行右眼"},
                        "DEFAULT": {"cmd": "DEFAULT", "tts": "已执行默认"},
                        "ALL_ON": {"cmd": "ALL_ON", "tts": "已执行所有灯光"},
                        "ALL_OFF": {"cmd": "ALL_OFF", "tts": "已执行关闭灯光"},
                        "RAINBOW": {"cmd": "RAINBOW", "tts": "已执行彩虹"},
                        "BLINK": {"cmd": "BLINK", "tts": "已执行闪烁"},
                    }

                    # 命令匹配与发送
                    command_sent = False
                    # 优先尝试本地微调模型做语义意图识别，失败则回退关键词规则。
                    if predict_llm_command:
                        llm_cmd = predict_llm_command(text)
                        if llm_cmd and llm_cmd in command_by_id and len(text) < 60:
                            info = command_by_id[llm_cmd]
                            send_command(info["cmd"], command_sound, V_CURRENT_VOICE_STATUS, event_channel="voice")
                            V_LAST_CMD_TIME[0] = time.time()
                            command_sent = True
                            speak_text(info["tts"])

                    for keyword, info in command_map.items():
                        if command_sent:
                            break
                        # 精确包含 + 近似匹配，容忍少量识别错字。
                        if len(text) < 50 and _contains_like_keyword(text, keyword):
                            send_command(info["cmd"], command_sound, V_CURRENT_VOICE_STATUS, event_channel="voice")
                            V_LAST_CMD_TIME[0] = time.time()
                            command_sent = True

                            # 发送命令后播放反馈
                            speak_text(info["tts"])

                            # 特殊动作处理 (问题 6: 关闭)
                            if info.get("action") == "RESET_WAKE":
                                V_WAKE_DETECTED[0] = False  # 切换到表情交互状态
                                V_CURRENT_VOICE_STATUS[0] = "切换到表情交互，等待唤醒"

                            break
                    if not command_sent and text:
                        V_CURRENT_VOICE_STATUS[0] = f"未识别命令: {text}"
                        speak_text("未识别该命令")

                # 超时检查 (1分钟)
                command_timeout_real = CONFIG['COMMAND_TIMEOUT'] * 6  # 10*6 = 60秒
                if V_WAKE_DETECTED[0] and (time.time() - V_LAST_CMD_TIME[0] >= command_timeout_real):
                    V_WAKE_DETECTED[0] = False
                    V_CURRENT_VOICE_STATUS[0] = "命令超时（1分钟），等待唤醒"
                    speak_text("命令超时，请重新唤醒")

        except sr.WaitTimeoutError:
            # 监听超时处理
            command_timeout_real = CONFIG['COMMAND_TIMEOUT'] * 6
            is_awake = V_WAKE_DETECTED[0] and (time.time() - V_LAST_CMD_TIME[0] < command_timeout_real)
            if V_WAKE_DETECTED[0] and not is_awake:  # 真正超时
                V_WAKE_DETECTED[0] = False
                V_CURRENT_VOICE_STATUS[0] = "命令超时（1分钟），等待唤醒"
                speak_text("命令超时，请重新唤醒")
            continue
        except Exception as e:
            # 错误恢复机制
            error_msg = f"语音线程错误: {str(e)[:50]}"
            print(error_msg)
            time.sleep(1)  # 休息一下避免错误循环
            continue