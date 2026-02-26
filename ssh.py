"""SSH连接管理模块"""
import os
import stat
import time
import socket
import threading
from typing import Optional, Callable, List, Tuple
import paramiko
from PyQt5.QtCore import QObject, pyqtSignal, QThread

from config import ServerConfig


class SSHClient(QObject):
    """支持实时输出的SSH客户端封装"""
    
    # 信号定义
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    output_received = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, server: ServerConfig, parent=None):
        super().__init__(parent)
        self.server = server
        self.client: Optional[paramiko.SSHClient] = None
        self.sftp: Optional[paramiko.SFTPClient] = None
        self.channel = None
        self.current_channel = None  # 当前执行命令的channel
        self._connected = False
        self.hostname = ""
        self.current_path = "~"
        
    def connect(self) -> bool:
        """连接到服务器"""
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            if self.server.use_key and self.server.key_file:
                # 使用密钥认证
                key = paramiko.RSAKey.from_private_key_file(self.server.key_file)
                self.client.connect(
                    hostname=self.server.host,
                    port=self.server.port,
                    username=self.server.username,
                    pkey=key,
                    timeout=10
                )
            else:
                # 使用密码认证
                self.client.connect(
                    hostname=self.server.host,
                    port=self.server.port,
                    username=self.server.username,
                    password=self.server.password,
                    timeout=10
                )
            
            self._connected = True
            # 获取主机名
            try:
                _, hostname_output, _ = self.client.exec_command("hostname")
                self.hostname = hostname_output.read().decode('utf-8', errors='replace').strip()
            except:
                self.hostname = self.server.host
            
            self.connected.emit()
            return True
            
        except paramiko.AuthenticationException:
            self.error_occurred.emit("认证失败：用户名或密码错误")
            return False
        except paramiko.SSHException as e:
            self.error_occurred.emit(f"SSH错误：{str(e)}")
            return False
        except TimeoutError:
            self.error_occurred.emit(f"连接超时：无法连接到 {self.server.host}:{self.server.port}")
            return False
        except OSError as e:
            if "No route to host" in str(e) or "Network is unreachable" in str(e):
                self.error_occurred.emit(f"网络错误：无法访问 {self.server.host}")
            elif "Connection refused" in str(e):
                self.error_occurred.emit(f"连接被拒绝：请检查端口 {self.server.port} 是否正确")
            else:
                self.error_occurred.emit(f"连接错误：{str(e)}")
            return False
        except Exception as e:
            error_msg = str(e)
            if "timed out" in error_msg.lower():
                self.error_occurred.emit(f"连接超时：请检查IP地址和端口是否正确")
            else:
                self.error_occurred.emit(f"连接失败：{error_msg}")
            return False
    
    def disconnect(self):
        """断开连接"""
        try:
            if self.sftp:
                self.sftp.close()
                self.sftp = None
            if self.channel:
                self.channel.close()
                self.channel = None
            if self.client:
                self.client.close()
                self.client = None
            self._connected = False
            self.disconnected.emit()
        except Exception as e:
            self.error_occurred.emit(f"断开连接失败: {str(e)}")
    
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._connected and self.client is not None
    
    def execute_command(self, command: str) -> Tuple[str, str]:
        """执行命令（快速命令，等待完成）"""
        if not self.is_connected():
            return "", "未连接到服务器"
        
        try:
            stdin, stdout, stderr = self.client.exec_command(command, timeout=30)
            output = stdout.read().decode('utf-8', errors='replace')
            error = stderr.read().decode('utf-8', errors='replace')
            return output, error
        except Exception as e:
            return "", str(e)
    
    def execute_command_interactive(self, command: str):
        """执行交互式命令（支持实时输出和中断）"""
        if not self.is_connected():
            return None
        
        try:
            transport = self.client.get_transport()
            self.current_channel = transport.open_session()
            self.current_channel.get_pty()  # 获取伪TTY，支持Ctrl+C
            self.current_channel.exec_command(command)
            return self.current_channel
        except Exception as e:
            self.error_occurred.emit(f"执行命令失败: {str(e)}")
            return None
    
    def send_ctrl_c(self):
        """发送Ctrl+C中断信号"""
        if self.current_channel:
            try:
                self.current_channel.send('\x03')  # Ctrl+C
            except:
                pass
    
    def close_current_channel(self):
        """关闭当前命令channel"""
        if self.current_channel:
            try:
                self.current_channel.close()
            except:
                pass
            self.current_channel = None
    
    def get_sftp(self) -> Optional[paramiko.SFTPClient]:
        """获取SFTP客户端"""
        if not self.is_connected():
            return None
        
        try:
            if self.sftp is None:
                self.sftp = self.client.open_sftp()
            return self.sftp
        except Exception as e:
            self.error_occurred.emit(f"打开SFTP失败: {str(e)}")
            return None
    
    def list_dir(self, path: str) -> List[Tuple[str, bool, int]]:
        """列出目录内容，返回 (文件名, 是否为目录, 文件大小) 列表"""
        sftp = self.get_sftp()
        if not sftp:
            return []
        
        try:
            result = []
            for attr in sftp.listdir_attr(path):
                is_dir = stat.S_ISDIR(attr.st_mode)
                result.append((attr.filename, is_dir, attr.st_size))
            return sorted(result, key=lambda x: (not x[1], x[0].lower()))
        except Exception as e:
            self.error_occurred.emit(f"列出目录失败: {str(e)}")
            return []
    
    def download_file(self, remote_path: str, local_path: str, 
                     progress_callback: Optional[Callable[[int, int], None]] = None) -> bool:
        """下载文件"""
        sftp = self.get_sftp()
        if not sftp:
            return False
        
        try:
            sftp.get(remote_path, local_path, callback=progress_callback)
            return True
        except Exception as e:
            self.error_occurred.emit(f"下载失败: {str(e)}")
            return False
    
    def upload_file(self, local_path: str, remote_path: str,
                   progress_callback: Optional[Callable[[int, int], None]] = None) -> bool:
        """上传文件"""
        sftp = self.get_sftp()
        if not sftp:
            return False
        
        try:
            sftp.put(local_path, remote_path, callback=progress_callback)
            return True
        except Exception as e:
            self.error_occurred.emit(f"上传失败: {str(e)}")
            return False
    
    def mkdir(self, path: str) -> bool:
        """创建目录"""
        sftp = self.get_sftp()
        if not sftp:
            return False
        
        try:
            sftp.mkdir(path)
            return True
        except Exception as e:
            self.error_occurred.emit(f"创建目录失败: {str(e)}")
            return False
    
    def remove_file(self, path: str) -> bool:
        """删除文件"""
        sftp = self.get_sftp()
        if not sftp:
            return False
        
        try:
            sftp.remove(path)
            return True
        except Exception as e:
            self.error_occurred.emit(f"删除文件失败: {str(e)}")
            return False
    
    def rmdir(self, path: str) -> bool:
        """删除目录"""
        sftp = self.get_sftp()
        if not sftp:
            return False
        
        try:
            sftp.rmdir(path)
            return True
        except Exception as e:
            self.error_occurred.emit(f"删除目录失败: {str(e)}")
            return False


