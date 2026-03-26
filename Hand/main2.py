import cv2
import mediapipe as mp
import numpy as np
import math
import time
import base64
import os

from web_bridge import publish_hand_snapshot, publish_hand_command, publish_hand_frame

# --- 1. MediaPipe 初始化 ---
MP_HAS_SOLUTIONS = hasattr(mp, "solutions")
if MP_HAS_SOLUTIONS:
    mp_hands = mp.solutions.hands
    mp_drawing = mp.solutions.drawing_utils
    mp_drawing_styles = mp.solutions.drawing_styles

BaseOptions = mp.tasks.BaseOptions
HandLandmarker = mp.tasks.vision.HandLandmarker
HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
HandLandmarkerResult = mp.tasks.vision.HandLandmarkerResult
VisionRunningMode = mp.tasks.vision.RunningMode

try:
    from mediapipe.framework.formats import landmark_pb2
except Exception:
    landmark_pb2 = None

detection_results = None
LOCAL_PREVIEW = os.getenv("DRIP_LOCAL_PREVIEW", "0") == "1"


def print_result(result: HandLandmarkerResult, output_image: mp.Image, timestamp_ms: int):
    global detection_results
    detection_results = result


options = HandLandmarkerOptions(
    base_options=BaseOptions(model_asset_path='hand_landmarker.task'),
    running_mode=VisionRunningMode.LIVE_STREAM,
    num_hands=2,
    result_callback=print_result
)


# --- 2. LED 模拟状态变量 (修改) ---

# 定义一个类来管理每个LED列的状态
class LEDColumn:
    def __init__(self, num_leds=8):
        # <--- 修改: 初始化一个包含8个LED状态的列表
        self.leds = []
        for _ in range(num_leds):
            self.leds.append({
                'brightness': 128,  # 0-255
                'color_idx': 0,
                'is_on': True
            })
        self.selected_led_index = -1  # 当前没有选中的LED


# LED 颜色列表 (BGR 格式)
LED_COLORS = [(0, 0, 255), (0, 255, 0), (255, 0, 0), (255, 255, 0), (0, 255, 255), (255, 0, 255)]

# --- 3. 手势识别状态变量 ---
hand_data = {
    'Left': {'last_wrist_y': None, 'last_wrist_x': None, 'last_detection_time': time.time(),
             'last_open_time': 0, 'last_closed_time': 0, 'last_v_sign_time': 0, 'last_motion_emit': 0},
    'Right': {'last_wrist_y': None, 'last_wrist_x': None, 'last_detection_time': time.time(),
              'last_open_time': 0, 'last_closed_time': 0, 'last_v_sign_time': 0, 'last_motion_emit': 0}
}

BRIGHTNESS_SENSITIVITY = 0.8
SPEED_SENSITIVITY = 0.05
FINGER_EXTENDED_THRESHOLD = 0.05
SWIPE_SPEED_THRESHOLD = 150
VERTICAL_SPEED_THRESHOLD = 50
DEBOUNCE_TIME = 0.5
HAND_COMMAND_COOLDOWN = 0.4

THUMB_TIP = 4
INDEX_FINGER_TIP = 8
MIDDLE_FINGER_TIP = 12
RING_FINGER_TIP = 16
PINKY_FINGER_TIP = 20
WRIST = 0


def open_camera(index=0):
    # Windows 下优先使用 DirectShow，可显著缩短摄像头启动等待
    if os.name == "nt":
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(index)
    else:
        cap = cv2.VideoCapture(index)

    if cap and cap.isOpened():
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)
        if hasattr(cv2, "CAP_PROP_BUFFERSIZE"):
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return cap


# --- 手势判断函数 ---
def is_finger_extended(landmarks, tip_idx, pip_idx):
    # 通过比较指尖和指关节的距离来判断手指是否伸直
    tip_point = np.array([landmarks[tip_idx].x, landmarks[tip_idx].y])
    pip_point = np.array([landmarks[pip_idx].x, landmarks[pip_idx].y])
    base_point = np.array([landmarks[pip_idx - 1].x, landmarks[pip_idx - 1].y])

    # 简单的距离判断可能不够准确，改为判断Y坐标
    # 对于竖直的手，指尖的Y坐标应该远小于关节的Y坐标
    return landmarks[tip_idx].y < landmarks[pip_idx].y


def is_hand_open(landmarks):
    return (is_finger_extended(landmarks, INDEX_FINGER_TIP, INDEX_FINGER_TIP - 2) and
            is_finger_extended(landmarks, MIDDLE_FINGER_TIP, MIDDLE_FINGER_TIP - 2) and
            is_finger_extended(landmarks, RING_FINGER_TIP, RING_FINGER_TIP - 2) and
            is_finger_extended(landmarks, PINKY_FINGER_TIP, PINKY_FINGER_TIP - 2))


