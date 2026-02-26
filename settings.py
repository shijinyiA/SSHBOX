from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QFrame, QFileDialog, QScrollArea
from PyQt5.QtGui import QPixmap
from qfluentwidgets import (SettingCardGroup, SettingCard,
                           ComboBox, PushButton,
                           InfoBar, InfoBarPosition, CardWidget, SubtitleLabel, 
                           BodyLabel, Slider, setTheme, Theme, FluentIcon as FIF)

import os
import json

from config import load_servers, save_servers

# 配置文件路径
CONFIG_FILE = "app_config.json"

class SettingInterface(QWidget):
    backgroundChanged = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.config_path = os.path.join(os.path.dirname(__file__), CONFIG_FILE)
        self.current_bg_path = ""
        self.scroll_area = None
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setup_ui()
        
    def setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # 创建滚动区域
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.scroll_area.setStyleSheet("QScrollArea { background-color: rgba(255, 255, 255, 0.1); border: none; }")
        
        # 滚动区域的内容容器
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background-color: transparent;")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(20, 20, 20, 20)
        scroll_layout.setSpacing(15)
        
        # 标题
        title = SubtitleLabel('设置', self)
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        scroll_layout.addWidget(title)
        
        # 个性化设置组
        personalization_group = SettingCardGroup('个性化', self)
        personalization_group.setStyleSheet("SettingCardGroup { background-color: rgba(255, 255, 255, 0.9); border-radius: 8px; }")
        scroll_layout.addWidget(personalization_group)
        
        # 背景图片
        self.bg_card = SettingCard(FIF.PHOTO, '背景图片', '设置自定义背景图片', self)
        self.bg_card.hBoxLayout.addSpacing(10)
        
        bg_button = PushButton('设置', self)
        bg_button.clicked.connect(self.select_background)
        self.bg_card.hBoxLayout.addWidget(bg_button)
        
        self.bg_card.hBoxLayout.addSpacing(10)
        
        delete_bg_button = PushButton('删除', self)
        delete_bg_button.clicked.connect(self.reset_background)
        self.bg_card.hBoxLayout.addWidget(delete_bg_button)
        
        personalization_group.addSettingCard(self.bg_card)
        
        # 背景模糊程度
        self.blur_card = SettingCard(FIF.VIEW, '背景模糊', '调整背景图片的模糊程度', self)
        self.blur_card.hBoxLayout.addSpacing(20)
        
        self.blur_slider = Slider(Qt.Horizontal, self)
        self.blur_slider.setRange(0, 100)
        self.blur_slider.setValue(0)
        self.blur_slider.setFixedWidth(150)
        self.blur_slider.valueChanged.connect(self.on_blur_changed)
        self.blur_card.hBoxLayout.addWidget(self.blur_slider)
        
        self.blur_value_label = BodyLabel('0%', self)
        self.blur_value_label.setFixedWidth(35)
        self.blur_card.hBoxLayout.addWidget(self.blur_value_label)
        
        personalization_group.addSettingCard(self.blur_card)
        
        # 数据管理组
        data_group = SettingCardGroup('数据管理', self)
        #data_group.setStyleSheet("SettingCardGroup { background-color: rgba(255, 255, 255, 0.9); border-radius: 8px; }")
        scroll_layout.addWidget(data_group)
        
        # 导出服务器列表
        export_card = SettingCard(FIF.SAVE, '导出服务器列表', '将服务器配置导出为JSON文件', self)
        export_card.hBoxLayout.addSpacing(10)
        
        export_button = PushButton('导出', self)
        export_button.clicked.connect(self.export_servers)
        export_card.hBoxLayout.addWidget(export_button)
        
        data_group.addSettingCard(export_card)
        
        # 导入服务器列表
        import_card = SettingCard(FIF.FOLDER_ADD, '导入服务器列表', '从JSON文件导入服务器配置', self)
        import_card.hBoxLayout.addSpacing(10)
        
        import_button = PushButton('导入', self)
        import_button.clicked.connect(self.import_servers)
        import_card.hBoxLayout.addWidget(import_button)
        
        data_group.addSettingCard(import_card)
        
        # 关于组
        about_group = SettingCardGroup('关于', self)
        #about_group.setStyleSheet("SettingCardGroup { background-color: rgba(255, 255, 255, 0.9); border-radius: 8px; }")
        scroll_layout.addWidget(about_group)
        
        # 开源仓库
        repo_card = SettingCard(FIF.GITHUB, 'GitHub 仓库', '查看源代码和提交问题', self)
        repo_card.hBoxLayout.addSpacing(10)
        
        repo_button = PushButton('访问', self)
        repo_button.clicked.connect(lambda: os.system('start https://github.com/shijinyiA/sshbox'))
        repo_card.hBoxLayout.addWidget(repo_button)
        
        about_group.addSettingCard(repo_card)
        
        scroll_layout.addStretch()
        
        # 设置滚动区域的内容
        self.scroll_area.setWidget(scroll_content)
        self.layout.addWidget(self.scroll_area)
        
        # 强制刷新布局
        self.update()
        
        # 加载配置
        self.load_config()
        
    def on_blur_changed(self, value: int):
        self.blur_value_label.setText(f'{value}%')
        self.backgroundChanged.emit(self.get_background_path())
        self.save_config()
        
    def get_blur_value(self) -> int:
        return self.blur_slider.value()
        
    def get_background_path(self) -> str:
        return self.current_bg_path
        
    def select_background(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择背景图片", "", "图片文件 (*.png *.jpg *.jpeg *.bmp)"
        )
        if file_path:
            self.current_bg_path = file_path
            # 只显示文件名，避免路径过长导致遮挡
            file_name = os.path.basename(file_path)
            if len(file_name) > 30:
                file_name = file_name[:27] + "..."
            self.bg_card.contentLabel.setText(file_name)
            self.backgroundChanged.emit(file_path)
            self.save_config()
            InfoBar.success("成功", "背景图片已设置", parent=self.window(),
                           position=InfoBarPosition.TOP)
    
    def reset_background(self):
        self.current_bg_path = ""
        self.bg_card.contentLabel.setText("未设置")
        self.backgroundChanged.emit("")
        self.save_config()
        InfoBar.success("成功", "背景图片已清除", parent=self.window(),
                       position=InfoBarPosition.TOP)
    
    def export_servers(self):
        """导出服务器列表"""
        servers = load_servers()
        if not servers:
            InfoBar.warning("提示", "没有可导出的服务器", parent=self.window(),
                           position=InfoBarPosition.TOP)
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出服务器列表", "servers.json", "JSON文件 (*.json)"
        )
        if file_path:
            try:
                data = [server.to_dict() for server in servers]
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                InfoBar.success("成功", f"已导出 {len(servers)} 个服务器", parent=self.window(),
                               position=InfoBarPosition.TOP)
            except Exception as e:
                InfoBar.error("错误", f"导出失败: {str(e)}", parent=self.window(),
                             position=InfoBarPosition.TOP)
    
    def import_servers(self):
        """导入服务器列表"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "导入服务器列表", "", "JSON文件 (*.json)"
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                from config import ServerConfig
                new_servers = [ServerConfig.from_dict(item) for item in data]
                
                # 加载现有服务器
                existing_servers = load_servers()
                
                # 合并服务器（避免重复）
                existing_ids = {s.id for s in existing_servers}
                for server in new_servers:
                    if server.id not in existing_ids:
                        existing_servers.append(server)
                
                # 保存
                save_servers(existing_servers)
                
                InfoBar.success("成功", f"已导入 {len(new_servers)} 个服务器", parent=self.window(),
                               position=InfoBarPosition.TOP)
            except Exception as e:
                InfoBar.error("错误", f"导入失败: {str(e)}", parent=self.window(),
                             position=InfoBarPosition.TOP)
    
    def load_config(self):
        """加载配置"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    
                    # 加载背景
                    bg_path = config.get('background', '')
                    if bg_path:
                        self.current_bg_path = bg_path
                        self.bg_card.contentLabel.setText(bg_path)
                    else:
                        self.current_bg_path = ""
                        self.bg_card.contentLabel.setText("未设置")
                    
                    # 加载模糊程度
                    blur = config.get('blur', 0)
                    self.blur_slider.setValue(blur)
                    self.blur_value_label.setText(f'{blur}%')
        except Exception as e:
            print(f"加载配置失败: {e}")
    
    def save_config(self):
        """保存配置"""
        try:
            config = {}
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            
            config['background'] = self.current_bg_path
            config['blur'] = self.blur_slider.value()
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存配置失败: {e}")
    
    def load_background_config(self) -> str:
        """加载背景配置"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    return config.get('background', '')
        except Exception as e:
            print(f"加载背景配置失败: {e}")
        return ""
