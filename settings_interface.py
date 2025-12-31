from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QFrame, QFileDialog
from PyQt5.QtGui import QPixmap
from qfluentwidgets import (SettingCardGroup, SwitchSettingCard, SettingCard,
                           PushSettingCard, HyperlinkCard, ComboBox, PushButton,
                           InfoBar, InfoBarPosition, CardWidget, SubtitleLabel, 
                           BodyLabel)
from qfluentwidgets import FluentIcon as FIF

import os
import json

from author_card import AuthorCard

# 配置文件路径
CONFIG_FILE = "app_config.json"

class BackgroundSettingCard(SettingCard):
    """背景图片设置卡片"""
    
    backgroundChanged = pyqtSignal(str)
    
    def __init__(self, icon, title, content=None, parent=None):
        super().__init__(icon, title, content, parent)
        
        self.choose_button = PushButton("选择图片")
        self.choose_button.clicked.connect(self.choose_background)
        self.hBoxLayout.addWidget(self.choose_button, 0)
        
        self.clear_button = PushButton("清除背景")
        self.clear_button.clicked.connect(self.clear_background)
        self.hBoxLayout.addWidget(self.clear_button, 0)
        self.hBoxLayout.addSpacing(16)
        
    def choose_background(self):
        """选择背景图片"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择背景图片", "", "图片文件 (*.png *.jpg *.jpeg *.bmp)"
        )
        if file_path:
            self.backgroundChanged.emit(file_path)
            
    def clear_background(self):
        """清除背景"""
        self.backgroundChanged.emit("")

class ThemeSettingCard(SettingCard):
    
    themeChanged = pyqtSignal(int)
    
    def __init__(self, icon, title, content=None, parent=None):
        super().__init__(icon, title, content, parent)
        self.comboBox = ComboBox(self)
        self.comboBox.addItems(["浅色"])
        self.comboBox.setMinimumWidth(120)
        self.comboBox.currentIndexChanged.connect(self.themeChanged)
        self.hBoxLayout.addWidget(self.comboBox, 0)
        self.hBoxLayout.addSpacing(16)

class SettingInterface(QWidget):
    themeChanged = pyqtSignal(str)
    backgroundChanged = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.config_path = os.path.join(os.path.dirname(__file__), CONFIG_FILE)
        self.setup_ui()
        
    def setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(20)
        
        # 标题
        title = SubtitleLabel('设置', self)
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        self.layout.addWidget(title)
        
        # 主设置卡片
        settings_card = CardWidget(self)
        settings_layout = QVBoxLayout(settings_card)
        
        # 主题设置
        theme_layout = QHBoxLayout()
        theme_label = BodyLabel('主题:', self)
        theme_layout.addWidget(theme_label)
        
        self.theme_combo = ComboBox()
        self.theme_combo.addItems(['浅色', '深色'])
        self.theme_combo.setCurrentIndex(0)
        self.theme_combo.currentTextChanged.connect(self.on_theme_changed)
        theme_layout.addWidget(self.theme_combo)
        theme_layout.addStretch()
        
        settings_layout.addLayout(theme_layout)
        
        # 背景图片设置
        bg_layout = QHBoxLayout()
        bg_label = BodyLabel('背景图片:', self)
        bg_layout.addWidget(bg_label)
        
        self.bg_path_label = BodyLabel('未选择', self)
        bg_layout.addWidget(self.bg_path_label)
        
        self.select_bg_btn = PushButton('选择图片')
        self.select_bg_btn.clicked.connect(self.select_background)
        bg_layout.addWidget(self.select_bg_btn)
        
        settings_layout.addLayout(bg_layout)
        
        # 重置背景按钮
        reset_layout = QHBoxLayout()
        reset_layout.addStretch()
        self.reset_bg_btn = PushButton('重置背景')
        self.reset_bg_btn.clicked.connect(self.reset_background)
        reset_layout.addWidget(self.reset_bg_btn)
        
        settings_layout.addLayout(reset_layout)
        
        self.layout.addWidget(settings_card)
        
        # 作者信息卡片
        author_card = CardWidget(self)
        author_layout = QVBoxLayout(author_card)
        
        author_title = SubtitleLabel('关于', self)
        author_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        author_layout.addWidget(author_title)
        
        avatar_path = os.path.join(os.path.dirname(__file__), "1.jpg")
        self.author_card = AuthorCard(avatar_path)
        author_layout.addWidget(self.author_card)
        
        self.layout.addWidget(author_card)
        
        self.layout.addStretch()
        
        # 加载配置
        self.load_config()
        
    def on_theme_changed(self, index):
        theme = "light" if index == 0 else "dark"
        self.themeChanged.emit(theme)
    
    def on_background_changed(self, path: str):
        self.backgroundChanged.emit(path)
        self.save_background_config(path)
        
        if path:
            InfoBar.success("成功", "背景图片已设置", parent=self.window(),
                           position=InfoBarPosition.TOP)
        else:
            InfoBar.success("成功", "背景图片已清除", parent=self.window(),
                           position=InfoBarPosition.TOP)
    
    def select_background(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择背景图片", "", "图片文件 (*.png *.jpg *.jpeg *.bmp)"
        )
        if file_path:
            self.bg_path_label.setText(file_path)
            self.on_background_changed(file_path)
    
    def reset_background(self):
        self.bg_path_label.setText("未选择")
        self.on_background_changed("")
    
    def load_config(self):
        bg_path = self.load_background_config()
        if bg_path:
            self.bg_path_label.setText(bg_path)
        else:
            self.bg_path_label.setText("未选择")
    
    def save_background_config(self, path: str):
        try:
            config = {}
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            
            config['background'] = path
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存背景配置失败: {e}")
    
    def load_background_config(self) -> str:
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    return config.get('background', '')
        except Exception as e:
            print(f"加载背景配置失败: {e}")
        return ""