class SSHWorker(QThread):
    """支持实时输出的SSH命令执行工作线程"""
    
    output_ready = pyqtSignal(str)
    error_ready = pyqtSignal(str)
    finished_signal = pyqtSignal()
    input_requested = pyqtSignal()  # 请求用户输入信号
    
    def __init__(self, ssh_client: SSHClient, command: str, parent=None):
        super().__init__(parent)
        self.ssh_client = ssh_client
        self.command = command
        self._stop_requested = False
        self.channel = None
        self.input_queue = []  # 输入队列
    
    def send_input(self, text: str):
        """发送用户输入到远程进程"""
        self.input_queue.append(text)
    
    def run(self):
        """ 执行命令并实时输出"""
        self.channel = self.ssh_client.execute_command_interactive(self.command)
        if not self.channel:
            self.error_ready.emit("无法执行命令\n")
            self.finished_signal.emit()
            return
        
        try:
            # 实时读取输出
            while not self.channel.exit_status_ready() and not self._stop_requested:
                # 发送用户输入
                while self.input_queue:
                    text = self.input_queue.pop(0)
                    try:
                        self.channel.send(text)
                    except:
                        pass
                
                if self.channel.recv_ready():
                    data = self.channel.recv(4096).decode('utf-8', errors='replace')
                    if data:
                        self.output_ready.emit(data)
                        
                        # 检查是否需要用户输入（简单检测）
                        if '[Y/n]' in data or '[y/N]' in data or 'yes/no' in data.lower():
                            self.input_requested.emit()
                
                if self.channel.recv_stderr_ready():
                    data = self.channel.recv_stderr(4096).decode('utf-8', errors='replace')
                    if data:
                        self.error_ready.emit(data)
                
                time.sleep(0.05)  # 避免CPU占用过高
            
            # 读取剩余输出
            while self.channel.recv_ready():
                data = self.channel.recv(4096).decode('utf-8', errors='replace')
                if data:
                    self.output_ready.emit(data)
            while self.channel.recv_stderr_ready():
                data = self.channel.recv_stderr(4096).decode('utf-8', errors='replace')
                if data:
                    self.error_ready.emit(data)
        except Exception as e:
            self.error_ready.emit(f"\n错误: {str(e)}\n")
        finally:
            if self.channel:
                self.channel.close()
            self.ssh_client.current_channel = None
            self.finished_signal.emit()
    
    def stop(self):
        """停止命令执行"""
        self._stop_requested = True
        if self.channel:
            try:
                self.channel.send('\x03')  # 发送Ctrl+C
            except:
                pass


