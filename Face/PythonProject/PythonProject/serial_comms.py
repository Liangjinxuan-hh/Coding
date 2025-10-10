import serial
import time
from tkinter import messagebox
# 导入 LAST_COMMAND_SENT
from config import CONFIG, serial_status, ser, LAST_COMMAND_SENT


# --- 串口初始化与命令发送 ---

def initialize_serial(reinit=False):
    """初始化或重新初始化串口连接"""
    global ser, serial_status

    # 如果正在重新初始化，先安全地关闭旧连接
    if reinit and ser and ser.is_open:
        try:
            ser.close()
        except Exception as e:
            print(f"关闭旧串口连接时出错: {e}")

    SERIAL_PORT = CONFIG['SERIAL_PORT']
    BAUD_RATE = CONFIG['BAUD_RATE']

    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        time.sleep(1)  # 等待Arduino重启和串口建立
        if reinit:
            print(f"串口重新连接成功: {SERIAL_PORT}")
        else:
            print(f"成功连接到串口: {SERIAL_PORT}")
        serial_status = f"串口已连接: {SERIAL_PORT}"
    except Exception as e:
        print(f"串口连接失败: {e}")
        ser = None
        serial_status = f"串口未连接 ({SERIAL_PORT})"
        if reinit:
            messagebox.showerror("串口错误", f"无法重新连接到串口: {SERIAL_PORT}\n请检查设备或端口号。")


def send_command(command, command_sound, current_voice_status_ref):
    """发送命令到串口设备 (例如Arduino)"""
    global serial_status
    if ser and ser.is_open:
        try:
            ser.write((command + '\n').encode('utf-8'))
            print(f"已发送命令: {command}")

            # 【核心功能】更新全局变量，以便在主屏幕显示
            LAST_COMMAND_SENT[0] = command

            current_voice_status_ref[0] = f"执行: {command}"
            if command_sound:
                command_sound.play()
        except Exception as e:
            error_msg = f"命令发送失败: {e}"
            print(error_msg)
            current_voice_status_ref[0] = error_msg
            serial_status = "串口发送失败"

            # 失败时也更新 UI
            LAST_COMMAND_SENT[0] = f"失败: {command}"

    else:
        msg = "串口未连接，无法发送"
        print(msg)
        current_voice_status_ref[0] = msg