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
last_hand_timestamp_ms = 0


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
             'last_open_time': 0, 'last_closed_time': 0, 'last_v_sign_time': 0, 'last_motion_emit': 0,
             'last_ring_select_time': 0, 'active_ring': 'A', 'ring_candidate': None, 'ring_candidate_count': 0},
    'Right': {'last_wrist_y': None, 'last_wrist_x': None, 'last_detection_time': time.time(),
              'last_open_time': 0, 'last_closed_time': 0, 'last_v_sign_time': 0, 'last_motion_emit': 0,
              'last_ring_select_time': 0, 'active_ring': 'A', 'ring_candidate': None, 'ring_candidate_count': 0,
              'last_direction_action': None, 'last_direction_emit': 0}
}

BRIGHTNESS_SENSITIVITY = 0.8
SPEED_SENSITIVITY = 0.05
FINGER_EXTENDED_THRESHOLD = 0.05
SWIPE_SPEED_THRESHOLD = 150
VERTICAL_SPEED_THRESHOLD = 50
DEBOUNCE_TIME = 0.5
HAND_COMMAND_COOLDOWN = 0.4
RING_SELECT_COOLDOWN = 0.5

THUMB_TIP = 4
INDEX_FINGER_TIP = 8
MIDDLE_FINGER_TIP = 12
RING_FINGER_TIP = 16
PINKY_FINGER_TIP = 20
WRIST = 0
THUMB_IP = 3
THUMB_MCP = 2
INDEX_FINGER_PIP = 6
MIDDLE_FINGER_PIP = 10
RING_FINGER_PIP = 14
PINKY_FINGER_PIP = 18
INDEX_FINGER_MCP = 5


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
    # 使用相对手腕距离判断手指是否伸直，减少对手掌朝向的依赖。
    wrist = landmarks[WRIST]
    tip_to_wrist = distance_2d(landmarks[tip_idx], wrist)
    pip_to_wrist = distance_2d(landmarks[pip_idx], wrist)
    mcp_to_wrist = distance_2d(landmarks[pip_idx - 1], wrist)
    return tip_to_wrist > pip_to_wrist * 1.06 and tip_to_wrist > mcp_to_wrist * 1.12


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


def distance_2d(p1, p2):
    return float(np.linalg.norm(np.array([p1.x, p1.y]) - np.array([p2.x, p2.y])))


