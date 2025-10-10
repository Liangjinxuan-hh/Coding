import cv2
import mediapipe as mp
import time
import threading
import tkinter as tk
from tkinter import messagebox
import numpy as np

from config import CONFIG, load_config, ser, LEFT_EYE_EAR_POINTS, RIGHT_EYE_EAR_POINTS, LAST_COMMAND_SENT
from serial_comms import initialize_serial, send_command, serial_status, receive_data
from face_analysis import eye_aspect_ratio, mouth_aspect_ratio, detect_face_direction
from voice_control import voice_recognition_thread, V_CURRENT_VOICE_STATUS, V_VOICE_AVAIL, V_LAST_SPEECH, speak_text, \
    V_WAKE_DETECTED
from ui_utils import show_settings_window, get_chinese_font, draw_text
from ui_manager import Button

# 全局变量
mouse_click_pos = None
current_face_status = "等待检测..."
WINDOW_NAME = "Face & Voice Control"


def mouse_callback(event, x, y, flags, param):
    """处理鼠标点击事件"""
    global mouse_click_pos
    if event == cv2.EVENT_LBUTTONDOWN:
        mouse_click_pos = (x, y)


def main(tk_root):
    """主程序入口"""
    global current_face_status, mouse_click_pos

    # 初始化
    load_config()
    initialize_serial()
    chinese_font_path = get_chinese_font()

    # 播放欢迎语（使用voice_control中的TTS函数）
    speak_text("系统已启动")

    # 启动语音识别线程
    voice_thread = threading.Thread(target=voice_recognition_thread, daemon=True)
    voice_thread.start()

    # 初始化摄像头
    cap = cv2.VideoCapture(CONFIG.get('CAMERA_INDEX', 0))
    if not cap.isOpened():
        messagebox.showerror("错误", "无法打开摄像头。请检查设备和配置。")
        return

    # 初始化MediaPipe Face Mesh
    mp_face_mesh = mp.solutions.face_mesh
    face_mesh = mp_face_mesh.FaceMesh(
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )

    # 状态控制变量
    last_eye_state = "睁眼"
    last_mouth_state = "闭嘴"
    last_direction = "LOOK_CENTER"
    last_state_change_time = time.time()
    state_change_cooldown = 0.5  # 状态改变冷却时间（秒）

    # 动态阈值计算变量
    ear_history = []
    baseline_ear = 0.3
    EAR_HISTORY_LENGTH = 300
    CALIBRATION_FRAMES = 150
    calibrated = False

    # **关键修改 1: 设置窗口为可缩放**
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(WINDOW_NAME, mouse_callback)

    while cap.isOpened():
        success, image = cap.read()
        if not success:
            break

        # 翻转图像，使其像镜子
        image = cv2.flip(image, 1)
        image.flags.writeable = False
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(image)
        image.flags.writeable = True
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        # **关键修改 2: 动态获取尺寸和计算 UI 元素位置**
        h, w, _ = image.shape
        padding = int(h * 0.02)  # 2% of height for padding
        line_height = int(h * 0.045)  # 4.5% of height for line spacing
        font_scale = h / 720 * 0.6  # Base font scale on a standard 720p height

        # 动态创建/更新设置按钮的位置 (右上角)
        SETTINGS_BUTTON_WIDTH = int(w * 0.12)  # 12% of width
        SETTINGS_BUTTON_HEIGHT = int(h * 0.05)  # 5% of height
        button_x = w - SETTINGS_BUTTON_WIDTH - padding
        button_y = padding
        # 在每次循环中重新定义 Button 对象，使用动态坐标
        settings_button = Button(
            (button_x, button_y),
            SETTINGS_BUTTON_WIDTH,
            SETTINGS_BUTTON_HEIGHT,
            "设置"
        )
        # ----------------------------------------------------------------------

        # 检查设置按钮点击 (使用新的 settings_button)
        if mouse_click_pos and settings_button.is_clicked(mouse_click_pos):
            show_settings_window(tk_root)
            mouse_click_pos = None  # 重置点击位置

        landmarks = None
        if results.multi_face_landmarks:
            landmarks = results.multi_face_landmarks[0].landmark

            # 人脸网格绘制 (如果配置开启)
            if CONFIG['DRAW_MESH']:
                mp_drawing = mp.solutions.drawing_utils
                mp_drawing.draw_landmarks(
                    image=image,
                    landmark_list=results.multi_face_landmarks[0],
                    connections=mp_face_mesh.FACEMESH_CONTOURS,
                    landmark_drawing_spec=None,
                    connection_drawing_spec=mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=1, circle_radius=1)
                )

            # --- EAR 动态校准 ---
            left_ear = eye_aspect_ratio(landmarks, LEFT_EYE_EAR_POINTS, image)
            right_ear = eye_aspect_ratio(landmarks, RIGHT_EYE_EAR_POINTS, image)
            avg_ear = (left_ear + right_ear) / 2

            if not calibrated:
                ear_history.append(avg_ear)
                if len(ear_history) > CALIBRATION_FRAMES:
                    # 取历史记录的前150帧的90%分位数作为基准睁眼EAR
                    baseline_ear = np.percentile(ear_history[-CALIBRATION_FRAMES:], 90)
                    calibrated = True
                    ear_history = []
                    current_face_status = "校准完成，开始交互"
            else:
                ear_history.append(avg_ear)
                if len(ear_history) > EAR_HISTORY_LENGTH:
                    ear_history.pop(0)

            # --- 状态判断 ---
            eye_sensitivity = CONFIG['EYE_SENSITIVITY']
            # 闭眼阈值：基准EAR * 敏感度 (敏感度越低，阈值越低，越灵敏)
            dynamic_eye_threshold = baseline_ear * eye_sensitivity

            # 眼睛状态
            if avg_ear < dynamic_eye_threshold:
                current_eye_state = "闭眼"
            else:
                current_eye_state = "睁眼"

            # 嘴巴状态
            mouth_dist_ref = [0]
            mouth_ratio_ref = [0]
            mar = mouth_aspect_ratio(landmarks, image, mouth_dist_ref, mouth_ratio_ref)
            if mar > CONFIG['MOUTH_THRESHOLD']:
                current_mouth_state = "张嘴"
            else:
                current_mouth_state = "闭嘴"

            # 头部方向
            direction = detect_face_direction(landmarks)

            # 状态变化检测与命令发送
            current_time = time.time()

            # 检查语音交互状态 (V_WAKE_DETECTED[0] == True 表示处于语音交互模式)
            if V_WAKE_DETECTED[0]:
                # 语音模式下，面部命令被屏蔽
                current_face_status = f"头:{direction.replace('LOOK_', '')} | 眼:{current_eye_state} | 嘴:{current_mouth_state} (语音模式)"
                # 不发送面部命令到下位机
            else:
                # 处于面部交互模式时才发送命令 (表情交互状态)
                if current_time - last_state_change_time > state_change_cooldown:
                    command = None

                    if current_eye_state != last_eye_state:
                        command = "CLOSE_EYES" if current_eye_state == "闭眼" else "OPEN_EYES"
                        last_eye_state = current_eye_state

                    elif current_mouth_state != last_mouth_state:
                        command = "OPEN_MOUTH" if current_mouth_state == "张嘴" else "CLOSE_MOUTH"
                        last_mouth_state = current_mouth_state

                    elif direction != last_direction:
                        if direction == "LOOK_LEFT":
                            command = "LOOK_LEFT"
                        elif direction == "LOOK_RIGHT":
                            command = "LOOK_RIGHT"
                        else:
                            command = "DEFAULT"  # 头部回正
                        last_direction = direction

                    if command:
                        send_command(command, None, V_CURRENT_VOICE_STATUS)  # 语音状态引用仅用于调试信息显示
                        last_state_change_time = current_time

                current_face_status = f"头:{direction.replace('LOOK_', '')} | 眼:{current_eye_state} | 嘴:{current_mouth_state}"

        else:
            current_face_status = "未检测到人脸"
            # 如果人脸消失，也重置状态
            last_eye_state = "睁眼"
            last_mouth_state = "闭嘴"
            last_direction = "LOOK_CENTER"

            # 人脸消失时清空历史 EAR
            if calibrated:
                ear_history = []
                calibrated = False

        # --- UI 绘制 (使用动态计算的坐标和尺寸) ---
        current_line_y = padding  # 初始行Y坐标

        # 1. 标题 (第一行，居中显示)
        title_text = "智能语音表情交互系统"
        # 字体尺寸需要乘以30或40才能传递给draw_text的PIL部分
        title_size_px = cv2.getTextSize(title_text, cv2.FONT_HERSHEY_SIMPLEX, font_scale * 1.5, 3)[0]
        title_x = (w - title_size_px[0]) // 2

        current_line_y += line_height
        image = draw_text(image, title_text, (title_x, current_line_y), font_scale * 1.3, (0, 255, 0), True,
                          chinese_font_path)

        # 2. 面部状态 (左侧区域)
        # **修正点 1: 确保行增量是整数**
        current_line_y += int(line_height * 1.5)
        image = draw_text(image, "表情状态:", (padding, current_line_y), font_scale * 1.1, (255, 255, 255), True,
                          chinese_font_path)
        current_line_y += line_height
        image = draw_text(image, current_face_status, (padding, current_line_y), font_scale, (255, 255, 0), False,
                          chinese_font_path)

        # 3. 语音状态
        # **修正点 2**
        current_line_y += int(line_height * 1.5)
        voice_status = f"语音状态: {V_CURRENT_VOICE_STATUS[0]}"
        last_speech = f"最后识别: {V_LAST_SPEECH[0]}"
        image = draw_text(image, "语音交互:", (padding, current_line_y), font_scale * 1.1, (255, 255, 255), True,
                          chinese_font_path)
        current_line_y += line_height
        image = draw_text(image, voice_status, (padding, current_line_y), font_scale, (0, 255, 255), False,
                          chinese_font_path)
        current_line_y += line_height
        image = draw_text(image, last_speech, (padding, current_line_y), font_scale, (0, 165, 255), False,
                          chinese_font_path)

        # 4. 动态阈值显示
        # **修正点 3**
        current_line_y += int(line_height * 1.5)
        if not calibrated:
            threshold_text = f"校准中... ({len(ear_history)}/{CALIBRATION_FRAMES})"
            image = draw_text(image, threshold_text, (padding, current_line_y), font_scale, (0, 165, 255), False,
                              chinese_font_path)
        else:
            threshold_text = f"动态闭眼阈值: {dynamic_eye_threshold:.2f} (基准: {baseline_ear:.2f})"
            image = draw_text(image, threshold_text, (padding, current_line_y), font_scale, (0, 255, 0), False,
                              chinese_font_path)

        # 5. 系统状态显示
        # **修正点 4 (报错行)**
        current_line_y += int(line_height * 1.5)
        image = draw_text(image, serial_status, (padding, current_line_y), font_scale, (200, 200, 200), False,
                          chinese_font_path)
        current_line_y += line_height
        image = draw_text(image, f"最后命令: {LAST_COMMAND_SENT[0]}", (padding, current_line_y), font_scale,
                          (255, 100, 255), False,
                          chinese_font_path)

        # 6. 绘制设置按钮 (已动态创建)
        image = settings_button.draw(image)

        # 7. 退出提示 (锚定左下角)
        exit_text = "按ESC退出"
        # **修正点 5: 确保 final position 是整数**
        image = draw_text(image, exit_text, (padding, h - padding), font_scale * 0.8, (128, 128, 128), False,
                          chinese_font_path)

        cv2.imshow(WINDOW_NAME, image)

        # 按键处理
        key = cv2.waitKey(5) & 0xFF
        if key == 27:  # ESC键退出
            break

    # 清理资源
    face_mesh.close()
    cap.release()
    cv2.destroyAllWindows()
    # 退出前关闭串口
    if ser and ser.is_open:
        try:
            ser.close()
        except Exception:
            pass
    print("程序已退出。")


if __name__ == "__main__":
    # 使用Tkinter root作为设置窗口的父窗口
    root = tk.Tk()
    root.withdraw()  # 隐藏主Tkinter窗口
    try:
        main(root)
    finally:
        root.destroy()