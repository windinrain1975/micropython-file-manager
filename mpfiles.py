import sys
import os
import serial
import serial.tools.list_ports
import ast
import time
import shutil
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QStatusBar, QComboBox, QFileSystemModel, 
                             QTreeView, QHeaderView, QMessageBox, QInputDialog, QFileDialog,
                             QSplitter, QAbstractItemView, QLineEdit, QToolButton)
from PyQt5.QtCore import Qt, QTimer, QDir, QByteArray, QMimeData, QUrl, QRectF, QSettings, QSize
from PyQt5.QtGui import QIcon, QDragEnterEvent, QDropEvent, QPainter, QPixmap
from PyQt5.QtSvg import QSvgRenderer

import tempfile

from PyQt5.QtCore import QAbstractItemModel, QModelIndex, Qt, QDateTime
from PyQt5.QtGui import QStandardItem, QStandardItemModel

class MicroPythonFileModel(QStandardItemModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHorizontalHeaderLabels(['Name', 'Size', 'Type', 'Last Modified'])
        self.root_path = '/'

    def refresh(self, file_list, is_dir_list, size_list, mtime_list):
        self.clear()
        self.setHorizontalHeaderLabels(['Name', 'Size', 'Type', 'Last Modified'])
        for name, is_dir, size, mtime in zip(file_list, is_dir_list, size_list, mtime_list):
            name_item = QStandardItem(name)
            size_item = QStandardItem(str(size) if not is_dir else '')
            type_item = QStandardItem('Directory' if is_dir else 'File')
            mtime_item = QStandardItem(QDateTime.fromSecsSinceEpoch(mtime).toString("yyyy-MM-dd HH:mm:ss"))
            self.appendRow([name_item, size_item, type_item, mtime_item])

    def set_root_path(self, path):
        self.root_path = path

    def filePath(self, index):
        if not index.isValid():
            return self.root_path
        path = self.root_path
        while index.isValid():
            path = f"{path}/{index.data()}"
            index = index.parent()
        return path


class CustomTreeView(QTreeView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(True)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.CopyAction)
            event.accept()
            for url in event.mimeData().urls():
                self.parent().handle_file_drop(url.toLocalFile())

class NavigationWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        self.path_edit = QLineEdit()
        self.back_button = QToolButton()
        self.forward_button = QToolButton()
        self.up_button = QToolButton()
        self.browse_button = QToolButton()

        layout.addWidget(self.back_button)
        layout.addWidget(self.forward_button)
        layout.addWidget(self.up_button)
        layout.addWidget(self.path_edit)
        layout.addWidget(self.browse_button)

        self.set_button_icon(self.back_button, 'icon_back')
        self.set_button_icon(self.forward_button, 'icon_forward')
        self.set_button_icon(self.up_button, 'icon_up')
        self.set_button_icon(self.browse_button, 'icon_window')

    def set_button_icon(self, button, icon_name):
        svg_bytes = QByteArray(MicroPythonFileManager.get_icon_svg(icon_name).encode('utf-8'))
        renderer = QSvgRenderer(svg_bytes)
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        button.setIcon(QIcon(pixmap))
        button.setIconSize(QSize(24, 24))

class MicroPythonFileManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MicroPython File Manager")
        self.setGeometry(100, 100, 1000, 600)

        self.local_history = []
        self.local_current = -1
        self.mp_history = ['/']
        self.mp_current = 0

        self.serial = None
        self.status_bar = self.statusBar()
        self.board_info = QLabel()
        self.status_bar.addPermanentWidget(self.board_info)

        self.set_window_icon()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        top_layout = QHBoxLayout()
        self.port_combo = QComboBox()
        self.port_combo.addItem("Select Port")
        self.refresh_ports_button = QPushButton("Refresh Ports")
        self.connect_button = QPushButton("Connect")
        top_layout.addWidget(QLabel("Port:"))
        top_layout.addWidget(self.port_combo)
        top_layout.addWidget(self.refresh_ports_button)
        top_layout.addWidget(self.connect_button)
        top_layout.addStretch()

        splitter = QSplitter(Qt.Horizontal)

        # Local file system
        local_widget = QWidget()
        local_layout = QVBoxLayout(local_widget)
        self.local_nav = NavigationWidget()
        self.local_tree = CustomTreeView(self)
        self.local_model = QFileSystemModel()
        self.local_model.setRootPath(QDir.rootPath())
        self.local_tree.setModel(self.local_model)
        local_layout.addWidget(self.local_nav)
        local_layout.addWidget(self.local_tree)

        # MicroPython file system
        mp_widget = QWidget()
        mp_layout = QVBoxLayout(mp_widget)
        self.mp_nav = NavigationWidget()
        self.mp_tree = CustomTreeView(self)
        self.micro_model = QFileSystemModel()
        mp_layout.addWidget(self.mp_nav)
        mp_layout.addWidget(self.mp_tree)

        splitter.addWidget(local_widget)
        splitter.addWidget(mp_widget)

        bottom_layout = QHBoxLayout()
        self.refresh_button = QPushButton("Refresh")
        self.upload_button = QPushButton("Upload")
        self.download_button = QPushButton("Download")
        self.sync_to_button = QPushButton("Sync to Board")
        self.sync_from_button = QPushButton("Sync from Board")
        self.delete_button = QPushButton("Delete")
        bottom_layout.addWidget(self.refresh_button)
        bottom_layout.addWidget(self.upload_button)
        bottom_layout.addWidget(self.download_button)
        bottom_layout.addWidget(self.sync_to_button)
        bottom_layout.addWidget(self.sync_from_button)
        bottom_layout.addWidget(self.delete_button)

        self.set_button_icons()

        main_layout.addLayout(top_layout)
        main_layout.addWidget(splitter)
        main_layout.addLayout(bottom_layout)

        self.refresh_ports_button.clicked.connect(self.refresh_ports)
        self.connect_button.clicked.connect(self.toggle_connection)
        self.refresh_button.clicked.connect(self.refresh_files)
        self.upload_button.clicked.connect(self.upload_file)
        self.download_button.clicked.connect(self.download_file)
        self.sync_to_button.clicked.connect(self.sync_to_board)
        self.sync_from_button.clicked.connect(self.sync_from_board)
        self.delete_button.clicked.connect(self.delete_file)

        self.local_nav.path_edit.returnPressed.connect(self.navigate_local)
        self.local_nav.browse_button.clicked.connect(self.browse_local_folder)
        self.local_nav.back_button.clicked.connect(self.local_go_back)
        self.local_nav.forward_button.clicked.connect(self.local_go_forward)
        self.local_nav.up_button.clicked.connect(self.go_up_local)

        self.mp_nav.path_edit.returnPressed.connect(self.navigate_mp)
        self.mp_nav.back_button.clicked.connect(self.mp_go_back)
        self.mp_nav.forward_button.clicked.connect(self.mp_go_forward)
        self.mp_nav.up_button.clicked.connect(self.go_up_mp)

        self.local_tree.doubleClicked.connect(self.on_local_double_click)
        self.mp_tree.doubleClicked.connect(self.on_mp_double_click)

        self.load_last_directory()
        self.refresh_ports()

        self.setStyleSheet("""
        QWidget {
            font-family: 'Segoe UI', 'Noto Sans', 'Helvetica', 'Arial', sans-serif;
            font-size: 10pt;
        }
        """)

        self.micro_model = MicroPythonFileModel(self)
        self.mp_tree.setModel(self.micro_model)

    def local_go_back(self):
        if self.local_current > 0:
            self.local_current -= 1
            path = self.local_history[self.local_current]
            self.set_local_path(path)

    def local_go_forward(self):
        if self.local_current < len(self.local_history) - 1:
            self.local_current += 1
            path = self.local_history[self.local_current]
            self.set_local_path(path)

    def local_go_up(self):
        current_path = self.local_model.rootPath()
        parent_path = os.path.dirname(current_path)
        self.set_local_path(parent_path)

    def set_local_path(self, path):
        index = self.local_model.index(path)
        if index.isValid():
            self.local_tree.setRootIndex(index)
            self.local_nav.path_edit.setText(path)
            
            # Update history
            if self.local_current == -1 or path != self.local_history[self.local_current]:
                self.local_current += 1
                self.local_history = self.local_history[:self.local_current]
                self.local_history.append(path)
            
            self.update_local_nav_buttons()        

    def update_local_nav_buttons(self):
        self.local_nav.back_button.setEnabled(self.local_current > 0)
        self.local_nav.forward_button.setEnabled(self.local_current < len(self.local_history) - 1)
        self.local_nav.up_button.setEnabled(os.path.dirname(self.local_model.rootPath()) != self.local_model.rootPath())

    def mp_go_back(self):
        if self.mp_current > 0:
            self.mp_current -= 1
            path = self.mp_history[self.mp_current]
            self.set_mp_path(path)

    def mp_go_forward(self):
        if self.mp_current < len(self.mp_history) - 1:
            self.mp_current += 1
            path = self.mp_history[self.mp_current]
            self.set_mp_path(path)

    def mp_go_up(self):
        current_path = self.get_current_mp_path()
        parent_path = os.path.dirname(current_path)
        self.set_mp_path(parent_path)
        
    def set_mp_path(self, path):
        # 标准化路径
        path = path.replace('\\', '/')
        if not path.startswith('/'):
            path = '/' + path
        if path == '':
            path = '/'

        # 尝试在 MicroPython 设备上切换目录
        try:
            # 切换目录
            self.send_command(f"import os")
            result = self.send_command(f"os.chdir('{path}')")
            
            # 验证当前目录
            current_path = self.send_command("print(os.getcwd())")
            if current_path.strip() != path:
                raise Exception(f"Failed to change directory to {path}")
            
            # 更新 UI 中的路径显示
            self.mp_nav.path_edit.setText(path)
            
            # 更新历史记录
            if self.mp_current == -1 or path != self.mp_history[self.mp_current]:
                self.mp_current += 1
                self.mp_history = self.mp_history[:self.mp_current]
                self.mp_history.append(path)
            
            # 更新导航按钮状态
            self.update_mp_nav_buttons()
            
            # 刷新文件列表
            self.get_file_list()
            
            # 更新可用空间显示
            self.update_free_space()
            
        except Exception as e:
            # 如果出现错误，显示错误消息
            QMessageBox.critical(self, "Error", f"Failed to set path: {str(e)}")
            
            # 如果切换目录失败，回退到上一个有效路径
            if self.mp_current > 0:
                self.mp_current -= 1
                last_valid_path = self.mp_history[self.mp_current]
                self.mp_nav.path_edit.setText(last_valid_path)

    def update_mp_nav_buttons(self):
        # 更新后退按钮状态
        self.mp_nav.back_button.setEnabled(self.mp_current > 0)
        
        # 更新前进按钮状态
        self.mp_nav.forward_button.setEnabled(self.mp_current < len(self.mp_history) - 1)
        
        # 更新向上按钮状态（根目录时禁用）
        current_path = self.mp_history[self.mp_current]
        self.mp_nav.up_button.setEnabled(current_path != '/')

    def closeEvent(self, event):
        self.disconnect()
        self.save_last_directory()
        event.accept()

    def set_window_icon(self):
        svg = QSvgRenderer(QByteArray(self.get_icon_svg('icon_window').encode('utf-8')))
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        svg.render(painter)
        painter.end()
        self.setWindowIcon(QIcon(pixmap))

    def set_button_icons(self):
        icons = self.get_button_icons()
        icon_size = QSize(32, 32)
        for name, button in [('refresh_ports', self.refresh_ports_button),
                             ('refresh', self.refresh_button), 
                             ('connect', self.connect_button), 
                             ('upload', self.upload_button), 
                             ('download', self.download_button), 
                             ('sync_to', self.sync_to_button), 
                             ('sync_from', self.sync_from_button), 
                             ('delete', self.delete_button)]:
            button.setIcon(icons[name])
            button.setIconSize(icon_size)

    def get_button_icons(self):
        icons = {}
        for name in ['refresh_ports', 'refresh', 'disconnect', 'connect', 'upload', 'download', 'sync_to', 'sync_from', 'delete']:
            svg = QSvgRenderer(QByteArray(self.get_icon_svg(f'icon_{name}').encode('utf-8')))
            pixmap = QPixmap(32, 32)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            svg.render(painter)
            painter.end()
            icons[name] = QIcon(pixmap)
        return icons

    def refresh_ports(self):
        self.port_combo.clear()
        ports = serial.tools.list_ports.comports()
        micropython_ports = []
        
        for port in ports:
            try:
                ser = serial.Serial(port.device, 115200, timeout=1)
                ser.write(b'\x04')  # Soft reset
                time.sleep(0.5)
                response = ser.read_all().decode('utf-8', errors='ignore')
                
                if 'MicroPython' in response:
                    micropython_ports.append(port)
                    self.port_combo.addItem(f"{port.device} - MicroPython", port.device)
                else:
                    self.port_combo.addItem(f"{port.device}", port.device)
                
                ser.close()
            except:
                self.port_combo.addItem(f"{port.device}", port.device)
        
        if micropython_ports:
            self.port_combo.setCurrentIndex(self.port_combo.findData(micropython_ports[0].device))
        
        self.status_bar.showMessage(f"Found {len(micropython_ports)} MicroPython device(s)")

    def toggle_connection(self):
        if self.serial is None or not self.serial.is_open:
            self.connect()
        else:
            self.disconnect()

    def connect(self):
        port = self.port_combo.currentData()
        try:
            self.serial = serial.Serial(port, 115200, timeout=1)
            self.connect_button.setText("Disconnect")
            self.connect_button.setIcon(self.get_button_icons()['disconnect'])
            self.status_bar.showMessage(f"Connected to {port}")
            self.get_board_info()
            self.get_file_list()
            self.update_file_ops_buttons(True)
        except serial.SerialException as e:
            QMessageBox.critical(self, "Connection Error", f"Failed to connect: {str(e)}")
            self.status_bar.showMessage(f"Failed to connect: {str(e)}")

    def disconnect(self):
        if self.serial:
            self.serial.close()
        self.serial = None
        self.connect_button.setText("Connect")
        self.connect_button.setIcon(self.get_button_icons()['connect'])
        self.status_bar.showMessage("Disconnected")
        self.board_info.setText("")
        self.micro_model.clear()
        self.micro_model.setHorizontalHeaderLabels(['Name', 'Size', 'Type', 'Last Modified'])
        self.micro_model.set_root_path('/')
        self.mp_tree.setRootIndex(QModelIndex())
        self.update_file_ops_buttons(False)
        self.update_free_space()


    def get_board_info(self):
        if not self.serial:
            return
        self.serial.write(b'\x04')  # Soft reset
        time.sleep(0.5)
        response = self.serial.read_all().decode('utf-8', errors='ignore').split('\n')[0]
        self.board_info.setText(response)

    def get_file_list(self):
        if not self.serial:
            return
        
        self.send_command("import os")
        response = self.send_command("print(os.listdir())")
        
        try:
            files = ast.literal_eval(response)
        except (SyntaxError, ValueError) as e:
            QMessageBox.warning(self, "Parse Error", f"Failed to parse file list: {str(e)}")
            return
        
        is_dir_list = []
        size_list = []
        mtime_list = []
        for file in files:
            stat_result = self.send_command(f"print(os.stat('{file}'))")
            try:
                stat = ast.literal_eval(stat_result)
                is_dir = stat[0] & 0x4000 != 0  # Check if it's a directory
                size = stat[6]  # st_size
                mtime = stat[8]  # st_mtime
            except (SyntaxError, ValueError, IndexError) as e:
                print(f"Error parsing stat for {file}: {e}")
                is_dir = False
                size = 0
                mtime = 0
            
            is_dir_list.append(is_dir)
            size_list.append(size)
            mtime_list.append(mtime)
        
        self.micro_model.refresh(files, is_dir_list, size_list, mtime_list)
        self.micro_model.set_root_path('/')
        self.mp_tree.setRootIndex(QModelIndex())
        
        self.update_free_space()

    def update_free_space(self):
        if not self.serial:
            return
        
        response = self.send_command("import os; print(os.statvfs('/'))")
        try:
            stat = ast.literal_eval(response)
            free_space = stat[0] * stat[3]  # f_bsize * f_bfree
            self.status_bar.showMessage(f"Free space: {free_space / 1024:.2f} KB")
        except (SyntaxError, ValueError) as e:
            self.status_bar.showMessage("Failed to get free space")

    def send_command(self, command):
        if not self.serial:
            raise Exception("Serial connection is not established")
        
        self.serial.write(f"{command}\r\n".encode())
        response = b""
        timeout = time.time() + 5  # 5 seconds timeout
        
        while True:
            if self.serial.in_waiting:
                line = self.serial.readline()
                if b">>>" in line:
                    break
                response += line
            
            if time.time() > timeout:
                QMessageBox.warning(self, "Error", "Timeout Error!")
                return None
                #raise Exception("Command timeout")
        
        response = response.decode().strip()
        return response.replace(command, "").replace(">>>", "").strip()

    def update_file_ops_buttons(self, enabled):
        self.upload_button.setEnabled(enabled)
        self.download_button.setEnabled(enabled)
        self.delete_button.setEnabled(enabled)
        self.sync_to_button.setEnabled(enabled)
        self.sync_from_button.setEnabled(enabled)

    def upload_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File to Upload")
        if file_path:
            self.upload_single_file(file_path)

    def upload_single_file(self, file_path):
        if not self.serial:
            QMessageBox.warning(self, "Error", "Not connected to a device")
            return

        file_name = os.path.basename(file_path)
        destination = self.get_current_mp_path()
        full_destination = os.path.join(destination, file_name).replace('\\', '/')

        # Check if file already exists
        if self.send_command(f"import os; print(os.path.exists('{full_destination}'))") == "True":
            reply = QMessageBox.question(self, 'File exists', 
                                         f"File {file_name} already exists. Do you want to overwrite?",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.No:
                return

        with open(file_path, 'rb') as file:
            content = file.read()

        self.send_command(f"f = open('{full_destination}', 'wb')")
        chunk_size = 1024
        for i in range(0, len(content), chunk_size):
            chunk = content[i:i+chunk_size]
            self.send_command(f"f.write({chunk})")
        self.send_command("f.close()")

        QMessageBox.information(self, "Upload Complete", f"File {file_name} uploaded successfully")
        self.refresh_files()

    def download_file(self):
        indexes = self.mp_tree.selectedIndexes()
        if not indexes:
            QMessageBox.warning(self, "Error", "No file selected")
            return

        file_path = self.micro_model.filePath(indexes[0])
        file_name = os.path.basename(file_path)
        source = self.get_current_mp_path()
        full_source = os.path.join(source, file_name).replace('\\', '/')

        save_path, _ = QFileDialog.getSaveFileName(self, "Save File", file_name)
        if save_path:
            # Get file size
            size = int(self.send_command(f"import os; print(os.stat('{full_source}')[6])"))
            
            with open(save_path, 'wb') as file:
                # Read file in chunks
                chunk_size = 1024
                for i in range(0, size, chunk_size):
                    chunk = self.send_command(f"print(open('{full_source}', 'rb').read({chunk_size}))")
                    chunk = ast.literal_eval(chunk)  # Convert string representation of bytes to actual bytes
                    file.write(chunk)
            
            QMessageBox.information(self, "Download Complete", f"File {file_name} downloaded successfully")

    def delete_file(self):
        indexes = self.mp_tree.selectedIndexes()
        if not indexes:
            QMessageBox.warning(self, "Error", "No file selected")
            return

        file_path = self.micro_model.filePath(indexes[0])
        file_name = os.path.basename(file_path)
        full_path = os.path.join(self.get_current_mp_path(), file_name).replace('\\', '/')

        reply = QMessageBox.question(self, 'Confirm Deletion', 
                                     f"Are you sure you want to delete {file_name}?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.send_command(f"import os; os.remove('{full_path}')")
            self.refresh_files()

    def sync_to_board(self):
        local_path = self.local_model.filePath(self.local_tree.rootIndex())
        mp_path = self.get_current_mp_path()
        self.sync_folders(local_path, mp_path, to_board=True)

    def sync_from_board(self):
        local_path = self.local_model.filePath(self.local_tree.rootIndex())
        mp_path = self.get_current_mp_path()
        self.sync_folders(local_path, mp_path, to_board=False)

    def sync_folders(self, local_path, mp_path, to_board):
        if to_board:
            for root, dirs, files in os.walk(local_path):
                for file in files:
                    local_file = os.path.join(root, file)
                    relative_path = os.path.relpath(local_file, local_path)
                    #mp_file = os.path.join(mp_path, relative_path).replace('\\', '/')
                    self.upload_single_file(local_file)
        else:
            # Recursively list files on MicroPython board
            def list_files(dir_path):
                command = f"import os; print('\\n'.join([f for f in os.listdir('{dir_path}') if os.stat('{dir_path}/'+f)[0] & 0x8000]))"
                files = self.send_command(command).split('\n')
                
                for file in files:
                    if file:  # Ignore empty strings
                        full_path = os.path.join(dir_path, file).replace('\\', '/')
                        yield full_path

                command = f"import os; print('\\n'.join([d for d in os.listdir('{dir_path}') if not os.stat('{dir_path}/'+d)[0] & 0x8000]))"
                dirs = self.send_command(command).split('\n')
                
                for dir in dirs:
                    if dir:  # Ignore empty strings
                        yield from list_files(os.path.join(dir_path, dir).replace('\\', '/'))

            mp_files = list(list_files(mp_path))
            
            for mp_file in mp_files:
                relative_path = os.path.relpath(mp_file, mp_path)
                local_file = os.path.join(local_path, relative_path)
                self.download_single_file(mp_file, local_file)

        self.refresh_files()

    def download_single_file(self, mp_file, local_file):
        # Get file size
        print(mp_file)
        size = int(self.send_command(f"import os; print(os.stat('{mp_file}')[6])"))
        
        # Ensure the local directory exists
        os.makedirs(os.path.dirname(local_file), exist_ok=True)
        
        with open(local_file, 'wb') as file:
            # Read and write file in chunks
            chunk_size = 1024
            for i in range(0, size, chunk_size):
                chunk = self.send_command(f"print(open('{mp_file}', 'rb').read({chunk_size}))")
                chunk = ast.literal_eval(chunk)  # Convert string representation of bytes to actual bytes
                file.write(chunk)


    def refresh_files(self):
        self.get_file_list()

    def handle_file_drop(self, file_path):
        self.upload_single_file(file_path)

    def navigate_local(self):
        path = self.local_nav.path_edit.text()
        if os.path.exists(path):
            index = self.local_model.index(path)
            self.local_tree.setRootIndex(index)
            self.local_nav.path_edit.setText(path)
        else:
            self.status_bar.showMessage("Invalid path", 3000)

    def navigate_mp(self):
        path = self.mp_nav.path_edit.text()
        if self.send_command(f"import os; print(os.path.exists('{path}'))") == "True":
            self.set_mp_path(path)
        else:
            self.status_bar.showMessage("Invalid path", 3000)

    def browse_local_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            index = self.local_model.index(folder)
            self.local_tree.setRootIndex(index)
            self.local_nav.path_edit.setText(folder)

    def go_up_local(self):
        current_index = self.local_tree.rootIndex()
        parent_index = current_index.parent()
        if parent_index.isValid():
            self.local_tree.setRootIndex(parent_index)
            self.local_nav.path_edit.setText(self.local_model.filePath(parent_index))

    def go_up_mp(self):
        current_path = self.get_current_mp_path()
        parent_path = os.path.dirname(current_path)
        self.set_mp_path(parent_path)

    def on_local_double_click(self, index):
        if self.local_model.isDir(index):
            self.local_tree.setRootIndex(index)
            self.local_nav.path_edit.setText(self.local_model.filePath(index))

    def on_mp_double_click(self, index):
        file_path = self.micro_model.filePath(index)
        if self.send_command(f"import os; print(os.path.isdir('{file_path}'))") == "True":
            self.set_mp_path(file_path)

    def get_current_mp_path(self):
        return self.mp_nav.path_edit.text() or "/"

    def load_last_directory(self):
        settings = QSettings("YourCompany", "MicroPythonFileManager")
        last_dir = settings.value("last_directory", QDir.homePath())
        index = self.local_model.index(last_dir)
        self.local_tree.setRootIndex(index)
        self.local_nav.path_edit.setText(last_dir)

    def save_last_directory(self):
        current_dir = self.local_model.filePath(self.local_tree.rootIndex())
        settings = QSettings("YourCompany", "MicroPythonFileManager")
        settings.setValue("last_directory", current_dir)

    @staticmethod
    def format_size(size):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0

    @staticmethod
    def get_icon_svg(name):
        icons = {
            'icon_window': '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><circle cx="12" cy="12" r="11" fill="#607D8B"/><path d="M6 6h12v12H6z" fill="none" stroke="white" stroke-width="2"/><path d="M6 10h12M10 6v12" stroke="white" stroke-width="2"/></svg>',
            'icon_refresh': '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><circle cx="12" cy="12" r="11" fill="#4CAF50"/><path d="M12 6A6 6 0 1 0 18 12" stroke="white" stroke-width="2" fill="none"/><path d="M18 8L18 12L14 12" fill="white"/></svg>',
            'icon_connect': '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><circle cx="12" cy="12" r="11" fill="#2196F3"/><path d="M7 12h10M12 7v10" stroke="white" stroke-width="2"/></svg>',
            'icon_disconnect': '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><circle cx="12" cy="12" r="11" fill="#F44336"/><path d="M7 12h10" stroke="white" stroke-width="2"/></svg>',
            'icon_upload': '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><circle cx="12" cy="12" r="11" fill="#FFC107"/><path d="M6 12L12 6L18 12M12 6v12" stroke="white" stroke-width="2" fill="none"/></svg>',
            'icon_download': '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><circle cx="12" cy="12" r="11" fill="#9C27B0"/><path d="M6 12L12 18L18 12M12 6v12" stroke="white" stroke-width="2" fill="none"/></svg>',
            'icon_sync_to': '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><circle cx="12" cy="12" r="11" fill="#FF9800"/><path d="M12 6A6 6 0 1 0 18 12" stroke="white" stroke-width="2" fill="none"/><path d="M18 8L18 12L14 12" fill="white"/></svg>',
            'icon_sync_from': '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><circle cx="12" cy="12" r="11" fill="#FF9800"/><path d="M12 18A6 6 0 1 1 18 12" stroke="white" stroke-width="2" fill="none"/><path d="M18 16L18 12L14 12" fill="white"/></svg>',
            'icon_delete': '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><circle cx="12" cy="12" r="11" fill="#E91E63"/><path d="M7 7l10 10M17 7L7 17" stroke="white" stroke-width="2"/></svg>',
            'icon_back': '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><circle cx="12" cy="12" r="11" fill="#795548"/><path d="M15 6l-6 6 6 6" stroke="white" stroke-width="2" fill="none"/></svg>',
            'icon_forward': '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><circle cx="12" cy="12" r="11" fill="#795548"/><path d="M9 6l6 6-6 6" stroke="white" stroke-width="2" fill="none"/></svg>',
            'icon_up': '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><circle cx="12" cy="12" r="11" fill="#3F51B5"/><path d="M6 15l6-6 6 6" stroke="white" stroke-width="2" fill="none"/></svg>',
            'icon_refresh_ports': '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><circle cx="12" cy="12" r="11" fill="#00BCD4"/><path d="M7 12h10v5H7z" fill="none" stroke="white" stroke-width="2"/><path d="M9 12V9m3 3V9m3 3V9" stroke="white" stroke-width="2"/><path d="M17 7A5 5 0 0 0 12 4" stroke="white" stroke-width="2" fill="none"/><path d="M17 7l2-2-2-2" stroke="white" stroke-width="2" fill="none"/></svg>',
        }
        return icons.get(name, '')


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MicroPythonFileManager()
    window.show()
    sys.exit(app.exec_())


