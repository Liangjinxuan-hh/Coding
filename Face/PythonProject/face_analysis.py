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


def _distance_2d(point_a, point_b):
    return float(np.linalg.norm(np.array([point_a.x, point_a.y]) - np.array([point_b.x, point_b.y])))


def detect_face_expression(landmarks, image, mar, mouth_threshold):
    """根据嘴型和嘴角位置判断常见表情，并映射成节奏模式。
    
    改进的算法：更合理的表情识别条件，避免条件互相冲突
    """
    try:
        upper_lip = landmarks[UPPER_LIP_CENTER_INDEX]
        lower_lip = landmarks[LOWER_LIP_CENTER_INDEX]
        left_corner = landmarks[61]
        right_corner = landmarks[291]
        left_eye = landmarks[33]
        right_eye = landmarks[263]

        eye_span = max(_distance_2d(left_eye, right_eye), 1e-4)
        mouth_width_ratio = _distance_2d(left_corner, right_corner) / eye_span
        mouth_center_y = (upper_lip.y + lower_lip.y) / 2.0
        mouth_corner_y = (left_corner.y + right_corner.y) / 2.0
        corner_lift = mouth_center_y - mouth_corner_y

        # 诊断输出（临时用于调试）
        print(f"[表情诊断] MAR={mar:.4f} 嘴宽比={mouth_width_ratio:.4f} 嘴角抬升={corner_lift:.6f}")

        # ========== 改进的表情识别逻辑 ==========
        # 优先级：嘴角下垂（负向情绪）> 大开口笑/惊讶 > 抿嘴微笑 > 平静
        # 关键分离：抿嘴微笑必须满足“低 MAR”，避免与咧嘴大笑混淆。
        
        # 统一阈值（与 mouth_threshold 联动，并设安全下限）
        grin_mar_high = max(mouth_threshold * 1.55, 0.19)
        grin_mar_mid = max(mouth_threshold * 1.30, 0.16)
        subtle_smile_mar_max = max(mouth_threshold * 1.08, 0.14)
        grin_corner_lift_min_high = 0.006
        grin_corner_lift_min_mid = 0.004
        angry_corner_lift_max = -0.017
        sad_corner_lift_max = -0.010
        angry_mar_max = max(mouth_threshold * 1.03, 0.13)
        sad_mar_min = max(mouth_threshold * 0.98, 0.12)
        sad_mar_max = max(mouth_threshold * 1.24, 0.17)

        # 1. 先判断嘴角下垂（负向表情）
        # 愤怒：嘴角下压更强，且嘴更紧（MAR 更小）
        if corner_lift <= angry_corner_lift_max and mar <= angry_mar_max:
            return "愤怒", "angry"

        # 难过抽泣交互已停用：保留条件但回退为平静，避免触发 slow 节奏。
        if corner_lift <= sad_corner_lift_max and sad_mar_min <= mar <= sad_mar_max:
            return "平静", "normal"

        # 2. 大开口优先判定（先区分咧嘴大笑/惊讶）
        # 咧嘴大笑需要：大开口 + 明显横向拉伸 + 嘴角上扬。
        # 惊讶通常：大开口但嘴角不上扬（甚至下压）或横向拉伸不足。
        if mar >= grin_mar_high:
            if mouth_width_ratio >= 0.50 and corner_lift >= grin_corner_lift_min_high:
                return "咧嘴大笑", "fast"
            return "惊讶", "surprise"

        # 中高开口时，仍要求一定嘴角上扬，避免把“惊讶张口”误判成咧嘴笑
        if mar >= grin_mar_mid:
            if mouth_width_ratio >= 0.46 and corner_lift >= grin_corner_lift_min_mid:
                return "咧嘴大笑", "fast"
            return "惊讶", "surprise"

        # 3. 抿嘴微笑（严格限制：低开口 + 嘴角上扬 + 一定嘴宽）
        if corner_lift > 0.010 and mar <= subtle_smile_mar_max and mouth_width_ratio >= 0.34:
            return "抿嘴微笑", "happy"
        
        # 3. 默认
        return "平静", "normal"
    except (IndexError, TypeError):
        return "平静", "normal"


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

        # 输入帧已做镜像，用户视角下的左右应在此反向修正：
        # 向左看 -> LOOK_LEFT，向右看 -> LOOK_RIGHT。
        if delta_x > 0.02:
            return "LOOK_LEFT"
        elif delta_x < -0.02:
            return "LOOK_RIGHT"
        else:
            return "LOOK_FORWARD"
    except (IndexError, TypeError):
        return "LOOK_FORWARD"


def detect_head_tilt(landmarks):
    """根据关键点判断头部竖直倾斜方向（抬头/低头）"""
    try:
        # 关键点标记点：眼睛、鼻尖、下颌
        # 10: 额头中心
        # 4: 鼻尖
        # 152: 下颌中心
        forehead = landmarks[10]
        nose_tip = landmarks[4]
        chin = landmarks[152]

        # 比较鼻尖和头顶、下颌之间的纵向位置
        # 纵向距离：眼睛（33/263的中点）和下颌之间的距离
        left_eye = landmarks[33]
        right_eye = landmarks[263]
        eye_center_y = (left_eye.y + right_eye.y) / 2

        # 计算鼻尖相对于眼睛的纵向位置（数值越大表示越靠下）
        nose_to_eye = nose_tip.y - eye_center_y
        # 计算下颌相对于眼睛的纵向位置
        chin_to_eye = chin.y - eye_center_y

        # 如果鼻子偏离眼睛太多，可能是低头状态
        # 如果下颌偏离眼睛较多，可能是抬头状态
        tilt_ratio = chin_to_eye - nose_to_eye

        # 根据下颌和鼻尖的纵向关系判断
        # 正常姿态：chin.y > nose.y （下颌在鼻尖下面）
        # 抬头：chin.y 和 nose.y 的距离变小，下颌相对上移
        # 低头：chin.y 和 nose.y 的距离变大，下颌相对下移

        nose_chin_distance = chin.y - nose_tip.y

        # 基于鼻下颌之间的距离和角度来判断
        # 当低头时，鼻和下颌之间的距离会增大
        # 当抬头时，鼻和下颌之间的距离会减小
        if nose_chin_distance > 0.15:  # 低头时下颌离鼻较远
            return "LOOK_DOWN"
        elif nose_chin_distance < 0.08:  # 抬头时下颌离鼻较近
            return "LOOK_UP"
        else:
            return "LOOK_STRAIGHT"
    except (IndexError, TypeError):
        return "LOOK_STRAIGHT"


def detect_eye_pattern(left_ear, right_ear, threshold):
    """左右眼独立开合组合映射为 A/B/C/D。

    A: 用户视角左眼单开（镜像输入下对应 right_open）
    B: 用户视角右眼单开（镜像输入下对应 left_open）
    C: 双眼睁
    D: 双眼闭
    """
    left_open = left_ear >= threshold
    right_open = right_ear >= threshold

    # 摄像头帧在主流程中已镜像，A/B 在此做左右对调以匹配用户直觉。
    if (not left_open) and right_open:
        return "A"
    if left_open and (not right_open):
        return "B"
    if left_open and right_open:
        return "C"
    return "D"