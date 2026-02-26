"""SSH终端管理器 - 主程序"""
import sys
import os
import time
from PyQt5.QtCore import Qt, QMargins, QPoint, QTimer
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget, 
                            QHBoxLayout, QStackedWidget, QSplitter, QGraphicsBlurEffect, QLabel,
                            QGraphicsScene, QGraphicsPixmapItem)
from PyQt5.QtGui import QFontDatabase, QFont, QPalette, QBrush, QPixmap, QPainter, QColor, QPen, QPainterPath, QCursor, QImage
from qfluentwidgets import (NavigationInterface, NavigationItemPosition, 
                           setThemeColor, InfoBar, InfoBarPosition)
from qfluentwidgets import FluentIcon as FIF

from config import ServerConfig
from servers import ServerListWidget
from terminal import SSHTerminalInterface
from tabs import TerminalTabWidget
from sftp import SFTPFileInterface
from settings import SettingInterface
from title import CustomTitleBar


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 设置无边框窗口和圆角效果
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window | Qt.WindowMinMaxButtonsHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        
        self.setWindowTitle('SSH工具箱')
        self.setGeometry(100, 100, 1280, 720)
        self.setMinimumSize(800, 600)
        
        # 启用鼠标跟踪，以便在没有按下鼠标按钮时也能接收鼠标移动事件
        self.setMouseTracking(True)
        
        self.terminal_manager = None
        self._last_warning_time = 0
        self._resize_timer = None
        self._pending_bg_update = False
        
        # 创建背景标签
        self.background_label = QLabel(self)
        self.background_label.setGeometry(0, 0, 0, 0)
        self.background_label.lower()
        self.background_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        self.central_widget = QWidget()
        self.central_widget.setMouseTracking(True)
        self.setCentralWidget(self.central_widget)
        
        self.root_layout = QVBoxLayout(self.central_widget)
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(0)
        
        self.title_bar = CustomTitleBar(self)
        self.root_layout.addWidget(self.title_bar)
        
        self.main_container = QWidget()
        self.main_container.setMouseTracking(True)
        self.main_layout = QHBoxLayout(self.main_container)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.root_layout.addWidget(self.main_container)
        
        self.navigation_interface = NavigationInterface(self, showMenuButton=True)
        self.navigation_interface.setMinimumWidth(200)
        self.navigation_interface.setMaximumWidth(250)
        self.main_layout.addWidget(self.navigation_interface)
        
        self.content_widget = QWidget()
        self.content_widget.setMouseTracking(True)
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(10, 10, 10, 10)
        
        self.stack_widget = QStackedWidget()
        self.stack_widget.setMouseTracking(True)
        self.content_layout.addWidget(self.stack_widget)
        
        self.server_interface = ServerListWidget()
        self.server_interface.setMouseTracking(True)
        self.server_interface.connectRequested.connect(self.connect_to_server)
        self.stack_widget.addWidget(self.server_interface)
        
        self.terminal_manager = TerminalTabWidget()
        self.terminal_manager.setMouseTracking(True)
        self.terminal_manager.disconnected.connect(self.on_all_terminals_closed)
        self.stack_widget.addWidget(self.terminal_manager)
        
        self.setting_interface = SettingInterface(self)
        self.setting_interface.setMouseTracking(True)
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
        
        # 绘制圆角背景 - 使用半透明白色
        rect = self.rect().marginsRemoved(QMargins(1, 1, 1, 1))
        path = QPainterPath()
        path.addRoundedRect(rect.x(), rect.y(), rect.width(), rect.height(), 12, 12)  # 12像素圆角
        
        # 使用半透明白色背景（90%不透明度）
        painter.fillPath(path, QColor(255, 255, 255, 230))
        
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
            
    def on_background_changed(self, path: str):
        """处理背景更改"""
        self.set_background(path)
    
    def set_background(self, image_path: str):
        """设置背景图片"""
        if image_path and os.path.exists(image_path):
            # 加载图片
            pixmap = QPixmap(image_path)
            # 缩放图片以适应窗口
            scaled_pixmap = pixmap.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            
            # 获取模糊程度
            blur_value = self.setting_interface.get_blur_value()
            
            # 如果需要模糊，应用模糊效果
            if blur_value > 0:
                # 创建场景和项目
                scene = QGraphicsScene()
                item = QGraphicsPixmapItem(scaled_pixmap)
                scene.addItem(item)
                
                # 创建模糊效果
                blur = QGraphicsBlurEffect()
                blur.setBlurRadius(blur_value * 0.5)  # 将0-100映射到0-50
                item.setGraphicsEffect(blur)
                
                # 渲染场景到图片
                result = QImage(scaled_pixmap.size(), QImage.Format_ARGB32)
                result.fill(Qt.transparent)
                painter = QPainter(result)
                scene.render(painter)
                painter.end()
                
                # 转换回QPixmap
                scaled_pixmap = QPixmap.fromImage(result)
            
            # 设置到背景标签
            self.background_label.setPixmap(scaled_pixmap)
            self.background_label.setGeometry(0, 0, self.width(), self.height())
        else:
            # 清除背景
            self.background_label.clear()
    
    def load_background(self):
        """加载背景图片配置"""
        bg_path = self.setting_interface.load_background_config()
        if bg_path:
            self.set_background(bg_path)
    
    def resizeEvent(self, event):
        """窗口大小改变时重新设置背景"""
        super().resizeEvent(event)
        
        # 检查窗口是否太小
        min_width = 800
        min_height = 600
        if self.width() < min_width or self.height() < min_height:
            current_time = time.time()
            if current_time - self._last_warning_time > 2:
                self._last_warning_time = current_time
                InfoBar.warning(
                    title='窗口太小了喵！！',
                    content=f'建议窗口大小至少为 {min_width}x{min_height}',
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
        
        # 使用定时器延迟更新背景，避免频繁重绘导致掉帧
        if self._resize_timer:
            self._resize_timer.stop()
        
        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self._update_background)
        self._resize_timer.start(100)  # 100ms后更新背景
    
    def _update_background(self):
        """延迟更新背景"""
        bg_path = self.setting_interface.load_background_config()
        if bg_path:
            self.set_background(bg_path)
    
    def mousePressEvent(self, event):
        """鼠标按下事件 - 用于窗口拖拽和大小调整"""
        if event.button() == Qt.LeftButton:
            # 获取鼠标位置相对于窗口的坐标
            pos = event.pos()
            # 检查是否在窗口边缘（8像素范围内）
            if self.is_on_resize_border(pos):
                self.resizing = True
                self.resize_direction = self.get_resize_direction(pos)
                self.last_pos = event.globalPos()
                event.accept()
            else:
                # 如果不在边缘，不处理拖拽，让标题栏处理
                self.resizing = False
                event.ignore()
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件 - 处理窗口大小调整"""
        pos = event.pos()
        if not hasattr(self, 'resizing'):
            self.resizing = False
            
        if self.resizing and self.resize_direction:
            # 计算鼠标移动距离
            delta = event.globalPos() - self.last_pos
            self.resize_window(delta)
            self.last_pos = event.globalPos()
            event.accept()
        else:
            # 根据鼠标位置更新光标形状
            if self.is_on_resize_border(pos):
                cursor_shape = self.get_cursor_for_position(pos)
                self.setCursor(cursor_shape)
            else:
                self.setCursor(Qt.ArrowCursor)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.LeftButton:
            self.resizing = False
            self.resize_direction = None
            # 恢复默认光标
            self.setCursor(Qt.ArrowCursor)
            event.accept()
        else:
            event.ignore()
    
    def is_on_resize_border(self, pos):
        """检查鼠标是否在窗口边缘"""
        width, height = self.width(), self.height()
        border_size = 12  # 增加边缘检测区域大小
        
        return (pos.x() < border_size or pos.x() > width - border_size or
                pos.y() < border_size or pos.y() > height - border_size)
    
    def get_resize_direction(self, pos):
        """获取调整方向"""
        width, height = self.width(), self.height()
        border_size = 12
        
        left = pos.x() < border_size
        right = pos.x() > width - border_size
        top = pos.y() < border_size
        bottom = pos.y() > height - border_size
        
        if left and top:
            return 'top_left'
        elif right and top:
            return 'top_right'
        elif left and bottom:
            return 'bottom_left'
        elif right and bottom:
            return 'bottom_right'
        elif left:
            return 'left'
        elif right:
            return 'right'
        elif top:
            return 'top'
        elif bottom:
            return 'bottom'
        else:
            return None
    
    def get_cursor_for_position(self, pos):
        """根据位置返回适当的光标形状"""
        width, height = self.width(), self.height()
        border_size = 12
        
        left = pos.x() < border_size
        right = pos.x() > width - border_size
        top = pos.y() < border_size
        bottom = pos.y() > height - border_size
        
        if (left and top) or (right and bottom):
            return Qt.SizeFDiagCursor
        elif (right and top) or (left and bottom):
            return Qt.SizeBDiagCursor
        elif left or right:
            return Qt.SizeHorCursor
        elif top or bottom:
            return Qt.SizeVerCursor
        else:
            return Qt.ArrowCursor
    
    def resize_window(self, delta):
        """调整窗口大小"""
        if not self.resize_direction:
            return
            
        current_geometry = self.geometry()
        new_x, new_y = current_geometry.x(), current_geometry.y()
        new_width, new_height = current_geometry.width(), current_geometry.height()
        
        min_width, min_height = self.minimumWidth(), self.minimumHeight()
        if min_width <= 0:
            min_width = 400
        if min_height <= 0:
            min_height = 300
        
        if 'left' in self.resize_direction:
            new_width -= delta.x()
            new_x += delta.x()
        elif 'right' in self.resize_direction:
            new_width += delta.x()
            
        if 'top' in self.resize_direction:
            new_height -= delta.y()
            new_y += delta.y()
        elif 'bottom' in self.resize_direction:
            new_height += delta.y()
        
        # 限制最小尺寸
        new_width = max(new_width, min_width)
        new_height = max(new_height, min_height)
        
        # 应用新尺寸和位置
        self.setGeometry(new_x, new_y, new_width, new_height)


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