def detect_ring_gesture(landmarks):
    thumb_tip = landmarks[THUMB_TIP]
    thumb_ip = landmarks[THUMB_IP]
    thumb_mcp = landmarks[THUMB_MCP]
    wrist = landmarks[WRIST]
    index_tip = landmarks[INDEX_FINGER_TIP]
    index_mcp = landmarks[INDEX_FINGER_MCP]
    middle_mcp = landmarks[9]
    ring_mcp = landmarks[13]
    pinky_mcp = landmarks[17]

    index_extended = is_finger_extended(landmarks, INDEX_FINGER_TIP, INDEX_FINGER_PIP)
    middle_extended = is_finger_extended(landmarks, MIDDLE_FINGER_TIP, MIDDLE_FINGER_PIP)
    ring_extended = is_finger_extended(landmarks, RING_FINGER_TIP, RING_FINGER_PIP)
    pinky_extended = is_finger_extended(landmarks, PINKY_FINGER_TIP, PINKY_FINGER_PIP)

    other_four_extended = index_extended and middle_extended and ring_extended and pinky_extended
    other_four_bent = (not index_extended) and (not middle_extended) and (not ring_extended) and (not pinky_extended)

    palm_scale = max(distance_2d(index_mcp, wrist), 1e-4)
    thumb_length_ratio = distance_2d(thumb_tip, thumb_mcp) / palm_scale
    thumb_index_ratio = distance_2d(thumb_tip, index_tip) / palm_scale
    thumb_wrist_ratio = distance_2d(thumb_tip, wrist) / palm_scale
    thumb_middle_mcp_ratio = distance_2d(thumb_tip, middle_mcp) / palm_scale
    palm_center_x = (wrist.x + index_mcp.x + middle_mcp.x + ring_mcp.x + pinky_mcp.x) / 5.0
    palm_center_y = (wrist.y + index_mcp.y + middle_mcp.y + ring_mcp.y + pinky_mcp.y) / 5.0
    thumb_palm_center_ratio = float(np.linalg.norm(np.array([thumb_tip.x - palm_center_x, thumb_tip.y - palm_center_y]))) / palm_scale
    finger_spread_ratio = distance_2d(landmarks[INDEX_FINGER_TIP], landmarks[PINKY_FINGER_TIP]) / palm_scale

    # 拇指弯曲角度（IP 点）：越小表示越弯曲。
    def angle_deg(a, b, c):
        ba = np.array([a.x - b.x, a.y - b.y], dtype=float)
        bc = np.array([c.x - b.x, c.y - b.y], dtype=float)
        na = np.linalg.norm(ba)
        nc = np.linalg.norm(bc)
        if na < 1e-6 or nc < 1e-6:
            return 180.0
        cosv = float(np.dot(ba, bc) / (na * nc))
        cosv = max(-1.0, min(1.0, cosv))
        return float(np.degrees(np.arccos(cosv)))

    thumb_ip_angle = angle_deg(thumb_tip, thumb_ip, thumb_mcp)

    finger_tip_mcp_ratios = [
        distance_2d(landmarks[INDEX_FINGER_TIP], index_mcp) / palm_scale,
        distance_2d(landmarks[MIDDLE_FINGER_TIP], middle_mcp) / palm_scale,
        distance_2d(landmarks[RING_FINGER_TIP], ring_mcp) / palm_scale,
        distance_2d(landmarks[PINKY_FINGER_TIP], pinky_mcp) / palm_scale,
    ]
    avg_tip_mcp = sum(finger_tip_mcp_ratios) / 4.0
    curled_count = sum(1 for r in finger_tip_mcp_ratios if r < 0.62)
    semi_curled_count = sum(1 for r in finger_tip_mcp_ratios if r < 0.82)
    extended_count = sum(1 for r in finger_tip_mcp_ratios if r > 0.78)

    def sat(v, lo, hi):
        if v <= lo:
            return 0.0
        if v >= hi:
            return 1.0
        return (v - lo) / (hi - lo)

    # C/D 依赖卷曲程度，A/B 依赖拇指开合与四指伸缩。
    score_a = (
        sat(curled_count, 2.5, 4.0)
        * sat(thumb_index_ratio, 0.48, 0.80)
        * sat(thumb_middle_mcp_ratio, 0.66, 0.95)
        * sat(thumb_wrist_ratio, 0.62, 0.95)
    )
    score_b = (
        sat(extended_count, 3.2, 4.0)
        * sat(avg_tip_mcp, 0.62, 1.05)
        * sat(finger_spread_ratio, 0.38, 0.95)
        * sat(0.62 - thumb_palm_center_ratio, 0.06, 0.34)
        * sat(0.98 - thumb_index_ratio, 0.05, 0.45)
        * sat(0.55 - thumb_middle_mcp_ratio, 0.05, 0.30)
    )
    score_c = (
        sat(semi_curled_count, 2.5, 4.0)
        * sat(avg_tip_mcp, 0.42, 0.70)
        * sat(0.90 - avg_tip_mcp, 0.06, 0.35)
        * sat(thumb_index_ratio, 0.38, 0.85)
    )
    score_d = (
        sat(curled_count, 3.2, 4.0)
        * sat(0.62 - avg_tip_mcp, 0.08, 0.28)
        * sat(0.60 - thumb_index_ratio, 0.06, 0.30)
        * sat(0.78 - thumb_middle_mcp_ratio, 0.08, 0.30)
    )

    scores = {
        "A": score_a,
        "B": score_b,
        "C": score_c,
        "D": score_d,
    }

    # B 手势强规则: 四指伸直且有展开，拇指收在掌心。
    palm_mcp_avg_y = (index_mcp.y + middle_mcp.y + ring_mcp.y + pinky_mcp.y) / 4.0
    palm_x_min = min(index_mcp.x, pinky_mcp.x) - 0.08
    palm_x_max = max(index_mcp.x, pinky_mcp.x) + 0.08
    thumb_inside_palm_box = (
        palm_x_min <= thumb_tip.x <= palm_x_max
        and thumb_tip.y >= (palm_mcp_avg_y - 0.08)
    )
    thumb_folded_in_palm = (
        thumb_palm_center_ratio < 0.58
        and thumb_index_ratio < 0.92
        and thumb_middle_mcp_ratio < 0.45
        and thumb_ip_angle < 170.0
    )
    if other_four_extended and finger_spread_ratio > 0.40 and thumb_folded_in_palm and (
        thumb_inside_palm_box or thumb_palm_center_ratio < 0.40
    ):
        return "B"

    best_ring = max(scores, key=scores.get)
    best_score = scores[best_ring]
    second_score = max(v for k, v in scores.items() if k != best_ring)
    if best_score < 0.22 or (best_score - second_score) < 0.05:
        return None
    return best_ring


