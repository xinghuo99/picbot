import sys
import requests
import json
import logging
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QTextEdit, QLineEdit, QPushButton, QLabel, QFileDialog
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QMetaObject, Q_ARG, QRect, QPoint
from PyQt5.QtGui import QPixmap, QScreen, QPainter, QPen, QCursor, QColor, QPolygon, QBrush

import os
import base64
from openai import OpenAI

# 配置日志
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# API 配置
API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
API_KEY = "sk-aaaaaaaaa"  # 替换为自己的 API Key，去模型平台注册账号，并申请API Key.


class PicBot(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
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

        self.doodle_button = QPushButton('涂鸦')
        self.doodle_button.clicked.connect(self.toggle_doodle)
        layout.addWidget(self.doodle_button)

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
        
        # 创建全屏截图窗口
        screen = QApplication.primaryScreen()
        screenshot = screen.grabWindow(0)
        
        # 创建截图选择窗口
        self.screenshot_window = ScreenshotWindow(screenshot)
        self.screenshot_window.screenshot_taken.connect(self.on_screenshot_taken)
        self.screenshot_window.screenshot_canceled.connect(self.on_screenshot_canceled)
        self.screenshot_window.showFullScreen()
    
    def on_screenshot_canceled(self):
        # 取消截图，重新显示主窗口
        self.show()

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


class ScreenshotWindow(QWidget):
    screenshot_taken = pyqtSignal(QPixmap)
    screenshot_canceled = pyqtSignal()
    
    def __init__(self, screenshot):
        super().__init__()
        self.screenshot = screenshot
        self.start_pos = None
        self.end_pos = None
        self.initUI()
    
    def initUI(self):
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setStyleSheet("background-color: rgba(0, 0, 0, 0.3);")
    
    def paintEvent(self, event):
        from PyQt5.QtGui import QPainter, QPen, QBrush, QPainterPath, QColor
        painter = QPainter(self)
        
        # 绘制全屏截图（保留原始内容）
        painter.drawPixmap(self.rect(), self.screenshot)
        
        # 创建一个包含整个窗口的路径
        path = QPainterPath()
        rect = self.rect()
        path.addRect(rect.x(), rect.y(), rect.width(), rect.height())
        
        # 如果正在选择区域，从路径中减去选中区域
        if self.start_pos and self.end_pos:
            select_rect = self.get_rect()
            path.addRect(select_rect.x(), select_rect.y(), select_rect.width(), select_rect.height())
            # 使用奇偶填充规则，这样选中区域会被排除
            path.setFillRule(Qt.OddEvenFill)
        
        # 绘制半透明黑色遮罩（只覆盖选中区域之外的部分）
        painter.fillPath(path, QBrush(QColor(0, 0, 0, 150)))
        
        # 如果正在选择区域，绘制红框
        if self.start_pos and self.end_pos:
            select_rect = self.get_rect()
            pen = QPen(Qt.red, 2)
            painter.setPen(pen)
            painter.drawRect(select_rect)
    
    def get_rect(self):
        x = min(self.start_pos.x(), self.end_pos.x())
        y = min(self.start_pos.y(), self.end_pos.y())
        width = abs(self.start_pos.x() - self.end_pos.x())
        height = abs(self.start_pos.y() - self.end_pos.y())
        return QRect(x, y, width, height)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.start_pos = event.pos()
            self.end_pos = event.pos()
    
    def mouseMoveEvent(self, event):
        if self.start_pos:
            self.end_pos = event.pos()
            self.update()
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.start_pos:
            rect = self.get_rect()
            if rect.width() > 10 and rect.height() > 10:
                cropped_pixmap = self.screenshot.copy(rect)
                self.screenshot_taken.emit(cropped_pixmap)
            else:
                # 区域太小，取消截图
                self.screenshot_canceled.emit()
            self.close()
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.screenshot_canceled.emit()
            self.close()
    
    def closeEvent(self, event):
        # 确保窗口关闭时总是通知主窗口
        # 只有在没有发出过截图完成信号的情况下才发出取消信号
        # 这是一个安全保障
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

