import sys
import requests
import json
import logging
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QTextEdit, QLineEdit, QPushButton, QLabel, QFileDialog, QInputDialog, QFontDialog, QColorDialog, QMenu, QAction, QShortcut
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QMetaObject, Q_ARG, QRect, QPoint
from PyQt5.QtGui import QPixmap, QScreen, QPainter, QPen, QCursor, QColor, QPolygon, QBrush, QFont, QKeySequence

import os
import base64
import ctypes
from ctypes import wintypes
from openai import OpenAI

# 配置日志
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# API 配置
API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
API_KEY = "sk-xxx"  # 替换为自己的 API Key，去模型平台注册账号，并申请API Key.


class PicBot(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.pinned_windows = []
        self.messages = [{'role': 'system', 'content': '你是一个非常专业的识图专家。'}]
    #    self.messages = [{'role': 'system', 'content': '你是一个温柔可爱的聊天小能手。'}]
    #    self.messages = [{'role': 'system', 'content': '你是一个非常专业的代码编程专家。'}]
        self.image_path = ""

        self.client = OpenAI(
            api_key=API_KEY,
            base_url=API_URL,
        )

    def get_response(self):
        completion = self.client.chat.completions.create(
            model = "qwen3-vl-plus",
            #model = "qwen-max-latest",
            #model = "qwen3-coder-plus",
            messages = self.messages,
            stream=True
        )

        #print(completion.choices[0].message.content)
        #return completion.choices[0].message.content
        return completion

    def encode_image_to_base64(self, image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def initUI(self):
        self.setWindowTitle('picbot')
        self.setGeometry(100, 100, 1000, 1200)

        # 将窗体显示在屏幕中间
        screen = QApplication.primaryScreen().geometry()
        size = self.geometry()
        self.move((screen.width() - size.width()) // 2, (screen.height() - size.height()) // 2)

        # 设置暗黑风格样式
        self.setStyleSheet("""
            QWidget {
                background-color: black;
                color: white;
            }
            QTextEdit#input_box {
                border: 2px solid #555555;
                background-color: #1a1a1a;
                color: white;
                font-family: 'Microsoft YaHei';
                font-size: 12pt;
            }
            QTextEdit#input_box:hover, QTextEdit#input_box:focus {
                border: 2px solid red;
                background-color: #1a1a1a;
                color: white;
                font-family: 'Microsoft YaHei';
                font-size: 12pt;
            }
            QTextEdit {
                border: 2px solid #555555;
                background-color: #1a1a1a;
                color: white;
                font-family: 'Microsoft YaHei';
                font-size: 12pt;
            }
            QLineEdit {
                border: 2px solid #555555;
                background-color: #1a1a1a;
                color: white;
            }
            QPushButton {
                border: 2px solid #555555;
                background-color: #333333;
                color: white;
                padding: 5px;
            }
            QPushButton:hover {
                border: 2px solid red;
                background-color: #444444;
            }
            QLabel {
                border: 2px solid #555555;
                background-color: #1a1a1a;
                color: white;
                padding: 5px;
            }
            QLabel:hover {
                border: 2px solid red;
            }
        """)

        layout = QVBoxLayout()

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setFixedHeight(600)
        layout.addWidget(self.chat_display)

        self.input_box = QTextEdit()
        self.input_box.setObjectName("input_box")
        self.input_box.setPlaceholderText("请输入对图片的诉求...")
        self.input_box.setFixedHeight(200)
        self.input_box.installEventFilter(self)
        layout.addWidget(self.input_box)

        self.send_button = QPushButton('发送')
        self.send_button.clicked.connect(self.send_message)
        layout.addWidget(self.send_button)

        self.image_label = QLabel()
        layout.addWidget(self.image_label)

        self.upload_image_button = QPushButton('上传图片')
        self.upload_image_button.clicked.connect(self.upload_image)
        layout.addWidget(self.upload_image_button)

        self.clear_image_button = QPushButton('清空图片')
        self.clear_image_button.clicked.connect(self.clear_image)
        layout.addWidget(self.clear_image_button)

        self.screenshot_button = QPushButton('截图')
        self.screenshot_button.clicked.connect(self.take_screenshot)
        layout.addWidget(self.screenshot_button)

        self.shortcut_screenshot = QShortcut(QKeySequence('Alt+1'), self)
        self.shortcut_screenshot.activated.connect(self.take_screenshot)

        self.doodle_button = QPushButton('涂鸦')
        self.doodle_button.clicked.connect(self.toggle_doodle)
        layout.addWidget(self.doodle_button)

        self.shortcut_doodle = QShortcut(QKeySequence('Alt+P'), self)
        self.shortcut_doodle.activated.connect(self.toggle_doodle)

        self.setLayout(layout)
        
        self.doodle_window = None
        self.is_doodling = False

    def send_message(self):
        user_input = self.input_box.toPlainText()
        if user_input:
            self.messages.append({"role": "user", "content": user_input})
            self.chat_display.append(f"用户: {user_input}\n")
            #self.update_chat_display_stream(f"用户: {user_input}\n")
            self.input_box.clear()

            image_path = self.image_path
        
            if not os.path.exists(image_path):
                print(f"图片不存在：{image_path} ，进入纯聊天模式。")
                messages_data = {
                    "role": "user",
                    "content": user_input,
                }
            else:
                base64_image = self.encode_image_to_base64(image_path)
                image_url = f"data:image/jpeg;base64,{base64_image}"
                messages_data = {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_url
                            },
                        },
                        {"type": "text", "text": user_input},
                    ],
                }

            self.messages.append(messages_data)
            #assistant_output = self.get_response()
            #self.messages.append({"role": "assistant", "content": assistant_output})
            #print(f"picbot处理结果：{assistant_output}\n")

            completion = self.get_response()
        
            full_content = ""
            print("流式输出内容为：")
            self.update_chat_display_stream(f"picbot：")
            for chunk in completion:
                # 如果stream_options.include_usage为True，则最后一个chunk的choices字段为空列表，需要跳过（可以通过chunk.usage获取 Token 使用量）
                if chunk.choices and chunk.choices[0].delta.content != "":
                    full_content += chunk.choices[0].delta.content
                    print(chunk.choices[0].delta.content)
                    self.update_chat_display_stream(f"{chunk.choices[0].delta.content}")
            print(f"完整内容为：{full_content}")
            self.update_chat_display_stream(f"\n")

            self.messages.append({"role": "assistant", "content": full_content})
            print(f"picbot处理结果：{full_content}\n")

        #self.update_chat_display_stream(f"picbot：{assistant_output}\n")
             

    def update_chat_display_stream(self, content):
        # 确保在主线程中更新UI
        if self.thread() != QThread.currentThread():
            QMetaObject.invokeMethod(self, "update_chat_display_stream", Qt.QueuedConnection, Q_ARG(str, content))
            return
        
        # 移动光标到末尾
        self.chat_display.moveCursor(self.chat_display.textCursor().End)
        # 插入文本
        self.chat_display.insertPlainText(content)
        # 再次移动光标到末尾
        self.chat_display.moveCursor(self.chat_display.textCursor().End)
        # 强制刷新控件
        self.chat_display.repaint()
        # 处理所有待处理的事件，确保UI及时更新
        QApplication.processEvents()

    def upload_image(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "上传图片", "", "Images (*.png *.jpg *.jpeg)", options=options)
        if file_name:
            pixmap = QPixmap(file_name)
            self.image_label.setPixmap(pixmap.scaled(200, 200))
            self.image_path = file_name
            print(f"picbot图片路径：{self.image_path}")

    def clear_image(self):
        # 清空图片显示
        self.image_label.clear()
        # 清空图片路径
        self.image_path = ""
        print("图片已清空")

    def take_screenshot(self):
        # 隐藏主窗口
        self.hide()
        
        # 强制处理事件队列，确保窗口真正隐藏
        QApplication.processEvents()
        
        # 延迟一小段时间确保窗口完全隐藏
        import time
        time.sleep(0.1)
        
        # 获取所有屏幕的截图并合并
        screens = QApplication.screens()
        screen_geoms = [s.geometry() for s in screens]
        all_x = min(g.x() for g in screen_geoms)
        all_y = min(g.y() for g in screen_geoms)
        all_right = max(g.x() + g.width() for g in screen_geoms)
        all_bottom = max(g.y() + g.height() for g in screen_geoms)
        total_w = all_right - all_x
        total_h = all_bottom - all_y
        
        combined = QPixmap(total_w, total_h)
        combined.fill(Qt.black)
        painter = QPainter(combined)
        for s in screens:
            geom = s.geometry()
            shot = s.grabWindow(0)
            painter.drawPixmap(geom.x() - all_x, geom.y() - all_y, shot)
        painter.end()
        
        # 创建截图选择窗口，覆盖所有屏幕
        self.screenshot_window = ScreenshotWindow(combined)
        self.screenshot_window.screenshot_taken.connect(self.on_screenshot_taken)
        self.screenshot_window.screenshot_canceled.connect(self.on_screenshot_canceled)
        self.screenshot_window.screenshot_pinned.connect(self.on_screenshot_pinned)
        self.screenshot_window.setGeometry(all_x, all_y, total_w, total_h)
        self.screenshot_window.show()
    
    def on_screenshot_canceled(self):
        # 取消截图，重新显示主窗口
        self.show()
    
    def on_screenshot_pinned(self, pixmap, pos):
        # 钉图后，重新显示主窗口，并创建钉图窗口
        self.show()
        pinned = PinnedWindow(pixmap, pos)
        pinned.show()
        self.pinned_windows.append(pinned)

    def toggle_doodle(self):
        if not self.is_doodling:
            # 开始涂鸦
            self.is_doodling = True
            self.doodle_button.setText('结束涂鸦')
            
            # 隐藏主窗口
            self.hide()
            
            # 强制处理事件队列，确保窗口真正隐藏
            QApplication.processEvents()
            
            # 延迟一小段时间确保窗口完全隐藏
            import time
            time.sleep(0.1)
            
            # 截取当前屏幕内容
            screen = QApplication.primaryScreen()
            screenshot = screen.grabWindow(0)
            
            # 创建涂鸦窗口，传递屏幕截图作为背景
            self.doodle_window = DoodleWindow(screenshot)
            self.doodle_window.doodle_finished.connect(self.on_doodle_finished)
            self.doodle_window.showFullScreen()
        else:
            # 结束涂鸦
            self.stop_doodle()
    
    def stop_doodle(self):
        if self.doodle_window:
            self.doodle_window.close()
            self.doodle_window = None
        
        self.is_doodling = False
        self.doodle_button.setText('涂鸦')
        self.show()
    
    def on_doodle_finished(self, pixmap):
        # 涂鸦完成，显示结果
        if pixmap:
            self.image_label.setPixmap(pixmap.scaled(200, 200))
            
            # 保存涂鸦到临时文件
            import tempfile
            temp_path = os.path.join(tempfile.gettempdir(), "doodle.png")
            pixmap.save(temp_path)
            self.image_path = temp_path
            print(f"涂鸦保存路径：{self.image_path}")
        
        self.stop_doodle()

    def on_screenshot_taken(self, pixmap):
        # 显示截图到image_label
        self.image_label.setPixmap(pixmap.scaled(200, 200))
        
        # 保存截图到临时文件
        import tempfile
        temp_path = os.path.join(tempfile.gettempdir(), "screenshot.png")
        pixmap.save(temp_path)
        self.image_path = temp_path
        print(f"截图保存路径：{self.image_path}")
        
        # 显示主窗口
        self.show()

    def eventFilter(self, obj, event):
        from PyQt5.QtCore import Qt
        if obj == self.input_box and event.type() == event.KeyPress:
            if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                # 检查是否同时按下了Shift键，如果是则换行，否则发送消息
                if not (event.modifiers() & Qt.ShiftModifier):
                    self.send_message()
                    return True
        return super().eventFilter(obj, event)
    
    def closeEvent(self, event):
        for w in self.pinned_windows:
            if w is not None:
                w.close()
        event.accept()


