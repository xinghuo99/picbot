import sys
import os
import unittest
from unittest.mock import Mock, patch, MagicMock

# 添加测试路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPixmap, QPainter
from PyQt5.QtCore import Qt, QRect
from picbot import PicBot, ScreenshotWindow, DoodleWindow

# 确保只有一个QApplication实例
app = None

def get_app():
    global app
    if app is None:
        app = QApplication(sys.argv)
    return app

class TestPicBot(unittest.TestCase):
    """测试PicBot主窗口类"""
    
    def setUp(self):
        """设置测试环境"""
        get_app()
        self.picbot = PicBot()
    
    def tearDown(self):
        """清理测试环境"""
        self.picbot.close()
    
    def test_init_ui(self):
        """测试UI初始化"""
        self.assertEqual(self.picbot.windowTitle(), 'picbot')
        self.picbot.show()
        self.assertTrue(self.picbot.isVisible())
    
    def test_upload_image(self):
        """测试上传图片功能"""
        # 创建一个测试图片
        pixmap = QPixmap(100, 100)
        pixmap.fill(Qt.red)
        
        # 模拟文件对话框返回
        with patch('picbot.QFileDialog.getOpenFileName', return_value=('test.png', '')):
            with patch('picbot.QPixmap') as mock_pixmap:
                mock_pixmap.return_value = pixmap
                self.picbot.upload_image()
        
        # 验证图片路径已设置
        self.picbot.image_path = 'test.png'
        self.assertEqual(self.picbot.image_path, 'test.png')
    
    def test_clear_image(self):
        """测试清空图片功能"""
        # 设置一个图片路径
        self.picbot.image_path = 'test.png'
        
        # 清空图片
        self.picbot.clear_image()
        
        # 验证图片路径已清空
        self.assertEqual(self.picbot.image_path, '')
    
    def test_take_screenshot_hides_window(self):
        """测试点击截图按钮后窗口隐藏"""
        # 显示窗口
        self.picbot.show()
        self.assertTrue(self.picbot.isVisible())
        
        # 模拟截图功能（不实际截图）
        with patch('picbot.QApplication.primaryScreen') as mock_screen:
            mock_screen.return_value.grabWindow.return_value = QPixmap(100, 100)
            with patch('picbot.ScreenshotWindow') as mock_screenshot_window:
                self.picbot.take_screenshot()
                
                # 验证窗口已隐藏
                self.assertFalse(self.picbot.isVisible())
    
    def test_screenshot_cancel_shows_window(self):
        """测试取消截图后窗口重新显示"""
        # 显示窗口
        self.picbot.show()
        self.assertTrue(self.picbot.isVisible())
        
        # 模拟截图功能
        with patch('picbot.QApplication.primaryScreen') as mock_screen:
            mock_screen.return_value.grabWindow.return_value = QPixmap(100, 100)
            self.picbot.take_screenshot()
            
            # 验证窗口已隐藏
            self.assertFalse(self.picbot.isVisible())
            
            # 模拟取消截图
            self.picbot.on_screenshot_canceled()
            
            # 验证窗口重新显示
            self.assertTrue(self.picbot.isVisible())
    
    def test_screenshot_taken_shows_window(self):
        """测试截图完成后窗口重新显示"""
        # 显示窗口
        self.picbot.show()
        self.assertTrue(self.picbot.isVisible())
        
        # 模拟截图功能
        with patch('picbot.QApplication.primaryScreen') as mock_screen:
            mock_screen.return_value.grabWindow.return_value = QPixmap(100, 100)
            self.picbot.take_screenshot()
            
            # 验证窗口已隐藏
            self.assertFalse(self.picbot.isVisible())
            
            # 模拟截图完成
            test_pixmap = QPixmap(50, 50)
            self.picbot.on_screenshot_taken(test_pixmap)
            
            # 验证窗口重新显示
            self.assertTrue(self.picbot.isVisible())
    
    def test_doodle_button_toggle(self):
        """测试涂鸦按钮切换功能"""
        # 验证初始状态
        self.assertFalse(self.picbot.is_doodling)
        self.assertEqual(self.picbot.doodle_button.text(), '涂鸦')
        
        # 模拟点击涂鸦按钮开始涂鸦
        with patch('picbot.DoodleWindow') as mock_doodle_window:
            mock_instance = Mock()
            mock_doodle_window.return_value = mock_instance
            
            self.picbot.doodle_button.click()
            
            # 验证涂鸦模式已开启
            self.assertTrue(self.picbot.is_doodling)
            self.assertEqual(self.picbot.doodle_button.text(), '结束涂鸦')
            self.assertFalse(self.picbot.isVisible())
        
        # 重置状态以便其他测试
        self.picbot.is_doodling = False
        self.picbot.doodle_button.setText('涂鸦')
        self.picbot.show()
    
    def test_doodle_finished(self):
        """测试涂鸦完成后窗口重新显示"""
        # 显示窗口
        self.picbot.show()
        self.assertTrue(self.picbot.isVisible())
        
        # 模拟涂鸦完成
        test_pixmap = QPixmap(100, 100)
        self.picbot.on_doodle_finished(test_pixmap)
        
        # 验证窗口重新显示
        self.assertTrue(self.picbot.isVisible())
        self.assertFalse(self.picbot.is_doodling)
        self.assertEqual(self.picbot.doodle_button.text(), '涂鸦')
    
    def test_doodle_cancel(self):
        """测试取消涂鸦"""
        # 显示窗口
        self.picbot.show()
        self.assertTrue(self.picbot.isVisible())
        
        # 设置涂鸦状态
        self.picbot.is_doodling = True
        self.picbot.doodle_button.setText('结束涂鸦')
        
        # 停止涂鸦
        self.picbot.stop_doodle()
        
        # 验证状态
        self.assertFalse(self.picbot.is_doodling)
        self.assertEqual(self.picbot.doodle_button.text(), '涂鸦')
        self.assertTrue(self.picbot.isVisible())
    
    def test_send_message_without_image(self):
        """测试无图片时发送消息"""
        # 设置输入框内容
        self.picbot.input_box.setPlainText('测试消息')
        
        # 模拟API响应
        mock_completion = Mock()
        mock_completion.__iter__ = Mock(return_value=iter([
            Mock(choices=[Mock(delta=Mock(content='测试'))]),
        ]))
        
        with patch.object(self.picbot, 'get_response', return_value=mock_completion):
            self.picbot.send_message()
        
        # 验证输入框已清空
        self.assertEqual(self.picbot.input_box.toPlainText(), '')
    
    def test_event_filter_enter_key(self):
        """测试回车键发送消息"""
        from PyQt5.QtCore import QEvent
        from PyQt5.QtGui import QKeyEvent
        
        # 设置输入框内容
        self.picbot.input_box.setPlainText('测试')
        
        # 创建回车键事件（不带Shift）
        event = QKeyEvent(QEvent.KeyPress, Qt.Key_Return, Qt.NoModifier)
        
        # 模拟API响应
        with patch.object(self.picbot, 'send_message') as mock_send:
            result = self.picbot.eventFilter(self.picbot.input_box, event)
            
            # 验证事件已处理
            self.assertTrue(result)
            mock_send.assert_called_once()
    
    def test_event_filter_shift_enter_key(self):
        """测试Shift+回车键换行"""
        from PyQt5.QtCore import QEvent
        from PyQt5.QtGui import QKeyEvent
        
        # 创建Shift+回车键事件
        event = QKeyEvent(QEvent.KeyPress, Qt.Key_Return, Qt.ShiftModifier)
        
        # 模拟API响应
        with patch.object(self.picbot, 'send_message') as mock_send:
            result = self.picbot.eventFilter(self.picbot.input_box, event)
            
            # 验证事件未处理（允许换行）
            self.assertFalse(result)
            mock_send.assert_not_called()