class FileTransferWorker(QThread):
    """文件传输工作线程"""
    
    progress = pyqtSignal(int, int)  # 已传输, 总大小
    finished_signal = pyqtSignal(bool, str)  # 成功, 消息
    
    def __init__(self, ssh_client: SSHClient, local_path: str, remote_path: str, 
                 is_upload: bool, parent=None):
        super().__init__(parent)
        self.ssh_client = ssh_client
        self.local_path = local_path
        self.remote_path = remote_path
        self.is_upload = is_upload
    
    def run(self):
        def progress_callback(transferred, total):
            self.progress.emit(transferred, total)
        
        try:
            if self.is_upload:
                success = self.ssh_client.upload_file(
                    self.local_path, self.remote_path, progress_callback
                )
            else:
                success = self.ssh_client.download_file(
                    self.remote_path, self.local_path, progress_callback
                )
            
            if success:
                self.finished_signal.emit(True, "传输完成")
            else:
                self.finished_signal.emit(False, "传输失败")
        except Exception as e:
            self.finished_signal.emit(False, str(e))


class SSHConnectWorker(QThread):
    """异步SSH连接工作线程"""
    
    connected = pyqtSignal()
    failed = pyqtSignal(str)
    
    def __init__(self, ssh_client: SSHClient, parent=None):
        super().__init__(parent)
        self.ssh_client = ssh_client
    
    def run(self):
        """ 在后台线程中执行连接"""
        if self.ssh_client.connect():
            self.connected.emit()
        else:
            # 错误信息已经通过ssh_client.error_occurred发送
            pass


class PingWorker(QThread):
    """服务器延迟检测工作线程"""
    
    ping_result = pyqtSignal(str, int)  # server_id, latency_ms (-1表示超时)
    
    def __init__(self, server_id: str, host: str, port: int, parent=None):
        super().__init__(parent)
        self.server_id = server_id
        self.host = host
        self.port = port
    
    def run(self):
        """ 检测服务器延迟"""
        try:
            start_time = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)  # 3秒超时
            result = sock.connect_ex((self.host, self.port))
            end_time = time.time()
            sock.close()
            
            if result == 0:
                latency = int((end_time - start_time) * 1000)
                self.ping_result.emit(self.server_id, latency)
            else:
                self.ping_result.emit(self.server_id, -1)
        except Exception:
            self.ping_result.emit(self.server_id, -1)


class SystemInfoWorker(QThread):
    """服务器系统信息获取工作线程"""
    
    info_ready = pyqtSignal(dict)  # {“cpu”: ..., “memory”: ..., “disk”: ...}
    
    def __init__(self, ssh_client: SSHClient, parent=None):
        super().__init__(parent)
        self.ssh_client = ssh_client
    
    def run(self):
        """获取服务器系统信息"""
        info = {
            "cpu": "未知",
            "memory_total": "未知",
            "memory_used": "未知",
            "memory_percent": "未知",
            "disk_total": "未知",
            "disk_used": "未知",
            "disk_percent": "未知",
            "os": "未知",
            "uptime": "未知"
        }
        
        try:
            # 获取CPU信息
            output, _ = self.ssh_client.execute_command(
                "cat /proc/cpuinfo | grep 'model name' | head -1 | cut -d ':' -f 2"
            )
            if output.strip():
                info["cpu"] = output.strip()
            
            # 获取内存信息
            output, _ = self.ssh_client.execute_command(
                "free -h | grep Mem | awk '{print $2, $3, $3/$2*100}'"
            )
            if output.strip():
                parts = output.strip().split()
                if len(parts) >= 2:
                    info["memory_total"] = parts[0]
                    info["memory_used"] = parts[1]
                if len(parts) >= 3:
                    try:
                        info["memory_percent"] = f"{float(parts[2]):.1f}%"
                    except:
                        pass
            
            # 获取磁盘信息（根目录）
            output, _ = self.ssh_client.execute_command(
                "df -h / | tail -1 | awk '{print $2, $3, $5}'"
            )
            if output.strip():
                parts = output.strip().split()
                if len(parts) >= 2:
                    info["disk_total"] = parts[0]
                    info["disk_used"] = parts[1]
                if len(parts) >= 3:
                    info["disk_percent"] = parts[2]
            
            # 获取操作系统信息
            output, _ = self.ssh_client.execute_command(
                "cat /etc/os-release 2>/dev/null | grep PRETTY_NAME | cut -d '=' -f 2 | tr -d '\"' || uname -s"
            )
            if output.strip():
                info["os"] = output.strip()
            
            # 获取运行时间
            output, _ = self.ssh_client.execute_command("uptime -p 2>/dev/null || uptime")
            if output.strip():
                uptime_str = output.strip()
                if uptime_str.startswith("up "):
                    uptime_str = uptime_str[3:]
                info["uptime"] = uptime_str
        
        except Exception as e:
            pass
        
        self.info_ready.emit(info)