def is_hand_closed(landmarks):
    # 如果所有四个手指的指尖Y坐标都大于它们中间关节的Y坐标，则认为是握拳
    return (landmarks[INDEX_FINGER_TIP].y > landmarks[INDEX_FINGER_TIP - 2].y and
            landmarks[MIDDLE_FINGER_TIP].y > landmarks[MIDDLE_FINGER_TIP - 2].y and
            landmarks[RING_FINGER_TIP].y > landmarks[RING_FINGER_TIP - 2].y and
            landmarks[PINKY_FINGER_TIP].y > landmarks[PINKY_FINGER_TIP - 2].y)


# <--- 新增: V字手势判断
def is_victory_sign(landmarks):
    index_extended = is_finger_extended(landmarks, INDEX_FINGER_TIP, INDEX_FINGER_TIP - 2)
    middle_extended = is_finger_extended(landmarks, MIDDLE_FINGER_TIP, MIDDLE_FINGER_TIP - 2)
    ring_bent = not is_finger_extended(landmarks, RING_FINGER_TIP, RING_FINGER_TIP - 2)
    pinky_bent = not is_finger_extended(landmarks, PINKY_FINGER_TIP, PINKY_FINGER_TIP - 2)
    return index_extended and middle_extended and ring_bent and pinky_bent


