#!/usr/bin/env python3
"""
诊断脚本：实时输出表情识别参数
用于调试表情识别为什么一直显示"平静"
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import cv2
import mediapipe as mp
from Face.PythonProject.config import CONFIG, load_config
from Face.PythonProject.face_analysis import (
    detect_face_expression,
    mouth_aspect_ratio,
    eye_aspect_ratio,
    UPPER_LIP_CENTER_INDEX,
    LOWER_LIP_CENTER_INDEX,
    RIGHT_EYE_EAR_POINTS,
    LEFT_EYE_EAR_POINTS,
    _distance_2d,
)

load_config()

# 初始化 MediaPipe
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    static_image_mode=False,
    max_num_faces=1,
    refine_landmarks=False,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7,
)

print("=" * 70)
print("表情识别诊断工具 - 实时参数输出")
print("=" * 70)
print(f"MOUTH_THRESHOLD: {CONFIG['MOUTH_THRESHOLD']}")
print("按 'q' 退出该脚本\n")

cap = cv2.VideoCapture(0)
frame_count = 0

while True:
    ret, image = cap.read()
    if not ret:
        print("无法读取摄像头")
        break

    h, w, c = image.shape
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(image_rgb)

    if results.multi_face_landmarks:
        landmarks = results.multi_face_landmarks[0].landmark

        # 计算 MAR
        mouth_dist_ref = [0]
        mouth_ratio_ref = [0]
        mar = mouth_aspect_ratio(landmarks, image, mouth_dist_ref, mouth_ratio_ref)

        # 计算表情相关参数
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

        # 眼睛比例
        left_ear = eye_aspect_ratio(landmarks, LEFT_EYE_EAR_POINTS, image)
        right_ear = eye_aspect_ratio(landmarks, RIGHT_EYE_EAR_POINTS, image)

        # 识别表情
        expression, tempo_mode = detect_face_expression(landmarks, image, mar, CONFIG['MOUTH_THRESHOLD'])

        grin_mar_high = max(CONFIG['MOUTH_THRESHOLD'] * 1.55, 0.19)
        grin_mar_mid = max(CONFIG['MOUTH_THRESHOLD'] * 1.30, 0.16)
        subtle_smile_mar_max = max(CONFIG['MOUTH_THRESHOLD'] * 1.08, 0.14)
        grin_corner_lift_min_high = 0.006
        grin_corner_lift_min_mid = 0.004
        angry_corner_lift_max = -0.017
        sad_corner_lift_max = -0.010
        angry_mar_max = max(CONFIG['MOUTH_THRESHOLD'] * 1.03, 0.13)
        sad_mar_min = max(CONFIG['MOUTH_THRESHOLD'] * 0.98, 0.12)
        sad_mar_max = max(CONFIG['MOUTH_THRESHOLD'] * 1.24, 0.17)

        frame_count += 1
        if frame_count % 10 == 0:  # 每 10 帧输出一次
            print("\n" + "-" * 70)
            print(f"帧 #{frame_count}")
            print(f"表情识别结果: {expression:8} | 节奏模式: {tempo_mode}")
            print("-" * 70)
            print(f"  MAR (嘴部开合比):        {mar:.4f}")
            print(f"    - 咧嘴大笑高阈值:    >= {grin_mar_high:.4f}")
            print(f"    - 咧嘴大笑中阈值:    >= {grin_mar_mid:.4f}")
            print(f"    - 抿嘴微笑上限:      <= {subtle_smile_mar_max:.4f}")
            print(f"  嘴宽比 (相对眼间距):    {mouth_width_ratio:.4f}")
            print(f"    - 咧嘴大笑(高阈值)需要: >= 0.50")
            print(f"    - 咧嘴大笑(中阈值)需要: >= 0.46")
            print(f"    - 抿嘴微笑需要:      >= 0.34")
            print(f"  嘴角抬升度:              {corner_lift:.6f}")
            print(f"    - 咧嘴大笑(高阈值)需要: >= {grin_corner_lift_min_high:.6f}")
            print(f"    - 咧嘴大笑(中阈值)需要: >= {grin_corner_lift_min_mid:.6f}")
            print(f"    - 抿嘴微笑需要:      > 0.010000")
            print(f"    - 难过抽泣需要:      <= {sad_corner_lift_max:.6f}")
            print(f"    - 愤怒需要:          <= {angry_corner_lift_max:.6f}")
            print(f"  左眼 EAR:                {left_ear:.4f}")
            print(f"  右眼 EAR:                {right_ear:.4f}")
            print()
            print("表情识别条件检查:")
            print(f"  ✓ 咧嘴大笑(高阈值): MAR >= {grin_mar_high:.4f} && 嘴宽比 >= 0.50 && 嘴角抬升 >= {grin_corner_lift_min_high:.6f}")
            print(f"    - MAR: {mar:.4f} >= {grin_mar_high:.4f}? {mar >= grin_mar_high}")
            print(f"    - 嘴宽比: {mouth_width_ratio:.4f} >= 0.50? {mouth_width_ratio >= 0.50}")
            print(f"    - 嘴角抬升: {corner_lift:.6f} >= {grin_corner_lift_min_high:.6f}? {corner_lift >= grin_corner_lift_min_high}")
            print(f"  ✓ 咧嘴大笑(中阈值): MAR >= {grin_mar_mid:.4f} && 嘴宽比 >= 0.46 && 嘴角抬升 >= {grin_corner_lift_min_mid:.6f}")
            print(f"    - MAR: {mar:.4f} >= {grin_mar_mid:.4f}? {mar >= grin_mar_mid}")
            print(f"    - 嘴宽比: {mouth_width_ratio:.4f} >= 0.46? {mouth_width_ratio >= 0.46}")
            print(f"    - 嘴角抬升: {corner_lift:.6f} >= {grin_corner_lift_min_mid:.6f}? {corner_lift >= grin_corner_lift_min_mid}")
            print(f"  ✓ 抿嘴微笑: 角度抬升 > 0.010 && MAR <= {subtle_smile_mar_max:.4f} && 嘴宽比 >= 0.34")
            print(f"    - 角度抬升: {corner_lift:.6f} > 0.010000? {corner_lift > 0.010}")
            print(f"    - MAR: {mar:.4f} <= {subtle_smile_mar_max:.4f}? {mar <= subtle_smile_mar_max}")
            print(f"    - 嘴宽比: {mouth_width_ratio:.4f} >= 0.34? {mouth_width_ratio >= 0.34}")
            print(f"  ✓ 难过抽泣: 角度抬升 <= {sad_corner_lift_max:.6f} && {sad_mar_min:.4f} <= MAR <= {sad_mar_max:.4f}")
            print(f"    - 角度抬升: {corner_lift:.6f} <= {sad_corner_lift_max:.6f}? {corner_lift <= sad_corner_lift_max}")
            print(f"    - MAR下限: {mar:.4f} >= {sad_mar_min:.4f}? {mar >= sad_mar_min}")
            print(f"    - MAR上限: {mar:.4f} <= {sad_mar_max:.4f}? {mar <= sad_mar_max}")
            print(f"  ✓ 愤怒: 角度抬升 <= {angry_corner_lift_max:.6f} && MAR <= {angry_mar_max:.4f}")
            print(f"    - 角度抬升: {corner_lift:.6f} <= {angry_corner_lift_max:.6f}? {corner_lift <= angry_corner_lift_max}")
            print(f"    - MAR: {mar:.4f} <= {angry_mar_max:.4f}? {mar <= angry_mar_max}")
    else:
        print("未检测到人脸")

    # 显示视频流
    cv2.imshow("表情识别诊断", image)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
print("\n诊断脚本已退出")
