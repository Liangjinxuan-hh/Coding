import cv2
import mediapipe as mp
import time
import threading
import tkinter as tk
from tkinter import messagebox
import numpy as np
# 【新增】导入 TTS 库
import pyttsx3

from config import CONFIG, load_config, ser, LEFT_EYE_EAR_POINTS, RIGHT_EYE_EAR_POINTS, LAST_COMMAND_SENT
from serial_comms import initialize_serial, send_command, serial_status
from face_analysis import eye_aspect_ratio, mouth_aspect_ratio, detect_face_direction
from voice_control import voice_recognition_thread, V_CURRENT_VOICE_STATUS, V_VOICE_AVAIL, V_LAST_SPEECH, wake_sound, \
    command_sound
from ui_utils import show_settings_window, get_chinese_font, draw_text
from ui_manager import Button

# --- 全局变量 ---
mouse_click_pos = None
current_face_status = "等待检测..."


# 【新增函数】TTS 欢迎语
def speak_welcome_message(text):
    """使用本地 TTS 引擎播放欢迎语"""
    try:
        # 在独立的线程中初始化和运行引擎，避免阻塞主线程
        def run_tts():
            engine = pyttsx3.init()
            voices = engine.getProperty('voices')
            # 尝试设置中文语音
            for voice in voices:
                if 'chinese' in voice.name.lower() or 'han' in voice.name.lower():
                    engine.setProperty('voice', voice.id)
                    # 降低语速，提高清晰度
                    engine.setProperty('rate', 150)
                    break

            engine.say(text)
            engine.runAndWait()

        threading.Thread(target=run_tts, daemon=True).start()
    except Exception as e:
        print(f"TTS 语音播放失败，请检查 pyttsx3 是否安装正确: {e}")


def mouse_callback(event, x, y, flags, param):
    """鼠标事件回调，用于处理按钮点击"""
    global mouse_click_pos
    if event == cv2.EVENT_LBUTTONDOWN:
        mouse_click_pos = (x, y)


