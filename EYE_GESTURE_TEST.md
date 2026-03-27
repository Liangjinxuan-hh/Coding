# 左右眼分离识别 - 快速测试指南

## 功能特性
使用面部识别精准判断左右眼的张合状态，生成4种眼睛手势信号ABCD。

| 手势 | 左眼 | 右眼 | 用途 |
|---|---|---|---|
| **A** | 张开 ✅ | 闭合 ❌ | 环A选择/命令1 |
| **B** | 闭合 ❌ | 张开 ✅ | 环B选择/命令2 |
| **C** | 张开 ✅ | 张开 ✅ | 环C选择/命令3 |
| **D** | 闭合 ❌ | 闭合 ❌ | 环D选择/命令4 |

## 技术实现

### 后端 (Hand/main2.py)
```python
# FaceLandmarker 集成
- detect_eye_gesture(landmarks) → 'A'|'B'|'C'|'D'|None
- 左右眼 EAR 独立计算 (LEFT/RIGHT_EYE_POINTS)
- 动态基准值校准 (150帧数据，90分位数)
- payload 中包含 eye_gesture 字段
```

### 前端显示 (web/client-main.js)
```javascript
// Hand card 中显示眼睛手势
if (payload.eye_gesture) {
  handBindings.badge.textContent = `眼睛手势: ${payload.eye_gesture}`;
}
```

## 测试步骤

### 1️⃣ 启动系统
```bash
# 终端1: Bridge服务
python -m uvicorn bridge.server:app --host 127.0.0.1 --port 5051

# 终端2: 面部识别 (可选GUI)
set DRIP_LOCAL_PREVIEW=1
cd Face\PythonProject
python main.py

# 终端3: 手势识别 (眼睛识别)
set DRIP_LOCAL_PREVIEW=1
cd Hand
python main2.py

# 终端4: Web服务
cd web
npm start  # 或 node app.js
```

### 2️⃣ 眼睛校准
- Hand 输出会显示 `校准中... (x/150)`
- 正常眨眼 150 帧，系统自动计算 EAR 基准值
- 出现 `校准完成` 后可开始测试

### 3️⃣ 测试手势
摄像头前做出以下动作，观察输出：

**摄像头本地窗口显示:**
```
眼睛手势: A (L:0.35 R:0.18)    ← 左睁右闭
```

**Web 前端显示:**
- Hand 卡片 badge 区域显示当前眼睛手势
- 如果启用了手势命令，会同步发送到模型

### 4️⃣ 验证准确性
| 动作 | 预期输出 | 验证 |
|---|---|---|
| 左眼睁、右眼闭 | `eye_gesture: A` | ✓ |
| 左眼闭、右眼睁 | `eye_gesture: B` | ✓ |
| 双眼都睁 | `eye_gesture: C` | ✓ |
| 双眼都闭 | `eye_gesture: D` | ✓ |
| 正常眨眼 | 在 A/B/C/D 快速切换 | ✓ |

## 故障排除

### ❌ 显示"未检测到人脸"
- 检查摄像头是否正常工作
- 确保脸部在画面中央，光线充足
- 距离摄像头 30-60cm

### ❌ 永远不停地显示"校准中"
- 检查 150 帧是否足够（约5秒视频）
- EAR 基准值可能异常，尝试关闭并重新启动

### ❌ 眼睛识别不准确
- 增加环境光线亮度
- 调整摄像头角度确保两只眼都清晰
- 尝试增加敏感度系数 (face_analysis.py 中的 `threshold = baseline_ear * 0.7`)

### ❌ FaceLandmarker 初始化失败
- 确保 `face_landmarker.task` 文件存在于 Hand/ 目录
- 检查 MediaPipe 版本兼容性: `pip list | grep mediapipe`

## 应用场景

1. **手势菜单选择:** A/B/C/D 对应 4 个菜单项
2. **环控制:** 用眼睛手势快速选择要控制的环
3. **辅助指令:** 配合手部动作，实现多模态控制
4. **表情互动:** A/B/C/D 映射到不同的表情或动作

## 相关文件

| 文件 | 功能 |
|---|---|
| Hand/main2.py | 眼睛识别 + 手势识别，发布 eye_gesture |
| Face/PythonProject/face_analysis.py | EAR 计算 (复用) |
| web/client-main.js | 前端解析和显示眼睛手势 |
| config.json | 灵敏度配置 |

---
📝 **最后更新:** 2026-03-26  
🔧 **作者:** DripMotion AI Assistant