# --- 4. 主循环 ---
def main():
    global detection_results

    cap = open_camera(0)
    if not cap.isOpened():
        print("无法打开摄像头")
        return

    # <--- 修改: 初始化两个LED列，每列8个LED
    led_column_left = LEDColumn(num_leds=8)
    led_column_right = LEDColumn(num_leds=8)

    with HandLandmarker.create_from_options(options) as detector:
        last_frame_push = 0.0
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.flip(frame, 1)
            H, W, _ = frame.shape
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            detector.detect_async(mp_image, time.time_ns() // 1_000_000)

            current_loop_time = time.time()
            gesture_display_info = []

            # 重置选中状态
            led_column_left.selected_led_index = -1
            led_column_right.selected_led_index = -1

            if detection_results and detection_results.hand_landmarks:
                for idx, hand_landmarks in enumerate(detection_results.hand_landmarks):
                    hand_label = detection_results.handedness[idx][0].category_name
                    current_hand_history = hand_data[hand_label]

                    if MP_HAS_SOLUTIONS and landmark_pb2 is not None:
                        landmark_list_for_drawing = landmark_pb2.NormalizedLandmarkList()
                        for lm in hand_landmarks:
                            landmark_for_drawing = landmark_list_for_drawing.landmark.add()
                            landmark_for_drawing.x, landmark_for_drawing.y, landmark_for_drawing.z = lm.x, lm.y, lm.z

                        mp_drawing.draw_landmarks(frame, landmark_list_for_drawing, mp_hands.HAND_CONNECTIONS,
                                                  mp_drawing_styles.get_default_hand_landmarks_style(),
                                                  mp_drawing_styles.get_default_hand_connections_style())

                    wrist_landmark = hand_landmarks[WRIST]
                    current_wrist_y = wrist_landmark.y * H
                    current_wrist_x = wrist_landmark.x * W
                    time_diff = current_loop_time - current_hand_history['last_detection_time']
                    wrist_speed_y = 0
                    if current_hand_history['last_wrist_y'] is not None and time_diff > 0:
                        wrist_speed_y = (current_wrist_y - current_hand_history['last_wrist_y']) / time_diff

                    # --- 新的LED控制逻辑 ---
                    target_led_column = led_column_left if hand_label == 'Left' else led_column_right

                    # 1. 根据手的高度选择LED
                    # 将手的Y坐标 (0, H) 映射到LED索引 (0, 7)
                    # 我们只用画面中间80%的区域进行映射，边缘区域不触发
                    y_margin = H * 0.1
                    if y_margin < current_wrist_y < H - y_margin:
                        # 线性映射
                        selected_led_index = int(np.interp(current_wrist_y, [y_margin, H - y_margin], [0, 7]))
                        target_led_column.selected_led_index = selected_led_index
                        gesture_display_info.append(f"{hand_label} selects LED {selected_led_index}")

                        # 2. 控制选中的LED
                        selected_led = target_led_column.leds[selected_led_index]

                        # 亮度控制
                        if abs(wrist_speed_y) > VERTICAL_SPEED_THRESHOLD:
                            change = abs(wrist_speed_y) * BRIGHTNESS_SENSITIVITY * time_diff
                            if wrist_speed_y < 0:  # 向上
                                selected_led['brightness'] = min(255, selected_led['brightness'] + change)
                            else:  # 向下
                                selected_led['brightness'] = max(0, selected_led['brightness'] - change)
                            gesture_display_info.append(f"  -> BRT: {int(selected_led['brightness'])}")

                            if current_loop_time - current_hand_history['last_motion_emit'] > HAND_COMMAND_COOLDOWN:
                                action = "moveUp" if wrist_speed_y < 0 else "moveDown"
                                publish_hand_command(action, {"hand": hand_label, "speed": abs(wrist_speed_y)})
                                current_hand_history['last_motion_emit'] = current_loop_time

                        # 颜色切换 (张开手)
                        if is_hand_open(hand_landmarks) and current_loop_time - current_hand_history[
                            'last_open_time'] > DEBOUNCE_TIME:
                            selected_led['color_idx'] = (selected_led['color_idx'] + 1) % len(LED_COLORS)
                            current_hand_history['last_open_time'] = current_loop_time
                            gesture_display_info.append(f"  -> CLR Change")
                            publish_hand_command("rotateLeft", {"hand": hand_label})

                        # 开关 (握拳)
                        if is_hand_closed(hand_landmarks) and current_loop_time - current_hand_history[
                            'last_closed_time'] > DEBOUNCE_TIME:
                            selected_led['is_on'] = not selected_led['is_on']
                            current_hand_history['last_closed_time'] = current_loop_time
                            gesture_display_info.append(f"  -> Toggle ON/OFF")
                            publish_hand_command("rotateRight", {"hand": hand_label})

                        # 全体点亮 (V字手势)
                        if is_victory_sign(hand_landmarks) and current_loop_time - current_hand_history[
                            'last_v_sign_time'] > DEBOUNCE_TIME:
                            current_color_idx = selected_led['color_idx']
                            for led in target_led_column.leds:
                                led['is_on'] = True
                                led['brightness'] = 255
                                led['color_idx'] = current_color_idx
                            current_hand_history['last_v_sign_time'] = current_loop_time
                            gesture_display_info.append(f"  -> V-Sign: Fill All!")
                            publish_hand_command("stop", {"hand": hand_label})

                    # 更新历史数据
                    current_hand_history['last_wrist_y'] = current_wrist_y
                    current_hand_history['last_detection_time'] = current_loop_time

            # --- 5. 模拟 LED 显示 (修改) ---
            draw_led_column(frame, led_column_left, 50, "Left Column (L-Hand)")
            draw_led_column(frame, led_column_right, W - 150, "Right Column (R-Hand)")

            # 显示手势信息
            y_offset = 30
            for line in gesture_display_info:
                cv2.putText(frame, line, (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                y_offset += 25

            if LOCAL_PREVIEW:
                cv2.imshow('Hand Gesture LED Control', frame)

            now_ts = time.time()
            if now_ts - last_frame_push > 0.35:
                preview = cv2.resize(frame, (480, int(frame.shape[0] * 480 / frame.shape[1])))
                success, buffer = cv2.imencode('.jpg', preview, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
                if success:
                    encoded = base64.b64encode(buffer).decode('ascii')
                    publish_hand_frame(encoded)
                    last_frame_push = now_ts

            publish_hand_snapshot({
                "gestures": gesture_display_info,
                "left": serialize_led_column(led_column_left),
                "right": serialize_led_column(led_column_right),
            })
            if LOCAL_PREVIEW and cv2.waitKey(1) & 0xFF == 27:
                break

    cap.release()
    if LOCAL_PREVIEW:
        cv2.destroyAllWindows()


# <--- 修改: 绘制单个LED列的辅助函数
def draw_led_column(frame, led_column, x_start, label):
    H, W, _ = frame.shape
    num_leds = len(led_column.leds)

    # 计算每个LED的尺寸和间距
    column_height = H * 0.8
    led_height = column_height / num_leds
    gap = led_height * 0.2
    effective_led_height = led_height - gap

    y_start = H * 0.1

    cv2.putText(frame, label, (x_start, int(y_start - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    for i, led in enumerate(led_column.leds):
        led_y_start = int(y_start + i * led_height)
        led_y_end = int(led_y_start + effective_led_height)

        # 获取颜色和亮度
        led_color_bgr = LED_COLORS[led['color_idx']]
        if led['is_on']:
            brightness_factor = led['brightness'] / 255.0
            display_color = (int(led_color_bgr[0] * brightness_factor),
                             int(led_color_bgr[1] * brightness_factor),
                             int(led_color_bgr[2] * brightness_factor))
        else:
            display_color = (30, 30, 30)  # 关闭状态为深灰色

        # 绘制LED
        cv2.rectangle(frame, (x_start, led_y_start), (x_start + 50, led_y_end), display_color, -1)

        # 如果是当前选中的LED，高亮显示边框
        if i == led_column.selected_led_index:
            cv2.rectangle(frame, (x_start, led_y_start), (x_start + 50, led_y_end), (255, 255, 255), 3)  # 白色粗边框
        else:
            cv2.rectangle(frame, (x_start, led_y_start), (x_start + 50, led_y_end), (100, 100, 100), 1)  # 灰色细边框


def serialize_led_column(led_column):
    return [
        {
            "is_on": bool(led['is_on']),
            "brightness": int(led['brightness']),
            "color": bgr_to_hex(LED_COLORS[led['color_idx']]),
            "selected": i == led_column.selected_led_index,
        }
        for i, led in enumerate(led_column.leds)
    ]


def bgr_to_hex(color_bgr):
    b, g, r = color_bgr
    return f"#{r:02X}{g:02X}{b:02X}"


if __name__ == "__main__":
    main()