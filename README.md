# MicroPython File Manager / MicroPython 文件管理器

[English](#english) | [中文](#中文)

## English

MicroPython File Manager is a graphical user interface tool for managing the file system of MicroPython devices. It allows users to easily transfer files between a computer and a MicroPython device, and provides intuitive file management functions.

### Features

- Connect to MicroPython devices
- Browse local and MicroPython device file systems
- Upload files to MicroPython devices
- Download files from MicroPython devices
- Delete files on MicroPython devices
- Synchronize local and MicroPython device folders
- Support drag and drop file upload

### Installation

#### Dependencies

- Python 3.6+
- PyQt5
- pyserial

#### Steps

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/micropython-file-manager.git
   ```

2. Enter the project directory:
   ```
   cd micropython-file-manager
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

### Usage

Run the main program:

```
python mpfiles.py
```

1. Select the serial port of the MicroPython device from the dropdown list
2. Click "Connect" to connect to the device
3. Use the left panel to browse the local file system, and the right panel to browse the MicroPython device file system
4. Use the toolbar buttons to perform file operations

### Contributing

Issue reports and pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

### License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 中文

MicroPython 文件管理器是一个用于管理 MicroPython 设备文件系统的图形用户界面工具。它允许用户轻松地在计算机和 MicroPython 设备之间传输文件,并提供直观的文件管理功能。

### 功能特性

- 连接到 MicroPython 设备
- 浏览本地和 MicroPython 设备文件系统
- 上传文件到 MicroPython 设备
- 从 MicroPython 设备下载文件
- 删除 MicroPython 设备上的文件
- 同步本地和 MicroPython 设备文件夹
- 支持拖放文件上传

### 安装

#### 依赖

- Python 3.6+
- PyQt5
- pyserial

#### 步骤

1. 克隆此仓库:
   ```
   git clone https://github.com/yourusername/micropython-file-manager.git
   ```

2. 进入项目目录:
   ```
   cd micropython-file-manager
   ```

3. 安装依赖:
   ```
   pip install -r requirements.txt
   ```

### 使用方法

运行主程序:

```
python mpfiles.py
```

1. 从下拉列表中选择 MicroPython 设备的串口
2. 点击 "Connect" 连接到设备
3. 使用左侧面板浏览本地文件系统,右侧面板浏览 MicroPython 设备文件系统
4. 使用工具栏按钮执行文件操作

### 贡献

欢迎提交问题报告和拉取请求。对于重大更改,请先开issue讨论您想要改变的内容。

### 许可证

本项目采用 MIT 许可证 - 详情请见 [LICENSE](LICENSE) 文件。