def main(tk_root):
    """主程序函数"""
    global current_face_status, mouse_click_pos

    # 1. 初始化
    load_config()
    initialize_serial()
    chinese_font_path = get_chinese_font()

    # 【整合】播放系统欢迎语
    speak_welcome_message("欢迎来到语音表情交互系统，请说唤醒词开始互动。")

    voice_thread = threading.Thread(target=voice_recognition_thread, daemon=True)
    voice_thread.start()

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        cap = cv2.VideoCapture(1)
        if not cap.isOpened():
            messagebox.showerror("摄像头错误", "无法打开任何可用的摄像头设备。")
            return

    # 2. 状态与窗口设置
    last_eye_state, last_mouth_state, last_direction = "睁眼", "闭嘴", "LOOK_FORWARD"
    last_state_change_time = 0
    state_change_cooldown = 0.4  # 状态改变冷却时间
    REQUIRED_CONSECUTIVE = 2
    mouth_state_counter, eye_state_counter = 0, 0

    WINDOW_NAME = "Smart Interaction System"
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(WINDOW_NAME, mouse_callback)
    settings_button = Button(pos=(10, 310), width=100, height=30, text="Settings")

    # 眼睛自适应阈值校准变量
    CALIBRATION_FRAMES = 100
    ear_values = []
    baseline_ear = None
    dynamic_eye_threshold = CONFIG['EYE_SENSITIVITY'] * 0.3  # 初始默认值
    frame_count = 0

    # MediaPipe 初始化
    mp_face_mesh = mp.solutions.face_mesh
    mp_drawing = mp.solutions.drawing_utils
    mp_drawing_styles = mp.solutions.drawing_utils.DrawingSpec(thickness=1, circle_radius=1)

    with mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.6,
            min_tracking_confidence=0.6) as face_mesh:

        while cap.isOpened():
            success, image = cap.read()
            if not success: continue
            image = cv2.flip(image, 1)

            # 3. 人脸处理
            image.flags.writeable = False
            results = face_mesh.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            image.flags.writeable = True

            new_command_sent = False
            current_eye_state = "睁眼"
            current_mouth_state = "闭嘴"
            direction = "LOOK_FORWARD"

            if results.multi_face_landmarks:
                frame_count += 1
                for face_landmarks in results.multi_face_landmarks:
                    if CONFIG['DRAW_MESH']:
                        mp_drawing.draw_landmarks(
                            image=image, landmark_list=face_landmarks,
                            connections=mp_face_mesh.FACEMESH_TESSELATION,
                            landmark_drawing_spec=None,
                            connection_drawing_spec=mp_drawing_styles)

                    landmarks = face_landmarks.landmark
                    left_ear = eye_aspect_ratio(landmarks, LEFT_EYE_EAR_POINTS, image)
                    right_ear = eye_aspect_ratio(landmarks, RIGHT_EYE_EAR_POINTS, image)
                    avg_ear = (left_ear + right_ear) / 2.0

                    # 眼睛阈值自适应校准
                    if baseline_ear is None and frame_count <= CALIBRATION_FRAMES:
                        ear_values.append(avg_ear)
                        if frame_count == CALIBRATION_FRAMES:
                            if ear_values:
                                baseline_ear = np.mean([x for x in ear_values if x > 0.1])
                                dynamic_eye_threshold = baseline_ear * CONFIG['EYE_SENSITIVITY']

                    current_eye_state = "闭眼" if avg_ear < dynamic_eye_threshold else "睁眼"

                    # 后续状态检测及命令发送逻辑
                    mar = mouth_aspect_ratio(landmarks, image, [0], [0])
                    current_mouth_state = "张嘴" if mar > CONFIG['MOUTH_THRESHOLD'] else "闭嘴"
                    direction = detect_face_direction(landmarks)

                    # ------------------------------------------------
                    # 【核心功能】视觉状态确认和命令发送的详细逻辑
                    current_time = time.time()

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
                            # 传递 V_CURRENT_VOICE_STATUS 引用以更新其状态
                            send_command(command, None, V_CURRENT_VOICE_STATUS)
                            last_state_change_time = current_time
                            new_command_sent = True

                    # ------------------------------------------------

                    current_face_status = f"头:{direction.replace('LOOK_', '')} | 眼:{current_eye_state} | 嘴:{current_mouth_state}"
            else:
                current_face_status = "未检测到人脸"

            # 4. 绘制UI
            image = draw_text(image, "智能语音视觉交互系统", (10, 30), 0.8, (0, 255, 0), True, chinese_font_path)
            image = draw_text(image, f"面部: {current_face_status}", (10, 70), 0.6, (255, 255, 0), False,
                              chinese_font_path)
            voice_text = V_CURRENT_VOICE_STATUS[0] if V_VOICE_AVAIL[0] else "语音功能不可用"
            image = draw_text(image, f"语音: {voice_text}", (10, 110), 0.6, (0, 255, 255), False, chinese_font_path)

            # 绘制语音识别的原始文本
            if V_LAST_SPEECH[0]:
                image = draw_text(image, f"识别: {V_LAST_SPEECH[0]}", (10, 150), 0.6, (255, 255, 255), False,
                                  chinese_font_path)

            if baseline_ear is None:
                calib_text = f"眼睛校准中...({frame_count}/{CALIBRATION_FRAMES}) 请正视前方"
                image = draw_text(image, calib_text, (10, 190), 0.6, (0, 165, 255), False, chinese_font_path)
            else:
                threshold_text = f"动态闭眼阈值: {dynamic_eye_threshold:.2f} (基准: {baseline_ear:.2f})"
                image = draw_text(image, threshold_text, (10, 190), 0.6, (0, 255, 0), False, chinese_font_path)

            image = draw_text(image, serial_status, (10, 230), 0.6, (200, 200, 200), False, chinese_font_path)

            # 【核心功能】绘制最后发送的命令
            image = draw_text(image, f"最后命令: {LAST_COMMAND_SENT[0]}", (10, 270), 0.6, (255, 100, 255), False,
                              chinese_font_path)

            settings_button.draw(image)
            image = draw_text(image, "按ESC退出", (10, image.shape[0] - 25), 0.5, (128, 128, 128), False,
                              chinese_font_path)
            cv2.imshow(WINDOW_NAME, image)

            # 5. 按键和按钮点击处理
            key = cv2.waitKey(5) & 0xFF
            if key == 27: break

            if key == ord('s') or settings_button.is_clicked(mouse_click_pos):
                mouse_click_pos = None
                try:
                    tk_root.deiconify()
                    show_settings_window(tk_root)
                finally:
                    tk_root.withdraw()

    # 6. 释放资源
    cap.release()
    cv2.destroyAllWindows()
    if ser and ser.is_open: ser.close()


if __name__ == "__main__":
    tk_root = tk.Tk()
    tk_root.withdraw()
    main(tk_root)