def get_b_debug_metrics(landmarks):
    wrist = landmarks[WRIST]
    index_mcp = landmarks[INDEX_FINGER_MCP]
    middle_mcp = landmarks[9]
    ring_mcp = landmarks[13]
    pinky_mcp = landmarks[17]
    thumb_tip = landmarks[THUMB_TIP]
    thumb_mcp = landmarks[THUMB_MCP]

    palm_scale = max(distance_2d(index_mcp, wrist), 1e-4)
    finger_spread_ratio = distance_2d(landmarks[INDEX_FINGER_TIP], landmarks[PINKY_FINGER_TIP]) / palm_scale
    thumb_index_ratio = distance_2d(thumb_tip, landmarks[INDEX_FINGER_TIP]) / palm_scale
    thumb_middle_mcp_ratio = distance_2d(thumb_tip, middle_mcp) / palm_scale
    palm_center_x = (wrist.x + index_mcp.x + middle_mcp.x + ring_mcp.x + pinky_mcp.x) / 5.0
    palm_center_y = (wrist.y + index_mcp.y + middle_mcp.y + ring_mcp.y + pinky_mcp.y) / 5.0
    thumb_palm_center_ratio = float(np.linalg.norm(np.array([thumb_tip.x - palm_center_x, thumb_tip.y - palm_center_y]))) / palm_scale
    finger_tip_mcp_ratios = [
        distance_2d(landmarks[INDEX_FINGER_TIP], index_mcp) / palm_scale,
        distance_2d(landmarks[MIDDLE_FINGER_TIP], middle_mcp) / palm_scale,
        distance_2d(landmarks[RING_FINGER_TIP], ring_mcp) / palm_scale,
        distance_2d(landmarks[PINKY_FINGER_TIP], pinky_mcp) / palm_scale,
    ]
    avg_tip_mcp = sum(finger_tip_mcp_ratios) / 4.0
    extended_count = sum(1 for r in finger_tip_mcp_ratios if r > 0.78)

    return {
        "spread": round(finger_spread_ratio, 2),
        "thumbPalm": round(thumb_palm_center_ratio, 2),
        "thumbIdx": round(thumb_index_ratio, 2),
        "thumbMid": round(thumb_middle_mcp_ratio, 2),
        "avgTip": round(avg_tip_mcp, 2),
        "ext": int(extended_count),
    }


def detect_index_direction_gesture(landmarks):
    """右手食指指向识别: up/down/left/right。"""
    index_extended = is_finger_extended(landmarks, INDEX_FINGER_TIP, INDEX_FINGER_PIP)
    middle_bent = not is_finger_extended(landmarks, MIDDLE_FINGER_TIP, MIDDLE_FINGER_PIP)
    ring_bent = not is_finger_extended(landmarks, RING_FINGER_TIP, RING_FINGER_PIP)
    pinky_bent = not is_finger_extended(landmarks, PINKY_FINGER_TIP, PINKY_FINGER_PIP)
    if not (index_extended and middle_bent and ring_bent and pinky_bent):
        return None

    mcp = landmarks[INDEX_FINGER_MCP]
    tip = landmarks[INDEX_FINGER_TIP]
    dx = tip.x - mcp.x
    dy = tip.y - mcp.y
    magnitude = math.hypot(dx, dy)
    if magnitude < 0.10:
        return None

    if abs(dx) > abs(dy) * 1.2:
        return "right" if dx > 0 else "left"
    if abs(dy) > abs(dx) * 1.2:
        return "down" if dy > 0 else "up"
    return None


