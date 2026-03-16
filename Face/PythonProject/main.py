import cv2
import mediapipe as mp
import time
import tkinter as tk
import os
from pathlib import Path
from tkinter import messagebox
from urllib import request
import numpy as np
import base64

import config as app_config
from config import CONFIG, load_config, LEFT_EYE_EAR_POINTS, RIGHT_EYE_EAR_POINTS, LAST_COMMAND_SENT
from serial_comms import initialize_serial, send_command, receive_data
from face_analysis import eye_aspect_ratio, mouth_aspect_ratio, detect_face_direction
from ui_utils import show_settings_window, get_chinese_font, draw_text
from ui_manager import Button
from web_bridge import publish_face_snapshot, publish_face_frame

# 全局变量
mouse_click_pos = None
current_face_status = "等待检测..."
WINDOW_NAME = "Face Control"
LOCAL_PREVIEW = os.getenv("DRIP_LOCAL_PREVIEW", "0") == "1"
FACE_TASK_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
    "face_landmarker/float16/latest/face_landmarker.task"
)
FACE_TASK_MODEL_PATH = Path(__file__).resolve().with_name("face_landmarker.task")

# Tasks 模式下的人脸轮廓线索引（基于 FaceMesh 常用关键点）
FACE_CONTOUR_PATHS = [
    # 脸部外轮廓
    [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377,
     152, 148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109, 10],
    # 左眉
    [70, 63, 105, 66, 107, 55, 65, 52, 53, 46],
    # 右眉
    [336, 296, 334, 293, 300, 285, 295, 282, 283, 276],
    # 左眼
    [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246, 33],
    # 右眼
    [263, 249, 390, 373, 374, 380, 381, 382, 362, 398, 384, 385, 386, 387, 388, 466, 263],
    # 鼻梁/鼻翼
    [168, 6, 197, 195, 5, 4, 1, 19, 94, 2, 164, 0],
    # 外唇
    [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 308, 324, 318, 402, 317, 14, 87, 178,
     88, 95, 61],
    # 内唇
    [78, 191, 80, 81, 82, 13, 312, 311, 310, 415, 308, 324, 318, 402, 317, 14, 87, 178, 88, 95, 78],
]


def mouse_callback(event, x, y, flags, param):
    """处理鼠标点击事件"""
    global mouse_click_pos
    if event == cv2.EVENT_LBUTTONDOWN:
        mouse_click_pos = (x, y)


def ensure_face_task_model() -> str:
    """确保 FaceLandmarker 模型存在，缺失时自动下载。"""
    if FACE_TASK_MODEL_PATH.exists():
        return str(FACE_TASK_MODEL_PATH)

    print("未检测到 face_landmarker.task，开始下载模型...")
    request.urlretrieve(FACE_TASK_MODEL_URL, str(FACE_TASK_MODEL_PATH))
    print(f"模型下载完成: {FACE_TASK_MODEL_PATH}")
    return str(FACE_TASK_MODEL_PATH)


def draw_tasks_landmarks(image, landmarks):
    """在 Tasks API 返回的关键点上绘制人脸轮廓线。"""
    h, w, _ = image.shape
    points = [(int(lm.x * w), int(lm.y * h)) for lm in landmarks]

    for path in FACE_CONTOUR_PATHS:
        last_idx = None
        for idx in path:
            if idx < 0 or idx >= len(points):
                last_idx = None
                continue
            if last_idx is not None:
                cv2.line(image, points[last_idx], points[idx], (0, 255, 0), 1, cv2.LINE_AA)
            last_idx = idx


