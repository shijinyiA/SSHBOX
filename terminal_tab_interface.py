from PyQt5.QtCore import pyqtSignal, Qt, QTimer
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QInputDialog, 
                            QMessageBox, QSplitter, QTabWidget, QTabBar as QtTabBar)
from qfluentwidgets import (FluentIcon as FIF, InfoBar, InfoBarPosition, 
                           CardWidget, PushButton)

from server_config import ServerConfig
from terminal_interface import SSHTerminalInterface
from sftp_interface import SFTPFileInterface


class TerminalTabWidget(QWidget):
    disconnected = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.terminals = {}
        self.is_closing = False
        self.setup_ui()
        self.update_theme()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        toolbar = CardWidget(self)
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(10, 5, 10, 5)
        
        self.add_terminal_btn = PushButton("新建终端", self)
        self.add_terminal_btn.setIcon(FIF.ADD)
        self.add_terminal_btn.clicked.connect(self.request_new_terminal)
        toolbar_layout.addWidget(self.add_terminal_btn)
        
        toolbar_layout.addStretch()
        layout.addWidget(toolbar)
        
        self.tab_widget = QTabWidget(self)
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_terminal)
        self.tab_widget.tabBarDoubleClicked.connect(self.rename_terminal)
        layout.addWidget(self.tab_widget)
    
    def update_theme(self):
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #e0e0e0;
                background-color: #ffffff;
            }
            QTabBar::tab {
                background-color: #f3f3f3;
                color: #000000;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #0078d4;
                color: #ffffff;
            }
            QTabBar::tab:hover {
                background-color: #e5e5e5;
            }
        """)
    
    def request_new_terminal(self):
        InfoBar.info("提示", "请从服务器列表选择要连接的服务器", parent=self,
                    position=InfoBarPosition.TOP)
    
    def add_terminal(self, server: ServerConfig, custom_name: str = None):
        if custom_name:
            tab_name = custom_name
        else:
            tab_name = f"{server.name}"
        
        terminal = SSHTerminalInterface(server)
        
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(terminal)
        
        index = self.tab_widget.addTab(splitter, f"{tab_name} (连接中...)")
        
        self.terminals[index] = {
            "terminal": terminal,
            "sftp": None,
            "server": server,
            "name": tab_name,
            "splitter": splitter
        }
        
        terminal.connect_to_server()
        
        def on_connect_success():
            current_index = self.get_terminal_index(terminal)
            if current_index >= 0:
                self.tab_widget.setTabText(current_index, tab_name)
                
                ssh_client = terminal.get_ssh_client()
                if ssh_client:
                    sftp = SFTPFileInterface(ssh_client)
                    splitter.addWidget(sftp)
                    splitter.setSizes([800, 400])
                    splitter.setStretchFactor(0, 3)
                    splitter.setStretchFactor(1, 2)
                    sftp.load_directory("/")
                    self.terminals[current_index]["sftp"] = sftp
        
        def on_connect_error(error):
            current_index = self.get_terminal_index(terminal)
            if current_index >= 0:
                self.tab_widget.setTabText(current_index, f"{tab_name} (连接失败)")
        
        terminal.ssh_client.connected.connect(on_connect_success) if terminal.ssh_client else None
        terminal.ssh_client.error_occurred.connect(on_connect_error) if terminal.ssh_client else None
        
        terminal.disconnected.connect(lambda: self.on_terminal_disconnected_by_object(terminal))
        
        self.tab_widget.setCurrentIndex(index)
        
        return index
    
    def get_terminal_index(self, terminal):
        for idx, info in self.terminals.items():
            if info["terminal"] == terminal:
                return idx
        return -1
    
    def close_terminal(self, index: int):
        if index not in self.terminals or self.is_closing:
            return
        
        reply = QMessageBox.question(
            self, "确认关闭",
            f"确定要关闭终端 '{self.terminals[index]['name']}' 吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.No:
            return
        
        self.is_closing = True
        
        terminal_info = self.terminals[index]
        terminal = terminal_info["terminal"]
        
        try:
            terminal.disconnected.disconnect()
        except:
            pass
        
        terminal.disconnect()
        
        self.tab_widget.removeTab(index)
        
        terminal_info["splitter"].deleteLater()
        del self.terminals[index]
        
        new_terminals = {}
        tab_count = self.tab_widget.count()
        sorted_indices = sorted(self.terminals.keys())
        
        for new_idx in range(tab_count):
            old_idx = sorted_indices[new_idx if new_idx < index else new_idx + 1] if new_idx < len(sorted_indices) else None
            if old_idx is not None and old_idx in self.terminals:
                new_terminals[new_idx] = self.terminals[old_idx]
        
        self.terminals = new_terminals
        
        self.is_closing = False
        
        if len(self.terminals) == 0:
            self.disconnected.emit()
    
    def on_terminal_disconnected_by_object(self, terminal):
        if self.is_closing:
            return
        
        index = self.get_terminal_index(terminal)
        if index >= 0:
            self.is_closing = True
            self.tab_widget.removeTab(index)
            if index in self.terminals:
                self.terminals[index]["splitter"].deleteLater()
                del self.terminals[index]
            
            new_terminals = {}
            for new_idx in range(self.tab_widget.count()):
                old_indices = sorted([k for k in self.terminals.keys() if k != index])
                if new_idx < len(old_indices):
                    new_terminals[new_idx] = self.terminals[old_indices[new_idx]]
            
            self.terminals = new_terminals
            self.is_closing = False
            
            if len(self.terminals) == 0:
                self.disconnected.emit()
    
    def rename_terminal(self, index: int):
        if index not in self.terminals:
            return
        
        current_name = self.terminals[index]["name"]
        new_name, ok = QInputDialog.getText(
            self, "重命名终端", "输入新名称:",
            text=current_name
        )
        
        if ok and new_name.strip():
            self.terminals[index]["name"] = new_name.strip()
            self.tab_widget.setTabText(index, new_name.strip())
            terminal = self.terminals[index]["terminal"]
            terminal.status_label.setText(f"连接到: {new_name.strip()}")
    
    def has_terminals(self) -> bool:
        return len(self.terminals) > 0
