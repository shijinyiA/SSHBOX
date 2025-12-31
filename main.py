"""SSH终端管理器 - 主程序"""
import sys
import os
from PyQt5.QtCore import Qt, QMargins
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget, 
                            QHBoxLayout, QStackedWidget, QSplitter)
from PyQt5.QtGui import QFontDatabase, QFont, QPalette, QBrush, QPixmap, QPainter, QColor, QPen, QPainterPath
from qfluentwidgets import (NavigationInterface, NavigationItemPosition, 
                           setThemeColor, InfoBar, InfoBarPosition)
from qfluentwidgets import FluentIcon as FIF

from server_config import ServerConfig
from server_interface import ServerListWidget
from terminal_interface import SSHTerminalInterface
from terminal_tab_interface import TerminalTabWidget
from sftp_interface import SFTPFileInterface
from settings_interface import SettingInterface
from title_bar import CustomTitleBar


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 设置无边框窗口和圆角效果
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        
        self.setWindowTitle('锦衣的SSH工具箱')
        self.setGeometry(100, 100, 1400, 900)
        self.setMinimumSize(1000, 700)
        
        self.terminal_manager = None
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        self.root_layout = QVBoxLayout(self.central_widget)
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(0)
        
        self.title_bar = CustomTitleBar(self)
        self.root_layout.addWidget(self.title_bar)
        
        self.main_container = QWidget()
        self.main_layout = QHBoxLayout(self.main_container)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.root_layout.addWidget(self.main_container)
        
        self.navigation_interface = NavigationInterface(self, showMenuButton=True)
        self.main_layout.addWidget(self.navigation_interface)
        
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(10, 10, 10, 10)
        
        self.stack_widget = QStackedWidget()
        self.content_layout.addWidget(self.stack_widget)
        
        self.server_interface = ServerListWidget()
        self.server_interface.connectRequested.connect(self.connect_to_server)
        self.stack_widget.addWidget(self.server_interface)
        
        self.terminal_manager = TerminalTabWidget()
        self.terminal_manager.disconnected.connect(self.on_all_terminals_closed)
        self.stack_widget.addWidget(self.terminal_manager)
        
        self.setting_interface = SettingInterface(self)
        self.setting_interface.themeChanged.connect(self.on_theme_changed)
        self.setting_interface.backgroundChanged.connect(self.on_background_changed)
        self.stack_widget.addWidget(self.setting_interface)
        
        self.main_layout.addWidget(self.content_widget)
        
        self.init_navigation()
        
        self.stack_widget.setCurrentWidget(self.server_interface)
        
        self.load_background()
        
    def paintEvent(self, event):
        # 创建圆角窗口
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        # 绘制圆角背景
        rect = self.rect().marginsRemoved(QMargins(1, 1, 1, 1))
        path = QPainterPath()
        path.addRoundedRect(rect.x(), rect.y(), rect.width(), rect.height(), 12, 12)  # 12像素圆角
        
        # 使用白色背景
        painter.fillPath(path, QColor(255, 255, 255))
        
        # 绘制边框 - 使用更浅的颜色或完全移除
        # painter.setPen(QPen(QColor(200, 200, 200), 2))
        # painter.drawPath(path)
    
    def init_navigation(self):
        """初始化导航项"""
        # 服务器管理
        self.navigation_interface.addItem(
            routeKey='servers',
            icon=FIF.IOT,
            text='服务器',
            onClick=lambda: self.switch_to_interface('servers')
        )
        
        # 终端
        self.navigation_interface.addItem(
            routeKey='terminal',
            icon=FIF.COMMAND_PROMPT,
            text='终端',
            onClick=lambda: self.switch_to_interface('terminal')
        )
        
        # 设置
        self.navigation_interface.addItem(
            routeKey='settings',
            icon=FIF.SETTING,
            text='设置',
            onClick=lambda: self.switch_to_interface('settings'),
            position=NavigationItemPosition.BOTTOM
        )
        
        # 设置默认选中项
        self.navigation_interface.setCurrentItem('servers')
        
    def switch_to_interface(self, interface_name):
        """切换界面"""
        if interface_name == 'servers':
            self.stack_widget.setCurrentWidget(self.server_interface)
        elif interface_name == 'terminal':
            if self.terminal_manager and self.terminal_manager.has_terminals():
                self.stack_widget.setCurrentWidget(self.terminal_manager)
            else:
                InfoBar.warning("提示", "请先连接到服务器", parent=self,
                               position=InfoBarPosition.TOP)
                self.navigation_interface.setCurrentItem('servers')
        elif interface_name == 'settings':
            self.stack_widget.setCurrentWidget(self.setting_interface)
    
    def connect_to_server(self, server: ServerConfig):
        """连接到服务器 - 添加新的终端标签页"""
        if not self.terminal_manager:
            InfoBar.error("错误", "终端管理器未初始化", parent=self,
                         position=InfoBarPosition.TOP)
            return
        
        # 添加新的终端标签页（异步连接）
        tab_id = self.terminal_manager.add_terminal(server)
        
        if tab_id is not None:
            # 切换到终端界面
            self.stack_widget.setCurrentWidget(self.terminal_manager)
            self.navigation_interface.setCurrentItem('terminal')
            
            InfoBar.info("提示", f"正在连接到 {server.name}...", parent=self,
                        position=InfoBarPosition.TOP)
    
    def on_all_terminals_closed(self):
        """所有终端关闭时回到服务器列表"""
        self.stack_widget.setCurrentWidget(self.server_interface)
        self.navigation_interface.setCurrentItem('servers')
            
    def on_theme_changed(self, theme):
        # 更新标题栏主题
        self.title_bar.update_theme()
        # 更新终端标签页主题
        if self.terminal_manager:
            self.terminal_manager.update_theme()
    
    def on_background_changed(self, path: str):
        """处理背景更改"""
        self.set_background(path)
    
    def set_background(self, image_path: str):
        """设置背景图片"""
        if image_path and os.path.exists(image_path):
            palette = QPalette()
            pixmap = QPixmap(image_path)
            # 缩放图片以适应窗口
            scaled_pixmap = pixmap.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            palette.setBrush(QPalette.Window, QBrush(scaled_pixmap))
            self.central_widget.setAutoFillBackground(True)
            self.central_widget.setPalette(palette)
        else:
            # 清除背景
            self.central_widget.setAutoFillBackground(False)
            self.central_widget.setPalette(QPalette())
    
    def load_background(self):
        """加载背景图片配置"""
        bg_path = self.setting_interface.load_background_config()
        if bg_path:
            self.set_background(bg_path)
    
    def resizeEvent(self, event):
        """窗口大小改变时重新设置背景"""
        super().resizeEvent(event)
        bg_path = self.setting_interface.load_background_config()
        if bg_path:
            self.set_background(bg_path)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # 加载自定义字体
    font_path = os.path.join(os.path.dirname(__file__), "hk4e_zh-cn.ttf")
    if os.path.exists(font_path):
        font_id = QFontDatabase.addApplicationFont(font_path)
        if font_id != -1:
            font_families = QFontDatabase.applicationFontFamilies(font_id)
            if font_families:
                # 设置全局字体
                custom_font = QFont(font_families[0], 10)
                app.setFont(custom_font)
    
    # 设置主题颜色
    setThemeColor('#0078d4')
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())