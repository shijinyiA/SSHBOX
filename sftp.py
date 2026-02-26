import os
from PyQt5.QtCore import pyqtSignal, Qt, QMimeData, QUrl, QPoint, QEasingCurve, QPropertyAnimation
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, 
                                    QTreeWidgetItem, QHeaderView, QFileDialog, QProgressBar,
                                    QAbstractItemView, QApplication, QMenu, QInputDialog,
                                    QFrame, QSizePolicy)
from PyQt5.QtGui import QDrag, QIcon, QCursor, QPainter, QColor
from qfluentwidgets import (PushButton, LineEdit, SubtitleLabel, BodyLabel,
                                   InfoBar, InfoBarPosition, FluentIcon as FIF,
                                   PrimaryPushButton, CardWidget, MessageBox,
                                   ProgressBar, Action, RoundMenu)

from ssh import SSHClient, FileTransferWorker


def format_size(size: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


class FileTreeWidget(QTreeWidget):
    
    filesDropped = pyqtSignal(list, str)  # 本地文件列表, 远程目标目录
    downloadRequested = pyqtSignal(str, str)  # 远程路径, 文件名
    renameRequested = pyqtSignal(str, str)  # 旧路径, 新名称
    deleteRequested = pyqtSignal(list)  # 要删除的路径列表
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.current_path = "/"
        
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        
    def setup_ui(self):
        self.setHeaderLabels(["名称", "大小", "类型"])
        self.setColumnWidth(0, 200)
        self.setColumnWidth(1, 100)
        self.setColumnWidth(2, 80)
        
        self.header().setSectionResizeMode(0, QHeaderView.Interactive)  # 名称列可调整
        self.header().setSectionResizeMode(1, QHeaderView.Fixed)       # 大小列固定
        self.header().setSectionResizeMode(2, QHeaderView.Fixed)       # 类型列固定
        
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDrop)
        self.setDefaultDropAction(Qt.CopyAction)
        
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setAlternatingRowColors(True)
        
        # 设置样式
        self.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                background-color: white;
            }
            QTreeWidget::item {
                padding: 5px;
                border-bottom: 1px solid #f0f0f0;
            }
            QTreeWidget::item:selected {
                background-color: #0078d4;
                color: white;
            }
            QTreeWidget::item:hover {
                background-color: #f0f0f0;
            }
        """)
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)
    
    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)
    
    def dropEvent(self, event):
        """处理文件拖放"""
        if event.mimeData().hasUrls():
            files = []
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    files.append(url.toLocalFile())
            
            if files:
                self.filesDropped.emit(files, self.current_path)
            
            event.acceptProposedAction()
        else:
            super().dropEvent(event)
    
    def startDrag(self, supportedActions):
        """开始拖拽 - 用于下载文件"""
        items = self.selectedItems()
        if not items:
            return
        
        # 只处理单个文件的拖拽
        if len(items) > 1:
            InfoBar.warning("提示", "一次只能拖拽一个文件", parent=self.window(),
                           position=InfoBarPosition.TOP)
            return
        
        item = items[0]
        is_dir = item.data(0, Qt.UserRole + 1)
        
        # 只允许拖拽文件，不允许拖拽目录
        if is_dir:
            InfoBar.warning("提示", "不支持拖拽文件夹，请使用右键菜单下载", parent=self.window(),
                           position=InfoBarPosition.TOP)
            return
        
        remote_path = item.data(0, Qt.UserRole)
        file_name = item.text(0)
        
        # 创建MimeData
        mime_data = QMimeData()
        
        # 创建一个临时文件路径用于拖拽
        import tempfile
        temp_dir = tempfile.gettempdir()
        temp_file_path = os.path.join(temp_dir, file_name)
        
        # 创建一个空的临时文件
        with open(temp_file_path, 'w') as f:
            pass
        
        # 将临时文件路径添加到MimeData
        url = QUrl.fromLocalFile(temp_file_path)
        mime_data.setUrls([url])
        
        # 存储远程路径信息，用于后续下载
        mime_data.setText(remote_path)
        
        # 创建拖拽对象
        drag = QDrag(self)
        drag.setMimeData(mime_data)
        
        # 设置拖拽图标
        pixmap = item.icon(0).pixmap(32, 32)
        drag.setPixmap(pixmap)
        drag.setHotSpot(QPoint(pixmap.width() // 2, pixmap.height() // 2))
        
        # 执行拖拽
        result = drag.exec_(Qt.CopyAction)
        
        # 删除临时文件
        try:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
        except:
            pass
        
        # 如果拖拽成功（用户将文件拖到了某个位置），则弹出保存对话框
        if result == Qt.CopyAction:
            # 弹出保存对话框
            local_path, _ = QFileDialog.getSaveFileName(
                self, "保存文件", file_name, "所有文件 (*)"
            )
            if local_path:
                # 触发下载
                self.downloadRequested.emit(remote_path, file_name)
                # 手动调用下载，因为downloadRequested信号不会自动传递local_path
                self.start_download(remote_path, local_path)
    
    def show_context_menu(self, position: QPoint):
        """显示右键菜单"""
        item = self.itemAt(position)
        if not item:
            return
        
        # 创建圆角菜单
        menu = RoundMenu(parent=self)
        
        remote_path = item.data(0, Qt.UserRole)
        is_dir = item.data(0, Qt.UserRole + 1)
        file_name = item.text(0)
        
        # 下载菜单项
        if not is_dir:
            download_action = Action(FIF.DOWN, "下载")
            download_action.triggered.connect(lambda: self.downloadRequested.emit(remote_path, file_name))
            menu.addAction(download_action)
        
        # 重命名菜单项
        rename_action = Action(FIF.EDIT, "重命名")
        rename_action.triggered.connect(lambda: self.rename_item(remote_path, file_name))
        menu.addAction(rename_action)
        
        # 分隔线
        menu.addSeparator()
        
        # 删除菜单项
        delete_action = Action(FIF.DELETE, "删除")
        delete_action.triggered.connect(lambda: self.delete_items([remote_path]))
        menu.addAction(delete_action)
        
        # 显示菜单
        menu.exec(QCursor.pos())
    
    def rename_item(self, old_path: str, old_name: str):
        """重命名项目"""
        new_name, ok = QInputDialog.getText(self, "重命名", "请输入新名称:", text=old_name)
        if ok and new_name and new_name != old_name:
            self.renameRequested.emit(old_path, new_name)
    
    def delete_items(self, paths: list):
        """删除项目"""
        self.deleteRequested.emit(paths)


class SFTPFileInterface(QWidget):
    
    def __init__(self, ssh_client: SSHClient, parent=None):
        super().__init__(parent)
        self.ssh_client = ssh_client
        self.current_path = "/"
        self.transfer_worker = None
        self.is_collapsed = False  # 是否已折叠
        self.setup_ui()
        
    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        self.sftp_container = QFrame()
        self.sftp_container.setObjectName("sftpContainer")
        self.sftp_container.setStyleSheet("""
            #sftpContainer {
                background-color: rgba(255, 255, 255, 200);
                border-radius: 8px;
                border: 1px solid rgba(0, 0, 0, 10%);
            }
            QFrame#sftpContainer {
                background-color: rgba(255, 255, 255, 200);
            }
        """)
        
        # SFTP布局
        layout = QVBoxLayout(self.sftp_container)
        layout.setContentsMargins(20, 20, 20, 20)  # 增大边距
        layout.setSpacing(15)
        
        # 路径导航栏
        nav_card = CardWidget(self.sftp_container)
        nav_card.setMinimumHeight(60)  # 增高导航栏
        nav_layout = QHBoxLayout(nav_card)
        nav_layout.setContentsMargins(10, 10, 10, 10)  # 增大内边距
        nav_layout.setSpacing(10)  # 增大间距
        
        self.home_button = PushButton()
        self.home_button.setIcon(FIF.HOME)
        self.home_button.setToolTip("主目录")
        self.home_button.clicked.connect(self.go_home)
        self.home_button.setFixedSize(40, 40)  # 增大按钮
        self.home_button.setStyleSheet("""
            QPushButton {
                border: 1px solid rgba(0, 0, 0, 10%);
                border-radius: 6px;  // 增大圆角
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 5%);
            }
        """)
        nav_layout.addWidget(self.home_button)
        
        self.up_button = PushButton()
        self.up_button.setIcon(FIF.UP)
        self.up_button.setToolTip("上级目录")
        self.up_button.clicked.connect(self.go_up)
        self.up_button.setFixedSize(40, 40)  # 增大按钮
        self.up_button.setStyleSheet("""
            QPushButton {
                border: 1px solid rgba(0, 0, 0, 10%);
                border-radius: 6px;  # 增大圆角
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 5%);
            }
        """)
        nav_layout.addWidget(self.up_button)
        
        self.refresh_button = PushButton()
        self.refresh_button.setIcon(FIF.SYNC)
        self.refresh_button.setToolTip("刷新")
        self.refresh_button.clicked.connect(self.refresh)
        self.refresh_button.setFixedSize(40, 40)  # 增大按钮
        self.refresh_button.setStyleSheet("""
            QPushButton {
                border: 1px solid rgba(0, 0, 0, 10%);
                border-radius: 6px;  # 增大圆角
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 5%);
            }
        """)
        nav_layout.addWidget(self.refresh_button)
        
        self.path_edit = LineEdit()
        self.path_edit.setPlaceholderText("路径")
        self.path_edit.returnPressed.connect(self.navigate_to_path)
        self.path_edit.setMinimumWidth(200)  # 增大路径输入框
        nav_layout.addWidget(self.path_edit)
        
        self.go_button = PushButton("前往")
        self.go_button.clicked.connect(self.navigate_to_path)
        nav_layout.addWidget(self.go_button)
        
        # 折叠按钮
        self.collapse_button = PushButton()
        self.collapse_button.setIcon(FIF.CHEVRON_RIGHT)
        self.collapse_button.setToolTip("折叠SFTP面板")
        self.collapse_button.clicked.connect(self.toggle_collapse)
        self.collapse_button.setFixedSize(40, 40)  # 增大按钮
        self.collapse_button.setStyleSheet("""
            QPushButton {
                border: 1px solid rgba(0, 0, 0, 10%);
                border-radius: 6px;  # 增大圆角
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 5%);
            }
        """)
        nav_layout.addWidget(self.collapse_button)
        
        layout.addWidget(nav_card)
        
        # 文件操作按钮
        action_card = CardWidget(self.sftp_container)
        action_card.setMinimumHeight(60)  # 增高操作栏
        action_layout = QHBoxLayout(action_card)
        action_layout.setContentsMargins(10, 10, 10, 10)  # 增大内边距
        action_layout.setSpacing(10)  # 增大间距
        
        self.upload_button = PrimaryPushButton("上传文件")
        self.upload_button.setIcon(FIF.UP)
        self.upload_button.clicked.connect(self.upload_files)
        self.upload_button.setMinimumWidth(100)
        action_layout.addWidget(self.upload_button)
        
        self.download_button = PushButton("下载文件")
        self.download_button.setIcon(FIF.DOWN)
        self.download_button.clicked.connect(self.download_selected)
        self.download_button.setMinimumWidth(100)
        action_layout.addWidget(self.download_button)
        
        self.mkdir_button = PushButton("新建文件夹")
        self.mkdir_button.setIcon(FIF.FOLDER_ADD)
        self.mkdir_button.clicked.connect(self.create_directory)
        self.mkdir_button.setMinimumWidth(120)
        action_layout.addWidget(self.mkdir_button)
        
        self.delete_button = PushButton("删除")
        self.delete_button.setIcon(FIF.DELETE)
        self.delete_button.clicked.connect(self.delete_selected)
        self.delete_button.setMinimumWidth(80)
        action_layout.addWidget(self.delete_button)
        
        action_layout.addStretch()
        layout.addWidget(action_card)
        
        # 提示信息
        tip_card = CardWidget(self.sftp_container)
        tip_layout = QVBoxLayout(tip_card)
        tip_layout.setContentsMargins(10, 10, 10, 10)  # 增大内边距
        
        tip_label = BodyLabel("提示: 可以直接拖拽本地文件到此处上传，或拖拽远程文件到本地下载")
        tip_label.setStyleSheet("color: #666;")
        tip_label.setWordWrap(True)
        tip_layout.addWidget(tip_label)
        layout.addWidget(tip_card)
        
        # 文件列表
        file_card = CardWidget(self.sftp_container)
        file_layout = QVBoxLayout(file_card)
        file_layout.setContentsMargins(0, 0, 0, 0)
        
        self.file_tree = FileTreeWidget()
        self.file_tree.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.file_tree.filesDropped.connect(self.on_files_dropped)
        self.file_tree.downloadRequested.connect(self.on_download_requested)
        self.file_tree.renameRequested.connect(self.on_rename_requested)
        self.file_tree.deleteRequested.connect(self.on_delete_requested)
        file_layout.addWidget(self.file_tree)
        layout.addWidget(file_card)
        
        # 传输进度条
        progress_card = CardWidget(self.sftp_container)
        progress_card.setMinimumHeight(50)  # 增高进度栏
        progress_layout = QHBoxLayout(progress_card)
        progress_layout.setContentsMargins(10, 10, 10, 10)  # 增大内边距
        
        self.progress_label = BodyLabel("")
        self.progress_label.setMinimumWidth(150)  # 增大标签
        progress_layout.addWidget(self.progress_label)
        
        self.progress_bar = ProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMinimumWidth(200)  # 增大进度条
        progress_layout.addWidget(self.progress_bar)
        
        progress_layout.addStretch()
        layout.addWidget(progress_card)
        
        main_layout.addWidget(self.sftp_container)
        
        self.expand_button = PushButton()
        self.expand_button.setIcon(FIF.CHEVRON_RIGHT)
        self.expand_button.setToolTip("展开SFTP面板")
        self.expand_button.clicked.connect(self.toggle_collapse)
        self.expand_button.setVisible(False)
        self.expand_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 200);
                border-radius: 15px;
                padding: 10px;
                border: 1px solid rgba(0, 0, 0, 10%);
            }
            QPushButton:hover {
                background-color: rgba(240, 240, 240, 220);
            }
        """)
        
        expand_container = QWidget()
        expand_layout = QVBoxLayout(expand_container)
        expand_layout.addWidget(self.expand_button, alignment=Qt.AlignCenter)
        expand_layout.setContentsMargins(0, 0, 0, 0)
        
        main_layout.addWidget(expand_container)
        
        self.sftp_container.setMinimumWidth(300)
        self.sftp_container.setMaximumWidth(16777215)  # 无限制最大宽度
        self.sftp_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    
    def load_directory(self, path: str = None):
        if path:
            self.current_path = path
        
        self.file_tree.current_path = self.current_path
        self.path_edit.setText(self.current_path)
        
        self.file_tree.clear()
        
        if not self.ssh_client or not self.ssh_client.is_connected():
            InfoBar.error("错误", "SSH连接已断开", parent=self.window(),
                         position=InfoBarPosition.TOP)
            return
        
        files = self.ssh_client.list_dir(self.current_path)
        
        for name, is_dir, size in files:
            item = QTreeWidgetItem()
            item.setText(0, name)
            
            if is_dir:
                item.setText(1, "-")
                item.setText(2, "文件夹")
                item.setIcon(0, FIF.FOLDER.icon())
            else:
                item.setText(1, format_size(size))
                item.setText(2, "文件")
                item.setIcon(0, FIF.DOCUMENT.icon())
            
            full_path = os.path.join(self.current_path, name).replace("\\", "/")
            item.setData(0, Qt.UserRole, full_path)
            item.setData(0, Qt.UserRole + 1, is_dir)
            
            self.file_tree.addTopLevelItem(item)
    
    def refresh(self):
        """刷新当前目录"""
        self.load_directory()
    
    def go_home(self):
        """返回主目录"""
        # 直接跳转到 /root 目录
        self.load_directory("/root")
    
    def go_up(self):
        """返回上级目录"""
        if self.current_path != "/":
            parent = os.path.dirname(self.current_path)
            if not parent:
                parent = "/"
            self.load_directory(parent)
    
    def toggle_collapse(self):
        """切换折叠/展开状态"""
        if self.is_collapsed:
            # 展开
            self.sftp_container.setVisible(True)
            self.expand_button.setVisible(False)
            self.collapse_button.setIcon(FIF.CHEVRON_RIGHT)
            self.collapse_button.setToolTip("折叠SFTP面板")
        else:
            # 折叠
            self.sftp_container.setVisible(False)
            self.expand_button.setVisible(True)
            self.expand_button.setIcon(FIF.CHEVRON_RIGHT)
            self.expand_button.setToolTip("展开SFTP面板")
        
        self.is_collapsed = not self.is_collapsed
    
    def navigate_to_path(self):
        """导航到指定路径"""
        path = self.path_edit.text().strip()
        if path:
            self.load_directory(path)
    
    def on_item_double_clicked(self, item, column):
        """双击项目"""
        is_dir = item.data(0, Qt.UserRole + 1)
        if is_dir:
            path = item.data(0, Qt.UserRole)
            self.load_directory(path)
    
    def on_files_dropped(self, files: list, remote_dir: str):
        """处理拖放的文件 - 上传"""
        for local_path in files:
            if os.path.isfile(local_path):
                file_name = os.path.basename(local_path)
                remote_path = os.path.join(remote_dir, file_name).replace("\\", "/")
                self.start_upload(local_path, remote_path)
    
    def on_download_requested(self, remote_path: str, file_name: str):
        """处理下载请求"""
        # 选择保存位置，默认使用文件名
        local_path, _ = QFileDialog.getSaveFileName(
            self, "保存文件", file_name, "所有文件 (*)"
        )
        if local_path:
            self.start_download(remote_path, local_path)
    
    def on_rename_requested(self, old_path: str, new_name: str):
        """处理重命名请求"""
        if not self.ssh_client or not self.ssh_client.is_connected():
            InfoBar.error("错误", "SSH连接已断开", parent=self.window(),
                         position=InfoBarPosition.TOP)
            return
        
        # 获取新路径
        parent_dir = os.path.dirname(old_path)
        new_path = os.path.join(parent_dir, new_name).replace("\\", "/")
        
        try:
            # 使用SFTP重命名
            sftp = self.ssh_client.get_sftp()
            if sftp:
                sftp.rename(old_path, new_path)
                InfoBar.success("成功", f"已重命名为: {new_name}", parent=self.window(),
                               position=InfoBarPosition.TOP)
                self.refresh()
        except Exception as e:
            InfoBar.error("错误", f"重命名失败: {str(e)}", parent=self.window(),
                         position=InfoBarPosition.TOP)
    
    def on_delete_requested(self, paths: list):
        """处理删除请求"""
        if not paths:
            return
        
        # 确认删除
        msg = MessageBox("确认删除", f"确定要删除选中的 {len(paths)} 个项目吗？", self.window())
        if not msg.exec_():
            return
        
        for path in paths:
            # 从 file_tree 中查找对应的项目以确定类型
            items = self.file_tree.findItems(os.path.basename(path), Qt.MatchExactly, 0)
            if items:
                is_dir = items[0].data(0, Qt.UserRole + 1)
                if is_dir:
                    self.ssh_client.rmdir(path)
                else:
                    self.ssh_client.remove_file(path)
        
        InfoBar.success("成功", "删除完成", parent=self.window(),
                       position=InfoBarPosition.TOP)
        self.refresh()
    
    def upload_files(self):
        """选择并上传文件"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择要上传的文件", "", "所有文件 (*)"
        )
        
        for local_path in files:
            file_name = os.path.basename(local_path)
            remote_path = os.path.join(self.current_path, file_name).replace("\\", "/")
            self.start_upload(local_path, remote_path)
    
    def download_selected(self):
        """下载选中的文件"""
        items = self.file_tree.selectedItems()
        if not items:
            InfoBar.warning("提示", "请先选择要下载的文件", parent=self.window(),
                           position=InfoBarPosition.TOP)
            return
        
        # 选择保存目录
        save_dir = QFileDialog.getExistingDirectory(self, "选择保存目录")
        if not save_dir:
            return
        
        for item in items:
            is_dir = item.data(0, Qt.UserRole + 1)
            if is_dir:
                continue  # 暂不支持下载目录
            
            remote_path = item.data(0, Qt.UserRole)
            file_name = item.text(0)
            local_path = os.path.join(save_dir, file_name)
            self.start_download(remote_path, local_path)
    
    def start_upload(self, local_path: str, remote_path: str):
        self.progress_label.setText(f"正在上传: {os.path.basename(local_path)}")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        self.transfer_worker = FileTransferWorker(
            self.ssh_client, local_path, remote_path, is_upload=True
        )
        self.transfer_worker.progress.connect(self.on_transfer_progress)
        self.transfer_worker.finished_signal.connect(self.on_upload_finished)
        self.transfer_worker.start()
    
    def start_download(self, remote_path: str, local_path: str):
        self.progress_label.setText(f"正在下载: {os.path.basename(remote_path)}")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        self.transfer_worker = FileTransferWorker(
            self.ssh_client, local_path, remote_path, is_upload=False
        )
        self.transfer_worker.progress.connect(self.on_transfer_progress)
        self.transfer_worker.finished_signal.connect(self.on_download_finished)
        self.transfer_worker.start()
    
    def on_transfer_progress(self, transferred: int, total: int):
        if total > 0:
            percent = int(transferred * 100 / total)
            self.progress_bar.setValue(percent)
    
    def on_upload_finished(self, success: bool, message: str):
        self.progress_bar.setVisible(False)
        self.progress_label.setText("")
        
        if success:
            InfoBar.success("成功", "文件上传完成", parent=self.window(),
                           position=InfoBarPosition.TOP)
            self.refresh()
        else:
            InfoBar.error("错误", f"上传失败: {message}", parent=self.window(),
                         position=InfoBarPosition.TOP)
    
    def on_download_finished(self, success: bool, message: str):
        self.progress_bar.setVisible(False)
        self.progress_label.setText("")
        
        if success:
            InfoBar.success("成功", "文件下载完成", parent=self.window(),
                           position=InfoBarPosition.TOP)
        else:
            InfoBar.error("错误", f"下载失败: {message}", parent=self.window(),
                         position=InfoBarPosition.TOP)
    
    def create_directory(self):
        from PyQt5.QtWidgets import QInputDialog
        
        name, ok = QInputDialog.getText(self, "新建文件夹", "请输入文件夹名称:")
        if ok and name:
            path = os.path.join(self.current_path, name).replace("\\", "/")
            if self.ssh_client.mkdir(path):
                InfoBar.success("成功", f"已创建文件夹: {name}", parent=self.window(),
                               position=InfoBarPosition.TOP)
                self.refresh()
            else:
                InfoBar.error("错误", "创建文件夹失败", parent=self.window(),
                             position=InfoBarPosition.TOP)
    
    def delete_selected(self):
        items = self.file_tree.selectedItems()
        if not items:
            InfoBar.warning("提示", "请先选择要删除的文件", parent=self.window(),
                           position=InfoBarPosition.TOP)
            return
        
        msg = MessageBox("确认删除", f"确定要删除选中的 {len(items)} 个项目吗？", self.window())
        if not msg.exec_():
            return
        
        for item in items:
            path = item.data(0, Qt.UserRole)
            is_dir = item.data(0, Qt.UserRole + 1)
            
            if is_dir:
                self.ssh_client.rmdir(path)
            else:
                self.ssh_client.remove_file(path)
        
        InfoBar.success("成功", "删除完成", parent=self.window(),
                       position=InfoBarPosition.TOP)
        self.refresh()
