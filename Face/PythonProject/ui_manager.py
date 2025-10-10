import cv2
import platform
import os
from PIL import Image, ImageDraw, ImageFont
import numpy as np


class Button:
    """在OpenCV窗口上创建一个可点击的按钮，支持中文显示和准确的点击检测"""

    def __init__(self, pos, width, height, text):
        self.pos = pos  # (x, y) 按钮左上角坐标
        self.width = width  # 按钮宽度
        self.height = height  # 按钮高度
        self.text = text  # 按钮文本
        self.chinese_font_path = self._get_default_chinese_font()  # 获取系统中文字体

    def _get_default_chinese_font(self):
        """获取系统默认中文字体路径，用于按钮文本绘制"""
        system = platform.system()
        if system == "Windows":
            for font in ["simhei.ttf", "msyh.ttc", "msyh.ttf", "simsun.ttc", "simkai.ttf"]:
                path = os.path.join("C:/Windows/Fonts", font)
                if os.path.exists(path):
                    return path
        elif system == "Linux":
            for path in [
                "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
                "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc"
            ]:
                if os.path.exists(path):
                    return path
        return None  # 返回 None 表示未找到中文字体

    def is_clicked(self, click_pos):
        """检查给定的点击坐标是否在按钮区域内"""
        if click_pos is None:
            return False
        x, y = click_pos
        return (self.pos[0] <= x <= self.pos[0] + self.width and
                self.pos[1] <= y <= self.pos[1] + self.height)

    def draw(self, img):
        """将按钮绘制到图像上，支持中文显示"""
        # 1. 绘制背景矩形
        cv2.rectangle(
            img,
            self.pos,
            (self.pos[0] + self.width, self.pos[1] + self.height),
            (200, 200, 200),  # 灰色背景
            -1
        )
        # 2. 绘制边框
        cv2.rectangle(
            img,
            self.pos,
            (self.pos[0] + self.width, self.pos[1] + self.height),
            (0, 0, 0),  # 黑色边框
            2
        )

        # 3. 绘制文本
        has_chinese = any(ord(c) > 127 for c in self.text)

        if has_chinese and self.chinese_font_path:
            try:
                # 转换为 PIL 格式
                img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
                draw = ImageDraw.Draw(img_pil)
                # 字体大小（大小自适应按钮高度）
                font_size = int(self.height * 0.6)  # 字体大小为按钮高度的60%
                font = ImageFont.truetype(self.chinese_font_path, font_size)
                # 获取文本尺寸（兼容新版本Pillow）
                bbox = draw.textbbox((0, 0), self.text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                # 计算居中坐标
                # PIL坐标是左上角
                pil_text_x = self.pos[0] + (self.width - text_width) // 2
                pil_text_y = self.pos[1] + (self.height - text_height) // 2
                # 绘制文本
                draw.text((pil_text_x, pil_text_y), self.text, font=font, fill=(0, 0, 0))
                # 转换回OpenCV格式并返回
                return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
            except Exception as e:
                # print(f"PIL绘制按钮文本失败: {e}，将使用OpenCV fallback")
                pass  # 忽略错误，使用OpenCV fallback

        # OpenCV绘制（英文 fallback 或 PIL 失败时）
        # 计算文本尺寸
        text_size, baseline = cv2.getTextSize(self.text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        # 重新计算居中位置
        text_x = self.pos[0] + (self.width - text_size[0]) // 2
        text_y = self.pos[1] + (self.height + text_size[1]) // 2

        cv2.putText(
            img,
            self.text,
            (text_x, text_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 0, 0),
            2,
            cv2.LINE_AA
        )
        return img  # 返回更新后的图像