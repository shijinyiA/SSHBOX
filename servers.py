from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                            QTableWidgetItem, QHeaderView, QAbstractItemView, 
                            QMenu, QAction, QMessageBox, QListWidget, QListWidgetItem)
from qfluentwidgets import (CardWidget, PushButton, FluentIcon as FIF, 
                           SubtitleLabel, PrimaryPushButton, ListWidget, ToolButton)

from config import ServerConfig, load_servers, save_servers


class ServerListWidgetItem(QListWidgetItem):
    def __init__(self, server: ServerConfig):
        super().__init__()
        self.server = server
        self.setText(f"{server.name}")
        self.setToolTip(f"{server.host}:{server.port} - {server.description}")
        
        # 设置显示文本
        self.setText(f"{server.name}\n{server.host}:{server.port}")
        
        # 存储服务器配置数据
        self.setData(0x0100, server)


class ServerListWidget(QWidget):
    connectRequested = pyqtSignal(ServerConfig)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.servers = load_servers()
        self.setup_ui()
        self.load_server_list()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 标题
        title = SubtitleLabel('服务器管理', self)
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)
        
        # 操作按钮区域
        button_layout = QHBoxLayout()
        
        self.add_server_btn = PrimaryPushButton('添加服务器', self)
        self.add_server_btn.setIcon(FIF.ADD)
        self.add_server_btn.clicked.connect(self.add_server)
        button_layout.addWidget(self.add_server_btn)
        
        self.edit_server_btn = PushButton('编辑', self)
        self.edit_server_btn.setIcon(FIF.EDIT)
        self.edit_server_btn.clicked.connect(self.edit_server)
        button_layout.addWidget(self.edit_server_btn)
        
        self.delete_server_btn = PushButton('删除', self)
        self.delete_server_btn.setIcon(FIF.DELETE)
        self.delete_server_btn.clicked.connect(self.delete_server)
        button_layout.addWidget(self.delete_server_btn)
        
        self.connect_btn = PushButton('连接', self)
        self.connect_btn.setIcon(FIF.CONNECT)
        self.connect_btn.clicked.connect(self.connect_to_selected)
        button_layout.addWidget(self.connect_btn)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # 服务器列表 - 采用类似左侧边栏的样式
        self.server_list = ListWidget(self)
        self.server_list.setStyleSheet("""
            QListWidget {
                background-color: rgba(255, 255, 255, 0.8);
                color: black;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 5px;
            }
            QListWidget::item {
                padding: 12px;
                border-bottom: 1px solid #f0f0f0;
                color: black;
            }
            QListWidget::item:selected {
                background-color: #0078d4;
                color: white;
                border-radius: 6px;
            }
            QListWidget::item:selected:!active {
                background-color: #0078d4;
                color: white;
            }
            QListWidget::item:hover {
                background-color: #e6f3ff;
                color: black;
                border-radius: 6px;
            }
            QListWidget::item:last {
                border-bottom: none;
            }
        """)
        self.server_list.itemDoubleClicked.connect(self.connect_to_selected)
        self.server_list.itemSelectionChanged.connect(self.on_item_selection_changed)
        
        layout.addWidget(self.server_list)
    
    def load_server_list(self):
        self.server_list.clear()
        
        for server in self.servers:
            item = ServerListWidgetItem(server)
            self.server_list.addItem(item)
    
    def on_item_selection_changed(self):
        # 当选择项目改变时更新按钮状态
        current_item = self.server_list.currentItem()
        has_selection = current_item is not None
        self.edit_server_btn.setEnabled(has_selection)
        self.delete_server_btn.setEnabled(has_selection)
        self.connect_btn.setEnabled(has_selection)
    
    def add_server(self):
        from config import ServerConfigDialog
        dialog = ServerConfigDialog(self)
        if dialog.exec_() == dialog.Accepted:
            config = dialog.get_config()
            if config:
                self.servers.append(config)
                save_servers(self.servers)
                self.load_server_list()
    
    def edit_server(self):
        current_item = self.server_list.currentItem()
        if current_item:
            server = current_item.data(0x0100)  # 获取服务器配置数据
            from config import ServerConfigDialog
            dialog = ServerConfigDialog(self, server)
            if dialog.exec_() == dialog.Accepted:
                updated_config = dialog.get_config()
                if updated_config:
                    # 找到服务器在列表中的索引并更新
                    for i, s in enumerate(self.servers):
                        if s.id == updated_config.id:
                            self.servers[i] = updated_config
                            break
                    save_servers(self.servers)
                    self.load_server_list()
        else:
            QMessageBox.warning(self, "警告", "请先选择一个服务器")
    
    def delete_server(self):
        current_item = self.server_list.currentItem()
        if current_item:
            server = current_item.data(0x0100)  # 获取服务器配置数据
            reply = QMessageBox.question(
                self, "确认删除",
                f"确定要删除服务器 '{server.name}' 吗？",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.servers = [s for s in self.servers if s.id != server.id]
                save_servers(self.servers)
                self.load_server_list()
        else:
            QMessageBox.warning(self, "警告", "请先选择一个服务器")
    
    def connect_to_selected(self):
        current_item = self.server_list.currentItem()
        if current_item:
            server = current_item.data(0x0100)  # 获取服务器配置数据
            self.connectRequested.emit(server)
        else:
            QMessageBox.warning(self, "警告", "请先选择一个服务器")
    
    def show_context_menu(self, position):
        menu = QMenu(self)
        
        connect_action = QAction("连接", self)
        connect_action.triggered.connect(self.connect_to_selected)
        menu.addAction(connect_action)
        
        edit_action = QAction("编辑", self)
        edit_action.triggered.connect(self.edit_server)
        menu.addAction(edit_action)
        
        delete_action = QAction("删除", self)
        delete_action.triggered.connect(self.delete_server)
        menu.addAction(delete_action)
        
        menu.exec_(self.server_list.viewport().mapToGlobal(position))