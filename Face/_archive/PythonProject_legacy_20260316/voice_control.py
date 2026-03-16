import threading
import time
import speech_recognition as sr
import pygame
import os
# 导入配置文件和串口发送函数
from config import CONFIG, wake_word_detected, last_command_time
from serial_comms import send_command

# 初始化Pygame音频
try:
    pygame.mixer.init()
except pygame.error as e:
    print(f"Pygame音频初始化失败: {e}. 音效功能将禁用。")

# 加载提示音效
wake_sound = None
command_sound = None
try:
    if os.path.exists("wake.wav"):
        wake_sound = pygame.mixer.Sound("wake.wav")
    if os.path.exists("command.wav"):
        command_sound = pygame.mixer.Sound("command.wav")
except pygame.error as e:
    print(f"Pygame音频加载失败: {e}")
    wake_sound = None
    command_sound = None

# 状态变量的引用 (用于在线程中安全地修改主线程的全局变量)
V_WAKE_DETECTED = [wake_word_detected]
V_LAST_CMD_TIME = [last_command_time]
V_CURRENT_VOICE_STATUS = ["等待唤醒..."]
V_LAST_SPEECH = [""]  # 存储最后识别的原始文本
V_VOICE_AVAIL = [True]


def voice_recognition_thread():
    """语音识别线程主函数"""
    global V_VOICE_AVAIL, V_CURRENT_VOICE_STATUS, V_LAST_SPEECH

    # 检查PyAudio依赖
    try:
        import pyaudio
    except ImportError:
        V_CURRENT_VOICE_STATUS[0] = "错误: 缺少PyAudio库 (需安装: pip install pyaudio)"
        V_VOICE_AVAIL[0] = False
        return

    recognizer = sr.Recognizer()
    source = None

    # 选择合适的麦克风设备
    try:
        mic_list = sr.Microphone.list_microphone_names()
        # 优先选择包含"麦克风"关键词的设备
        for i, name in enumerate(mic_list):
            if "麦克风" in name or "mic" in name.lower():
                source = sr.Microphone(device_index=i)
                print(f"使用麦克风设备 {i}: {name}")
                break
        # 若未找到特定设备，使用默认设备
        if not source:
            source = sr.Microphone()
            print("使用默认麦克风设备")
    except Exception as e:
        V_CURRENT_VOICE_STATUS[0] = f"麦克风选择失败: {e}"
        V_VOICE_AVAIL[0] = False
        return

    # 调整监听参数，加快反应
    recognizer.pause_threshold = 0.5
    recognizer.phrase_threshold = 0.2
    CHINESE_LANGUAGE_MODEL = "zh-CN"

    print("语音识别线程启动")
    while True:
        try:
            # 关键修复：每次循环都通过with语句管理麦克风资源
            with source as s:
                # 每次监听前校准环境噪音（适应环境变化）
                recognizer.adjust_for_ambient_noise(s, duration=0.2)
                command_timeout = CONFIG['COMMAND_TIMEOUT']
                audio = None

                if V_WAKE_DETECTED[0]:
                    V_CURRENT_VOICE_STATUS[0] = f"已唤醒，等待命令...（{command_timeout}秒超时）"
                    audio = recognizer.listen(s, timeout=3, phrase_time_limit=5)
                else:
                    V_CURRENT_VOICE_STATUS[0] = f"等待唤醒词: {CONFIG['WAKE_WORD']}"
                    audio = recognizer.listen(s, timeout=10, phrase_time_limit=3)

                text = ""
                if audio:
                    # 优先尝试离线识别
                    try:
                        text = recognizer.recognize_sphinx(audio, language=CHINESE_LANGUAGE_MODEL)
                    except sr.UnknownValueError:
                        V_LAST_SPEECH[0] = "离线识别：未识别到语音"
                    except sr.RequestError as e:
                        print(f"PocketSphinx错误: {e}，尝试在线识别...")
                        try:
                            text = recognizer.recognize_google(audio, language="zh-CN")
                        except sr.UnknownValueError:
                            V_LAST_SPEECH[0] = "在线识别：未识别到语音"
                        except sr.RequestError:
                            V_LAST_SPEECH[0] = "在线识别失败：网络问题"

                # 更新识别结果
                if text:
                    text = text.strip()
                    V_LAST_SPEECH[0] = text
                    print(f"识别内容: {text}")

                # 处理唤醒逻辑
                if not V_WAKE_DETECTED[0]:
                    if CONFIG['WAKE_WORD'] in text:
                        V_WAKE_DETECTED[0] = True
                        V_LAST_CMD_TIME[0] = time.time()
                        V_CURRENT_VOICE_STATUS[0] = "唤醒成功，请说命令"
                        if wake_sound:
                            wake_sound.play()
                else:
                    # 命令映射表，简化代码
                    command_map = {
                        "打开眼睛": "OPEN_EYES",
                        "关闭眼睛": "CLOSE_EYES",
                        "打开嘴巴": "OPEN_MOUTH",
                        "张嘴": "OPEN_MOUTH",
                        "关闭嘴巴": "CLOSE_MOUTH",
                        "所有灯光": "ALL_ON",
                        "全部点亮": "ALL_ON",
                        "关闭灯光": "ALL_OFF",
                        "彩虹": "RAINBOW",
                        "七彩": "RAINBOW",
                        "闪烁": "BLINK",
                        "闪光": "BLINK",
                        "左眼": "LEFT_ONLY",
                        "右眼": "RIGHT_ONLY",
                        "默认": "DEFAULT",
                        "停止": "DEFAULT"
                    }
                    # 检查命令是否匹配
                    for keyword, cmd in command_map.items():
                        if keyword in text:
                            send_command(cmd, command_sound, V_CURRENT_VOICE_STATUS)
                            V_LAST_CMD_TIME[0] = time.time()  # 更新命令时间
                            break
                    else:
                        if text:
                            V_CURRENT_VOICE_STATUS[0] = f"未识别命令: {text}"

                # 超时检查
                if V_WAKE_DETECTED[0] and (time.time() - V_LAST_CMD_TIME[0] >= command_timeout):
                    V_WAKE_DETECTED[0] = False
                    V_CURRENT_VOICE_STATUS[0] = "命令超时，等待唤醒"

        except sr.WaitTimeoutError:
            # 监听超时是正常情况，仅检查唤醒状态超时
            if V_WAKE_DETECTED[0] and (time.time() - V_LAST_CMD_TIME[0] >= command_timeout):
                V_WAKE_DETECTED[0] = False
                V_CURRENT_VOICE_STATUS[0] = "命令超时，等待唤醒"
            continue
        except Exception as e:
            # 捕获其他错误并尝试恢复
            error_msg = f"语音线程错误: {str(e)[:50]}"
            V_CURRENT_VOICE_STATUS[0] = error_msg
            V_VOICE_AVAIL[0] = False
            print(f"语音识别线程异常: {e}")
            time.sleep(2)  # 休眠避免频繁报错
            V_VOICE_AVAIL[0] = True  # 尝试恢复