class PinnedWindow(QWidget):
    def __init__(self, pixmap, pos=None):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        
        self.original_pixmap = pixmap
        self.pixmap = pixmap
        self.drag_offset = None
        self.scale_factor = 1.0
        
        # 使用 pixmap 原始尺寸，不做 DPI 缩放，避免跨屏 setGeometry 冲突
        self.resize(pixmap.width(), pixmap.height())
        
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        
        if pos is not None:
            self.move(pos)
        else:
            screen_geo = QApplication.primaryScreen().geometry()
            x = (screen_geo.width() - pixmap.width()) // 2
            y = (screen_geo.height() - pixmap.height()) // 2
            self.move(x, y)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        scaled = self.original_pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        painter.drawPixmap(self.rect(), scaled)
        
        red = QColor(255, 0, 0)
        for i in range(3):
            glow_color = QColor(255, 0, 0, 80 - i * 20)
            pen = QPen(glow_color, (3 - i) * 2 + 2)
            painter.setPen(pen)
            painter.drawRect(QRect(i, i, self.width() - i * 2 - 1, self.height() - i * 2 - 1))
        
        pen = QPen(red, 2)
        painter.setPen(pen)
        painter.drawRect(QRect(2, 2, self.width() - 5, self.height() - 5))
        
        painter.end()
    
    def show_context_menu(self, pos):
        menu = QMenu(self)
        close_action = menu.addAction('关闭')
        close_action.triggered.connect(self.close)
        menu.exec_(self.mapToGlobal(pos))
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_offset = event.pos()
    
    def mouseMoveEvent(self, event):
        if self.drag_offset is not None:
            global_pos = event.globalPos()
            new_x = global_pos.x() - self.drag_offset.x()
            new_y = global_pos.y() - self.drag_offset.y()
            hwnd = int(self.winId())
            SWP_NOZORDER = 0x0004
            SWP_NOSIZE = 0x0001
            SWP_NOACTIVATE = 0x0010
            ctypes.windll.user32.SetWindowPos(hwnd, 0, new_x, new_y, 0, 0,
                SWP_NOZORDER | SWP_NOSIZE | SWP_NOACTIVATE)
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_offset = None
    
    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta > 0:
            self.scale_factor = min(self.scale_factor + 0.1, 5.0)
        else:
            self.scale_factor = max(self.scale_factor - 0.1, 0.2)
        new_w = int(self.original_pixmap.width() * self.scale_factor)
        new_h = int(self.original_pixmap.height() * self.scale_factor)
        self.resize(new_w, new_h)