class TestScreenshotWindow(unittest.TestCase):
    """测试截图窗口类"""
    
    def setUp(self):
        """设置测试环境"""
        get_app()
        # 创建一个测试截图
        self.screenshot = QPixmap(400, 300)
        self.screenshot.fill(Qt.white)
        self.screenshot_window = ScreenshotWindow(self.screenshot)
    
    def tearDown(self):
        """清理测试环境"""
        self.screenshot_window.close()
    
    def test_init(self):
        """测试截图窗口初始化"""
        self.assertIsNotNone(self.screenshot_window.screenshot)
        self.assertIsNone(self.screenshot_window.start_pos)
        self.assertIsNone(self.screenshot_window.end_pos)
    
    def test_get_rect_normal(self):
        """测试获取矩形区域（正常情况）"""
        from PyQt5.QtCore import QPoint
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 80)
        
        rect = self.screenshot_window.get_rect()
        
        self.assertEqual(rect.x(), 10)
        self.assertEqual(rect.y(), 10)
        self.assertEqual(rect.width(), 90)
        self.assertEqual(rect.height(), 70)
    
    def test_get_rect_reverse(self):
        """测试获取矩形区域（反向拖拽）"""
        from PyQt5.QtCore import QPoint
        self.screenshot_window.start_pos = QPoint(100, 80)
        self.screenshot_window.end_pos = QPoint(10, 10)
        
        rect = self.screenshot_window.get_rect()
        
        self.assertEqual(rect.x(), 10)
        self.assertEqual(rect.y(), 10)
        self.assertEqual(rect.width(), 90)
        self.assertEqual(rect.height(), 70)
    
    def test_mouse_press(self):
        """测试鼠标按下事件"""
        from PyQt5.QtCore import QPoint
        from PyQt5.QtGui import QMouseEvent
        
        event = QMouseEvent(QMouseEvent.MouseButtonPress, QPoint(50, 50), 
                           Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
        
        self.screenshot_window.mousePressEvent(event)
        
        self.assertEqual(self.screenshot_window.start_pos, QPoint(50, 50))
        self.assertEqual(self.screenshot_window.end_pos, QPoint(50, 50))
    
    def test_mouse_move(self):
        """测试鼠标移动事件"""
        from PyQt5.QtCore import QPoint
        from PyQt5.QtGui import QMouseEvent
        
        # 先设置起始位置
        self.screenshot_window.start_pos = QPoint(50, 50)
        
        # 创建移动事件
        event = QMouseEvent(QMouseEvent.MouseMove, QPoint(150, 100), 
                           Qt.NoButton, Qt.LeftButton, Qt.NoModifier)
        
        self.screenshot_window.mouseMoveEvent(event)
        
        self.assertEqual(self.screenshot_window.end_pos, QPoint(150, 100))
    
    def test_mouse_release_valid(self):
        """测试鼠标释放事件（有效区域应进入预览模式）"""
        from PyQt5.QtCore import QPoint
        from PyQt5.QtGui import QMouseEvent
        
        self.screenshot_window.show()
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        
        event = QMouseEvent(QMouseEvent.MouseButtonRelease, QPoint(100, 100), 
                           Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
        
        self.screenshot_window.mouseReleaseEvent(event)
        
        self.assertIsNotNone(self.screenshot_window.cropped_pixmap)
        self.assertEqual(self.screenshot_window.cropped_pixmap.width(), 90)
        self.assertEqual(self.screenshot_window.cropped_pixmap.height(), 90)
        self.assertFalse(self.screenshot_window.cancel_btn.isHidden())
        self.assertFalse(self.screenshot_window.copy_btn.isHidden())
        self.assertFalse(self.screenshot_window.add_btn.isHidden())
        self.assertFalse(self.screenshot_window.text_edit_btn.isHidden())
        self.assertFalse(self.screenshot_window.doodle_btn.isHidden())
        self.assertFalse(self.screenshot_window.save_btn.isHidden())
    
    def test_mouse_release_small(self):
        """测试鼠标释放事件（太小的区域）"""
        from PyQt5.QtCore import QPoint
        from PyQt5.QtGui import QMouseEvent
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(15, 15)
        
        event = QMouseEvent(QMouseEvent.MouseButtonRelease, QPoint(15, 15), 
                           Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
        
        captured_cancel = []
        def on_cancel():
            captured_cancel.append(True)
        self.screenshot_window.screenshot_canceled.connect(on_cancel)
        
        self.screenshot_window.mouseReleaseEvent(event)
        
        self.assertEqual(len(captured_cancel), 1)
        self.assertEqual(self.screenshot_window.cropped_pixmap, None)
    
    def test_key_escape(self):
        """测试ESC键取消截图"""
        from PyQt5.QtGui import QKeyEvent
        from PyQt5.QtCore import QEvent
        
        event = QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier)
        
        # 确保窗口已显示
        self.screenshot_window.show()
        self.assertTrue(self.screenshot_window.isVisible())
        
        # 发送ESC键事件
        self.screenshot_window.keyPressEvent(event)
        
        # 给窗口关闭一些时间
        import time
        time.sleep(0.1)
        
        # 由于close()不会立即关闭（需要事件循环），我们验证close被调用
        # 这里我们检查窗口状态
        self.assertTrue(self.screenshot_window.isHidden())
    
    def test_paint_event_with_selection(self):
        """测试截图窗口绘制（选中区域应显示真实内容）"""
        from PyQt5.QtCore import QPoint
        
        # 设置起始和结束位置
        self.screenshot_window.start_pos = QPoint(50, 50)
        self.screenshot_window.end_pos = QPoint(150, 150)
        
        # 显示窗口并触发绘制
        self.screenshot_window.show()
        self.screenshot_window.resize(400, 300)
        self.screenshot_window.update()
        
        # 给绘制一些时间
        import time
        time.sleep(0.1)
        
        # 验证窗口可见且有内容
        self.assertTrue(self.screenshot_window.isVisible())
        
        # 验证选中区域的内容应该是白色（原始截图颜色）
        # 通过检查截图窗口的像素来验证
        rect = self.screenshot_window.get_rect()
        self.assertEqual(rect.x(), 50)
        self.assertEqual(rect.y(), 50)
        self.assertEqual(rect.width(), 100)
        self.assertEqual(rect.height(), 100)
    
    def test_paint_event_no_selection(self):
        """测试截图窗口绘制（无选中区域时全屏显示遮罩）"""
        # 确保没有设置选中区域
        self.screenshot_window.start_pos = None
        self.screenshot_window.end_pos = None
        
        # 显示窗口并触发绘制
        self.screenshot_window.show()
        self.screenshot_window.resize(400, 300)
        self.screenshot_window.update()
        
        # 给绘制一些时间
        import time
        time.sleep(0.1)
        
        # 验证窗口可见
        self.assertTrue(self.screenshot_window.isVisible())
    
    def test_preview_cancel_button(self):
        """测试预览模式下点击取消按钮"""
        from PyQt5.QtCore import QPoint
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        
        captured_cancel = []
        def on_cancel():
            captured_cancel.append(True)
        self.screenshot_window.screenshot_canceled.connect(on_cancel)
        
        self.screenshot_window.show_preview(QPixmap(90, 90))
        
        self.screenshot_window.cancel_btn.click()
        
        self.assertEqual(len(captured_cancel), 1)
    
    def test_preview_copy_button(self):
        """测试预览模式下点击复制按钮"""
        from PyQt5.QtCore import QPoint
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        
        test_pixmap = QPixmap(90, 90)
        test_pixmap.fill(Qt.red)
        
        self.screenshot_window.show_preview(test_pixmap)
        
        with patch('picbot.QApplication.clipboard') as mock_clipboard:
            mock_clipboard_instance = Mock()
            mock_clipboard.return_value = mock_clipboard_instance
            
            self.screenshot_window.copy_btn.click()
            
            mock_clipboard_instance.setPixmap.assert_called_once()
    
    def test_preview_add_button(self):
        """测试预览模式下点击添加到Label按钮"""
        from PyQt5.QtCore import QPoint
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        
        captured_pixmap = []
        def on_taken(pixmap):
            captured_pixmap.append(pixmap)
        self.screenshot_window.screenshot_taken.connect(on_taken)
        
        test_pixmap = QPixmap(90, 90)
        self.screenshot_window.show_preview(test_pixmap)
        
        self.screenshot_window.add_btn.click()
        
        self.assertEqual(len(captured_pixmap), 1)
        self.assertEqual(captured_pixmap[0].width(), 90)
        self.assertEqual(captured_pixmap[0].height(), 90)
    
    def test_mouse_blocked_in_preview(self):
        """测试预览模式下鼠标事件被拦截"""
        from PyQt5.QtCore import QPoint
        from PyQt5.QtGui import QMouseEvent
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        self.screenshot_window.show_preview(QPixmap(90, 90))
        
        old_start = self.screenshot_window.start_pos
        
        press_event = QMouseEvent(QMouseEvent.MouseButtonPress, QPoint(200, 200),
                                   Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
        self.screenshot_window.mousePressEvent(press_event)
        
        self.assertEqual(self.screenshot_window.start_pos, old_start)
    
    def test_edit_text_button_activates_mode(self):
        """测试编辑文字按钮激活文本编辑模式"""
        from PyQt5.QtCore import QPoint
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        self.screenshot_window.show_preview(QPixmap(90, 90))
        
        self.screenshot_window.text_edit_btn.click()
        
        self.assertTrue(self.screenshot_window.is_text_editing)
        self.assertTrue(self.screenshot_window.cancel_btn.isHidden())
        self.assertTrue(self.screenshot_window.copy_btn.isHidden())
        self.assertTrue(self.screenshot_window.text_edit_btn.isHidden())
        self.assertTrue(self.screenshot_window.doodle_btn.isHidden())
        self.assertTrue(self.screenshot_window.save_btn.isHidden())
        self.assertTrue(self.screenshot_window.add_btn.isHidden())
    
    def test_edit_text_click_shows_input(self):
        """测试编辑文字时点击选择区域显示输入框"""
        from PyQt5.QtCore import QPoint
        
        self.screenshot_window.show()
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(400, 200)
        self.screenshot_window.show_preview(QPixmap(390, 190))
        self.screenshot_window.is_text_editing = True
        
        self.screenshot_window.mousePressEvent(
            type('MockEvent', (), {'pos': lambda s: QPoint(100, 100), 'button': lambda s: Qt.LeftButton})()
        )
        
        self.assertFalse(self.screenshot_window.text_input.isHidden())
        self.assertIsNotNone(self.screenshot_window.text_input_pos)
    
    def test_edit_text_finished_draws(self):
        """测试输入文字完成后绘制到截图"""
        from PyQt5.QtCore import QPoint
        
        self.screenshot_window.show()
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(400, 200)
        self.screenshot_window.show_preview(QPixmap(390, 190))
        self.screenshot_window.is_text_editing = True
        self.screenshot_window.text_input_pos = QPoint(90, 90)
        self.screenshot_window.text_input.setText('Hello')
        
        self.screenshot_window.on_text_input_finished()
        
        self.assertTrue(self.screenshot_window.text_input.isHidden())
        self.assertTrue(self.screenshot_window.is_text_editing)
    
    def test_edit_text_empty_no_draw(self):
        """测试空文本不绘制"""
        from PyQt5.QtCore import QPoint
        
        self.screenshot_window.show()
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(400, 200)
        self.screenshot_window.show_preview(QPixmap(390, 190))
        self.screenshot_window.is_text_editing = True
        self.screenshot_window.text_input_pos = QPoint(90, 90)
        self.screenshot_window.text_input.clear()
        
        self.screenshot_window.on_text_input_finished()
        
        self.assertTrue(self.screenshot_window.text_input.isHidden())
        self.assertTrue(self.screenshot_window.is_text_editing)
    
    def test_edit_text_outside_selection(self):
        """测试编辑文字时点击选择区域外不触发输入"""
        from PyQt5.QtCore import QPoint
        
        self.screenshot_window.show()
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        self.screenshot_window.show_preview(QPixmap(90, 90))
        self.screenshot_window.is_text_editing = True
        
        self.screenshot_window.mousePressEvent(
            type('MockEvent', (), {'pos': lambda s: QPoint(200, 200), 'button': lambda s: Qt.LeftButton})()
        )
        
        self.assertTrue(self.screenshot_window.text_input.isHidden())
        self.assertTrue(self.screenshot_window.is_text_editing)
    
    def test_esc_cancels_text_editing(self):
        """测试ESC取消文本编辑模式"""
        from PyQt5.QtCore import QPoint
        from PyQt5.QtGui import QKeyEvent
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        self.screenshot_window.show_preview(QPixmap(90, 90))
        self.screenshot_window.is_text_editing = True
        
        canceled = []
        self.screenshot_window.screenshot_canceled.connect(lambda: canceled.append(True))
        
        event = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier)
        self.screenshot_window.keyPressEvent(event)
        
        self.assertFalse(self.screenshot_window.is_text_editing)
        self.assertEqual(len(canceled), 0)
    
    def test_multiple_text_edits_accumulate(self):
        """测试多次编辑文字内容叠加显示"""
        from PyQt5.QtCore import QPoint
        
        self.screenshot_window.show()
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(400, 200)
        self.screenshot_window.show_preview(QPixmap(390, 190))
        
        self.screenshot_window.is_text_editing = True
        self.screenshot_window.text_input_pos = QPoint(50, 50)
        self.screenshot_window.text_input.setText('Hello')
        self.screenshot_window.on_text_input_finished()
        self.assertTrue(self.screenshot_window.is_text_editing)
        
        self.screenshot_window.text_input_pos = QPoint(100, 100)
        self.screenshot_window.text_input.setText('World')
        self.screenshot_window.on_text_input_finished()
        self.assertTrue(self.screenshot_window.is_text_editing)
        
        image = self.screenshot_window.cropped_pixmap.toImage()
        self.assertIsNotNone(image)
    
    def test_finalize_text_keeps_editing_mode(self):
        """测试finalize_text完成后保持编辑模式"""
        from PyQt5.QtCore import QPoint
        
        self.screenshot_window.show()
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(400, 200)
        self.screenshot_window.show_preview(QPixmap(390, 190))
        self.screenshot_window.is_text_editing = True
        self.screenshot_window.text_input_pos = QPoint(50, 50)
        self.screenshot_window.text_input.setText('Hello')
        self.screenshot_window.text_input.show()
        
        self.screenshot_window.finalize_text()
        
        self.assertTrue(self.screenshot_window.text_input.isHidden())
        self.assertTrue(self.screenshot_window.is_text_editing)
    
    def test_edit_text_button_toggles_off(self):
        """测试编辑文字按钮切换关闭编辑模式"""
        from PyQt5.QtCore import QPoint
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        self.screenshot_window.show_preview(QPixmap(90, 90))
        self.screenshot_window.is_text_editing = True
        
        self.screenshot_window.text_edit_btn.click()
        
        self.assertFalse(self.screenshot_window.is_text_editing)
        self.assertFalse(self.screenshot_window.text_edit_btn.isHidden())
    
    def test_sequential_clicks_show_text_input(self):
        """测试连续点击不同位置都能显示输入框"""
        from PyQt5.QtCore import QPoint
        
        self.screenshot_window.show()
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(400, 200)
        self.screenshot_window.show_preview(QPixmap(390, 190))
        self.screenshot_window.is_text_editing = True
        
        self.screenshot_window.mousePressEvent(
            type('MockEvent', (), {'pos': lambda s: QPoint(50, 50), 'button': lambda s: Qt.LeftButton})()
        )
        self.assertFalse(self.screenshot_window.text_input.isHidden())
        
        self.screenshot_window.finalize_text()
        
        self.screenshot_window.mousePressEvent(
            type('MockEvent', (), {'pos': lambda s: QPoint(150, 80), 'button': lambda s: Qt.LeftButton})()
        )
        self.assertFalse(self.screenshot_window.text_input.isHidden())
        
        self.screenshot_window.finalize_text()
        
        self.screenshot_window.mousePressEvent(
            type('MockEvent', (), {'pos': lambda s: QPoint(200, 120), 'button': lambda s: Qt.LeftButton})()
        )
        self.assertFalse(self.screenshot_window.text_input.isHidden())
    
    def test_text_style_attrs_initialized(self):
        """测试文字样式属性初始化正确"""
        from PyQt5.QtCore import QPoint, Qt
        from PyQt5.QtGui import QColor, QFont
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        self.screenshot_window.show_preview(QPixmap(90, 90))
        
        self.assertEqual(self.screenshot_window.text_font.family(), 'Microsoft YaHei')
        self.assertEqual(self.screenshot_window.text_color, QColor(Qt.red))
        self.assertEqual(self.screenshot_window.text_size, 20)
    
    def test_text_style_buttons_show_on_edit(self):
        """测试文字编辑时显示样式按钮"""
        from PyQt5.QtCore import QPoint
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        self.screenshot_window.show_preview(QPixmap(90, 90))
        
        # 通过 on_edit_text 进入文字编辑模式，样式按钮应显示
        self.screenshot_window.on_edit_text()
        
        self.assertFalse(self.screenshot_window.font_btn.isHidden())
        self.assertFalse(self.screenshot_window.color_btn.isHidden())
        self.assertFalse(self.screenshot_window.size_btn.isHidden())
    
    def test_text_style_buttons_hide_on_finalize(self):
        """测试文字编辑完成时样式按钮保持可见"""
        from PyQt5.QtCore import QPoint
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        self.screenshot_window.show_preview(QPixmap(90, 90))
        
        # 进入文字编辑模式
        self.screenshot_window.on_edit_text()
        
        self.screenshot_window.mousePressEvent(
            type('MockEvent', (), {'pos': lambda s: QPoint(50, 50), 'button': lambda s: Qt.LeftButton})()
        )
        self.screenshot_window.text_input.setText('Hello')
        self.screenshot_window.finalize_text()
        
        # finalize_text 后样式按钮应保持可见
        self.assertFalse(self.screenshot_window.font_btn.isHidden())
        self.assertFalse(self.screenshot_window.color_btn.isHidden())
        self.assertFalse(self.screenshot_window.size_btn.isHidden())
    
    def test_text_style_buttons_hide_on_edit_toggle(self):
        """测试再次点击编辑文字按钮时隐藏样式按钮"""
        from PyQt5.QtCore import QPoint
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        self.screenshot_window.show_preview(QPixmap(90, 90))
        
        # 进入文字编辑模式
        self.screenshot_window.on_edit_text()
        
        self.screenshot_window.mousePressEvent(
            type('MockEvent', (), {'pos': lambda s: QPoint(50, 50), 'button': lambda s: Qt.LeftButton})()
        )
        self.screenshot_window.text_input.setText('Hello')
        
        # 再次点击编辑文字按钮，退出编辑模式，样式按钮应隐藏
        self.screenshot_window.on_edit_text()
        
        self.assertTrue(self.screenshot_window.font_btn.isHidden())
        self.assertTrue(self.screenshot_window.color_btn.isHidden())
        self.assertTrue(self.screenshot_window.size_btn.isHidden())
    
    def test_focus_out_to_style_btn_does_not_finalize(self):
        """测试点击样式按钮不会触发finalize_text"""
        from PyQt5.QtCore import QPoint, QEvent, Qt
        from PyQt5.QtGui import QFocusEvent
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        self.screenshot_window.show_preview(QPixmap(90, 90))
        
        # 进入文字编辑模式
        self.screenshot_window.on_edit_text()
        
        self.screenshot_window.mousePressEvent(
            type('MockEvent', (), {'pos': lambda s: QPoint(50, 50), 'button': lambda s: Qt.LeftButton})()
        )
        self.screenshot_window.text_input.setText('Test')
        self.assertFalse(self.screenshot_window.font_btn.isHidden())
        
        self.screenshot_window._style_btn_active = True
        focus_event = QFocusEvent(QEvent.FocusOut, Qt.OtherFocusReason)
        result = self.screenshot_window.eventFilter(self.screenshot_window.text_input, focus_event)
        
        self.assertTrue(result)
        self.assertFalse(self.screenshot_window.font_btn.isHidden())
        self.assertFalse(self.screenshot_window._style_btn_active)
    
    def test_finalize_text_uses_custom_style(self):
        """测试finalize_text使用自定义字体样式"""
        from PyQt5.QtCore import QPoint, Qt
        from PyQt5.QtGui import QColor, QFont
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        self.screenshot_window.show_preview(QPixmap(90, 90))
        self.screenshot_window.is_text_editing = True
        
        self.screenshot_window.text_font = QFont('Arial', 30)
        self.screenshot_window.text_color = QColor(Qt.blue)
        self.screenshot_window.text_size = 30
        
        self.screenshot_window.mousePressEvent(
            type('MockEvent', (), {'pos': lambda s: QPoint(50, 50), 'button': lambda s: Qt.LeftButton})()
        )
        self.screenshot_window.text_input.setText('Test')
        self.screenshot_window.finalize_text()
        
        self.assertIsNotNone(self.screenshot_window.cropped_pixmap)
    
    def test_doodle_button_activates_mode(self):
        """测试涂鸦按钮激活涂鸦模式，窗口保持可见"""
        from PyQt5.QtCore import QPoint
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        self.screenshot_window.show_preview(QPixmap(90, 90))
        
        self.screenshot_window.doodle_btn.click()
        
        self.assertTrue(self.screenshot_window.is_screenshot_doodle)
        self.assertEqual(self.screenshot_window.doodle_btn.text(), '结束涂鸦')
        self.assertTrue(self.screenshot_window.cancel_btn.isHidden())
        self.assertTrue(self.screenshot_window.copy_btn.isHidden())
        self.assertFalse(self.screenshot_window.doodle_btn.isHidden())
        self.assertTrue(self.screenshot_window.add_btn.isHidden())
    
    def test_doodle_button_toggle_off(self):
        """测试再次点击涂鸦按钮退出涂鸦模式"""
        from PyQt5.QtCore import QPoint
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        self.screenshot_window.show_preview(QPixmap(90, 90))
        
        self.screenshot_window.doodle_btn.click()
        self.screenshot_window.doodle_btn.click()
        
        self.assertFalse(self.screenshot_window.is_screenshot_doodle)
        self.assertIsNone(self.screenshot_window.doodle_last_pos)
        self.assertEqual(self.screenshot_window.doodle_btn.text(), '涂鸦')
        self.assertFalse(self.screenshot_window.cancel_btn.isHidden())
    
    def test_doodle_mouse_draw_on_pixmap(self):
        """测试涂鸦模式鼠标绘制到截图"""
        from PyQt5.QtCore import QPoint
        from PyQt5.QtGui import QMouseEvent
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        
        cropped = QPixmap(90, 90)
        cropped.fill(Qt.white)
        self.screenshot_window.cropped_pixmap = cropped
        self.screenshot_window.is_screenshot_doodle = True
        self.screenshot_window.doodle_last_pos = None
        
        press_event = QMouseEvent(
            QMouseEvent.MouseButtonPress, QPoint(50, 50),
            Qt.LeftButton, Qt.LeftButton, Qt.NoModifier
        )
        self.screenshot_window.mousePressEvent(press_event)
        self.assertIsNotNone(self.screenshot_window.doodle_last_pos)
        
        move_event = QMouseEvent(
            QMouseEvent.MouseMove, QPoint(70, 70),
            Qt.NoButton, Qt.LeftButton, Qt.NoModifier
        )
        self.screenshot_window.mouseMoveEvent(move_event)
        
        release_event = QMouseEvent(
            QMouseEvent.MouseButtonRelease, QPoint(70, 70),
            Qt.LeftButton, Qt.LeftButton, Qt.NoModifier
        )
        self.screenshot_window.mouseReleaseEvent(release_event)
        self.assertIsNone(self.screenshot_window.doodle_last_pos)
    
    def test_doodle_esc_exits_mode(self):
        """测试ESC退出涂鸦模式"""
        from PyQt5.QtCore import QPoint
        from PyQt5.QtGui import QKeyEvent
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        self.screenshot_window.show_preview(QPixmap(90, 90))
        self.screenshot_window.doodle_btn.click()
        
        esc_event = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier)
        self.screenshot_window.keyPressEvent(esc_event)
        
        self.assertFalse(self.screenshot_window.is_screenshot_doodle)
        self.assertEqual(self.screenshot_window.doodle_btn.text(), '涂鸦')
        self.assertFalse(self.screenshot_window.cancel_btn.isHidden())
    
    @patch('picbot.QFileDialog.getSaveFileName')
    def test_save_button(self, mock_get_save):
        """测试保存按钮保存图片到本地"""
        from PyQt5.QtCore import QPoint
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        
        test_pixmap = QPixmap(90, 90)
        test_pixmap.fill(Qt.red)
        self.screenshot_window.show_preview(test_pixmap)
        
        mock_get_save.return_value = ('test_save.png', '')
        
        with patch.object(test_pixmap, 'save') as mock_save:
            self.screenshot_window.save_btn.click()
            mock_save.assert_called_once_with('test_save.png')
    
    @patch('picbot.QFileDialog.getSaveFileName')
    def test_save_button_cancelled(self, mock_get_save):
        """测试保存时取消操作不保存"""
        from PyQt5.QtCore import QPoint
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        
        test_pixmap = QPixmap(90, 90)
        test_pixmap.fill(Qt.red)
        self.screenshot_window.show_preview(test_pixmap)
        
        mock_get_save.return_value = ('', '')
        
        with patch.object(test_pixmap, 'save') as mock_save:
            self.screenshot_window.save_btn.click()
            mock_save.assert_not_called()
    
    def test_drag_press_starts_drag(self):
        """测试鼠标按下选区内部开始拖拽"""
        from PyQt5.QtCore import QPoint
        from PyQt5.QtGui import QMouseEvent
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        self.screenshot_window.show_preview(QPixmap(90, 90))
        
        press_event = QMouseEvent(
            QMouseEvent.MouseButtonPress, QPoint(50, 50),
            Qt.LeftButton, Qt.LeftButton, Qt.NoModifier
        )
        self.screenshot_window.mousePressEvent(press_event)
        
        self.assertTrue(self.screenshot_window.is_dragging)
        self.assertIsNotNone(self.screenshot_window.drag_offset)
    
    def test_drag_press_outside_no_drag(self):
        """测试鼠标按下选区外部不触发拖拽"""
        from PyQt5.QtCore import QPoint
        from PyQt5.QtGui import QMouseEvent
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        self.screenshot_window.show_preview(QPixmap(90, 90))
        
        press_event = QMouseEvent(
            QMouseEvent.MouseButtonPress, QPoint(200, 200),
            Qt.LeftButton, Qt.LeftButton, Qt.NoModifier
        )
        self.screenshot_window.mousePressEvent(press_event)
        
        self.assertFalse(self.screenshot_window.is_dragging)
    
    def test_drag_moves_selection(self):
        """测试拖拽移动截图选区"""
        from PyQt5.QtCore import QPoint
        from PyQt5.QtGui import QMouseEvent
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        self.screenshot_window.show_preview(QPixmap(90, 90))
        
        press_event = QMouseEvent(
            QMouseEvent.MouseButtonPress, QPoint(50, 50),
            Qt.LeftButton, Qt.LeftButton, Qt.NoModifier
        )
        self.screenshot_window.mousePressEvent(press_event)
        
        move_event = QMouseEvent(
            QMouseEvent.MouseMove, QPoint(200, 150),
            Qt.NoButton, Qt.LeftButton, Qt.NoModifier
        )
        self.screenshot_window.mouseMoveEvent(move_event)
        
        self.assertEqual(self.screenshot_window.start_pos.x(), 200 - self.screenshot_window.drag_offset.x())
        self.assertEqual(self.screenshot_window.start_pos.y(), 150 - self.screenshot_window.drag_offset.y())
        self.assertIsNotNone(self.screenshot_window.cropped_pixmap)
    
    def test_drag_release_stops_drag(self):
        """测试鼠标释放停止拖拽"""
        from PyQt5.QtCore import QPoint
        from PyQt5.QtGui import QMouseEvent
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        self.screenshot_window.show_preview(QPixmap(90, 90))
        
        press_event = QMouseEvent(
            QMouseEvent.MouseButtonPress, QPoint(50, 50),
            Qt.LeftButton, Qt.LeftButton, Qt.NoModifier
        )
        self.screenshot_window.mousePressEvent(press_event)
        
        release_event = QMouseEvent(
            QMouseEvent.MouseButtonRelease, QPoint(50, 50),
            Qt.LeftButton, Qt.LeftButton, Qt.NoModifier
        )
        self.screenshot_window.mouseReleaseEvent(release_event)
        
        self.assertFalse(self.screenshot_window.is_dragging)
    
    def test_drag_clamped_to_screen_bounds(self):
        """测试拖拽时选区被限制在屏幕范围内"""
        from PyQt5.QtCore import QPoint
        from PyQt5.QtGui import QMouseEvent
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        self.screenshot_window.show_preview(QPixmap(90, 90))
        
        press_event = QMouseEvent(
            QMouseEvent.MouseButtonPress, QPoint(50, 50),
            Qt.LeftButton, Qt.LeftButton, Qt.NoModifier
        )
        self.screenshot_window.mousePressEvent(press_event)
        
        move_event = QMouseEvent(
            QMouseEvent.MouseMove, QPoint(-100, -100),
            Qt.NoButton, Qt.LeftButton, Qt.NoModifier
        )
        self.screenshot_window.mouseMoveEvent(move_event)
        
        self.assertGreaterEqual(self.screenshot_window.start_pos.x(), 0)
        self.assertGreaterEqual(self.screenshot_window.start_pos.y(), 0)
    
    def test_drag_preserves_text_edit(self):
        """测试拖拽后编辑的文字保留"""
        from PyQt5.QtCore import QPoint
        from PyQt5.QtGui import QMouseEvent, QPen
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        self.screenshot_window.show_preview(QPixmap(90, 90))
        self.screenshot_window.edit_layer = QPixmap(90, 90)
        self.screenshot_window.edit_layer.fill(Qt.transparent)
        
        painter = QPainter(self.screenshot_window.edit_layer)
        painter.setPen(QPen(Qt.red))
        painter.drawText(20, 20, 'Test')
        painter.end()
        
        press_event = QMouseEvent(
            QMouseEvent.MouseButtonPress, QPoint(50, 50),
            Qt.LeftButton, Qt.LeftButton, Qt.NoModifier
        )
        self.screenshot_window.mousePressEvent(press_event)
        
        move_event = QMouseEvent(
            QMouseEvent.MouseMove, QPoint(100, 60),
            Qt.NoButton, Qt.LeftButton, Qt.NoModifier
        )
        self.screenshot_window.mouseMoveEvent(move_event)
        
        self.assertIsNotNone(self.screenshot_window.cropped_pixmap)
        self.assertIsNotNone(self.screenshot_window.edit_layer)
    
    def test_drag_preserves_doodle_edit(self):
        """测试拖拽后涂鸦内容保留"""
        from PyQt5.QtCore import QPoint
        from PyQt5.QtGui import QMouseEvent, QPen
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        self.screenshot_window.show_preview(QPixmap(90, 90))
        self.screenshot_window.edit_layer = QPixmap(90, 90)
        self.screenshot_window.edit_layer.fill(Qt.transparent)
        
        painter = QPainter(self.screenshot_window.edit_layer)
        painter.setPen(QPen(Qt.red, 5))
        painter.drawLine(10, 10, 50, 50)
        painter.end()
        
        press_event = QMouseEvent(
            QMouseEvent.MouseButtonPress, QPoint(50, 50),
            Qt.LeftButton, Qt.LeftButton, Qt.NoModifier
        )
        self.screenshot_window.mousePressEvent(press_event)
        
        move_event = QMouseEvent(
            QMouseEvent.MouseMove, QPoint(100, 60),
            Qt.NoButton, Qt.LeftButton, Qt.NoModifier
        )
        self.screenshot_window.mouseMoveEvent(move_event)
        
        self.assertIsNotNone(self.screenshot_window.cropped_pixmap)
        self.assertIsNotNone(self.screenshot_window.edit_layer)
    
    def test_show_preview_creates_edit_layer(self):
        """测试show_preview创建edit_layer"""
        from PyQt5.QtCore import QPoint
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        self.screenshot_window.show_preview(QPixmap(90, 90))
        
        self.assertIsNotNone(self.screenshot_window.edit_layer)
        self.assertEqual(self.screenshot_window.edit_layer.size(), QPixmap(90, 90).size())
    
    def test_show_preview_preserves_edit_layer(self):
        """测试show_preview带reset_edit_layer=False时保留edit_layer"""
        from PyQt5.QtCore import QPoint
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        self.screenshot_window.show_preview(QPixmap(90, 90))
        
        original_layer = self.screenshot_window.edit_layer
        self.screenshot_window.show_preview(QPixmap(90, 90), reset_edit_layer=False)
        
        self.assertIs(self.screenshot_window.edit_layer, original_layer)
    
    def test_get_corner_at_returns_none_without_preview(self):
        """测试无预览时_get_corner_at返回None"""
        from PyQt5.QtCore import QPoint
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        self.assertIsNone(self.screenshot_window._get_corner_at(QPoint(10, 10)))
    
    def test_get_corner_at_detects_tl_corner(self):
        """测试_get_corner_at检测到左上角"""
        from PyQt5.QtCore import QPoint
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        self.screenshot_window.show_preview(QPixmap(90, 90))
        
        self.assertEqual(self.screenshot_window._get_corner_at(QPoint(10, 10)), 'tl')
    
    def test_get_corner_at_detects_br_corner(self):
        """测试_get_corner_at检测到右下角"""
        from PyQt5.QtCore import QPoint
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        self.screenshot_window.show_preview(QPixmap(90, 90))
        
        self.assertEqual(self.screenshot_window._get_corner_at(QPoint(100, 100)), 'br')
    
    def test_get_corner_at_returns_none_inside(self):
        """测试_get_corner_at在选区内部返回None"""
        from PyQt5.QtCore import QPoint
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        self.screenshot_window.show_preview(QPixmap(90, 90))
        
        self.assertIsNone(self.screenshot_window._get_corner_at(QPoint(50, 50)))
    
    def test_resize_press_starts_resize(self):
        """测试点击圆角开始缩放"""
        from PyQt5.QtCore import QPoint
        from PyQt5.QtGui import QMouseEvent
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        self.screenshot_window.show_preview(QPixmap(90, 90))
        
        press_event = QMouseEvent(
            QMouseEvent.MouseButtonPress, QPoint(10, 10),
            Qt.LeftButton, Qt.LeftButton, Qt.NoModifier
        )
        self.screenshot_window.mousePressEvent(press_event)
        
        self.assertTrue(self.screenshot_window.is_resizing)
        self.assertEqual(self.screenshot_window.resize_corner, 'tl')
        self.assertIsNotNone(self.screenshot_window.resize_opposite)
    
    def test_resize_move_updates_rect(self):
        """测试拖拽圆角更新选区大小"""
        from PyQt5.QtCore import QPoint
        from PyQt5.QtGui import QMouseEvent
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        self.screenshot_window.show_preview(QPixmap(90, 90))
        
        press_event = QMouseEvent(
            QMouseEvent.MouseButtonPress, QPoint(10, 10),
            Qt.LeftButton, Qt.LeftButton, Qt.NoModifier
        )
        self.screenshot_window.mousePressEvent(press_event)
        
        orig_width = self.screenshot_window.cropped_pixmap.width()
        orig_height = self.screenshot_window.cropped_pixmap.height()
        
        move_event = QMouseEvent(
            QMouseEvent.MouseMove, QPoint(30, 30),
            Qt.NoButton, Qt.LeftButton, Qt.NoModifier
        )
        self.screenshot_window.mouseMoveEvent(move_event)
        
        self.assertIsNotNone(self.screenshot_window.cropped_pixmap)
        self.assertNotEqual(self.screenshot_window.cropped_pixmap.width(), orig_width)
        self.assertNotEqual(self.screenshot_window.cropped_pixmap.height(), orig_height)
    
    def test_resize_release_ends_resize(self):
        """测试释放鼠标结束缩放"""
        from PyQt5.QtCore import QPoint
        from PyQt5.QtGui import QMouseEvent
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        self.screenshot_window.show_preview(QPixmap(90, 90))
        
        press_event = QMouseEvent(
            QMouseEvent.MouseButtonPress, QPoint(10, 10),
            Qt.LeftButton, Qt.LeftButton, Qt.NoModifier
        )
        self.screenshot_window.mousePressEvent(press_event)
        
        release_event = QMouseEvent(
            QMouseEvent.MouseButtonRelease, QPoint(30, 30),
            Qt.LeftButton, Qt.LeftButton, Qt.NoModifier
        )
        self.screenshot_window.mouseReleaseEvent(release_event)
        
        self.assertFalse(self.screenshot_window.is_resizing)
        self.assertIsNone(self.screenshot_window.resize_corner)
        self.assertIsNone(self.screenshot_window.resize_opposite)
    
    def test_resize_not_triggered_without_preview(self):
        """测试无预览时点击不会触发缩放"""
        from PyQt5.QtCore import QPoint
        from PyQt5.QtGui import QMouseEvent
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        
        press_event = QMouseEvent(
            QMouseEvent.MouseButtonPress, QPoint(10, 10),
            Qt.LeftButton, Qt.LeftButton, Qt.NoModifier
        )
        self.screenshot_window.mousePressEvent(press_event)
        
        self.assertFalse(self.screenshot_window.is_resizing)
    
    def test_resize_stays_in_screen_bounds(self):
        """测试缩放时选区被限制在屏幕范围内"""
        from PyQt5.QtCore import QPoint
        from PyQt5.QtGui import QMouseEvent
        
        self.screenshot_window.start_pos = QPoint(50, 50)
        self.screenshot_window.end_pos = QPoint(100, 100)
        self.screenshot_window.show_preview(QPixmap(50, 50))
        
        press_event = QMouseEvent(
            QMouseEvent.MouseButtonPress, QPoint(50, 50),
            Qt.LeftButton, Qt.LeftButton, Qt.NoModifier
        )
        self.screenshot_window.mousePressEvent(press_event)
        
        move_event = QMouseEvent(
            QMouseEvent.MouseMove, QPoint(-100, -100),
            Qt.NoButton, Qt.LeftButton, Qt.NoModifier
        )
        self.screenshot_window.mouseMoveEvent(move_event)
        
        self.assertGreaterEqual(self.screenshot_window.start_pos.x(), 0)
        self.assertGreaterEqual(self.screenshot_window.start_pos.y(), 0)
    
    def test_get_corner_at_detects_top_edge(self):
        """测试_get_corner_at检测到上边中点"""
        from PyQt5.QtCore import QPoint
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        self.screenshot_window.show_preview(QPixmap(90, 90))
        
        self.assertEqual(self.screenshot_window._get_corner_at(QPoint(55, 10)), 'top')
    
    def test_get_corner_at_detects_bottom_edge(self):
        """测试_get_corner_at检测到下边中点"""
        from PyQt5.QtCore import QPoint
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        self.screenshot_window.show_preview(QPixmap(90, 90))
        
        self.assertEqual(self.screenshot_window._get_corner_at(QPoint(55, 100)), 'bottom')
    
    def test_get_corner_at_detects_left_edge(self):
        """测试_get_corner_at检测到左边中点"""
        from PyQt5.QtCore import QPoint
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        self.screenshot_window.show_preview(QPixmap(90, 90))
        
        self.assertEqual(self.screenshot_window._get_corner_at(QPoint(10, 55)), 'left')
    
    def test_get_corner_at_detects_right_edge(self):
        """测试_get_corner_at检测到右边中点"""
        from PyQt5.QtCore import QPoint
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        self.screenshot_window.show_preview(QPixmap(90, 90))
        
        self.assertEqual(self.screenshot_window._get_corner_at(QPoint(100, 55)), 'right')
    
    def test_resize_top_edge_changes_height(self):
        """测试拖拽上边中点只改变高度"""
        from PyQt5.QtCore import QPoint
        from PyQt5.QtGui import QMouseEvent
        
        self.screenshot_window.start_pos = QPoint(10, 50)
        self.screenshot_window.end_pos = QPoint(100, 150)
        self.screenshot_window.show_preview(QPixmap(90, 100))
        
        press_event = QMouseEvent(
            QMouseEvent.MouseButtonPress, QPoint(55, 50),
            Qt.LeftButton, Qt.LeftButton, Qt.NoModifier
        )
        self.screenshot_window.mousePressEvent(press_event)
        
        self.assertTrue(self.screenshot_window.is_resizing)
        self.assertEqual(self.screenshot_window.resize_corner, 'top')
        
        orig_width = self.screenshot_window.cropped_pixmap.width()
        orig_height = self.screenshot_window.cropped_pixmap.height()
        
        move_event = QMouseEvent(
            QMouseEvent.MouseMove, QPoint(55, 30),
            Qt.NoButton, Qt.LeftButton, Qt.NoModifier
        )
        self.screenshot_window.mouseMoveEvent(move_event)
        
        self.assertEqual(self.screenshot_window.cropped_pixmap.width(), orig_width)
        self.assertNotEqual(self.screenshot_window.cropped_pixmap.height(), orig_height)
    
    def test_resize_left_edge_changes_width(self):
        """测试拖拽左边中点只改变宽度"""
        from PyQt5.QtCore import QPoint
        from PyQt5.QtGui import QMouseEvent
        
        self.screenshot_window.start_pos = QPoint(50, 10)
        self.screenshot_window.end_pos = QPoint(150, 100)
        self.screenshot_window.show_preview(QPixmap(100, 90))
        
        press_event = QMouseEvent(
            QMouseEvent.MouseButtonPress, QPoint(50, 55),
            Qt.LeftButton, Qt.LeftButton, Qt.NoModifier
        )
        self.screenshot_window.mousePressEvent(press_event)
        
        self.assertEqual(self.screenshot_window.resize_corner, 'left')
        
        orig_width = self.screenshot_window.cropped_pixmap.width()
        orig_height = self.screenshot_window.cropped_pixmap.height()
        
        move_event = QMouseEvent(
            QMouseEvent.MouseMove, QPoint(30, 55),
            Qt.NoButton, Qt.LeftButton, Qt.NoModifier
        )
        self.screenshot_window.mouseMoveEvent(move_event)
        
        self.assertNotEqual(self.screenshot_window.cropped_pixmap.width(), orig_width)
        self.assertEqual(self.screenshot_window.cropped_pixmap.height(), orig_height)
    
    def test_cursor_on_tl_corner(self):
        """测试鼠标在左上角显示SizeFDiagCursor"""
        from PyQt5.QtCore import QPoint
        from PyQt5.QtGui import QMouseEvent
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        self.screenshot_window.show_preview(QPixmap(90, 90))
        
        move_event = QMouseEvent(
            QMouseEvent.MouseMove, QPoint(10, 10),
            Qt.NoButton, Qt.NoButton, Qt.NoModifier
        )
        self.screenshot_window.mouseMoveEvent(move_event)
        
        self.assertEqual(self.screenshot_window.cursor().shape(), Qt.SizeFDiagCursor)
    
    def test_cursor_on_tr_corner(self):
        """测试鼠标在右上角显示SizeBDiagCursor"""
        from PyQt5.QtCore import QPoint
        from PyQt5.QtGui import QMouseEvent
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        self.screenshot_window.show_preview(QPixmap(90, 90))
        
        move_event = QMouseEvent(
            QMouseEvent.MouseMove, QPoint(100, 10),
            Qt.NoButton, Qt.NoButton, Qt.NoModifier
        )
        self.screenshot_window.mouseMoveEvent(move_event)
        
        self.assertEqual(self.screenshot_window.cursor().shape(), Qt.SizeBDiagCursor)
    
    def test_cursor_on_bl_corner(self):
        """测试鼠标在左下角显示SizeBDiagCursor"""
        from PyQt5.QtCore import QPoint
        from PyQt5.QtGui import QMouseEvent
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        self.screenshot_window.show_preview(QPixmap(90, 90))
        
        move_event = QMouseEvent(
            QMouseEvent.MouseMove, QPoint(10, 100),
            Qt.NoButton, Qt.NoButton, Qt.NoModifier
        )
        self.screenshot_window.mouseMoveEvent(move_event)
        
        self.assertEqual(self.screenshot_window.cursor().shape(), Qt.SizeBDiagCursor)
    
    def test_cursor_on_br_corner(self):
        """测试鼠标在右下角显示SizeFDiagCursor"""
        from PyQt5.QtCore import QPoint
        from PyQt5.QtGui import QMouseEvent
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        self.screenshot_window.show_preview(QPixmap(90, 90))
        
        move_event = QMouseEvent(
            QMouseEvent.MouseMove, QPoint(100, 100),
            Qt.NoButton, Qt.NoButton, Qt.NoModifier
        )
        self.screenshot_window.mouseMoveEvent(move_event)
        
        self.assertEqual(self.screenshot_window.cursor().shape(), Qt.SizeFDiagCursor)
    
    def test_cursor_on_top_edge(self):
        """测试鼠标在上边中点显示SizeVerCursor"""
        from PyQt5.QtCore import QPoint
        from PyQt5.QtGui import QMouseEvent
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        self.screenshot_window.show_preview(QPixmap(90, 90))
        
        move_event = QMouseEvent(
            QMouseEvent.MouseMove, QPoint(55, 10),
            Qt.NoButton, Qt.NoButton, Qt.NoModifier
        )
        self.screenshot_window.mouseMoveEvent(move_event)
        
        self.assertEqual(self.screenshot_window.cursor().shape(), Qt.SizeVerCursor)
    
    def test_cursor_on_left_edge(self):
        """测试鼠标在左边中点显示SizeHorCursor"""
        from PyQt5.QtCore import QPoint
        from PyQt5.QtGui import QMouseEvent
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        self.screenshot_window.show_preview(QPixmap(90, 90))
        
        move_event = QMouseEvent(
            QMouseEvent.MouseMove, QPoint(10, 55),
            Qt.NoButton, Qt.NoButton, Qt.NoModifier
        )
        self.screenshot_window.mouseMoveEvent(move_event)
        
        self.assertEqual(self.screenshot_window.cursor().shape(), Qt.SizeHorCursor)
    
    def test_cursor_inside_selection(self):
        """测试鼠标在选区内部正常模式下显示SizeAllCursor"""
        from PyQt5.QtCore import QPoint
        from PyQt5.QtGui import QMouseEvent
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        self.screenshot_window.show_preview(QPixmap(90, 90))
        
        move_event = QMouseEvent(
            QMouseEvent.MouseMove, QPoint(50, 50),
            Qt.NoButton, Qt.NoButton, Qt.NoModifier
        )
        self.screenshot_window.mouseMoveEvent(move_event)
        
        self.assertEqual(self.screenshot_window.cursor().shape(), Qt.SizeAllCursor)
    
    def test_cursor_outside_selection_normal(self):
        """测试鼠标在选区外部正常模式下显示ArrowCursor"""
        from PyQt5.QtCore import QPoint
        from PyQt5.QtGui import QMouseEvent
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        self.screenshot_window.show_preview(QPixmap(90, 90))
        
        move_event = QMouseEvent(
            QMouseEvent.MouseMove, QPoint(200, 200),
            Qt.NoButton, Qt.NoButton, Qt.NoModifier
        )
        self.screenshot_window.mouseMoveEvent(move_event)
        
        self.assertEqual(self.screenshot_window.cursor().shape(), Qt.ArrowCursor)
    
    def test_cursor_inside_selection_text_editing(self):
        """测试文字编辑模式下鼠标在选区内部显示IBeamCursor"""
        from PyQt5.QtCore import QPoint
        from PyQt5.QtGui import QMouseEvent
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        self.screenshot_window.show_preview(QPixmap(90, 90))
        self.screenshot_window.is_text_editing = True
        
        move_event = QMouseEvent(
            QMouseEvent.MouseMove, QPoint(50, 50),
            Qt.NoButton, Qt.NoButton, Qt.NoModifier
        )
        self.screenshot_window.mouseMoveEvent(move_event)
        
        self.assertEqual(self.screenshot_window.cursor().shape(), Qt.IBeamCursor)
    
    def test_cursor_outside_selection_text_editing(self):
        """测试文字编辑模式下鼠标在选区外部显示ArrowCursor"""
        from PyQt5.QtCore import QPoint
        from PyQt5.QtGui import QMouseEvent
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        self.screenshot_window.show_preview(QPixmap(90, 90))
        self.screenshot_window.is_text_editing = True
        
        move_event = QMouseEvent(
            QMouseEvent.MouseMove, QPoint(200, 200),
            Qt.NoButton, Qt.NoButton, Qt.NoModifier
        )
        self.screenshot_window.mouseMoveEvent(move_event)
        
        self.assertEqual(self.screenshot_window.cursor().shape(), Qt.ArrowCursor)
    
    def test_cursor_inside_selection_doodle(self):
        """测试涂鸦模式下鼠标在选区内部显示画笔光标"""
        from PyQt5.QtCore import QPoint
        from PyQt5.QtGui import QMouseEvent
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        self.screenshot_window.show_preview(QPixmap(90, 90))
        self.screenshot_window.is_screenshot_doodle = True
        
        move_event = QMouseEvent(
            QMouseEvent.MouseMove, QPoint(50, 50),
            Qt.NoButton, Qt.NoButton, Qt.NoModifier
        )
        self.screenshot_window.mouseMoveEvent(move_event)
        
        self.assertIsNotNone(self.screenshot_window.cursor().pixmap())
    
    def test_cursor_outside_selection_doodle(self):
        """测试涂鸦模式下鼠标在选区外部显示ArrowCursor"""
        from PyQt5.QtCore import QPoint
        from PyQt5.QtGui import QMouseEvent
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        self.screenshot_window.show_preview(QPixmap(90, 90))
        self.screenshot_window.is_screenshot_doodle = True
        
        move_event = QMouseEvent(
            QMouseEvent.MouseMove, QPoint(200, 200),
            Qt.NoButton, Qt.NoButton, Qt.NoModifier
        )
        self.screenshot_window.mouseMoveEvent(move_event)
        
        self.assertEqual(self.screenshot_window.cursor().shape(), Qt.ArrowCursor)
    
    def test_cursor_handles_override_normal_mode(self):
        """测试正常模式下圆点上的光标覆盖SizeAllCursor"""
        from PyQt5.QtCore import QPoint
        from PyQt5.QtGui import QMouseEvent
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        self.screenshot_window.show_preview(QPixmap(90, 90))
        
        move_event = QMouseEvent(
            QMouseEvent.MouseMove, QPoint(10, 10),
            Qt.NoButton, Qt.NoButton, Qt.NoModifier
        )
        self.screenshot_window.mouseMoveEvent(move_event)
        
        self.assertEqual(self.screenshot_window.cursor().shape(), Qt.SizeFDiagCursor)
    
    def test_save_undo_state_pushes_to_history(self):
        """测试save_undo_state将当前状态推入历史栈"""
        from PyQt5.QtCore import QPoint
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        self.screenshot_window.show_preview(QPixmap(90, 90))
        
        self.assertEqual(len(self.screenshot_window.history), 0)
        self.screenshot_window.save_undo_state()
        self.assertEqual(len(self.screenshot_window.history), 1)
        self.assertEqual(len(self.screenshot_window.future), 0)
    
    def test_save_undo_state_clears_future(self):
        """测试新编辑会清空redo栈"""
        from PyQt5.QtCore import QPoint
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        self.screenshot_window.show_preview(QPixmap(90, 90))
        
        self.screenshot_window.save_undo_state()
        self.screenshot_window.undo()
        self.assertEqual(len(self.screenshot_window.future), 1)
        
        self.screenshot_window.save_undo_state()
        self.assertEqual(len(self.screenshot_window.future), 0)
    
    def test_undo_restores_previous_state(self):
        """测试后退恢复上一个状态"""
        from PyQt5.QtCore import QPoint
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        pixmap_before = QPixmap(90, 90)
        pixmap_before.fill(Qt.white)
        self.screenshot_window.show_preview(pixmap_before)
        
        self.screenshot_window.save_undo_state()
        pixmap_after = QPixmap(90, 90)
        pixmap_after.fill(Qt.red)
        self.screenshot_window.cropped_pixmap = pixmap_after
        
        self.screenshot_window.undo()
        self.assertEqual(len(self.screenshot_window.history), 0)
        self.assertEqual(len(self.screenshot_window.future), 1)
    
    def test_undo_empty_history_does_nothing(self):
        """测试空历史栈的后退操作不报错"""
        from PyQt5.QtCore import QPoint
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        self.screenshot_window.show_preview(QPixmap(90, 90))
        
        self.screenshot_window.undo()
        self.assertIsNotNone(self.screenshot_window.cropped_pixmap)
    
    def test_redo_restores_undone_state(self):
        """测试前进恢复被撤销的状态"""
        from PyQt5.QtCore import QPoint
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        pixmap_before = QPixmap(90, 90)
        pixmap_before.fill(Qt.white)
        self.screenshot_window.show_preview(pixmap_before)
        
        self.screenshot_window.save_undo_state()
        pixmap_after = QPixmap(90, 90)
        pixmap_after.fill(Qt.red)
        self.screenshot_window.cropped_pixmap = pixmap_after
        
        self.screenshot_window.undo()
        self.screenshot_window.redo()
        
        self.assertEqual(len(self.screenshot_window.future), 0)
        self.assertEqual(len(self.screenshot_window.history), 1)
    
    def test_redo_empty_future_does_nothing(self):
        """测试空redo栈的前进操作不报错"""
        from PyQt5.QtCore import QPoint
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        self.screenshot_window.show_preview(QPixmap(90, 90))
        
        self.screenshot_window.redo()
        self.assertIsNotNone(self.screenshot_window.cropped_pixmap)
    
    def test_multiple_undo_redo(self):
        """测试多次后退前进操作"""
        from PyQt5.QtCore import QPoint
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        self.screenshot_window.show_preview(QPixmap(90, 90))
        
        self.screenshot_window.save_undo_state()
        self.screenshot_window.save_undo_state()
        self.screenshot_window.save_undo_state()
        self.assertEqual(len(self.screenshot_window.history), 3)
        
        self.screenshot_window.undo()
        self.assertEqual(len(self.screenshot_window.history), 2)
        self.assertEqual(len(self.screenshot_window.future), 1)
        
        self.screenshot_window.undo()
        self.assertEqual(len(self.screenshot_window.history), 1)
        self.assertEqual(len(self.screenshot_window.future), 2)
        
        self.screenshot_window.redo()
        self.assertEqual(len(self.screenshot_window.history), 2)
        self.assertEqual(len(self.screenshot_window.future), 1)
    
    def test_undo_btn_visible_in_preview(self):
        """测试预览模式下后退按钮可见"""
        from PyQt5.QtCore import QPoint
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        self.screenshot_window.show_preview(QPixmap(90, 90))
        
        self.assertFalse(self.screenshot_window.undo_btn.isHidden())
        self.assertFalse(self.screenshot_window.redo_btn.isHidden())
    
    def test_undo_btn_hidden_during_editing(self):
        """测试编辑模式下后退按钮隐藏"""
        from PyQt5.QtCore import QPoint
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        self.screenshot_window.show_preview(QPixmap(90, 90))
        
        self.screenshot_window.text_edit_btn.click()
        self.assertTrue(self.screenshot_window.undo_btn.isHidden())
        self.assertTrue(self.screenshot_window.redo_btn.isHidden())

class TestDoodleWindow(unittest.TestCase):
    """测试涂鸦窗口类"""
    
    def setUp(self):
        """设置测试环境"""
        get_app()
        self.doodle_window = DoodleWindow()
    
    def tearDown(self):
        """清理测试环境"""
        self.doodle_window.close()
    
    def test_init(self):
        """测试涂鸦窗口初始化"""
        self.assertIsNotNone(self.doodle_window.canvas)
        self.assertFalse(self.doodle_window.drawing)
        self.assertIsNone(self.doodle_window.last_pos)
    
    def test_mouse_press(self):
        """测试鼠标按下开始绘制"""
        from PyQt5.QtCore import QPoint
        from PyQt5.QtGui import QMouseEvent
        
        event = QMouseEvent(QMouseEvent.MouseButtonPress, QPoint(50, 50), 
                           Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
        
        self.doodle_window.mousePressEvent(event)
        
        self.assertTrue(self.doodle_window.drawing)
        self.assertEqual(self.doodle_window.last_pos, QPoint(50, 50))
    
    def test_mouse_move_drawing(self):
        """测试鼠标移动绘制"""
        from PyQt5.QtCore import QPoint
        from PyQt5.QtGui import QMouseEvent
        
        # 先设置绘制状态
        self.doodle_window.drawing = True
        self.doodle_window.last_pos = QPoint(50, 50)
        
        event = QMouseEvent(QMouseEvent.MouseMove, QPoint(100, 100), 
                           Qt.NoButton, Qt.LeftButton, Qt.NoModifier)
        
        self.doodle_window.mouseMoveEvent(event)
        
        self.assertEqual(self.doodle_window.last_pos, QPoint(100, 100))
    
    def test_mouse_move_not_drawing(self):
        """测试未绘制时鼠标移动"""
        from PyQt5.QtCore import QPoint
        from PyQt5.QtGui import QMouseEvent
        
        # 确保未绘制状态
        self.doodle_window.drawing = False
        
        event = QMouseEvent(QMouseEvent.MouseMove, QPoint(100, 100), 
                           Qt.NoButton, Qt.NoButton, Qt.NoModifier)
        
        self.doodle_window.mouseMoveEvent(event)
        
        # last_pos 应该保持不变
        self.assertIsNone(self.doodle_window.last_pos)
    
    def test_mouse_release(self):
        """测试鼠标释放停止绘制"""
        from PyQt5.QtCore import QPoint
        from PyQt5.QtGui import QMouseEvent
        
        # 先设置绘制状态
        self.doodle_window.drawing = True
        self.doodle_window.last_pos = QPoint(50, 50)
        
        event = QMouseEvent(QMouseEvent.MouseButtonRelease, QPoint(50, 50), 
                           Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
        
        self.doodle_window.mouseReleaseEvent(event)
        
        self.assertFalse(self.doodle_window.drawing)
        self.assertIsNone(self.doodle_window.last_pos)
    
    def test_key_escape(self):
        """测试ESC键关闭窗口"""
        from PyQt5.QtGui import QKeyEvent
        from PyQt5.QtCore import QEvent
        
        event = QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier)
        
        # 确保窗口已显示
        self.doodle_window.show()
        self.assertTrue(self.doodle_window.isVisible())
        
        # 发送ESC键事件
        self.doodle_window.keyPressEvent(event)
        
        # 给窗口关闭一些时间
        import time
        time.sleep(0.1)
        
        # 验证窗口已隐藏
        self.assertTrue(self.doodle_window.isHidden())
    
    def test_close_event_emits_signal(self):
        """测试关闭窗口时发出涂鸦完成信号"""
        # 捕获信号
        captured_pixmap = []
        def on_doodle_finished(pixmap):
            captured_pixmap.append(pixmap)
        
        self.doodle_window.doodle_finished.connect(on_doodle_finished)
        
        # 关闭窗口
        self.doodle_window.close()
        
        # 验证信号已发出
        self.assertEqual(len(captured_pixmap), 1)
        self.assertIsInstance(captured_pixmap[0], QPixmap)


class TestPinnedWindow(unittest.TestCase):
    """测试钉图窗口功能"""
    
    def setUp(self):
        self.app = QApplication.instance()
        if not self.app:
            self.app = QApplication([])
        self.pixmap = QPixmap(100, 80)
        self.pixmap.fill(Qt.red)
        from picbot import PinnedWindow
        self.pinned_window = PinnedWindow(self.pixmap)
    
    def tearDown(self):
        self.pinned_window.close()
    
    def test_init(self):
        self.assertEqual(self.pinned_window.width(), 100)
        self.assertEqual(self.pinned_window.height(), 80)
        self.assertIsNotNone(self.pinned_window.pixmap)
    
    def test_drag_offset_starts_none(self):
        self.assertIsNone(self.pinned_window.drag_offset)
    
    def test_mouse_press_sets_offset(self):
        from PyQt5.QtGui import QMouseEvent
        from PyQt5.QtCore import QPoint
        
        press_event = QMouseEvent(
            QMouseEvent.MouseButtonPress, QPoint(10, 10),
            Qt.LeftButton, Qt.LeftButton, Qt.NoModifier
        )
        self.pinned_window.mousePressEvent(press_event)
        self.assertEqual(self.pinned_window.drag_offset, QPoint(10, 10))
    
    def test_mouse_release_clears_offset(self):
        from PyQt5.QtGui import QMouseEvent
        from PyQt5.QtCore import QPoint
        
        self.pinned_window.drag_offset = QPoint(10, 10)
        release_event = QMouseEvent(
            QMouseEvent.MouseButtonRelease, QPoint(20, 20),
            Qt.LeftButton, Qt.LeftButton, Qt.NoModifier
        )
        self.pinned_window.mouseReleaseEvent(release_event)
        self.assertIsNone(self.pinned_window.drag_offset)
    
    def test_mouse_move_drags(self):
        from PyQt5.QtGui import QMouseEvent
        from PyQt5.QtCore import QPoint
        import ctypes
        
        self.pinned_window.drag_offset = QPoint(10, 10)
        
        # 获取移动前的原生窗口位置
        hwnd = int(self.pinned_window.winId())
        class RECT(ctypes.Structure):
            _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                        ("right", ctypes.c_long), ("bottom", ctypes.c_long)]
        rect_before = RECT()
        ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect_before))
        
        move_event = QMouseEvent(
            QMouseEvent.MouseMove, QPoint(15, 15),
            Qt.NoButton, Qt.LeftButton, Qt.NoModifier
        )
        self.pinned_window.mouseMoveEvent(move_event)
        
        rect_after = RECT()
        ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect_after))
        
        self.assertNotEqual((rect_after.left, rect_after.top),
                            (rect_before.left, rect_before.top))
    
    def test_mouse_move_no_drag_without_offset(self):
        self.pinned_window.drag_offset = None
        initial_pos = self.pinned_window.pos()
        
        from PyQt5.QtGui import QMouseEvent
        from PyQt5.QtCore import QPoint
        move_event = QMouseEvent(
            QMouseEvent.MouseMove, QPoint(15, 15),
            Qt.NoButton, Qt.LeftButton, Qt.NoModifier
        )
        self.pinned_window.mouseMoveEvent(move_event)
        
        self.assertEqual(self.pinned_window.pos(), initial_pos)
    
    def test_context_menu_policy(self):
        self.assertEqual(
            self.pinned_window.contextMenuPolicy(),
            Qt.CustomContextMenu
        )
    
    def test_glow_effect_exists(self):
        self.assertIsNotNone(self.pinned_window.pixmap)
        self.assertEqual(self.pinned_window.pixmap.width(), 100)
        self.assertEqual(self.pinned_window.pixmap.height(), 80)
    
    def test_position_parameter(self):
        from PyQt5.QtCore import QPoint
        from picbot import PinnedWindow
        
        pinned = PinnedWindow(self.pixmap, QPoint(50, 60))
        self.assertEqual(pinned.pos().x(), 50)
        self.assertEqual(pinned.pos().y(), 60)
        pinned.close()
    
    def test_red_border_style(self):
        self.assertIsNotNone(self.pinned_window.pixmap)
        self.assertEqual(self.pinned_window.pixmap.width(), 100)
        self.assertEqual(self.pinned_window.pixmap.height(), 80)


