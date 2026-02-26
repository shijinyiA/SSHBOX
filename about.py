"""自定义作者卡片组件"""
import os
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt5.QtGui import QPixmap, QPainter, QPainterPath
from qfluentwidgets import CardWidget


class RoundedAvatar(QLabel):
    """圆形头像组件"""
    
    def __init__(self, image_path: str, size: int = 64, parent=None):
        super().__init__(parent)
        self.size = size
        self.setFixedSize(size, size)
        
        if os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            # 缩放到正方形
            pixmap = pixmap.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            
            # 创建圆形遮罩
            rounded = QPixmap(size, size)
            rounded.fill(Qt.transparent)
            
            painter = QPainter(rounded)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            
            path = QPainterPath()
            path.addEllipse(0, 0, size, size)
            painter.setClipPath(path)
            
            # 居中绘制
            x = (size - pixmap.width()) // 2
            y = (size - pixmap.height()) // 2
            painter.drawPixmap(x, y, pixmap)
            painter.end()
            
            self.setPixmap(rounded)


class AuthorCard(CardWidget):
    """作者信息卡片"""
    
    def __init__(self, avatar_path: str = None, parent=None):
        super().__init__(parent)
        self.setup_ui(avatar_path)
        
    def setup_ui(self, avatar_path: str):
        # 设置无边框样式
        self.setStyleSheet("""
            AuthorCard {
                background-color: transparent;
                border: none;
                border-radius: 8px;
            }
        """)
        
        # 主布局
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        
        # 左侧文字区域
        text_layout = QVBoxLayout()
        text_layout.setSpacing(8)
        text_layout.setAlignment(Qt.AlignCenter)
        
        # 作者标签
        author_label = QLabel("作者")
        author_label.setStyleSheet("font-size: 14px; color: #666;")
        author_label.setAlignment(Qt.AlignCenter)
        text_layout.addWidget(author_label)
        
        # 名字
        name_label = QLabel("锦衣")
        name_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        name_label.setAlignment(Qt.AlignCenter)
        text_layout.addWidget(name_label)
        
        main_layout.addLayout(text_layout)
        main_layout.addStretch()
        
        # 右侧头像
        if avatar_path and os.path.exists(avatar_path):
            avatar = RoundedAvatar(avatar_path, 80)
            main_layout.addWidget(avatar)
