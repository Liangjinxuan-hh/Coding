import tkinter as tk
from tkinter import messagebox, ttk
import serial
import serial.tools.list_ports
import os
import platform
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from config import CONFIG, save_config
from serial_comms import initialize_serial


# --- Tkinter 设置窗口 ---

def show_settings_window(parent):
    """显示设置窗口，支持唤醒词配置和语音交互开关"""
    current_config = CONFIG.copy()

    root = tk.Toplevel(parent)
    root.title("交互系统设置")
    root.geometry("420x520")  # 增加窗口高度以容纳新选项
    root.resizable(False, False)

    available_ports = [port.device for port in serial.tools.list_ports.comports()]
    if current_config['SERIAL_PORT'] not in available_ports:
        available_ports.append(current_config['SERIAL_PORT'])

    frame = tk.Frame(root, padx=10, pady=10)
    frame.pack(fill='both', expand=True)
    frame.columnconfigure(1, weight=1)

    row_num = 0

    def add_section(text):
        nonlocal row_num
        tk.Label(frame, text=text, font=('Arial', 10, 'bold')).grid(row=row_num, column=0, columnspan=2, pady=5,
                                                                    sticky='w')
        row_num += 1

    # 串口设置
    add_section("串口设置")
    tk.Label(frame, text="串口号:").grid(row=row_num, column=0, sticky='w')
    port_var = tk.StringVar(root)
    port_var.set(current_config['SERIAL_PORT'])
    if available_ports:
        port_menu = ttk.Combobox(frame, textvariable=port_var, values=available_ports, state='readonly')
        port_menu.grid(row=row_num, column=1, sticky='ew', padx=5, pady=2)
    else:
        tk.Label(frame, text="未找到可用串口").grid(row=row_num, column=1, sticky='w')
    row_num += 1

    tk.Label(frame, text="波特率:").grid(row=row_num, column=0, sticky='w')
    baud_var = tk.IntVar(root)
    baud_var.set(current_config['BAUD_RATE'])
    baud_menu = ttk.Combobox(frame, textvariable=baud_var, values=[9600, 115200, 57600], state='readonly')
    baud_menu.grid(row=row_num, column=1, sticky='ew', padx=5, pady=2)
    row_num += 1

    # 面部阈值
    add_section("面部阈值")
    tk.Label(frame, text="嘴巴阈值 (0.05-0.5):").grid(row=row_num, column=0, sticky='w')
    mouth_scale = tk.Scale(frame, from_=0.05, to=0.5, resolution=0.01, orient=tk.HORIZONTAL)
    mouth_scale.set(current_config['MOUTH_THRESHOLD'])
    mouth_scale.grid(row=row_num, column=1, sticky='ew', padx=5, pady=2)
    row_num += 1

    tk.Label(frame, text="闭眼敏感度 (0.5-0.9):").grid(row=row_num, column=0, sticky='w')
    eye_scale = tk.Scale(frame, from_=0.5, to=0.9, resolution=0.01, orient=tk.HORIZONTAL)
    eye_scale.set(current_config['EYE_SENSITIVITY'])
    eye_scale.grid(row=row_num, column=1, sticky='ew', padx=5, pady=2)
    row_num += 1

    # 语音参数
    add_section("语音参数")
    tk.Label(frame, text="唤醒词:").grid(row=row_num, column=0, sticky='w')
    wake_word_var = tk.StringVar(root)
    wake_word_var.set(current_config['WAKE_WORD'])
    wake_word_entry = tk.Entry(frame, textvariable=wake_word_var)
    wake_word_entry.grid(row=row_num, column=1, sticky='ew', padx=5, pady=2)
    row_num += 1

    tk.Label(frame, text="命令超时 (秒):").grid(row=row_num, column=0, sticky='w')
    timeout_scale = tk.Scale(frame, from_=2, to=15, resolution=1, orient=tk.HORIZONTAL)
    timeout_scale.set(current_config['COMMAND_TIMEOUT'])
    timeout_scale.grid(row=row_num, column=1, sticky='ew', padx=5, pady=2)
    row_num += 1

    # 语音交互开关
    voice_active_var = tk.BooleanVar()
    voice_active_var.set(CONFIG.get('VOICE_ACTIVE', True))  # 兼容旧配置
    voice_active_check = tk.Checkbutton(frame, text="启用语音交互", variable=voice_active_var)
    voice_active_check.grid(row=row_num, column=0, columnspan=2, sticky='w')
    row_num += 1

    # 显示设置
    add_section("显示设置")
    draw_mesh_var = tk.BooleanVar()
    draw_mesh_var.set(current_config['DRAW_MESH'])
    draw_mesh_check = tk.Checkbutton(frame, text="绘制面部网格", variable=draw_mesh_var)
    draw_mesh_check.grid(row=row_num, column=0, columnspan=2, sticky='w')
    row_num += 1

    # 调试设置
    add_section("调试选项")
    debug_mode_var = tk.BooleanVar()
    debug_mode_var.set(CONFIG.get('DEBUG_MODE', False))
    debug_mode_check = tk.Checkbutton(frame, text="启用调试模式 (显示更多信息)", variable=debug_mode_var)
    debug_mode_check.grid(row=row_num, column=0, columnspan=2, sticky='w')
    row_num += 1

    def test_serial_connection():
        test_port = port_var.get()
        test_baud = baud_var.get()
        try:
            temp_ser = serial.Serial(test_port, test_baud, timeout=1)
            temp_ser.close()
            messagebox.showinfo("串口测试", f"成功连接到串口: {test_port} ({test_baud})")
        except Exception as e:
            messagebox.showerror("串口测试", f"连接失败: {test_port}\n错误: {e}")

    def apply_settings():
        port_changed = (port_var.get() != CONFIG['SERIAL_PORT']) or (baud_var.get() != CONFIG['BAUD_RATE'])
        CONFIG['SERIAL_PORT'] = port_var.get()
        CONFIG['BAUD_RATE'] = baud_var.get()
        CONFIG['MOUTH_THRESHOLD'] = mouth_scale.get()
        CONFIG['EYE_SENSITIVITY'] = eye_scale.get()
        CONFIG['WAKE_WORD'] = wake_word_var.get()
        CONFIG['COMMAND_TIMEOUT'] = timeout_scale.get()
        CONFIG['DRAW_MESH'] = draw_mesh_var.get()
        CONFIG['VOICE_ACTIVE'] = voice_active_var.get()  # 新增语音开关配置
        CONFIG['DEBUG_MODE'] = debug_mode_var.get()  # 新增调试模式配置
        save_config()

        if port_changed:
            initialize_serial(reinit=True)

        messagebox.showinfo("设置保存", "设置已保存并应用。\n部分设置可能需要重启程序才能生效。")
        root.destroy()

    button_frame = tk.Frame(root)
    button_frame.pack(pady=10)
    tk.Button(button_frame, text="测试串口连接", command=test_serial_connection).pack(side=tk.LEFT, padx=10)
    tk.Button(button_frame, text="保存并应用", command=apply_settings).pack(side=tk.LEFT, padx=10)

    root.transient(parent)
    root.grab_set()
    parent.wait_window(root)