def is_stop_pose_hand(landmarks):
    """单只手是否满足停止手势的姿态要求。"""
    try:
        index_extended = is_finger_extended(landmarks, INDEX_FINGER_TIP, INDEX_FINGER_PIP)
        middle_bent = not is_finger_extended(landmarks, MIDDLE_FINGER_TIP, MIDDLE_FINGER_PIP)
        ring_bent = not is_finger_extended(landmarks, RING_FINGER_TIP, RING_FINGER_PIP)
        pinky_bent = not is_finger_extended(landmarks, PINKY_FINGER_TIP, PINKY_FINGER_PIP)
        thumb_bent = landmarks[THUMB_TIP].y > landmarks[THUMB_IP].y
        return index_extended and middle_bent and ring_bent and pinky_bent and thumb_bent
    except (IndexError, TypeError):
        return False


def detect_stop_gesture_pair(hand_states):
    """检测双手停止手势：左右手食指同时竖起并彼此靠近。"""
    left_hand = next((item for item in hand_states if item.get('hand_label') == 'Left' and item.get('stop_pose')), None)
    right_hand = next((item for item in hand_states if item.get('hand_label') == 'Right' and item.get('stop_pose')), None)

    if not left_hand or not right_hand:
        return []

    left_tip = left_hand['landmarks'][INDEX_FINGER_TIP]
    right_tip = right_hand['landmarks'][INDEX_FINGER_TIP]
    if distance_2d(left_tip, right_tip) <= 0.08:
        return [left_hand, right_hand]

    return []