class ScreenshotWindow(QWidget):
    screenshot_taken = pyqtSignal(QPixmap)
    screenshot_canceled = pyqtSignal()
    screenshot_pinned = pyqtSignal(QPixmap, QPoint)
    
    def __init__(self, screenshot):
        super().__init__()
        self.screenshot = screenshot
        self.start_pos = None
        self.end_pos = None
        self.cropped_pixmap = None
        self.is_text_editing = False
        self.text_input = None
        self.text_input_pos = None
        self.cropped_pixmap_original = None
        self.is_screenshot_doodle = False
        self.doodle_last_pos = None
        self.is_dragging = False
        self.drag_offset = None
        self.history = []
        self.future = []
        self.max_history = 50
        self.edit_layer = None
        self.text_font = QFont('Microsoft YaHei', 20)
        self.text_font.setBold(True)
        self.text_color = QColor(Qt.red)
        self.text_size = 20
        self._style_btn_active = False
        self.is_resizing = False
        self.resize_corner = None
        self.resize_opposite = None
        self.setMouseTracking(True)
        self.initUI()
    
    def initUI(self):
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setStyleSheet("background-color: transparent;")
        #self.setStyleSheet("background-color: rgba(0, 0, 0, 0.3);")

        
        self.cancel_btn = QPushButton('取消', self)
        self.cancel_btn.setStyleSheet("background-color: gray; color: white; border: none; padding: 8px 16px; font-size: 14px;")
        self.cancel_btn.clicked.connect(self.on_cancel)
        self.cancel_btn.hide()
        
        self.copy_btn = QPushButton('复制', self)
        self.copy_btn.setStyleSheet("background-color: blue; color: white; border: none; padding: 8px 16px; font-size: 14px;")
        self.copy_btn.clicked.connect(self.on_copy)
        self.copy_btn.hide()
        
        self.add_btn = QPushButton('添加到Label', self)
        self.add_btn.setStyleSheet("background-color: green; color: white; border: none; padding: 8px 16px; font-size: 14px;")
        self.add_btn.clicked.connect(self.on_add)
        self.add_btn.hide()
        
        self.text_edit_btn = QPushButton('编辑文字', self)
        self.text_edit_btn.setStyleSheet("background-color: #4169E1; color: white; border: none; padding: 8px 16px; font-size: 14px;")
        self.text_edit_btn.clicked.connect(self.on_edit_text)
        self.text_edit_btn.hide()
        
        self.doodle_btn = QPushButton('涂鸦', self)
        self.doodle_btn.setStyleSheet("background-color: purple; color: white; border: none; padding: 8px 16px; font-size: 14px;")
        self.doodle_btn.clicked.connect(self.on_doodle)
        self.doodle_btn.hide()
        
        self.save_btn = QPushButton('保存', self)
        self.save_btn.setStyleSheet("background-color: orange; color: white; border: none; padding: 8px 16px; font-size: 14px;")
        self.save_btn.clicked.connect(self.on_save)
        self.save_btn.hide()
        
        self.undo_btn = QPushButton('后退', self)
        self.undo_btn.setStyleSheet("background-color: #555555; color: white; border: none; padding: 8px 16px; font-size: 14px;")
        self.undo_btn.clicked.connect(self.undo)
        self.undo_btn.hide()
        
        self.redo_btn = QPushButton('前进', self)
        self.redo_btn.setStyleSheet("background-color: #555555; color: white; border: none; padding: 8px 16px; font-size: 14px;")
        self.redo_btn.clicked.connect(self.redo)
        self.redo_btn.hide()
        
        self.pin_btn = QPushButton('钉图', self)
        self.pin_btn.setStyleSheet("background-color: #8B008B; color: white; border: none; padding: 8px 16px; font-size: 14px;")
        self.pin_btn.clicked.connect(self.on_pin)
        self.pin_btn.hide()
        
        self.font_btn = QPushButton('字体', self)
        self.font_btn.setStyleSheet("background-color: #2E8B57; color: white; border: none; padding: 4px 8px; font-size: 12px;")
        self.font_btn.pressed.connect(self._on_style_btn_pressed)
        self.font_btn.clicked.connect(self.on_select_font)
        self.font_btn.hide()
        
        self.color_btn = QPushButton('颜色', self)
        self.color_btn.setStyleSheet("background-color: #CD853F; color: white; border: none; padding: 4px 8px; font-size: 12px;")
        self.color_btn.pressed.connect(self._on_style_btn_pressed)
        self.color_btn.clicked.connect(self.on_select_color)
        self.color_btn.hide()
        
        self.size_btn = QPushButton('大小', self)
        self.size_btn.setStyleSheet("background-color: #8B4513; color: white; border: none; padding: 4px 8px; font-size: 12px;")
        self.size_btn.pressed.connect(self._on_style_btn_pressed)
        self.size_btn.clicked.connect(self.on_select_size)
        self.size_btn.hide()
        
        self.text_input = QLineEdit(self)
        self.text_input.setStyleSheet("background: transparent; border: 2px solid #4169E1; color: red; font-size: 20px; font-weight: bold; font-family: Microsoft YaHei;")
        self.text_input.setFixedSize(300, 40)
        self.text_input.hide()
        self.text_input.returnPressed.connect(self.on_text_input_finished)
        self.text_input.installEventFilter(self)
        self.text_input.textChanged.connect(self.on_text_input_changed)
        
        self.shortcut_paste = QShortcut(QKeySequence('Alt+2'), self)
        self.shortcut_paste.activated.connect(self.on_add)
    
    def show_preview(self, cropped_pixmap, reset_edit_layer=True):
        self.cropped_pixmap = cropped_pixmap
        if reset_edit_layer:
            self.edit_layer = QPixmap(cropped_pixmap.size())
            self.edit_layer.fill(Qt.transparent)
        
        select_rect = self.get_rect()
        btn_y = select_rect.bottom() + 10
        btn_width = 80
        btn_height = 36
        spacing = 5
        
        row1_count = 7
        total_width = btn_width * row1_count + spacing * (row1_count - 1)
        start_x = select_rect.center().x() - total_width // 2
        
        if btn_y + btn_height * 2 + spacing > self.height():
            btn_y = select_rect.top() - btn_height * 2 - spacing - 10
        
        self.cancel_btn.setGeometry(start_x, btn_y, btn_width, btn_height)
        self.copy_btn.setGeometry(start_x + (btn_width + spacing), btn_y, btn_width, btn_height)
        self.text_edit_btn.setGeometry(start_x + (btn_width + spacing) * 2, btn_y, btn_width, btn_height)
        self.doodle_btn.setGeometry(start_x + (btn_width + spacing) * 3, btn_y, btn_width, btn_height)
        self.save_btn.setGeometry(start_x + (btn_width + spacing) * 4, btn_y, btn_width, btn_height)
        self.add_btn.setGeometry(start_x + (btn_width + spacing) * 5, btn_y, btn_width, btn_height)
        self.undo_btn.setGeometry(start_x + (btn_width + spacing) * 6, btn_y, btn_width, btn_height)
        
        row2_y = btn_y + btn_height + spacing
        self.redo_btn.setGeometry(start_x, row2_y, btn_width * 2 + spacing, btn_height)
        redo_width = btn_width * 2 + spacing
        self.pin_btn.setGeometry(start_x + redo_width + spacing, row2_y, btn_width, btn_height)
        
        self.cancel_btn.show()
        self.copy_btn.show()
        self.text_edit_btn.show()
        self.doodle_btn.show()
        self.save_btn.show()
        self.add_btn.show()
        self.undo_btn.show()
        self.redo_btn.show()
        self.pin_btn.show()
        
        self.update()
    
    def hide_buttons(self):
        self.cancel_btn.hide()
        self.copy_btn.hide()
        self.text_edit_btn.hide()
        self.doodle_btn.hide()
        self.save_btn.hide()
        self.add_btn.hide()
        self.undo_btn.hide()
        self.redo_btn.hide()
        self.pin_btn.hide()
    
    def show_buttons(self):
        self.cancel_btn.show()
        self.copy_btn.show()
        self.text_edit_btn.show()
        self.doodle_btn.show()
        self.doodle_btn.setText('涂鸦')
        self.save_btn.show()
        self.add_btn.show()
        self.undo_btn.show()
        self.redo_btn.show()
        self.pin_btn.show()
    
    def on_cancel(self):
        self.screenshot_canceled.emit()
        self.close()
    
    def on_copy(self):
        clipboard = QApplication.clipboard()
        clipboard.setPixmap(self.cropped_pixmap)
    
    def on_add(self):
        self.screenshot_taken.emit(self.cropped_pixmap)
        self.close()
    
    def on_save(self):
        file_path, _ = QFileDialog.getSaveFileName(self, '保存图片', '', 'PNG (*.png);;JPEG (*.jpg);;BMP (*.bmp)')
        if file_path:
            self.cropped_pixmap.save(file_path)
    
    def on_pin(self):
        if self.cropped_pixmap:
            select_rect = self.get_rect()
            pos = self.mapToGlobal(QPoint(select_rect.x(), select_rect.y()))
            self.screenshot_pinned.emit(self.cropped_pixmap.copy(), pos)
            self.close()
            
    
    def on_edit_text(self):
        if self.is_text_editing:
            if self.text_input.isVisible():
                self.finalize_text()
            self.is_text_editing = False
            self.setCursor(Qt.ArrowCursor)
            #self._hide_text_style_buttons()
            self.show_buttons()
            return
        if self.is_screenshot_doodle:
            self.is_screenshot_doodle = False
            self.doodle_last_pos = None
            self.doodle_btn.setText('涂鸦')
            self.setCursor(Qt.ArrowCursor)
        self.is_text_editing = True
        self.hide_buttons()
        self.setCursor(Qt.IBeamCursor)
    
    def finalize_text(self):
        text = self.text_input.text()
        if text and self.text_input_pos:
            painter = QPainter(self.cropped_pixmap)
            painter.setFont(self.text_font)
            painter.setPen(QPen(self.text_color))
            painter.drawText(self.text_input_pos.x(), self.text_input_pos.y(), text)
            painter.end()
            if self.edit_layer:
                painter = QPainter(self.edit_layer)
                painter.setFont(self.text_font)
                painter.setPen(QPen(self.text_color))
                painter.drawText(self.text_input_pos.x(), self.text_input_pos.y(), text)
                painter.end()
        self.cropped_pixmap_original = None
        self.text_input.hide()
        #self._hide_text_style_buttons()
        self.update()
    
    def on_text_input_finished(self):
        self.finalize_text()
    
    def on_text_input_changed(self, text):
        if self.cropped_pixmap_original and self.text_input_pos:
            self.cropped_pixmap = self.cropped_pixmap_original.copy()
            if text:
                painter = QPainter(self.cropped_pixmap)
                painter.setFont(self.text_font)
                painter.setPen(QPen(self.text_color))
                painter.drawText(self.text_input_pos.x(), self.text_input_pos.y(), text)
                painter.end()
            self.update()
    
    def on_select_font(self):
        font, ok = QFontDialog.getFont(self.text_font, self, '选择字体')
        if ok:
            self.text_font = font
            self._apply_text_style()
    
    def on_select_color(self):
        color = QColorDialog.getColor(self.text_color, self, '选择颜色')
        if color.isValid():
            self.text_color = color
            self._apply_text_style()
    
    def on_select_size(self):
        size, ok = QInputDialog.getInt(self, '选择大小', '字体大小:', self.text_size, 8, 200, 1)
        if ok:
            self.text_size = size
            self.text_font.setPixelSize(size)
            self._apply_text_style()
    
    def _apply_text_style(self):
        color_name = self.text_color.name()
        self.text_input.setStyleSheet(
            f"background: transparent; border: 2px solid #4169E1;"
            f"color: {color_name}; font-size: {self.text_size}px;"
            f"font-weight: {'bold' if self.text_font.bold() else 'normal'};"
            f"font-family: {self.text_font.family()};"
        )
    
    def _show_text_style_buttons(self):
        select_rect = self.get_rect()
        btn_y = select_rect.bottom() + 10
        btn_width = 80
        btn_height = 36
        spacing = 5
        
        if btn_y + btn_height * 2 + spacing > self.height():
            btn_y = select_rect.top() - btn_height * 2 - spacing - 10
        
        row1_count = 7
        total_width = btn_width * row1_count + spacing * (row1_count - 1)
        start_x = select_rect.center().x() - total_width // 2
        
        row2_y = btn_y + btn_height + spacing
        redo_width = btn_width * 2 + spacing
        
        style_x = start_x + redo_width + spacing + (btn_width + spacing)
        self.font_btn.setGeometry(style_x, row2_y, btn_width, btn_height)
        self.color_btn.setGeometry(style_x + (btn_width + spacing), row2_y, btn_width, btn_height)
        self.size_btn.setGeometry(style_x + (btn_width + spacing) * 2, row2_y, btn_width, btn_height)
        self.font_btn.show()
        self.color_btn.show()
        self.size_btn.show()
    
    def _hide_text_style_buttons(self):
        self.font_btn.hide()
        self.color_btn.hide()
        self.size_btn.hide()
    
    def save_undo_state(self):
        if self.cropped_pixmap:
            edit_copy = self.edit_layer.copy() if self.edit_layer else None
            self.history.append((self.cropped_pixmap.copy(), edit_copy))
            if len(self.history) > self.max_history:
                self.history.pop(0)
            self.future.clear()
    
    def undo(self):
        if not self.history:
            return
        edit_copy = self.edit_layer.copy() if self.edit_layer else None
        self.future.append((self.cropped_pixmap.copy(), edit_copy))
        self.cropped_pixmap, self.edit_layer = self.history.pop()
        self.is_text_editing = False
        if self.text_input and self.text_input.isVisible():
            self.text_input.hide()
        self.update()
    
    def redo(self):
        if not self.future:
            return
        edit_copy = self.edit_layer.copy() if self.edit_layer else None
        self.history.append((self.cropped_pixmap.copy(), edit_copy))
        self.cropped_pixmap, self.edit_layer = self.future.pop()
        self.is_text_editing = False
        if self.text_input and self.text_input.isVisible():
            self.text_input.hide()
        self.update()
    
    def eventFilter(self, obj, event):
        if obj == self.text_input:
            from PyQt5.QtCore import QEvent
            if event.type() == QEvent.FocusOut:
                if not self._style_btn_active:
                    self.finalize_text()
                self._style_btn_active = False
                return True
        return super().eventFilter(obj, event)
    
    def _on_style_btn_pressed(self):
        self._style_btn_active = True
    
    def on_doodle(self):
        if not self.is_screenshot_doodle:
            self.is_screenshot_doodle = True
            self.doodle_btn.setText('结束涂鸦')
            self.hide_buttons()
            self.doodle_btn.show()
            self.doodle_last_pos = None
            self.setCursor(self.create_pen_cursor())
        else:
            self.is_screenshot_doodle = False
            self.doodle_last_pos = None
            self.doodle_btn.setText('涂鸦')
            self.setCursor(Qt.ArrowCursor)
            self.show_buttons()
    
    def create_pen_cursor(self):
        cursor_size = 40
        cursor_pixmap = QPixmap(cursor_size, cursor_size)
        cursor_pixmap.fill(Qt.transparent)
        
        painter = QPainter(cursor_pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        pen_color = QColor(255, 0, 0)
        body_color = QColor(200, 200, 200)
        
        painter.setBrush(QBrush(body_color))
        painter.setPen(QPen(Qt.black, 1))
        painter.drawRect(5, 5, 10, 25)
        
        painter.setPen(QPen(Qt.gray, 1))
        painter.drawLine(5, 12, 15, 12)
        painter.drawLine(5, 18, 15, 18)
        
        painter.setBrush(QBrush(pen_color))
        painter.setPen(QPen(Qt.black, 1))
        tip_points = QPolygon([
            QPoint(5, 32),
            QPoint(15, 32),
            QPoint(10, cursor_size - 2)
        ])
        painter.drawPolygon(tip_points)
        
        painter.setBrush(QBrush(QColor(255, 100, 100)))
        tip_inner = QPolygon([
            QPoint(7, 32),
            QPoint(13, 32),
            QPoint(10, cursor_size - 4)
        ])
        painter.drawPolygon(tip_inner)
        
        painter.end()
        
        from PyQt5.QtGui import QCursor
        return QCursor(cursor_pixmap, 5, cursor_size - 2)
    
    def on_doodle_finished(self, doodle_pixmap):
        select_rect = self.get_rect()
        doodle_crop = doodle_pixmap.copy(select_rect)
        self.cropped_pixmap = doodle_crop
        
        self.show()
        self.show_buttons()
        self.is_text_editing = False
        self.update()
    
    def paintEvent(self, event):
        from PyQt5.QtGui import QPainter, QPen, QBrush, QPainterPath, QColor
        painter = QPainter(self)
        
        painter.drawPixmap(self.rect(), self.screenshot)
        
        if self.cropped_pixmap and self.start_pos and self.end_pos:
            select_rect = self.get_rect()
            painter.drawPixmap(select_rect.x(), select_rect.y(), self.cropped_pixmap)
        
        path = QPainterPath()
        rect = self.rect()
        path.addRect(rect.x(), rect.y(), rect.width(), rect.height())
        
        if self.start_pos and self.end_pos:
            select_rect = self.get_rect()
            path.addRect(select_rect.x(), select_rect.y(), select_rect.width(), select_rect.height())
            path.setFillRule(Qt.OddEvenFill)
        
        painter.fillPath(path, QBrush(QColor(0, 0, 0, 150)))
        
        if self.start_pos and self.end_pos:
            select_rect = self.get_rect()
            pen = QPen(Qt.red, 2)
            painter.setPen(pen)
            painter.drawRect(select_rect)
            
            if self.cropped_pixmap:
                handle_r = 8
                painter.setBrush(QBrush(Qt.red))
                painter.setPen(QPen(Qt.green, 2))
                painter.drawEllipse(QPoint(select_rect.x(), select_rect.y()), handle_r, handle_r)
                painter.drawEllipse(QPoint(select_rect.x() + select_rect.width(), select_rect.y()), handle_r, handle_r)
                painter.drawEllipse(QPoint(select_rect.x(), select_rect.y() + select_rect.height()), handle_r, handle_r)
                painter.drawEllipse(QPoint(select_rect.x() + select_rect.width(), select_rect.y() + select_rect.height()), handle_r, handle_r)
                painter.drawEllipse(QPoint(select_rect.x() + select_rect.width() // 2, select_rect.y()), handle_r, handle_r)
                painter.drawEllipse(QPoint(select_rect.x() + select_rect.width() // 2, select_rect.y() + select_rect.height()), handle_r, handle_r)
                painter.drawEllipse(QPoint(select_rect.x(), select_rect.y() + select_rect.height() // 2), handle_r, handle_r)
                painter.drawEllipse(QPoint(select_rect.x() + select_rect.width(), select_rect.y() + select_rect.height() // 2), handle_r, handle_r)
    
    def get_rect(self):
        x = min(self.start_pos.x(), self.end_pos.x())
        y = min(self.start_pos.y(), self.end_pos.y())
        width = abs(self.start_pos.x() - self.end_pos.x())
        height = abs(self.start_pos.y() - self.end_pos.y())
        return QRect(x, y, width, height)
    
    def _get_corner_at(self, pos):
        if not self.cropped_pixmap:
            return None
        select_rect = self.get_rect()
        handle_r = 6
        handles = {
            'tl': QPoint(select_rect.x(), select_rect.y()),
            'tr': QPoint(select_rect.x() + select_rect.width(), select_rect.y()),
            'bl': QPoint(select_rect.x(), select_rect.y() + select_rect.height()),
            'br': QPoint(select_rect.x() + select_rect.width(), select_rect.y() + select_rect.height()),
            'top': QPoint(select_rect.x() + select_rect.width() // 2, select_rect.y()),
            'bottom': QPoint(select_rect.x() + select_rect.width() // 2, select_rect.y() + select_rect.height()),
            'left': QPoint(select_rect.x(), select_rect.y() + select_rect.height() // 2),
            'right': QPoint(select_rect.x() + select_rect.width(), select_rect.y() + select_rect.height() // 2),
        }
        for name, pt in handles.items():
            if (pos - pt).manhattanLength() <= handle_r * 2:
                return name
        return None
    
    def mousePressEvent(self, event):
        if self.is_screenshot_doodle and self.cropped_pixmap:
            select_rect = self.get_rect()
            if select_rect.contains(event.pos()):
                self.save_undo_state()
                self.doodle_last_pos = QPoint(event.pos().x() - select_rect.x(), event.pos().y() - select_rect.y())
            return
        
        if self.is_text_editing and self.cropped_pixmap:
            select_rect = self.get_rect()
            if select_rect.contains(event.pos()):
                if self.text_input.isVisible():
                    self.on_text_input_finished()
                self.cropped_pixmap_original = self.cropped_pixmap.copy()
                self.save_undo_state()
                self.text_input_pos = QPoint(event.pos().x() - select_rect.x(), event.pos().y() - select_rect.y())
                self.text_input.move(event.pos())
                self.text_input.clear()
                self.text_input.show()
                self.text_input.setFocus()
                self._apply_text_style()
                self._show_text_style_buttons()
            return
        
        if self.cropped_pixmap:
            corner = self._get_corner_at(event.pos())
            if corner and event.button() == Qt.LeftButton:
                self.is_resizing = True
                self.resize_corner = corner
                select_rect = self.get_rect()
                if corner in ('tl', 'tr', 'bl', 'br'):
                    opposites = {
                        'tl': QPoint(select_rect.x() + select_rect.width(), select_rect.y() + select_rect.height()),
                        'tr': QPoint(select_rect.x(), select_rect.y() + select_rect.height()),
                        'bl': QPoint(select_rect.x() + select_rect.width(), select_rect.y()),
                        'br': QPoint(select_rect.x(), select_rect.y()),
                    }
                    self.resize_opposite = opposites[corner]
                else:
                    self.resize_opposite = None
                self.save_undo_state()
                return
            select_rect = self.get_rect()
            if select_rect.contains(event.pos()):
                self.is_dragging = True
                self.drag_offset = QPoint(event.pos().x() - select_rect.x(), event.pos().y() - select_rect.y())
                return
            if self.text_input.isVisible():
                self.on_text_input_finished()
            return
        if event.button() == Qt.LeftButton:
            self.start_pos = event.pos()
            self.end_pos = event.pos()
    
    def mouseMoveEvent(self, event):
        if self.is_resizing and self.cropped_pixmap:
            select_rect = self.get_rect()
            if self.resize_corner in ('tl', 'tr', 'bl', 'br'):
                new_x = event.pos().x()
                new_y = event.pos().y()
                new_x = max(0, min(new_x, self.screenshot.width() - 10))
                new_y = max(0, min(new_y, self.screenshot.height() - 10))
                self.start_pos = QPoint(new_x, new_y)
                self.end_pos = self.resize_opposite
            elif self.resize_corner == 'top':
                new_y = max(0, min(event.pos().y(), select_rect.y() + select_rect.height() - 10))
                self.start_pos = QPoint(select_rect.x(), new_y)
                self.end_pos = QPoint(select_rect.x() + select_rect.width(), select_rect.y() + select_rect.height())
            elif self.resize_corner == 'bottom':
                new_y = max(select_rect.y() + 10, min(event.pos().y(), self.screenshot.height()))
                self.start_pos = QPoint(select_rect.x(), select_rect.y())
                self.end_pos = QPoint(select_rect.x() + select_rect.width(), new_y)
            elif self.resize_corner == 'left':
                new_x = max(0, min(event.pos().x(), select_rect.x() + select_rect.width() - 10))
                self.start_pos = QPoint(new_x, select_rect.y())
                self.end_pos = QPoint(select_rect.x() + select_rect.width(), select_rect.y() + select_rect.height())
            elif self.resize_corner == 'right':
                new_x = max(select_rect.x() + 10, min(event.pos().x(), self.screenshot.width()))
                self.start_pos = QPoint(select_rect.x(), select_rect.y())
                self.end_pos = QPoint(new_x, select_rect.y() + select_rect.height())
            new_rect = self.get_rect()
            if new_rect.width() > 10 and new_rect.height() > 10:
                new_screen = self.screenshot.copy(new_rect)
                self.edit_layer = QPixmap(new_screen.size())
                self.edit_layer.fill(Qt.transparent)
                self.show_preview(new_screen, reset_edit_layer=False)
            return
        if self.is_screenshot_doodle and self.cropped_pixmap and self.doodle_last_pos:
            select_rect = self.get_rect()
            if select_rect.contains(event.pos()):
                current_pos = QPoint(event.pos().x() - select_rect.x(), event.pos().y() - select_rect.y())
                pen = QPen(Qt.red, 5, Qt.SolidLine, Qt.RoundCap)
                painter = QPainter(self.cropped_pixmap)
                painter.setPen(pen)
                painter.drawLine(self.doodle_last_pos, current_pos)
                painter.end()
                if self.edit_layer:
                    painter = QPainter(self.edit_layer)
                    painter.setPen(pen)
                    painter.drawLine(self.doodle_last_pos, current_pos)
                    painter.end()
                self.doodle_last_pos = current_pos
                self.update()
            else:
                self.doodle_last_pos = None
            return
        if self.is_dragging and self.cropped_pixmap:
            select_rect = self.get_rect()
            width = select_rect.width()
            height = select_rect.height()
            new_x = event.pos().x() - self.drag_offset.x()
            new_y = event.pos().y() - self.drag_offset.y()
            new_x = max(0, min(new_x, self.screenshot.width() - width))
            new_y = max(0, min(new_y, self.screenshot.height() - height))
            self.start_pos = QPoint(new_x, new_y)
            self.end_pos = QPoint(new_x + width, new_y + height)
            new_rect = self.get_rect()
            new_screen = self.screenshot.copy(new_rect)
            if self.edit_layer:
                painter = QPainter(new_screen)
                painter.drawPixmap(0, 0, self.edit_layer)
                painter.end()
            self.show_preview(new_screen, reset_edit_layer=False)
            return
        if self.cropped_pixmap:
            if self.is_text_editing:
                select_rect = self.get_rect()
                if select_rect.contains(event.pos()):
                    self.setCursor(Qt.IBeamCursor)
                else:
                    self.setCursor(Qt.ArrowCursor)
            elif self.is_screenshot_doodle:
                select_rect = self.get_rect()
                if select_rect.contains(event.pos()):
                    self.setCursor(self.create_pen_cursor())
                else:
                    self.setCursor(Qt.ArrowCursor)
            else:
                corner = self._get_corner_at(event.pos())
                if corner in ('top', 'bottom'):
                    self.setCursor(Qt.SizeVerCursor)
                elif corner in ('left', 'right'):
                    self.setCursor(Qt.SizeHorCursor)
                elif corner in ('tl', 'br'):
                    self.setCursor(Qt.SizeFDiagCursor)
                elif corner in ('tr', 'bl'):
                    self.setCursor(Qt.SizeBDiagCursor)
                else:
                    select_rect = self.get_rect()
                    if select_rect.contains(event.pos()):
                        self.setCursor(Qt.SizeAllCursor)
                    else:
                        self.setCursor(Qt.ArrowCursor)
            return
        if self.start_pos:
            self.end_pos = event.pos()
            self.update()
    
    def mouseReleaseEvent(self, event):
        if self.is_resizing:
            self.is_resizing = False
            self.resize_corner = None
            self.resize_opposite = None
            return
        if self.is_dragging:
            self.is_dragging = False
            return
        if self.is_screenshot_doodle:
            self.doodle_last_pos = None
            return
        if event.button() == Qt.LeftButton and self.start_pos and not self.cropped_pixmap:
            rect = self.get_rect()
            if rect.width() > 10 and rect.height() > 10:
                cropped_pixmap = self.screenshot.copy(rect)
                self.show_preview(cropped_pixmap)
            else:
                self.screenshot_canceled.emit()
                self.close()
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            if self.is_screenshot_doodle:
                self.is_screenshot_doodle = False
                self.doodle_last_pos = None
                self.doodle_btn.setText('涂鸦')
                self.setCursor(Qt.ArrowCursor)
                self.show_buttons()
                return
            if self.is_text_editing:
                if self.text_input.isVisible():
                    self.text_input.hide()
                self.is_text_editing = False
                self.setCursor(Qt.ArrowCursor)
                self._hide_text_style_buttons()
                self.show_buttons()
                return
            self.screenshot_canceled.emit()
            self.close()
    
    def closeEvent(self, event):
        event.accept()


class DoodleWindow(QWidget):
    doodle_finished = pyqtSignal(QPixmap)
    
    def __init__(self, screen_shot=None):
        super().__init__()
        self.screen_shot = screen_shot
        self.initUI()
        self.last_pos = None
        self.drawing = False
    
    def initUI(self):
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setStyleSheet("background-color: transparent;")
        
        # 获取屏幕尺寸
        screen_geometry = QApplication.primaryScreen().geometry()
        
        # 如果提供了屏幕截图，则使用截图作为画布背景
        if self.screen_shot:
            self.canvas = self.screen_shot.copy()
        else:
            # 否则截取当前屏幕内容作为画布背景
            screen = QApplication.primaryScreen()
            self.canvas = screen.grabWindow(0)
        
        # 设置画笔样式
        self.pen_color = Qt.red
        self.pen_width = 5
        
        # 设置画笔形状的光标
        self.setCursor(self.create_pen_cursor())
    
    def create_pen_cursor(self):
        # 创建一个更大更形象的画笔形状自定义光标
        cursor_size = 40
        cursor_pixmap = QPixmap(cursor_size, cursor_size)
        cursor_pixmap.fill(Qt.transparent)
        
        painter = QPainter(cursor_pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 画笔主体颜色
        pen_color = QColor(255, 0, 0)  # 红色
        body_color = QColor(200, 200, 200)  # 灰色笔杆
        
        # 绘制笔杆（矩形）
        painter.setBrush(QBrush(body_color))
        painter.setPen(QPen(Qt.black, 1))
        painter.drawRect(5, 5, 10, 25)
        
        # 绘制笔杆上的装饰线
        painter.setPen(QPen(Qt.gray, 1))
        painter.drawLine(5, 12, 15, 12)
        painter.drawLine(5, 18, 15, 18)
        
        # 绘制笔尖（三角形）
        painter.setBrush(QBrush(pen_color))
        painter.setPen(QPen(Qt.black, 1))
        # 笔尖三角形
        tip_points = QPolygon([
            QPoint(5, 32),
            QPoint(15, 32),
            QPoint(10, cursor_size - 2)
        ])
        painter.drawPolygon(tip_points)
        
        # 绘制笔尖内部高光
        painter.setBrush(QBrush(QColor(255, 100, 100)))
        tip_inner = QPolygon([
            QPoint(7, 32),
            QPoint(13, 32),
            QPoint(10, cursor_size - 4)
        ])
        painter.drawPolygon(tip_inner)
        
        # 绘制一些墨迹效果
        painter.setPen(QPen(pen_color, 3))
        painter.setBrush(QBrush(pen_color))
        painter.drawEllipse(22, 20, 5, 5)
        painter.drawEllipse(28, 25, 4, 4)
        painter.drawEllipse(25, 32, 6, 6)
        painter.drawEllipse(32, 28, 3, 3)
        
        painter.end()
        
        # 热点设置在笔尖位置
        return QCursor(cursor_pixmap, 10, cursor_size - 2)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(self.rect(), self.canvas)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drawing = True
            self.last_pos = event.pos()
    
    def mouseMoveEvent(self, event):
        if self.drawing and self.last_pos:
            painter = QPainter(self.canvas)
            painter.setPen(QPen(self.pen_color, self.pen_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            painter.drawLine(self.last_pos, event.pos())
            self.last_pos = event.pos()
            self.update()
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drawing = False
            self.last_pos = None
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
    
    def closeEvent(self, event):
        # 发出涂鸦完成信号，传递涂鸦内容
        self.doodle_finished.emit(self.canvas)
        event.accept()


if __name__ == '__main__':
    print("Starting picbot应用...")
    try:
        app = QApplication(sys.argv)
        print("picbot应用创建完成")
        chat_app = PicBot()
        print("picbot实例创建完成")
        chat_app.show()
        print("picbot应用显示完成")
        print("进入事件循环...")
        sys.exit(app.exec_())
    except Exception as e:
        print(f"错误：{str(e)}")
        import traceback
        traceback.print_exc()

