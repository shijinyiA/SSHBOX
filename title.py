import os
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PyQt5.QtGui import QMouseEvent, QPixmap
from qfluentwidgets import FluentIcon as FIF


class TitleBarButton(QPushButton):
    def __init__(self, icon_type: str, parent=None):
        super().__init__(parent)
        self.icon_type = icon_type
        self.setFixedSize(46, 32)
        self.update_style()
    
    def update_style(self):
        if self.icon_type == "close":
            self.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: none;
                    font-family: "Segoe MDL2 Assets";
                    font-size: 10px;
                }
                QPushButton:hover {
                    background-color: rgba(128, 128, 128, 0.3);
                    color: black;
                }
                QPushButton:pressed {
                    background-color: rgba(128, 128, 128, 0.5);
                    color: black;
                }
            """)
            self.setText("\uE8BB")
        elif self.icon_type == "maximize":
            self.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: none;
                    font-family: "Segoe MDL2 Assets";
                    font-size: 10px;
                }
                QPushButton:hover {
                    background-color: rgba(128, 128, 128, 0.3);
                }
                QPushButton:pressed {
                    background-color: rgba(128, 128, 128, 0.5);
                }
            """)
            self.setText("\uE922")
        elif self.icon_type == "minimize":
            self.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: none;
                    font-family: "Segoe MDL2 Assets";
                    font-size: 10px;
                }
                QPushButton:hover {
                    background-color: rgba(128, 128, 128, 0.3);
                }
                QPushButton:pressed {
                    background-color: rgba(128, 128, 128, 0.5);
                }
            """)
            self.setText("\uE921")
        elif self.icon_type == "restore":
            self.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: none;
                    font-family: "Segoe MDL2 Assets";
                    font-size: 10px;
                }
                QPushButton:hover {
                    background-color: rgba(128, 128, 128, 0.3);
                }
                QPushButton:pressed {
                    background-color: rgba(128, 128, 128, 0.5);
                }
            """)
            self.setText("\uE923")


class CustomTitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self._is_dragging = False
        self._drag_position = QPoint()
        self._is_maximized = False
        
        self.setup_ui()
    
    def setup_ui(self):
        self.setFixedHeight(32)
        self.setAutoFillBackground(True)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 0, 0)
        layout.setSpacing(0)
        
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(20, 20)
        self.icon_label.setScaledContents(True)
        icon_path = os.path.join(os.path.dirname(__file__), "1.ico")
        if os.path.exists(icon_path):
            pixmap = QPixmap(icon_path)
            self.icon_label.setPixmap(pixmap)
        layout.addWidget(self.icon_label)
        
        self.title_label = QLabel("锦衣的SSH工具箱")
        self.title_label.setStyleSheet("font-size: 12px; margin-left: 8px;")
        layout.addWidget(self.title_label)
        
        layout.addStretch()
        
        self.minimize_button = TitleBarButton("minimize")
        self.minimize_button.clicked.connect(self.minimize_window)
        layout.addWidget(self.minimize_button)
        
        self.maximize_button = TitleBarButton("maximize")
        self.maximize_button.clicked.connect(self.toggle_maximize)
        layout.addWidget(self.maximize_button)
        
        self.close_button = TitleBarButton("close")
        self.close_button.clicked.connect(self.close_window)
        layout.addWidget(self.close_button)
        
        self.update_theme()
    
    def update_theme(self):
        # 改进标题栏样式，使其与背景更好地融合
        self.setStyleSheet("""
            QWidget {
                border-radius: 12px 12px 0px 0px;
                background-color: transparent;  /* 透明背景以与主窗口融合 */
                color: black;
            }
        """)
        self.title_label.setStyleSheet("font-size: 12px; margin-left: 8px; color: black;")
    
    def set_title(self, title: str):
        self.title_label.setText(title)
    
    def minimize_window(self):
        if self.parent_window:
            self.parent_window.showMinimized()
    
    def toggle_maximize(self):
        if self.parent_window:
            if self._is_maximized:
                self.parent_window.showNormal()
                self.maximize_button.icon_type = "maximize"
                self.maximize_button.setText("\uE922")
                self._is_maximized = False
            else:
                self.parent_window.showMaximized()
                self.maximize_button.icon_type = "restore"
                self.maximize_button.setText("\uE923")
                self._is_maximized = True
    
    def close_window(self):
        if self.parent_window:
            self.parent_window.close()
    
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self._is_dragging = True
            self._drag_position = event.globalPos() - self.parent_window.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event: QMouseEvent):
        if self._is_dragging and event.buttons() == Qt.LeftButton:
            if self._is_maximized:
                self.toggle_maximize()
                self._drag_position = QPoint(
                    self.parent_window.width() // 2,
                    self.height() // 2
                )
            
            self.parent_window.move(event.globalPos() - self._drag_position)
            event.accept()
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        self._is_dragging = False
    
    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.toggle_maximize()