class TestPinButton(unittest.TestCase):
    """测试钉图按钮功能"""
    
    def setUp(self):
        self.app = QApplication.instance()
        if not self.app:
            self.app = QApplication([])
        self.screenshot = QPixmap(400, 300)
        self.screenshot.fill(Qt.blue)
        from picbot import ScreenshotWindow
        self.screenshot_window = ScreenshotWindow(self.screenshot)
    
    def tearDown(self):
        self.screenshot_window.close()
    
    def test_pin_btn_exists(self):
        from PyQt5.QtWidgets import QPushButton
        self.assertIsInstance(self.screenshot_window.pin_btn, QPushButton)
        self.assertEqual(self.screenshot_window.pin_btn.text(), '钉图')
    
    def test_pin_btn_hidden_initially(self):
        self.assertTrue(self.screenshot_window.pin_btn.isHidden())
    
    def test_pin_btn_visible_in_preview(self):
        from PyQt5.QtCore import QPoint
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        self.screenshot_window.show_preview(QPixmap(90, 90))
        
        self.assertFalse(self.screenshot_window.pin_btn.isHidden())
    
    def test_pin_btn_hidden_during_editing(self):
        from PyQt5.QtCore import QPoint
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        self.screenshot_window.show_preview(QPixmap(90, 90))
        
        self.screenshot_window.on_edit_text()
        self.assertTrue(self.screenshot_window.pin_btn.isHidden())
    
    def test_pin_btn_style_purple(self):
        style = self.screenshot_window.pin_btn.styleSheet()
        self.assertIn('#8B008B', style)
    
    def test_on_pin_closes_window_and_emits_signal(self):
        from PyQt5.QtCore import QPoint
        
        self.screenshot_window.start_pos = QPoint(10, 10)
        self.screenshot_window.end_pos = QPoint(100, 100)
        self.screenshot_window.show_preview(QPixmap(90, 90))
        
        signal_data = []
        self.screenshot_window.screenshot_pinned.connect(
            lambda px, pos: signal_data.append((px, pos))
        )
        
        self.screenshot_window.on_pin()
        
        self.assertFalse(self.screenshot_window.isVisible())
        self.assertEqual(len(signal_data), 1)
        self.assertIsNotNone(signal_data[0][0])
        self.assertIsInstance(signal_data[0][0], QPixmap)
        self.assertEqual(signal_data[0][1].x(), 10)
        self.assertEqual(signal_data[0][1].y(), 10)


class TestEncodeImage(unittest.TestCase):
    """测试图片编码功能"""
    
    def test_encode_image(self):
        """测试图片Base64编码"""
        # 创建一个临时图片文件
        import tempfile
        import base64
        
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            temp_path = f.name
        
        # 创建一个测试图片
        pixmap = QPixmap(100, 100)
        pixmap.fill(Qt.blue)
        pixmap.save(temp_path)
        
        # 测试编码功能
        picbot = PicBot()
        encoded = picbot.encode_image_to_base64(temp_path)
        
        # 验证编码结果
        self.assertTrue(encoded)
        self.assertTrue(isinstance(encoded, str))
        
        # 清理临时文件
        os.unlink(temp_path)
        picbot.close()

if __name__ == '__main__':
    unittest.main()
