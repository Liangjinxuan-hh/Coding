import cv2

class Button:
    """在OpenCV窗口上创建一个可点击的按钮"""

    def __init__(self, pos, width, height, text):
        self.pos = pos
        self.width = width
        self.height = height
        self.text = text

    def draw(self, img):
        """将按钮绘制到图像上"""
        # 绘制按钮背景
        cv2.rectangle(img, self.pos, (self.pos[0] + self.width, self.pos[1] + self.height), (220, 220, 220), -1)
        # 绘制按钮边框
        cv2.rectangle(img, self.pos, (self.pos[0] + self.width, self.pos[1] + self.height), (100, 100, 100), 2)

        # 计算文本位置使其居中
        text_size, _ = cv2.getTextSize(self.text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        text_x = self.pos[0] + (self.width - text_size[0]) // 2
        text_y = self.pos[1] + (self.height + text_size[1]) // 2

        # 绘制按钮文本
        cv2.putText(img, self.text, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

    def is_clicked(self, mouse_pos):
        """检查给定的鼠标坐标是否在按钮范围内"""
        if mouse_pos is None:
            return False

        x, y = mouse_pos
        return (self.pos[0] <= x <= self.pos[0] + self.width and
                self.pos[1] <= y <= self.pos[1] + self.height)