# --- 绘图辅助函数 ---
def get_chinese_font():
    """查找系统中可用的中文字体路径，扩展字体搜索列表"""
    system = platform.system()
    if system == "Windows":
        for font in ["simhei.ttf", "msyh.ttc", "msyh.ttf", "simsun.ttc", "simkai.ttf", "microsoftyahei.ttf"]:
            path = os.path.join("C:/Windows/Fonts", font)
            if os.path.exists(path):
                return path
    elif system == "Linux":
        for path in [
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
            "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf"
        ]:
            if os.path.exists(path):
                return path
    elif system == "Darwin":  # macOS
        for path in [
            "/System/Library/Fonts/PingFang.ttc",
            "/Library/Fonts/Songti.ttc",
            "/Library/Fonts/Heiti.ttc"
        ]:
            if os.path.exists(path):
                return path
    return None


def draw_text(img, text, pos, font_size, color, is_bold=False, chinese_font_path=None, bg_color=None):
    """
    在图像上绘制文本，支持中文和可选背景色

    参数:
        img: 要绘制的图像
        text: 文本内容
        pos: (x, y) 绘制位置
        font_size: 字体大小
        color: 文本颜色 (BGR格式)
        is_bold: 是否加粗
        chinese_font_path: 中文字体路径
        bg_color: 背景颜色 (BGR格式，None表示无背景)
    """
    # 处理带背景的文本
    if bg_color is not None:
        # 先计算文本尺寸以确定背景大小
        if chinese_font_path and any(ord(c) > 127 for c in text):
            try:
                img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
                draw = ImageDraw.Draw(img_pil)
                font = ImageFont.truetype(chinese_font_path, int(font_size * 30))
                # 获取文本尺寸（兼容新版本Pillow）
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                # 绘制背景矩形
                bg_pos = (pos[0] - 2, pos[1] - text_height)
                bg_size = (text_width + 4, text_height + 4)
                draw.rectangle([bg_pos, (bg_pos[0] + bg_size[0], bg_pos[1] + bg_size[1])], fill=bg_color[::-1])
                img = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
            except:
                pass  # 绘制背景失败时继续
        else:
            # 使用OpenCV计算文本尺寸
            text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_size, 2)[0]
            # 绘制背景矩形
            cv2.rectangle(img,
                          (pos[0] - 2, pos[1] - text_size[1] - 2),
                          (pos[0] + text_size[0] + 2, pos[1] + 2),
                          bg_color, -1)

    # 绘制文本
    if chinese_font_path and any(ord(c) > 127 for c in text):
        try:
            img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            draw = ImageDraw.Draw(img_pil)
            font = ImageFont.truetype(chinese_font_path, int(font_size * 30))
            draw.text(pos, text, font=font, fill=color[::-1])  # 转换为RGB颜色
            return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
        except Exception as e:
            print(f"警告: 使用PIL绘制中文失败 - {e}")

    # 退回到OpenCV绘制
    thickness = 2 if is_bold else 1
    cv2.putText(img, text, pos, cv2.FONT_HERSHEY_SIMPLEX, font_size, color, thickness, cv2.LINE_AA)
    return img