import numpy as np
from config import UPPER_LIP_CENTER_INDEX, LOWER_LIP_CENTER_INDEX


# --- 眼睛和嘴巴比例计算 ---

def eye_aspect_ratio(landmarks, ear_points_indices, image):
    """
    根据6个核心关键点计算单只眼睛的开合比 (EAR - Eye Aspect Ratio)。
    EAR = (P1-P5的距离 + P2-P4的距离) / (2 * P0-P3的距离)
    """
    try:
        h, w, _ = image.shape
        P0_idx, P1_idx, P2_idx, P3_idx, P4_idx, P5_idx = ear_points_indices

        def to_pixel(idx):
            """将归一化的坐标转换为像素坐标"""
            return np.array([landmarks[idx].x * w, landmarks[idx].y * h])

        # 获取6个关键点的像素坐标
        P0 = to_pixel(P0_idx)
        P3 = to_pixel(P3_idx)
        P1 = to_pixel(P1_idx)
        P5 = to_pixel(P5_idx)
        P2 = to_pixel(P2_idx)
        P4 = to_pixel(P4_idx)

        # 计算垂直方向距离
        v1 = np.linalg.norm(P1 - P5)
        v2 = np.linalg.norm(P2 - P4)
        # 计算水平方向距离
        h_dist = np.linalg.norm(P0 - P3)

        # 计算EAR值，避免除以零
        ear = (v1 + v2) / (2.0 * h_dist) if h_dist > 0 else 0.3

        return ear
    except (IndexError, TypeError):
        # 如果 landmarks 数据不完整，返回一个安全的默认值
        return 0.3


def mouth_aspect_ratio(landmarks, image, distance_ref, ratio_ref):
    """计算嘴巴开合比 (MAR)"""
    try:
        h, w, _ = image.shape

        # 上下唇中心的垂直距离
        upper_lip = landmarks[UPPER_LIP_CENTER_INDEX]
        lower_lip = landmarks[LOWER_LIP_CENTER_INDEX]
        upper_y = int(upper_lip.y * h)
        lower_y = int(lower_lip.y * h)
        distance = abs(upper_y - lower_y)
        distance_ref[0] = distance  # 通过引用更新外部变量

        # 左右嘴角的水平宽度
        left_corner = landmarks[61]
        right_corner = landmarks[291]
        left_x = int(left_corner.x * w)
        right_x = int(right_corner.x * w)
        width = abs(left_x - right_x)

        # 计算比例，避免除以零
        ratio = distance / width if width > 0 else 0
        ratio_ref[0] = ratio  # 通过引用更新外部变量

        return ratio
    except (IndexError, TypeError):
        return 0


def detect_face_direction(landmarks):
    """根据关键点判断头部左右转动方向"""
    try:
        # 关键点：鼻尖、左眼角、右眼角
        nose_tip = landmarks[4]
        left_eye = landmarks[33]
        right_eye = landmarks[263]

        # 眼睛中心的x坐标
        center_x = (left_eye.x + right_eye.x) / 2
        # 鼻尖相对于眼睛中心的偏移量
        delta_x = nose_tip.x - center_x

        # 由于视频画面是水平镜像的，所以逻辑需要反转
        # 当人向右转时，在镜像画面中，鼻子会向右移动，x坐标变大
        if delta_x > 0.02:
            return "LOOK_RIGHT"
        # 当人向左转时，在镜像画面中，鼻子会向左移动，x坐标变小
        elif delta_x < -0.02:
            return "LOOK_LEFT"
        else:
            return "LOOK_FORWARD"
    except (IndexError, TypeError):
        return "LOOK_FORWARD"