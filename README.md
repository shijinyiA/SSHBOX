## 说明
无聊折腾，UI使用了[PyQt-Fluent-Widgets](https://github.com/zhiyiYo/PyQt-Fluent-Widgets)，环境请安装**Python**，一时出来的项目当然不会做的特别完善，需要的请自行修改使用。

## 项目文件说明

- `main.py` - 主程序入口，整个应用的框架都在这里
- `ssh_manager.py` - SSH连接管理，负责和服务器建立连接
- `terminal_interface.py` - SSH终端界面，就是那个命令行窗口
- `terminal_tab_interface.py` - 多标签页管理，可以同时开多个终端窗口
- `sftp_interface.py` - 文件传输功能，可以直接拖拽上传下载文件
- `server_config.py` - 服务器配置管理，保存服务器信息的
- `server_interface.py` - 服务器列表界面，管理服务器的地方
- `settings_interface.py` - 设置界面，可以改主题背景啥的
- `title_bar.py` - 自定义标题栏，让窗口看起来更像Windows 11
- `servers.json` - 服务器配置文件，保存的服务器信息都在这里
- `requirements.txt` - 依赖库列表
- `author_card.py` - 关于作者的界面

## 如何使用

### 克隆项目

```bash
git clone https://github.com/shijinyiA/sshbox
cd sshbox
```

### 安装依赖
**无法安装请换pip源**
```bash
pip install -r requirements.txt
```

如果遇到依赖安装问题，也可以手动安装：

```bash
pip install PyQt5 qfluentwidgets paramiko
```

### 运行程序

```bash
python main.py
```

### 额外:打包成exe

如果你想打包成exe文件，可以这样做：

1. 安装PyInstaller：
```bash
pip install pyinstaller
```

2. 打包命令：
```bash
pyinstaller -F -w -i 1.jpg main.py
```

打包后的exe文件在 `dist` 文件夹里。

## 特点

- 现代化的UI界面，类似Windows 11风格
- 支持多标签页SSH终端
- SFTP文件传输
- 服务器配置管理
- 支持主题切换
- 支持背景图片设置

## 附加
可随意修改并发布