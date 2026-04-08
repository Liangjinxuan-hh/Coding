#!/usr/bin/env python3
"""
完整表情识别诊断工具 - 逐条检查表情识别条件
实时显示哪些条件满足/不满足，帮助调试表情识别问题
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

def check_expression_conditions(landmarks, image, mar, mouth_threshold):
    """逐条检查所有表情识别条件"""
    
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

    # 计算阈值
    threshold_large_smile = max(mouth_threshold * 1.55, 0.18)
    threshold_surprise = max(mouth_threshold * 1.85, 0.22)
    threshold_subtle_smile = max(mouth_threshold * 1.10, 0.14)
    threshold_sad = max(mouth_threshold * 1.20, 0.16)
    threshold_angry = max(mouth_threshold * 1.05, 0.12)

    # 检查各表情条件
    results = {}
    
    # 咧嘴大笑
    cond1_laugh = mar >= threshold_large_smile
    cond2_laugh = mouth_width_ratio >= 0.48
    results['咧嘴大笑'] = {
        'matched': cond1_laugh and cond2_laugh,
        'conditions': [
            ('MAR >= ' + f'{threshold_large_smile:.4f}', cond1_laugh, mar),
            ('嘴宽比 >= 0.48', cond2_laugh, mouth_width_ratio),
        ]
    }
    
    # 惊讶
    cond1_surprise = mar >= threshold_surprise
    cond2_surprise = mouth_width_ratio < 0.48
    results['惊讶'] = {
        'matched': cond1_surprise and cond2_surprise,
        'conditions': [
            ('MAR >= ' + f'{threshold_surprise:.4f}', cond1_surprise, mar),
            ('嘴宽比 < 0.48', cond2_surprise, mouth_width_ratio),
        ]
    }
    
    # 抿嘴微笑
    cond1_smile = corner_lift > 0.010
    cond2_smile = mar <= threshold_subtle_smile
    cond3_smile = mouth_width_ratio >= 0.35
    results['抿嘴微笑'] = {
        'matched': cond1_smile and cond2_smile and cond3_smile,
        'conditions': [
            ('嘴角抬升 > 0.010000', cond1_smile, corner_lift),
            ('MAR <= ' + f'{threshold_subtle_smile:.4f}', cond2_smile, mar),
            ('嘴宽比 >= 0.35', cond3_smile, mouth_width_ratio),
        ]
    }
    
    # 难过抽泣
    cond1_sad = corner_lift < -0.008
    cond2_sad = mar <= threshold_sad
    results['难过抽泣'] = {
        'matched': cond1_sad and cond2_sad,
        'conditions': [
            ('嘴角抬升 < -0.008000', cond1_sad, corner_lift),
            ('MAR <= ' + f'{threshold_sad:.4f}', cond2_sad, mar),
        ]
    }
    
    # 愤怒
    cond1_angry = corner_lift < -0.014
    cond2_angry = mar <= threshold_angry
    results['愤怒'] = {
        'matched': cond1_angry and cond2_angry,
        'conditions': [
            ('嘴角抬升 < -0.014000', cond1_angry, corner_lift),
            ('MAR <= ' + f'{threshold_angry:.4f}', cond2_angry, mar),
        ]
    }
    
    return results, {
        'MAR': mar,
        'mouth_width_ratio': mouth_width_ratio,
        'corner_lift': corner_lift,
    }


print("=" * 80)
print("完整表情识别诊断工具 - 实时条件检查")
print("=" * 80)
print(f"MOUTH_THRESHOLD: {CONFIG['MOUTH_THRESHOLD']:.4f}")
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

        # 检查表情条件
        conditions, params = check_expression_conditions(landmarks, image, mar, CONFIG['MOUTH_THRESHOLD'])

        frame_count += 1
        if frame_count % 15 == 0:  # 每 15 帧输出一次
            print("\n" + "=" * 80)
            print(f"帧 #{frame_count}")
            print("=" * 80)
            print("\n【关键参数】")
            print(f"  MAR (嘴部开合比):        {params['MAR']:.4f}")
            print(f"  嘴宽比 (相对眼间距):    {params['mouth_width_ratio']:.4f}")
            print(f"  嘴角抬升度:              {params['corner_lift']:.6f}")
            
            print("\n【表情识别条件检查】\n")
            
            # 找出哪个表情被正确识别
            matched_expressions = [expr for expr, data in conditions.items() if data['matched']]
            
            if matched_expressions:
                print(f"✓ 识别结果: {matched_expressions[0]}\n")
            else:
                print("✗ 未识别出表情（所有条件评估如下）\n")
            
            # 详细列出每个表情的条件
            for expression in ['咧嘴大笑', '惊讶', '抿嘴微笑', '难过抽泣', '愤怒']:
                data = conditions[expression]
                status = "✓ 通过" if data['matched'] else "✗ 未通过"
                print(f"{expression}: {status}")
                
                for cond_text, cond_result, value in data['conditions']:
                    check = "✓" if cond_result else "✗"
                    print(f"  {check} {cond_text:30} | 值: {value:.6f}")
                
                print()
    
    else:
        print("未检测到人脸")

    # 显示视频流（可选，按需分号注释掉）
    cv2.imshow("表情诊断", image)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
print("\n诊断脚本已退出")
