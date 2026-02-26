"""SSH终端界面"""
import re
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QApplication)
from PyQt5.QtGui import QFont, QTextCursor, QColor, QClipboard
from qfluentwidgets import (PushButton, LineEdit, SubtitleLabel, BodyLabel,
                           InfoBar, InfoBarPosition, FluentIcon as FIF,
                           PrimaryPushButton, CardWidget)

from config import ServerConfig
from ssh import SSHClient, SSHWorker, SSHConnectWorker, SystemInfoWorker


class TerminalWidget(QTextEdit):
    """终端显示组件"""
    
    commandEntered = pyqtSignal(str)
    ctrlCPressed = pyqtSignal()  # Ctrl+C信号
    inputSubmitted = pyqtSignal(str)  # 用户输入提交信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.command_history = []
        self.history_index = 0
        self.current_input = ""
        self.prompt = "$ "
        self.is_command_running = False  # 是否有命令在执行
        self.waiting_for_input = False  # 是否在等待用户输入
    
    def set_prompt(self, username: str, hostname: str, path: str = "~", is_root: bool = False):
        """设置提示符"""
        symbol = "#" if is_root else "$"
        self.prompt = f"{username}@{hostname}:{path}{symbol} "
        
    def setup_ui(self):
        # 设置等宽字体
        font = QFont("Consolas", 11)
        self.setFont(font)
        
        # 设置样式
        self.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: none;
                padding: 10px;
            }
        """)
        
        self.setReadOnly(False)
        self.setAcceptRichText(False)
    
    def keyPressEvent(self, event):
        # 检查Ctrl+C
        if event.key() == Qt.Key_C and event.modifiers() == Qt.ControlModifier:
            if self.is_command_running:
                self.ctrlCPressed.emit()
                self.append_output("^C\n")
                return
            else:
                # 复制选中的文本
                cursor = self.textCursor()
                if cursor.hasSelection():
                    selected_text = cursor.selectedText()
                    clipboard = QApplication.clipboard()
                    clipboard.setText(selected_text)
                    # 显示复制成功提示
                    InfoBar.success("提示", "文本复制成功", parent=self.parent(),
                                   position=InfoBarPosition.TOP)
                return
        
        # 如果在等待用户输入，直接发送输入
        if self.waiting_for_input:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                # 提交输入
                cursor = self.textCursor()
                cursor.movePosition(QTextCursor.End)
                self.setTextCursor(cursor)
                
                # 获取当前行的输入内容（去掉提示符）
                line_start = cursor.position() - len(self.current_input)
                cursor.setPosition(line_start, QTextCursor.KeepAnchor)
                input_text = cursor.selectedText()
                
                # 发送输入
                self.inputSubmitted.emit(input_text + "\n")
                self.append_output("\n")
                self.waiting_for_input = False
                self.current_input = ""
            elif event.key() == Qt.Key_Backspace:
                # 允许删除输入内容
                if len(self.current_input) > 0:
                    self.current_input = self.current_input[:-1]
                    super().keyPressEvent(event)
            elif event.key() >= Qt.Key_Space and event.key() <= Qt.Key_AsciiTilde:
                # 添加可打印字符
                self.current_input += event.text()
                super().keyPressEvent(event)
            else:
                # 其他按键忽略
                pass
            return
        
        cursor = self.textCursor()
        
        # 获取当前行的起始位置
        cursor.movePosition(QTextCursor.StartOfLine)
        line_start = cursor.position()
        
        # 确保光标不会移动到提示符之前
        prompt_end = line_start + len(self.prompt)
        
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            # 获取当前输入的命令
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.StartOfLine)
            cursor.movePosition(QTextCursor.EndOfLine, QTextCursor.KeepAnchor)
            line = cursor.selectedText()
            
            # 移除提示符获取命令
            if line.startswith(self.prompt):
                command = line[len(self.prompt):]
            else:
                command = line
            
            if command.strip():
                self.command_history.append(command)
                self.history_index = len(self.command_history)
                self.commandEntered.emit(command)
            
            # 换行
            self.moveCursor(QTextCursor.End)
            self.insertPlainText("\n")
            
        elif event.key() == Qt.Key_Up:
            # 历史命令上翻
            if self.history_index > 0:
                self.history_index -= 1
                self.replace_current_line(self.command_history[self.history_index])
                
        elif event.key() == Qt.Key_Down:
            # 历史命令下翻
            if self.history_index < len(self.command_history) - 1:
                self.history_index += 1
                self.replace_current_line(self.command_history[self.history_index])
            elif self.history_index == len(self.command_history) - 1:
                self.history_index = len(self.command_history)
                self.replace_current_line("")
                
        elif event.key() == Qt.Key_Backspace:
            # 防止删除提示符
            if self.textCursor().position() > prompt_end:
                super().keyPressEvent(event)
                
        elif event.key() == Qt.Key_Home:
            # Home键移动到提示符之后
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.StartOfLine)
            cursor.movePosition(QTextCursor.Right, QTextCursor.MoveAnchor, len(self.prompt))
            self.setTextCursor(cursor)
            
        else:
            super().keyPressEvent(event)
    
    def replace_current_line(self, text):
        """替换当前行的命令"""
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.StartOfLine)
        cursor.movePosition(QTextCursor.EndOfLine, QTextCursor.KeepAnchor)
        cursor.removeSelectedText()
        cursor.insertText(self.prompt + text)
        self.setTextCursor(cursor)
    
    def append_output(self, text, is_error=False):
        """添加输出"""
        # 移除ANSI转义序列
        clean_text = self.remove_ansi_escape_sequences(text)
        
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.setTextCursor(cursor)
        
        if is_error:
            # 错误信息用红色
            self.setTextColor(QColor("#f14c4c"))
        else:
            self.setTextColor(QColor("#d4d4d4"))
        
        self.insertPlainText(clean_text)
        self.setTextColor(QColor("#d4d4d4"))
        
        # 滚动到底部
        self.moveCursor(QTextCursor.End)
    
    def remove_ansi_escape_sequences(self, text):
        """移除ANSI转义序列和控制字符"""
        # ANSI转义序列的正则表达式
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        cleaned = ansi_escape.sub('', text)
        
        # 移除其他控制字符（除了换行符）
        # 保留 \n (换行), \t (制表符)
        control_chars = re.compile(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]')
        cleaned = control_chars.sub('', cleaned)
        
        # 规范化空白字符序列，将多个连续的空格、制表符合并为单个空格
        # 但保留单独的换行符
        cleaned = re.sub(r'[ \t]+', ' ', cleaned)
        
        # 移除行首行尾的多余空格
        lines = cleaned.split('\n')
        cleaned_lines = [line.strip() for line in lines]
        cleaned = '\n'.join(cleaned_lines)
        
        # 移除多余的空行（超过2个连续的换行符）
        while '\n\n\n' in cleaned:
            cleaned = cleaned.replace('\n\n\n', '\n\n')
        
        return cleaned
    
    def show_prompt(self):
        """显示提示符"""
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.setTextCursor(cursor)
        self.insertPlainText(self.prompt)
        self.moveCursor(QTextCursor.End)
    
    def set_waiting_for_input(self, waiting: bool):
        """设置是否在等待用户输入"""
        self.waiting_for_input = waiting
        if waiting:
            self.current_input = ""
    
    def set_command_running(self, running: bool):
        """设置命令执行状态"""
        self.is_command_running = running
        if not running:
            self.waiting_for_input = False
            self.current_input = ""
    
    def clear_terminal(self):
        """清除终端"""
        self.clear()
        self.show_prompt()


class SSHTerminalInterface(QWidget):
    """SSH终端界面"""
    
    disconnected = pyqtSignal()
    
    def __init__(self, server: ServerConfig, parent=None):
        super().__init__(parent)
        self.server = server
        self.ssh_client = None
        self.current_worker = None
        self.connect_worker = None
        self.system_info_worker = None
        self.current_path = "~"
        self.system_info = {}  # 存储系统信息
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 顶部信息栏
        header_card = CardWidget(self)
        header_layout = QVBoxLayout(header_card)
        
        # 第一行：服务器名称和连接信息
        top_row = QHBoxLayout()
        
        self.status_label = SubtitleLabel(f"连接到: {self.server.name}")
        top_row.addWidget(self.status_label)
        
        # 优化服务器信息显示，IP和端口做*号处理
        masked_info = self.mask_server_info(self.server.host, self.server.port)
        self.host_label = BodyLabel(masked_info)
        top_row.addWidget(self.host_label)
        
        top_row.addStretch()
        
        self.clear_button = PushButton("清屏")
        self.clear_button.setIcon(FIF.DELETE)
        self.clear_button.clicked.connect(self.clear_terminal)
        top_row.addWidget(self.clear_button)
        
        self.disconnect_button = PushButton("断开连接")
        self.disconnect_button.setIcon(FIF.CLOSE)
        self.disconnect_button.clicked.connect(self.disconnect)
        top_row.addWidget(self.disconnect_button)
        
        header_layout.addLayout(top_row)
        
        # 第二行：系统信息
        self.system_info_label = BodyLabel("系统信息加载中...")
        self.system_info_label.setWordWrap(True)
        header_layout.addWidget(self.system_info_label)
        
        layout.addWidget(header_card)
        
        # 终端区域
        terminal_container = CardWidget(self)
        terminal_layout = QVBoxLayout(terminal_container)
        terminal_layout.setContentsMargins(0, 0, 0, 0)
        
        self.terminal = TerminalWidget()
        self.terminal.commandEntered.connect(self.execute_command)
        self.terminal.ctrlCPressed.connect(self.on_ctrl_c)
        self.terminal.inputSubmitted.connect(self.on_user_input)
        terminal_layout.addWidget(self.terminal)
        
        layout.addWidget(terminal_container)
        
        # 快捷命令栏
        quick_layout = QHBoxLayout()
        
        quick_commands = [
            ("ls -la", "列出文件"),
            ("pwd", "当前目录"),
            ("top", "进程监控"),
            ("df -h", "磁盘使用"),
            ("free -h", "内存使用"),
        ]
        
        for cmd, tip in quick_commands:
            btn = PushButton(cmd)
            btn.setToolTip(tip)
            btn.clicked.connect(lambda checked, c=cmd: self.execute_command(c))
            quick_layout.addWidget(btn)
        
        quick_layout.addStretch()
        layout.addLayout(quick_layout)
    
    def mask_server_info(self, host: str, port: int) -> str:
        """将IP和端口信息做*号处理"""
        # 获取IP前缀（如192.168）
        parts = host.split('.')
        if len(parts) >= 2:
            masked_ip = f"{parts[0]}.{parts[1]}.***.***"
        else:
            # 非标准IP格式（如域名）
            if len(host) > 10:
                masked_ip = host[:6] + "***"
            else:
                masked_ip = host[:3] + "***"
        
        # 端口做*号处理
        port_str = str(port)
        if len(port_str) > 2:
            masked_port = port_str[0] + "*" * (len(port_str) - 1)
        else:
            masked_port = "**"
        
        return f"{masked_ip}:{masked_port}"
    
    def connect_to_server(self):
        """异步连接到服务器"""
        self.ssh_client = SSHClient(self.server)
        self.ssh_client.connected.connect(self.on_connected)
        self.ssh_client.disconnected.connect(self.on_disconnected)
        self.ssh_client.error_occurred.connect(self.on_error)
        
        # 不再显示连接提示信息
        # self.terminal.append_output(f"正在连接到 {self.server.host}:{self.server.port}...\n")
        
        # 使用异步线程连接，避免卡顿UI
        self.connect_worker = SSHConnectWorker(self.ssh_client)
        self.connect_worker.connected.connect(self.on_connect_success)
        self.connect_worker.failed.connect(self.on_connect_failed)
        self.connect_worker.start()
        
        return True  # 返回True表示开始连接，实际连接结果通过信号通知
    
    def on_connect_success(self):
        """连接成功回调"""
        # connected信号会自动触发on_connected
        pass
    
    def on_connect_failed(self, error: str):
        """连接失败回调"""
        # 错误已经通过error_occurred信号发送
        self.terminal.show_prompt()
    
    def on_connected(self):
        """连接成功"""
        # 不再显示连接成功的提示信息
        # self.terminal.append_output(f"已连接到 {self.server.name}\n")
        # self.terminal.append_output(f"用户: {self.server.username}\n\n")
        
        # 设置真实的提示符
        is_root = self.server.username == "root"
        hostname = self.ssh_client.hostname if self.ssh_client.hostname else self.server.host
        self.terminal.set_prompt(self.server.username, hostname, "~", is_root)
        
        self.terminal.show_prompt()
        
        # 异步获取系统信息
        self.fetch_system_info()
    
    def fetch_system_info(self):
        """异步获取系统信息"""
        if self.ssh_client and self.ssh_client.is_connected():
            self.system_info_worker = SystemInfoWorker(self.ssh_client)
            self.system_info_worker.info_ready.connect(self.on_system_info_ready)
            self.system_info_worker.start()
    
    def on_system_info_ready(self, info: dict):
        """系统信息获取完成"""
        self.system_info = info
        
        # 更新显示
        info_text = (
            f"🖥️ CPU: {info.get('cpu', '未知')}  |  "
            f"💾 内存: {info.get('memory_used', '?')}/{info.get('memory_total', '?')} ({info.get('memory_percent', '?')})  |  "
            f"💿 磁盘: {info.get('disk_used', '?')}/{info.get('disk_total', '?')} ({info.get('disk_percent', '?')})  |  "
            f"💻 系统: {info.get('os', '未知')}"
        )
        self.system_info_label.setText(info_text)
    
    def get_system_info(self) -> dict:
        """获取系统信息"""
        return self.system_info
    
    def on_disconnected(self):
        """断开连接"""
        self.terminal.append_output("\n连接已断开\n")
        self.disconnected.emit()
    
    def on_error(self, error):
        """错误处理"""
        self.terminal.append_output(f"\n错误: {error}\n", is_error=True)
    
    def execute_command(self, command: str):
        """执行命令"""
        if not self.ssh_client or not self.ssh_client.is_connected():
            self.terminal.append_output("未连接到服务器\n", is_error=True)
            self.terminal.show_prompt()
            return
        
        # 特殊命令处理
        if command.strip() == "clear":
            self.clear_terminal()
            return
        
        if command.strip() == "exit":
            self.disconnect()
            return
        
        # 创建工作线程执行命令
        self.terminal.set_command_running(True)
        self.current_worker = SSHWorker(self.ssh_client, command)
        self.current_worker.output_ready.connect(self.on_output)
        self.current_worker.error_ready.connect(self.on_command_error)
        self.current_worker.finished_signal.connect(self.on_command_finished)
        self.current_worker.input_requested.connect(self.on_input_requested)
        self.current_worker.start()
    
    def on_input_requested(self):
        """处理输入请求"""
        self.terminal.set_waiting_for_input(True)
        self.terminal.append_output("")  # 添加新行以接收输入
    
    def on_user_input(self, text: str):
        """处理用户输入"""
        if self.current_worker:
            self.current_worker.send_input(text)
    
    def on_output(self, output: str):
        """命令输出"""
        self.terminal.append_output(output)
    
    def on_command_error(self, error: str):
        """命令错误"""
        self.terminal.append_output(error, is_error=True)
    
    def on_command_finished(self):
        """命令执行完成"""
        self.terminal.set_command_running(False)
        self.current_worker = None
        self.terminal.show_prompt()
    
    def on_ctrl_c(self):
        """处理Ctrl+C中断"""
        if self.current_worker:
            self.current_worker.stop()
            self.terminal.set_command_running(False)
    
    def clear_terminal(self):
        """清除终端"""
        self.terminal.clear_terminal()
    
    def disconnect(self):
        """断开连接"""
        if self.ssh_client:
            self.ssh_client.disconnect()
            self.ssh_client = None
        self.disconnected.emit()
    
    def get_ssh_client(self) -> SSHClient:
        """获取SSH客户端"""
        return self.ssh_client