# --- 4. 主循环 ---
def main():
    global detection_results, last_hand_timestamp_ms

    cap = open_camera(0)
    if not cap.isOpened():
        print("无法打开摄像头")
        return

    # <--- 修改: 初始化两个LED列，每列8个LED
    led_column_left = LEDColumn(num_leds=8)
    led_column_right = LEDColumn(num_leds=8)
    camera_read_failures = 0

    with HandLandmarker.create_from_options(options) as detector:
        last_frame_push = 0.0
        while True:
            ret, frame = cap.read()
            if not ret:
                camera_read_failures += 1
                if camera_read_failures >= 20:
                    print("摄像头连续读取失败，尝试重新打开")
                    cap.release()
                    time.sleep(0.2)
                    cap = open_camera(0)
                    camera_read_failures = 0
                    if not cap.isOpened():
                        print("重新打开摄像头失败")
                        break
                time.sleep(0.03)
                continue

            camera_read_failures = 0

            frame = cv2.flip(frame, 1)
            H, W, _ = frame.shape
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            frame_timestamp_ms = time.monotonic_ns() // 1_000_000
            if frame_timestamp_ms <= last_hand_timestamp_ms:
                frame_timestamp_ms = last_hand_timestamp_ms + 1
            last_hand_timestamp_ms = frame_timestamp_ms
            detector.detect_async(mp_image, frame_timestamp_ms)

            current_loop_time = time.time()
            gesture_display_info = []
            frame_hand_states = []
            left_seen = False
            right_seen = False
            left_ring_detected = None
            right_direction_detected = None

            # 重置选中状态
            led_column_left.selected_led_index = -1
            led_column_right.selected_led_index = -1

            if detection_results and detection_results.hand_landmarks:
                handedness_list = detection_results.handedness or []
                for idx, hand_landmarks in enumerate(detection_results.hand_landmarks):
                    if idx >= len(handedness_list) or not handedness_list[idx]:
                        continue

                    hand_label_raw = handedness_list[idx][0].category_name
                    # 画面做了水平镜像，逻辑上的左右手需要交换。
                    hand_label = 'Right' if hand_label_raw == 'Left' else 'Left'
                    if hand_label not in hand_data:
                        continue
                    current_hand_history = hand_data[hand_label]

                    if MP_HAS_SOLUTIONS and landmark_pb2 is not None:
                        landmark_list_for_drawing = landmark_pb2.NormalizedLandmarkList()
                        for lm in hand_landmarks:
                            landmark_for_drawing = landmark_list_for_drawing.landmark.add()
                            landmark_for_drawing.x, landmark_for_drawing.y, landmark_for_drawing.z = lm.x, lm.y, lm.z

                        mp_drawing.draw_landmarks(frame, landmark_list_for_drawing, mp_hands.HAND_CONNECTIONS,
                                                  mp_drawing_styles.get_default_hand_landmarks_style(),
                                                  mp_drawing_styles.get_default_hand_connections_style())

                    selected_led_index = -1
                    active_ring = hand_data['Left'].get('active_ring') or 'A'

                    if hand_label == 'Left':
                        left_seen = True
                        bdbg = get_b_debug_metrics(hand_landmarks)
                        ring_letter = detect_ring_gesture(hand_landmarks)
                        left_ring_detected = ring_letter
                        if ring_letter:
                            if current_hand_history.get('ring_candidate') == ring_letter:
                                current_hand_history['ring_candidate_count'] = current_hand_history.get('ring_candidate_count', 0) + 1
                            else:
                                current_hand_history['ring_candidate'] = ring_letter
                                current_hand_history['ring_candidate_count'] = 1

                            if (
                                current_hand_history['ring_candidate_count'] >= 2
                                and current_loop_time - current_hand_history['last_ring_select_time'] > RING_SELECT_COOLDOWN
                            ):
                                current_hand_history['active_ring'] = ring_letter
                                current_hand_history['last_ring_select_time'] = current_loop_time
                                current_hand_history['ring_candidate_count'] = 0
                                publish_hand_command("selectRing", {"hand": hand_label, "ring": ring_letter})
                        else:
                            current_hand_history['ring_candidate'] = None
                            current_hand_history['ring_candidate_count'] = 0

                        active_ring = current_hand_history.get('active_ring') or 'A'

                    if hand_label == 'Right':
                        right_seen = True
                        direction = detect_index_direction_gesture(hand_landmarks)
                        right_direction_detected = direction
                        frame_hand_states.append({
                            "hand_label": hand_label,
                            "direction": direction,
                        })

                    # 更新历史数据
                    current_hand_history['last_detection_time'] = current_loop_time

            right_history = hand_data['Right']
            active_ring = hand_data['Left'].get('active_ring') or 'A'
            right_direction = next((s.get("direction") for s in frame_hand_states if s.get("hand_label") == "Right"), None)
            left_active_ring = hand_data['Left'].get('active_ring') or 'A'
            left_detect_text = left_ring_detected if left_ring_detected else ('none' if left_seen else 'not_detected')
            right_detect_text = right_direction_detected if right_direction_detected else ('neutral' if right_seen else 'not_detected')

            direction_to_action = {
                "up": "moveUp",
                "down": "moveDown",
                "left": "rotateLeft",
                "right": "rotateRight",
            }

            if right_direction in direction_to_action:
                action = direction_to_action[right_direction]
                should_emit = (
                    action != right_history.get('last_direction_action')
                    or current_loop_time - right_history.get('last_direction_emit', 0) > HAND_COMMAND_COOLDOWN
                )
                if should_emit:
                    publish_hand_command(
                        action,
                        {
                            "hand": "Right",
                            "ring": active_ring,
                            "axis": "index_direction",
                            "direction": right_direction,
                        },
                    )
                    right_history['last_direction_action'] = action
                    right_history['last_direction_emit'] = current_loop_time
            else:
                if (
                    right_history.get('last_direction_action') is not None
                    and current_loop_time - right_history.get('last_direction_emit', 0) > HAND_COMMAND_COOLDOWN
                ):
                    publish_hand_command("stop", {"hand": "Right", "ring": active_ring})
                    right_history['last_direction_action'] = None
                    right_history['last_direction_emit'] = current_loop_time

            # 每帧固定输出左右手结果，避免只显示单侧导致误解。
            gesture_display_info.append(f"Left Ring Gesture: {left_detect_text}")
            gesture_display_info.append(f"Left Active Ring: {left_active_ring}")
            gesture_display_info.append(f"Right Index Direction: {right_detect_text}")

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
                "left_status": {
                    "ring_gesture": left_detect_text,
                    "active_ring": left_active_ring,
                    "seen": left_seen,
                },
                "right_status": {
                    "index_direction": right_detect_text,
                    "seen": right_seen,
                },
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