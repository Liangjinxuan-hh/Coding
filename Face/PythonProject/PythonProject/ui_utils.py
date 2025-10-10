import tkinter as tk
from tkinter import messagebox, ttk
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
    """显示设置窗口"""
    current_config = CONFIG.copy()

    root = tk.Toplevel(parent)
    root.title("交互系统设置")
    root.geometry("420x450")
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
    tk.Label(frame, text="命令超时 (秒):").grid(row=row_num, column=0, sticky='w')
    timeout_scale = tk.Scale(frame, from_=2, to=15, resolution=1, orient=tk.HORIZONTAL)
    timeout_scale.set(current_config['COMMAND_TIMEOUT'])
    timeout_scale.grid(row=row_num, column=1, sticky='ew', padx=5, pady=2)
    row_num += 1

    # 显示设置
    add_section("显示设置")
    draw_mesh_var = tk.BooleanVar()
    draw_mesh_var.set(current_config['DRAW_MESH'])
    draw_mesh_check = tk.Checkbutton(frame, text="绘制面部网格", variable=draw_mesh_var)
    draw_mesh_check.grid(row=row_num, column=0, columnspan=2, sticky='w')
    row_num += 1

    def test_serial_connection():
        test_port = port_var.get()
        test_baud = CONFIG['BAUD_RATE']
        try:
            temp_ser = serial.Serial(test_port, test_baud, timeout=1)
            temp_ser.close()
            messagebox.showinfo("串口测试", f"成功连接到串口: {test_port}")
        except Exception as e:
            messagebox.showerror("串口测试", f"连接失败: {test_port}\n错误: {e}")

    def apply_settings():
        port_changed = (port_var.get() != CONFIG['SERIAL_PORT'])
        CONFIG['SERIAL_PORT'] = port_var.get()
        CONFIG['MOUTH_THRESHOLD'] = mouth_scale.get()
        CONFIG['EYE_SENSITIVITY'] = eye_scale.get()
        CONFIG['COMMAND_TIMEOUT'] = timeout_scale.get()
        CONFIG['DRAW_MESH'] = draw_mesh_var.get()
        save_config()
        if port_changed:
            initialize_serial(reinit=True)
        messagebox.showinfo("设置保存", "设置已保存并应用。")
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
    """查找系统中可用的中文字体路径"""
    system = platform.system()
    if system == "Windows":
        for font in ["simhei.ttf", "msyh.ttc", "msyh.ttf"]:  # 优先使用黑体或雅黑
            path = os.path.join("C:/Windows/Fonts", font)
            if os.path.exists(path): return path
    elif system == "Linux":
        for path in ["/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
                     "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"]:
            if os.path.exists(path): return path
    return None


def draw_text(img, text, pos, font_size, color, is_bold=False, chinese_font_path=None):
    """
    在图像上绘制文本，智能判断是否使用Pillow(PIL)来支持中文。
    """
    # --- 核心修正逻辑 ---
    # 如果找到了中文字体文件, 并且文本中含有任何非ASCII字符(中文), 则使用Pillow绘制
    if chinese_font_path and any(ord(c) > 127 for c in text):
        try:
            # 将OpenCV图像(BGR)转换为Pillow图像(RGB)
            img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            draw = ImageDraw.Draw(img_pil)
            # 根据font_size参数调整Pillow字体大小
            font = ImageFont.truetype(chinese_font_path, int(font_size * 30))
            # 在图像上绘制文本 (Pillow使用RGB颜色)
            draw.text(pos, text, font=font, fill=color[::-1])
            # 将Pillow图像转换回OpenCV图像格式
            return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
        except Exception as e:
            print(f"警告: 使用PIL绘制中文失败 - {e}")
            # 如果Pillow绘制失败, 仍然会退回到OpenCV的putText, 这时中文会乱码, 但程序不会崩溃

    # 对于纯英文/数字文本, 或Pillow绘制失败的情况, 使用OpenCV原生函数
    cv2.putText(img, text, pos, cv2.FONT_HERSHEY_SIMPLEX, font_size, color, 2 if is_bold else 1)
    return img