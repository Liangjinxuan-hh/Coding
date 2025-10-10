import serial
import time
from tkinter import messagebox
from config import CONFIG, serial_status, ser, LAST_COMMAND_SENT


def initialize_serial(reinit=False):
    """初始化或重新初始化串口连接"""
    global ser, serial_status

    # 关闭现有连接（如果重新初始化）
    if reinit and ser and ser.is_open:
        try:
            ser.close()
        except Exception as e:
            print(f"关闭旧串口连接时出错: {e}")

    SERIAL_PORT = CONFIG['SERIAL_PORT']
    BAUD_RATE = CONFIG['BAUD_RATE']

    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        time.sleep(1)  # 等待设备初始化
        status = f"串口已连接: {SERIAL_PORT}"
        if reinit:
            print(f"串口重新连接成功: {SERIAL_PORT}")
        else:
            print(f"成功连接到串口: {SERIAL_PORT}")
    except Exception as e:
        ser = None
        status = f"串口未连接 ({SERIAL_PORT})"
        print(f"串口连接失败: {e}")
        if reinit:
            messagebox.showerror("串口错误", f"无法重新连接到串口: {SERIAL_PORT}\n请检查设备或端口号。")

    serial_status = status


def send_command(command, command_sound, current_voice_status_ref):
    """发送命令到串口设备，带状态跟踪"""
    global serial_status
    if ser and ser.is_open:
        try:
            # 发送命令并添加换行符作为结束标志
            ser.write((command + '\n').encode('utf-8'))
            print(f"已发送命令: {command}")

            # 更新全局状态
            LAST_COMMAND_SENT[0] = command
            current_voice_status_ref[0] = f"执行: {command}"

            # 播放反馈音效
            if command_sound:
                command_sound.play()

        except Exception as e:
            error_msg = f"命令发送失败: {str(e)[:30]}"
            print(error_msg)
            current_voice_status_ref[0] = error_msg
            serial_status = "串口发送失败"
            LAST_COMMAND_SENT[0] = f"失败: {command}"
    else:
        msg = "串口未连接，无法发送"
        print(msg)
        current_voice_status_ref[0] = msg
        LAST_COMMAND_SENT[0] = f"失败: {msg}"


def receive_data():
    """接收串口返回的数据（新增函数）"""
    if ser and ser.is_open:
        try:
            if ser.in_waiting > 0:
                return ser.readline().decode('utf-8').strip()
        except Exception as e:
            print(f"串口接收错误: {e}")
    return None