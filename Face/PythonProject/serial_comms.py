import serial
import time
from tkinter import messagebox
import config

try:
    from web_bridge import publish_face_command
except Exception:  # pragma: no cover - bridge optional
    def publish_face_command(*_, **__):
        return


def initialize_serial(reinit=False):
    """初始化或重新初始化串口连接"""
    # 关闭现有连接（如果重新初始化）
    if reinit and config.ser and config.ser.is_open:
        try:
            config.ser.close()
        except Exception as e:
            print(f"关闭旧串口连接时出错: {e}")

    SERIAL_PORT = config.CONFIG['SERIAL_PORT']
    BAUD_RATE = config.CONFIG['BAUD_RATE']

    try:
        config.ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        time.sleep(1)  # 等待设备初始化
        status = f"串口已连接: {SERIAL_PORT}"
        if reinit:
            print(f"串口重新连接成功: {SERIAL_PORT}")
        else:
            print(f"成功连接到串口: {SERIAL_PORT}")
    except Exception as e:
        config.ser = None
        status = f"串口未连接 ({SERIAL_PORT})"
        print(f"串口连接失败: {e}")
        if reinit:
            messagebox.showerror("串口错误", f"无法重新连接到串口: {SERIAL_PORT}\n请检查设备或端口号。")

    config.serial_status = status


def send_command(command, command_sound, current_voice_status_ref):
    """发送命令到串口设备，带状态跟踪"""
    if config.ser and config.ser.is_open:
        try:
            # 发送命令并添加换行符作为结束标志
            config.ser.write((command + '\n').encode('utf-8'))
            print(f"已发送命令: {command}")

            # 更新全局状态
            config.LAST_COMMAND_SENT[0] = command
            current_voice_status_ref[0] = f"执行: {command}"

            # 播放反馈音效
            if command_sound:
                command_sound.play()

            publish_face_command(command, {"status": "ok"})

        except Exception as e:
            error_msg = f"命令发送失败: {str(e)[:30]}"
            print(error_msg)
            current_voice_status_ref[0] = error_msg
            config.serial_status = "串口发送失败"
            config.LAST_COMMAND_SENT[0] = f"失败: {command}"
    else:
        msg = "串口未连接，无法发送"
        print(msg)
        current_voice_status_ref[0] = msg
        config.LAST_COMMAND_SENT[0] = f"失败: {msg}"


def receive_data():
    """接收串口返回的数据（新增函数）"""
    if config.ser and config.ser.is_open:
        try:
            if config.ser.in_waiting > 0:
                return config.ser.readline().decode('utf-8').strip()
        except Exception as e:
            print(f"串口接收错误: {e}")
    return None