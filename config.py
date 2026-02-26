"""服务器配置数据模型"""
import json
import os
import uuid
from dataclasses import dataclass, asdict, field
from typing import List, Optional

CONFIG_FILE = "servers.json"

@dataclass
class ServerConfig:
    """服务器配置"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    host: str = ""
    port: int = 22
    username: str = ""
    password: str = ""
    description: str = ""  # 服务器描述
    key_file: str = ""  # SSH私钥文件路径
    use_key: bool = False  # 是否使用密钥认证
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ServerConfig':
        return cls(**data)


class ServerConfigManager:
    """服务器配置管理器"""
    
    def __init__(self):
        self.servers: List[ServerConfig] = []
        self.config_path = os.path.join(os.path.dirname(__file__), CONFIG_FILE)
        self.load()
    
    def load(self):
        """从文件加载服务器配置"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.servers = [ServerConfig.from_dict(s) for s in data]
            except Exception as e:
                print(f"加载配置失败: {e}")
                self.servers = []
        else:
            self.servers = []
    
    def save(self):
        """保存服务器配置到文件"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                data = [s.to_dict() for s in self.servers]
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存配置失败: {e}")
    
    def add_server(self, server: ServerConfig) -> None:
        """添加服务器"""
        self.servers.append(server)
        self.save()
    
    def update_server(self, server: ServerConfig) -> None:
        """更新服务器配置"""
        for i, s in enumerate(self.servers):
            if s.id == server.id:
                self.servers[i] = server
                break
        self.save()
    
    def delete_server(self, server_id: str) -> None:
        """删除服务器"""
        self.servers = [s for s in self.servers if s.id != server_id]
        self.save()
    
    def get_server(self, server_id: str) -> Optional[ServerConfig]:
        """获取服务器配置"""
        for s in self.servers:
            if s.id == server_id:
                return s
        return None
    
    def get_all_servers(self) -> List[ServerConfig]:
        """获取所有服务器"""
        return self.servers.copy()


# 创建全局管理器实例
config_manager = ServerConfigManager()


def load_servers():
    """加载所有服务器配置"""
    return config_manager.get_all_servers()


def save_servers(servers: List[ServerConfig]):
    """保存服务器配置"""
    config_manager.servers = servers
    config_manager.save()


# ServerConfigDialog implementation
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QPushButton, QDialogButtonBox, QMessageBox, QLabel
from PyQt5.QtCore import Qt
from qfluentwidgets import CardWidget, SubtitleLabel, LineEdit, PushButton, PrimaryPushButton, ComboBox, Theme, setTheme


class ServerConfigDialog(QDialog):
    def __init__(self, parent=None, server: ServerConfig = None):
        super().__init__(parent)
        self.setWindowTitle("服务器配置" if server is None else "编辑服务器")
        self.setFixedSize(450, 400)
        
        self.server = server or ServerConfig()
        
        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # 标题
        title = SubtitleLabel("服务器配置", self)
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        main_layout.addWidget(title)
        
        # 卡片容器
        card = CardWidget(self)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(15)
        
        # 表单布局
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        form_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        
        # 名称输入
        self.name_edit = LineEdit(card)
        self.name_edit.setText(self.server.name)
        self.name_edit.setPlaceholderText("输入服务器名称")
        form_layout.addRow("名称:", self.name_edit)
        
        # 主机输入
        self.host_edit = LineEdit(card)
        self.host_edit.setText(self.server.host)
        self.host_edit.setPlaceholderText("例如: 192.168.1.1")
        form_layout.addRow("主机:", self.host_edit)
        
        # 端口输入
        self.port_edit = LineEdit(card)
        self.port_edit.setText(str(self.server.port))
        self.port_edit.setPlaceholderText("默认: 22")
        form_layout.addRow("端口:", self.port_edit)
        
        # 用户名输入
        self.username_edit = LineEdit(card)
        self.username_edit.setText(self.server.username)
        self.username_edit.setPlaceholderText("输入用户名")
        form_layout.addRow("用户名:", self.username_edit)
        
        # 密码输入
        self.password_edit = LineEdit(card)
        self.password_edit.setText(self.server.password)
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setPlaceholderText("输入密码")
        form_layout.addRow("密码:", self.password_edit)
        
        # 认证方式选择
        auth_layout = QHBoxLayout()
        self.auth_combo = ComboBox(card)
        self.auth_combo.addItems(["密码认证", "密钥认证"])
        self.auth_combo.setCurrentIndex(0 if not self.server.use_key else 1)
        auth_layout.addWidget(self.auth_combo)
        
        self.key_file_btn = PushButton("选择密钥文件", card)
        self.key_file_btn.setVisible(self.server.use_key)
        auth_layout.addWidget(self.key_file_btn)
        
        form_layout.addRow("认证方式:", auth_layout)
        
        # 描述输入
        self.description_edit = LineEdit(card)
        self.description_edit.setText(self.server.description)
        self.description_edit.setPlaceholderText("服务器描述信息")
        form_layout.addRow("描述:", self.description_edit)
        
        card_layout.addLayout(form_layout)
        main_layout.addWidget(card)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_btn = PushButton("取消", card)
        button_layout.addWidget(self.cancel_btn)
        
        self.ok_btn = PrimaryPushButton("确定", card)
        button_layout.addWidget(self.ok_btn)
        
        card_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
        
        # 连接信号
        self.cancel_btn.clicked.connect(self.reject)
        self.ok_btn.clicked.connect(self.accept)
        self.auth_combo.currentTextChanged.connect(self.on_auth_changed)
        
    def on_auth_changed(self, text):
        # 根据认证方式显示/隐藏密钥文件按钮
        is_key_auth = text == "密钥认证"
        self.key_file_btn.setVisible(is_key_auth)
        if is_key_auth:
            self.key_file_btn.clicked.connect(self.select_key_file)
    
    def select_key_file(self):
        from PyQt5.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(self, "选择密钥文件", "", "密钥文件 (*.pem *.key *.ppk);;所有文件 (*)")
        if file_path:
            self.key_file_btn.setText(file_path.split("/")[-1])
    
    def get_config(self):
        # Validate inputs
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "警告", "请输入服务器名称")
            return None
        if not self.host_edit.text().strip():
            QMessageBox.warning(self, "警告", "请输入主机地址")
            return None
        if not self.username_edit.text().strip():
            QMessageBox.warning(self, "警告", "请输入用户名")
            return None
        
        try:
            port = int(self.port_edit.text().strip())
            if not (1 <= port <= 65535):
                raise ValueError("Port out of range")
        except ValueError:
            QMessageBox.warning(self, "警告", "请输入有效的端口号(1-65535)")
            return None
        
        # Create and return server config
        config = ServerConfig(
            id=self.server.id,  # Keep the same ID when editing
            name=self.name_edit.text().strip(),
            host=self.host_edit.text().strip(),
            port=port,
            username=self.username_edit.text().strip(),
            password=self.password_edit.text().strip(),
            description=self.description_edit.text().strip(),
            use_key=self.auth_combo.currentText() == "密钥认证",
            key_file=self.key_file_btn.text() if self.key_file_btn.isVisible() else ""
        )
        return config