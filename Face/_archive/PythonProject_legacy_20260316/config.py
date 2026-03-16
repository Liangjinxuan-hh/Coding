import json
import os

# --- 全局配置与状态 ---
CONFIG_FILE = 'config.json'

# 全局配置字典 (默认值)
CONFIG = {
    'SERIAL_PORT': 'COM3',
    'BAUD_RATE': 9600,
    'MOUTH_THRESHOLD': 0.13,
    'EYE_SENSITIVITY': 0.7,  # 眼睛闭合敏感度 (基准EAR的百分比, 越低越灵敏)
    'COMMAND_TIMEOUT': 5,      # 语音命令超时时间 (秒)
    'WAKE_WORD': '狄仁杰',
    'DRAW_MESH': True          # 是否绘制面部网格
}

# 全局状态变量 (程序运行时动态改变)
wake_word_detected = False
last_command_time = 0
current_face_status = "等待检测..."
current_voice_status = "等待唤醒词..."
voice_recognition_available = True
eye_close_count = 0
last_eye_state_for_count = "睁眼"
mouth_distance = 0
mouth_ratio = 0
ser = None
serial_status = ""
# ------------------------------------------------
# 【新增】用于在主屏幕上显示最后发送的命令
LAST_COMMAND_SENT = ["无"]
# ------------------------------------------------

# MediaPipe 面部特征点索引 (固定值)
LEFT_EYE_EAR_POINTS = [362, 385, 387, 263, 373, 380]
RIGHT_EYE_EAR_POINTS = [33, 159, 158, 133, 145, 144]
UPPER_LIP_CENTER_INDEX = 13
LOWER_LIP_CENTER_INDEX = 14


def load_config():
    """从 config.json 文件中加载配置, 如果文件不存在则使用默认值"""
    global CONFIG
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
                # 仅更新预期的键, 防止配置文件格式错误
                for key, default_value in CONFIG.items():
                    if key in loaded_config:
                        # 确保从json加载的值类型正确
                        if isinstance(default_value, bool):
                            CONFIG[key] = bool(loaded_config[key])
                        elif isinstance(default_value, float):
                            CONFIG[key] = float(loaded_config[key])
                        elif isinstance(default_value, int):
                            CONFIG[key] = int(loaded_config[key])
                        else:
                            CONFIG[key] = loaded_config[key]
        except Exception as e:
            print(f"加载配置错误: {e}。将使用默认设置。")


def save_config():
    """保存当前配置到 config.json 文件"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            # 修正: ensure_ascii=False 确保中文字符直接写入而不是作为编码
            json.dump(CONFIG, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"保存配置错误: {e}")