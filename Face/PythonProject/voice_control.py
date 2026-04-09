import threading
import time
import speech_recognition as sr
import pygame
import os
import pyttsx3  # 新增TTS库导入
from config import CONFIG, wake_word_detected, last_command_time
from serial_comms import send_command

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
    recognizer.pause_threshold = 0.5
    recognizer.phrase_threshold = 0.2
    CHINESE_LANGUAGE_MODEL = "zh-CN"
    online_error_log_cooldown_sec = 8.0
    last_online_error_log_at = 0.0

    WAKE_WORD_RESPONSE = "我在"  # 唤醒反馈

    print("语音识别线程启动")
    while V_VOICE_AVAIL[0]:
        try:
            with source as s:
                # 环境噪音校准
                recognizer.adjust_for_ambient_noise(s, duration=0.2)
                command_timeout_base = CONFIG['COMMAND_TIMEOUT']  # 基准超时时间
                # 实际超时时间为 60 秒 (1分钟)
                command_timeout_real = command_timeout_base * 6

                # 状态判断：当前是否处于唤醒状态
                is_awake = V_WAKE_DETECTED[0] and (time.time() - V_LAST_CMD_TIME[0] < command_timeout_real)

                audio = None

                # 根据唤醒状态调整监听策略
                if is_awake:
                    V_CURRENT_VOICE_STATUS[0] = f"已唤醒，等待命令...（{command_timeout_real}秒超时）"
                    # 唤醒后，等待命令，可以监听长一点
                    audio = recognizer.listen(s, timeout=5, phrase_time_limit=10)
                else:
                    V_CURRENT_VOICE_STATUS[0] = f"等待唤醒词: {CONFIG['WAKE_WORD']}"
                    # 未唤醒，快速监听，抓取唤醒词
                    audio = recognizer.listen(s, timeout=5, phrase_time_limit=3)

                text = ""
                if audio:
                    # **优先尝试离线识别 (PocketSphinx)**
                    try:
                        # 尝试离线识别中文
                        text = recognizer.recognize_sphinx(audio, language=CHINESE_LANGUAGE_MODEL)
                        print(f"离线识别结果: {text}")
                    except sr.UnknownValueError:
                        # 离线未识别到
                        pass
                    except sr.RequestError as e:
                        # 离线识别失败时尝试在线识别
                        print(f"PocketSphinx错误: {e}，尝试在线识别...")
                        try:
                            # 尝试在线识别 (Google)
                            text = recognizer.recognize_google(audio, language="zh-CN")
                            print(f"在线识别结果: {text}")
                        except sr.UnknownValueError:
                            pass
                        except sr.RequestError as online_err:
                            now_ts = time.time()
                            if now_ts - last_online_error_log_at > online_error_log_cooldown_sec:
                                print(f"在线识别不可用（网络异常），继续监听: {online_err}")
                                last_online_error_log_at = now_ts

                    if text:
                        text = text.strip()
                        V_LAST_SPEECH[0] = text
                        print(f"最终识别内容: {text}")

                # 处理识别结果
                if not text:
                    continue  # 没有识别内容则跳过命令处理

                # 唤醒词检测
                if not is_awake:
                    if CONFIG['WAKE_WORD'] in text:
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

                    # 命令匹配与发送
                    command_sent = False
                    for keyword, info in command_map.items():
                        # 使用 in 判断更灵活，且只取前50个字符进行匹配
                        if keyword in text and len(text) < 50:
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