def main(tk_root):
    """主程序入口"""
    global current_face_status, mouse_click_pos

    # 初始化
    load_config()
    initialize_serial()
    chinese_font_path = get_chinese_font()

    # 初始化摄像头
    cap = cv2.VideoCapture(CONFIG.get('CAMERA_INDEX', 0))
    if not cap.isOpened():
        messagebox.showerror("错误", "无法打开摄像头。请检查设备和配置。")
        return

    # 初始化MediaPipe Face Mesh（若可用）
    mp_face_mesh = None
    face_mesh = None
    face_landmarker = None
    use_tasks_api = not hasattr(mp, "solutions")
    if not use_tasks_api:
        mp_face_mesh = mp.solutions.face_mesh
        face_mesh = mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
    else:
        try:
            model_path = ensure_face_task_model()
            BaseOptions = mp.tasks.BaseOptions
            VisionRunningMode = mp.tasks.vision.RunningMode
            FaceLandmarker = mp.tasks.vision.FaceLandmarker
            FaceLandmarkerOptions = mp.tasks.vision.FaceLandmarkerOptions
            face_landmarker = FaceLandmarker.create_from_options(
                FaceLandmarkerOptions(
                    base_options=BaseOptions(model_asset_path=model_path),
                    running_mode=VisionRunningMode.VIDEO,
                    num_faces=1,
                )
            )
            print("已启用 MediaPipe Tasks FaceLandmarker。")
        except Exception as e:
            messagebox.showerror("错误", f"初始化 FaceLandmarker 失败: {e}")
            cap.release()
            return

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
    last_frame_push = 0.0
    face_command_status = [""]

    if LOCAL_PREVIEW:
        cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
        cv2.setMouseCallback(WINDOW_NAME, mouse_callback)

    while cap.isOpened():
        success, image = cap.read()
        if not success:
            break

        # 翻转图像，使其像镜子
        image = cv2.flip(image, 1)
        results = None
        task_face_landmarks = None

        if use_tasks_api:
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_image)
            task_result = face_landmarker.detect_for_video(mp_image, int(time.time() * 1000))
            if task_result.face_landmarks:
                task_face_landmarks = task_result.face_landmarks[0]
        else:
            image.flags.writeable = False
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            results = face_mesh.process(rgb_image)
            image.flags.writeable = True

        # **关键修改 2: 动态获取尺寸和计算 UI 元素位置**
        h, w, _ = image.shape
        padding = int(h * 0.02)  # 2% of height for padding
        line_height = int(h * 0.045)  # 4.5% of height for line spacing
        font_scale = h / 720 * 0.6  # Base font scale on a standard 720p height

        settings_button = None
        if LOCAL_PREVIEW:
            SETTINGS_BUTTON_WIDTH = int(w * 0.12)
            SETTINGS_BUTTON_HEIGHT = int(h * 0.05)
            button_x = w - SETTINGS_BUTTON_WIDTH - padding
            button_y = padding
            settings_button = Button(
                (button_x, button_y),
                SETTINGS_BUTTON_WIDTH,
                SETTINGS_BUTTON_HEIGHT,
                "设置"
            )

            if mouse_click_pos and settings_button.is_clicked(mouse_click_pos):
                show_settings_window(tk_root)
                mouse_click_pos = None

        landmarks = None
        direction = "LOOK_CENTER"
        current_eye_state = last_eye_state
        current_mouth_state = last_mouth_state
        has_face = bool(task_face_landmarks) if use_tasks_api else bool(results and results.multi_face_landmarks)
        if has_face:
            landmarks = task_face_landmarks if use_tasks_api else results.multi_face_landmarks[0].landmark

            # 人脸网格绘制 (如果配置开启)
            if CONFIG['DRAW_MESH']:
                if use_tasks_api:
                    draw_tasks_landmarks(image, landmarks)
                else:
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
                        command = "DEFAULT"
                    last_direction = direction

                if command:
                    send_command(command, None, face_command_status, event_channel="face")
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

        publish_face_snapshot({
            "status_text": current_face_status,
            "eye": current_eye_state,
            "mouth": current_mouth_state,
            "direction": direction,
            "calibrated": calibrated,
            "serial_status": app_config.serial_status,
            "last_command": LAST_COMMAND_SENT[0],
        })

        now_ts = time.time()
        if now_ts - last_frame_push > 0.35:
            preview = cv2.resize(image, (480, int(image.shape[0] * 480 / image.shape[1])))
            success, buffer = cv2.imencode(".jpg", preview, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
            if success:
                encoded = base64.b64encode(buffer).decode("ascii")
                publish_face_frame(encoded)
                last_frame_push = now_ts

        if LOCAL_PREVIEW:
            current_line_y = padding

            title_text = "智能语音表情交互系统"
            title_size_px = cv2.getTextSize(title_text, cv2.FONT_HERSHEY_SIMPLEX, font_scale * 1.5, 3)[0]
            title_x = (w - title_size_px[0]) // 2

            current_line_y += line_height
            image = draw_text(image, title_text, (title_x, current_line_y), font_scale * 1.3, (0, 255, 0), True,
                              chinese_font_path)

            current_line_y += int(line_height * 1.5)
            image = draw_text(image, "表情状态:", (padding, current_line_y), font_scale * 1.1, (255, 255, 255), True,
                              chinese_font_path)
            current_line_y += line_height
            image = draw_text(image, current_face_status, (padding, current_line_y), font_scale, (255, 255, 0), False,
                              chinese_font_path)

        if LOCAL_PREVIEW:
            current_line_y += int(line_height * 1.5)
            if not calibrated:
                threshold_text = f"校准中... ({len(ear_history)}/{CALIBRATION_FRAMES})"
                image = draw_text(image, threshold_text, (padding, current_line_y), font_scale, (0, 165, 255), False,
                                  chinese_font_path)
            else:
                threshold_text = f"动态闭眼阈值: {dynamic_eye_threshold:.2f} (基准: {baseline_ear:.2f})"
                image = draw_text(image, threshold_text, (padding, current_line_y), font_scale, (0, 255, 0), False,
                                  chinese_font_path)

            current_line_y += int(line_height * 1.5)
            image = draw_text(image, app_config.serial_status, (padding, current_line_y), font_scale, (200, 200, 200), False,
                              chinese_font_path)
            current_line_y += line_height
            image = draw_text(image, f"最后命令: {LAST_COMMAND_SENT[0]}", (padding, current_line_y), font_scale,
                              (255, 100, 255), False,
                              chinese_font_path)

            if settings_button:
                image = settings_button.draw(image)

            exit_text = "按ESC退出"
            image = draw_text(image, exit_text, (padding, h - padding), font_scale * 0.8, (128, 128, 128), False,
                              chinese_font_path)

            cv2.imshow(WINDOW_NAME, image)

            key = cv2.waitKey(5) & 0xFF
            if key == 27:
                break

    # 清理资源
    if face_mesh:
        face_mesh.close()
    if face_landmarker:
        face_landmarker.close()
    cap.release()
    if LOCAL_PREVIEW:
        cv2.destroyAllWindows()
    # 退出前关闭串口
    if app_config.ser and app_config.ser.is_open:
        try:
            app_config.ser.close()
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