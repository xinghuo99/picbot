import sys
import logging
import os
import ctypes
from ctypes import wintypes
from PyQt5.QtWidgets import QApplication, QWidget, QHBoxLayout, QLineEdit, QPushButton, QLabel, QFileDialog, QMenu, QAction, QShortcut, QFontComboBox, QComboBox
from PyQt5.QtCore import pyqtSignal, Qt, QRect, QPoint, QRectF, QTimer
from PyQt5.QtGui import QPixmap, QScreen, QPainter, QPen, QCursor, QColor, QPolygon, QBrush, QFont, QKeySequence, QIcon, QImage

# 配置日志
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# 启用高DPI支持（必须在 QApplication 创建之前设置）
if hasattr(Qt, 'AA_EnableHighDpiScaling'):
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

# 全局快捷键常量
MOD_ALT = 0x0001
MOD_NOREPEAT = 0x4000
WM_HOTKEY = 0x0312
VK_1 = 0x31
VK_2 = 0x32
VK_3 = 0x33
VK_A = 0x41
VK_S = 0x53
VK_Q = 0x51
VK_W = 0x57
HK_SCREENSHOT = 1
HK_PASTE = 2
HK_CANCEL_SCREENSHOT = 3
HK_DOODLE = 4
HK_DOODLE_END = 5
HK_DOODLE_UNDO = 6
HK_DOODLE_REDO = 7

# 当前活跃的截图窗口引用，用于全局快捷键取消截图
_active_screenshot_window = None
# 当前活跃的涂鸦窗口引用，用于全局快捷键结束涂鸦
_active_doodle_window = None
# 独立函数创建的钉图窗口列表，防止被垃圾回收
_standalone_pinned_windows = []


def _capture_full_desktop():
    """
    使用 mss 库捕获整个虚拟桌面（所有屏幕），返回 QPixmap（逻辑坐标）。
    正确处理多屏幕、不同DPI缩放比的情况。
    
    核心原理：
    1. mss 在物理像素级别捕获每个屏幕
    2. 使用 QImage 在逻辑尺寸下拼接各屏幕截图，但以 max_dpr 倍率创建高分辨率画布
    3. 设置 devicePixelRatio 使 Qt 正确渲染高分辨率图像，避免模糊
    """
    try:
        import mss
        with mss.MSS() as sct:
            screens = QApplication.screens()
            screen_geoms = [s.geometry() for s in screens]
            all_x = min(g.x() for g in screen_geoms)
            all_y = min(g.y() for g in screen_geoms)
            total_w = max(g.x() + g.width() for g in screen_geoms) - all_x
            total_h = max(g.y() + g.height() for g in screen_geoms) - all_y

            # 计算最大 DPR，用于创建高分辨率画布
            max_dpr = max(s.devicePixelRatio() for s in screens)
            img_w = max(1, int(total_w * max_dpr))
            img_h = max(1, int(total_h * max_dpr))

            combined_img = QImage(img_w, img_h, QImage.Format_RGB32)
            combined_img.fill(Qt.black)
            painter = QPainter(combined_img)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)

            for i, s in enumerate(screens):
                geom = s.geometry()
                dpr = s.devicePixelRatio()
                phys_x = int(round(geom.x() * dpr))
                phys_y = int(round(geom.y() * dpr))
                phys_w = int(round(geom.width() * dpr))
                phys_h = int(round(geom.height() * dpr))

                mon = None
                for m in sct.monitors[1:]:
                    if (m['left'] == phys_x and m['top'] == phys_y and
                            m['width'] == phys_w and m['height'] == phys_h):
                        mon = m
                        break
                if mon is None:
                    for m in sct.monitors[1:]:
                        if (abs(m['left'] - phys_x) <= 1 and abs(m['top'] - phys_y) <= 1):
                            mon = m
                            break
                if mon is None:
                    mon = sct.monitors[i + 1] if i + 1 < len(sct.monitors) else sct.monitors[1]

                shot = sct.grab(mon)
                qimg = QImage(shot.bgra, shot.width, shot.height, shot.width * 4, QImage.Format_RGB32)
                # 缩放到高分辨率画布对应的逻辑尺寸
                target_w = max(1, int(geom.width() * max_dpr))
                target_h = max(1, int(geom.height() * max_dpr))
                qimg = qimg.scaled(target_w, target_h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
                # 绘制到组合图像的高分辨率坐标位置
                draw_x = int((geom.x() - all_x) * max_dpr)
                draw_y = int((geom.y() - all_y) * max_dpr)
                painter.drawImage(draw_x, draw_y, qimg)

            painter.end()
            pixmap = QPixmap.fromImage(combined_img)
            pixmap.setDevicePixelRatio(max_dpr)
            logging.info(f"mss 截图完成: {total_w}x{total_h} (物理: {img_w}x{img_h}, dpr: {max_dpr}), {len(screens)}个屏幕")
            return pixmap
    except Exception as e:
        logging.warning(f"mss 截图失败，回退到 grabWindow: {e}")
        return _capture_full_desktop_fallback()


def _copy_pixmap_rect(pixmap, rect):
    """
    从带有 devicePixelRatio 的 QPixmap 中正确复制子区域。
    
    PyQt5 中 QPixmap.copy(QRect) 在高 DPI 模式下可能不正确处理 devicePixelRatio，
    导致复制的物理像素区域与逻辑坐标不匹配。本函数通过 QImage 中转来避免此问题。
    """
    dpr = pixmap.devicePixelRatio()
    if abs(dpr - 1.0) < 0.01:
        return pixmap.copy(rect)
    qimg = pixmap.toImage()
    phys_rect = QRect(int(rect.x() * dpr), int(rect.y() * dpr),
                      int(rect.width() * dpr), int(rect.height() * dpr))
    cropped = qimg.copy(phys_rect)
    result = QPixmap.fromImage(cropped)
    result.setDevicePixelRatio(dpr)
    return result


def _capture_full_desktop_fallback():
    """
    回退方案：使用 QScreen.grabWindow(0) 捕获，使用 QImage 拼接。
    高分辨率画布避免 DPI 模糊。
    """
    screens = QApplication.screens()
    screen_geoms = [s.geometry() for s in screens]
    all_x = min(g.x() for g in screen_geoms)
    all_y = min(g.y() for g in screen_geoms)
    total_w = max(g.x() + g.width() for g in screen_geoms) - all_x
    total_h = max(g.y() + g.height() for g in screen_geoms) - all_y

    max_dpr = max(s.devicePixelRatio() for s in screens)
    img_w = max(1, int(total_w * max_dpr))
    img_h = max(1, int(total_h * max_dpr))

    combined_img = QImage(img_w, img_h, QImage.Format_RGB32)
    combined_img.fill(Qt.black)
    painter = QPainter(combined_img)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)

    for s in screens:
        geom = s.geometry()
        shot = s.grabWindow(0)
        dpr = s.devicePixelRatio()
        target_w = max(1, int(geom.width() * max_dpr))
        target_h = max(1, int(geom.height() * max_dpr))
        if abs(dpr - 1.0) > 0.01 and shot.width() != geom.width():
            shot = shot.scaled(target_w, target_h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        else:
            shot = shot.scaled(target_w, target_h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        qimg = shot.toImage()
        draw_x = int((geom.x() - all_x) * max_dpr)
        draw_y = int((geom.y() - all_y) * max_dpr)
        painter.drawImage(draw_x, draw_y, qimg)

    painter.end()
    pixmap = QPixmap.fromImage(combined_img)
    pixmap.setDevicePixelRatio(max_dpr)
    logging.info(f"grabWindow 截图完成: {total_w}x{total_h} (物理: {img_w}x{img_h}, dpr: {max_dpr}), {len(screens)}个屏幕")
    return pixmap


def capture_screenshot():
    """
    独立的截图函数，与主窗口无关，可在任意地方调用。
    返回截取的区域图片 QPixmap，如果取消则返回 None。
    """
    from PyQt5.QtCore import QEventLoop
    
    # 截图所有屏幕
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    screens = QApplication.screens()
    screen_geoms = [s.geometry() for s in screens]
    all_x = min(g.x() for g in screen_geoms)
    all_y = min(g.y() for g in screen_geoms)
    all_right = max(g.x() + g.width() for g in screen_geoms)
    all_bottom = max(g.y() + g.height() for g in screen_geoms)
    total_w = all_right - all_x
    total_h = all_bottom - all_y
    
    # 使用 mss 捕获整个虚拟桌面，正确处理多屏 DPI
    combined = _capture_full_desktop()
    
    result = {'pixmap': None}
    loop = QEventLoop()
    
    window = ScreenshotWindow(combined)
    
    def on_taken(pixmap):
        global _active_screenshot_window
        _active_screenshot_window = None
        result['pixmap'] = pixmap
        loop.quit()
    
    def on_canceled():
        global _active_screenshot_window
        _active_screenshot_window = None
        result['pixmap'] = None
        loop.quit()
    
    def on_pinned(pixmap, pos):
        global _active_screenshot_window, _standalone_pinned_windows
        _active_screenshot_window = None
        pinned = PinnedWindow(pixmap, pos)
        pinned.show()
        _standalone_pinned_windows.append(pinned)
        result['pixmap'] = None
        loop.quit()
    
    window.screenshot_taken.connect(on_taken)
    window.screenshot_canceled.connect(on_canceled)
    window.screenshot_pinned.connect(on_pinned)
    window.setGeometry(all_x, all_y, total_w, total_h)
    
    global _active_screenshot_window
    _active_screenshot_window = window
    window.show()
    window.raise_()
    window.activateWindow()
    
    loop.exec_()
    return result['pixmap']


def start_doodle(pixmap):
    """
    独立的涂鸦函数，与主窗口无关，可在任意地方调用。
    传入原始图片 QPixmap，返回涂鸦后的图片 QPixmap。
    """
    from PyQt5.QtCore import QEventLoop
    
    result = {'pixmap': None}
    loop = QEventLoop()
    
    window = DoodleWindow(pixmap)
    
    def on_finished(doodled):
        global _active_doodle_window
        _active_doodle_window = None
        result['pixmap'] = doodled
        loop.quit()
    
    window.doodle_finished.connect(on_finished)
    
    # 窗口覆盖所有屏幕，与 pixmap 尺寸对齐
    screens = QApplication.screens()
    screen_geoms = [s.geometry() for s in screens]
    all_x = min(g.x() for g in screen_geoms)
    all_y = min(g.y() for g in screen_geoms)
    all_right = max(g.x() + g.width() for g in screen_geoms)
    all_bottom = max(g.y() + g.height() for g in screen_geoms)
    window.setGeometry(all_x, all_y, all_right - all_x, all_bottom - all_y)
    
    global _active_doodle_window
    _active_doodle_window = window
    window.show()
    window.raise_()
    window.activateWindow()
    window.toolbar.show_at_mouse_screen()
    
    loop.exec_()
    return result['pixmap']


class HotkeyManager(QWidget):
    """不可见的全局快捷键管理器"""

    def __init__(self):
        super().__init__()
        self._hotkeys_registered = False
        self._last_captured = None

    def register_hotkeys(self):
        """注册全局快捷键"""
        if self._hotkeys_registered:
            return
        try:
            hwnd = int(self.winId())
            if hwnd == 0:
                logging.warning("窗口句柄无效，无法注册全局快捷键")
                return
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            flags = MOD_ALT | MOD_NOREPEAT
            hotkeys = [
                (HK_SCREENSHOT, VK_1, "ALT+1"),
                (HK_PASTE, VK_2, "ALT+2"),
                (HK_CANCEL_SCREENSHOT, VK_3, "ALT+3"),
                (HK_DOODLE, VK_Q, "ALT+Q"),
                (HK_DOODLE_END, VK_W, "ALT+W"),
                (HK_DOODLE_UNDO, VK_A, "ALT+A"),
                (HK_DOODLE_REDO, VK_S, "ALT+S"),
            ]
            failed = []
            for hk_id, vk, name in hotkeys:
                if not user32.RegisterHotKey(hwnd, hk_id, flags, vk):
                    err = kernel32.GetLastError()
                    failed.append(name + "(错误码" + str(err) + ")")
                else:
                    logging.info("全局快捷键 " + name + " 注册成功")
            if failed:
                logging.warning("全局快捷键注册失败: " + ", ".join(failed))
            else:
                logging.info("全部全局快捷键注册成功")
            self._hotkeys_registered = True
        except Exception as e:
            logging.warning("注册全局快捷键异常: " + str(e))

    def unregister_hotkeys(self):
        """注销全局快捷键"""
        if not self._hotkeys_registered:
            return
        try:
            hwnd = int(self.winId())
            user32 = ctypes.windll.user32
            for hk_id in [HK_SCREENSHOT, HK_PASTE, HK_CANCEL_SCREENSHOT, HK_DOODLE, HK_DOODLE_END, HK_DOODLE_UNDO, HK_DOODLE_REDO]:
                user32.UnregisterHotKey(hwnd, hk_id)
            self._hotkeys_registered = False
        except Exception:
            pass

    def nativeEvent(self, eventType, message):
        """处理 Windows 原生事件，捕获全局快捷键"""
        if eventType == b"windows_generic_MSG":
            class MSG(ctypes.Structure):
                _fields_ = [
                    ("hwnd", wintypes.HWND),
                    ("message", wintypes.UINT),
                    ("wParam", wintypes.WPARAM),
                    ("lParam", wintypes.LPARAM),
                    ("time", wintypes.DWORD),
                    ("pt_x", wintypes.LONG),
                    ("pt_y", wintypes.LONG),
                ]
            msg = ctypes.cast(ctypes.c_void_p(int(message)), ctypes.POINTER(MSG))
            if msg.contents.message == WM_HOTKEY:
                hotkey_id = msg.contents.wParam
                logging.info("收到全局快捷键事件: id=" + str(hotkey_id))
                QTimer.singleShot(0, lambda hid=hotkey_id: self._on_hotkey(hid))
                return True, 0
        return False, 0

    def _on_hotkey(self, hotkey_id):
        """处理全局快捷键事件"""
        logging.info("处理全局快捷键: id=" + str(hotkey_id))
        if hotkey_id == HK_SCREENSHOT:
            self._hotkey_screenshot()
        elif hotkey_id == HK_PASTE:
            self._hotkey_paste()
        elif hotkey_id == HK_CANCEL_SCREENSHOT:
            self._hotkey_cancel_screenshot()
        elif hotkey_id == HK_DOODLE:
            self._hotkey_doodle()
        elif hotkey_id == HK_DOODLE_END:
            self._hotkey_doodle_end()
        elif hotkey_id == HK_DOODLE_UNDO:
            self._hotkey_doodle_undo()
        elif hotkey_id == HK_DOODLE_REDO:
            self._hotkey_doodle_redo()

    def _hotkey_screenshot(self):
        """ALT+1: 截图"""
        capture_screenshot()

    def _hotkey_paste(self):
        """ALT+2: 从剪贴板获取图片"""
        clipboard = QApplication.clipboard()
        pixmap = clipboard.pixmap()
        if pixmap and not pixmap.isNull():
            self._last_captured = pixmap

    def _hotkey_cancel_screenshot(self):
        """ALT+3: 取消/退出截图，并关闭所有钉图窗口"""
        global _active_screenshot_window, _standalone_pinned_windows
        if _active_screenshot_window and _active_screenshot_window.isVisible():
            _active_screenshot_window.close()
            _active_screenshot_window = None
        for w in _standalone_pinned_windows:
            if w is not None and w.isVisible():
                w.close()
        _standalone_pinned_windows.clear()

    def _hotkey_doodle(self):
        """ALT+Q: 开始涂鸦"""
        combined = _capture_full_desktop()
        start_doodle(combined)

    def _hotkey_doodle_end(self):
        """ALT+W: 结束涂鸦"""
        global _active_doodle_window
        if _active_doodle_window and _active_doodle_window.isVisible():
            _active_doodle_window.close()

    def _hotkey_doodle_undo(self):
        """ALT+A: 涂鸦撤销"""
        global _active_doodle_window, _active_screenshot_window
        if _active_doodle_window and _active_doodle_window.isVisible():
            _active_doodle_window.undo()
            return
        if _active_screenshot_window and _active_screenshot_window.isVisible() and _active_screenshot_window.is_screenshot_doodle:
            _active_screenshot_window.undo()

    def _hotkey_doodle_redo(self):
        """ALT+S: 涂鸦重做"""
        global _active_doodle_window, _active_screenshot_window
        if _active_doodle_window and _active_doodle_window.isVisible():
            _active_doodle_window.redo()
            return
        if _active_screenshot_window and _active_screenshot_window.isVisible() and _active_screenshot_window.is_screenshot_doodle:
            _active_screenshot_window.redo()

    def closeEvent(self, event):
        self.unregister_hotkeys()
        event.accept()


class PinnedWindow(QWidget):
    def __init__(self, pixmap, pos=None):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        
        self.original_pixmap = pixmap
        self.pixmap = pixmap
        self.drag_offset = None
        
        # 使用 pixmap 原始尺寸，不做 DPI 缩放，避免跨屏 setGeometry 冲突
        #self.resize(pixmap.width(), pixmap.height())
        dpr = pixmap.devicePixelRatio()
        self.resize(int(pixmap.width() / dpr), int(pixmap.height() / dpr))
        
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
        
        painter.drawPixmap(self.rect(), self.original_pixmap)
        
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
            self.move(event.globalPos() - self.drag_offset)
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_offset = None
    
    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta > 0:
            factor = 1.1
        else:
            factor = 0.9
        new_w = int(self.width() * factor)
        new_h = int(self.height() * factor)
        # 限制最小/最大尺寸，基于原始图片尺寸
        orig_w = self.original_pixmap.width()
        orig_h = self.original_pixmap.height()
        min_w = max(10, int(orig_w * 0.05))
        min_h = max(10, int(orig_h * 0.05))
        max_w = max(min_w + 1, int(orig_w * 5.0))
        max_h = max(min_h + 1, int(orig_h * 5.0))
        new_w = max(min_w, min(new_w, max_w))
        new_h = max(min_h, min(new_h, max_h))
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
        self.doodle_window = None
        self.is_dragging = False
        self.drag_offset = None
        self.history = []
        self.future = []
        self.max_history = 50
        self.edit_layer = None
        self.text_font = QFont('Microsoft YaHei')
        self.text_font.setPixelSize(20)
        self.text_font.setBold(True)
        self.text_color = QColor(Qt.red)
        self.text_size = 20
        self._style_btn_active = False
        self._finalizing = False
        self.is_resizing = False
        self.resize_corner = None
        self.resize_opposite = None
        self.setMouseTracking(True)
        self.initUI()
    
    def initUI(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setStyleSheet("background-color: transparent;")
        #self.setStyleSheet("background-color: rgba(0, 0, 0, 0.3);")
        
        # 设置红色十字光标
        crosshair_pixmap = QPixmap(32, 32)
        crosshair_pixmap.fill(Qt.transparent)
        ch_painter = QPainter(crosshair_pixmap)
        ch_painter.setPen(QPen(QColor(255, 0, 0), 2))
        ch_painter.drawLine(16, 0, 16, 32)
        ch_painter.drawLine(0, 16, 32, 16)
        ch_painter.end()
        self.setCursor(QCursor(crosshair_pixmap, 16, 16))

        
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
        
        # 截图内涂鸦颜色下拉框
        self._doodle_colors = [
            ('大红', '#FF0000'), ('赤', '#E60000'), ('橙', '#FF7F00'), ('黄', '#FFFF00'),
            ('绿', '#00FF00'), ('青', '#00FFFF'), ('蓝', '#0000FF'), ('紫', '#8B00FF'),
            ('黑', '#000000'), ('白', '#FFFFFF'), ('粉红', '#FFC0CB'), ('砖红', '#B22222'),
            ('酒红', '#8B0000'), ('浅绿', '#90EE90'), ('浅蓝', '#ADD8E6'),
        ]
        self.doodle_color_combo = QComboBox(self)
        self.doodle_color_combo.setStyleSheet(
            "QComboBox { background-color: #333; color: white; border: 1px solid #555; "
            "padding: 4px 8px; font-size: 12px; min-width: 70px; }"
            "QComboBox::drop-down { border: none; }"
            "QComboBox QAbstractItemView { background-color: #333; color: white; selection-background-color: #555; }"
        )
        for name, hex_color in self._doodle_colors:
            pixmap = QPixmap(16, 16)
            pixmap.fill(QColor(hex_color))
            self.doodle_color_combo.addItem(QIcon(pixmap), name)
        self.doodle_color_combo.setCurrentIndex(0)
        self.doodle_color_combo.currentIndexChanged.connect(self._on_doodle_color_changed)
        self.doodle_color_combo.hide()
        
        # 截图内涂鸦线条粗细下拉框
        self.doodle_width_combo = QComboBox(self)
        self.doodle_width_combo.setStyleSheet(
            "QComboBox { background-color: #333; color: white; border: 1px solid #555; "
            "padding: 4px 8px; font-size: 12px; min-width: 55px; }"
            "QComboBox::drop-down { border: none; }"
            "QComboBox QAbstractItemView { background-color: #333; color: white; selection-background-color: #555; }"
        )
        self.doodle_width_combo.addItems([str(i) for i in range(1, 21)])
        self.doodle_width_combo.setCurrentIndex(4)  # 默认 5
        self.doodle_width_combo.currentIndexChanged.connect(self._on_doodle_width_changed)
        self.doodle_width_combo.hide()
        
        self._doodle_pen_color = QColor('#FF0000')
        self._doodle_pen_width = 5
        
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
        
        self.end_edit_btn = QPushButton('结束编辑', self)
        self.end_edit_btn.setStyleSheet("background-color: #4169E1; color: white; border: none; padding: 8px 16px; font-size: 14px;")
        self.end_edit_btn.clicked.connect(self.on_end_edit)
        self.end_edit_btn.hide()
        
        self.font_btn = QFontComboBox(self)
        self.font_btn.setStyleSheet("background-color: #2E8B57; color: white; border: none; padding: 4px 8px; font-size: 12px;")
        self.font_btn.currentFontChanged.connect(self.on_font_changed)
        self.font_btn.activated.connect(self._on_style_btn_pressed)
        self.font_btn.hide()
        
        # 预设颜色列表: (名称, 颜色值)
        self._preset_colors = [
            ('赤', '#FF0000'), ('橙', '#FF7F00'), ('黄', '#FFFF00'),
            ('绿', '#00FF00'), ('青', '#00FFFF'), ('蓝', '#0000FF'),
            ('紫', '#8B00FF'), ('粉', '#FFC0CB'), ('黑', '#000000'),
            ('白', '#FFFFFF'), ('酒红', '#8B0000'), ('砖红', '#B22222'),
        ]
        
        self.color_btn = QComboBox(self)
        self.color_btn.setStyleSheet("background-color: #CD853F; color: white; border: none; padding: 4px 8px; font-size: 12px;")
        for name, hex_color in self._preset_colors:
            pixmap = QPixmap(16, 16)
            pixmap.fill(QColor(hex_color))
            self.color_btn.addItem(QIcon(pixmap), name)
        self.color_btn.activated.connect(self._on_style_btn_pressed)
        self.color_btn.currentTextChanged.connect(self.on_color_changed)
        self.color_btn.hide()
        
        self.size_btn = QComboBox(self)
        self.size_btn.setStyleSheet("background-color: #8B4513; color: white; border: none; padding: 4px 8px; font-size: 12px;")
        self.size_btn.addItems(['8', '10', '12', '14', '16', '18', '20', '24', '28', '32', '36', '48', '64', '72'])
        self.size_btn.setCurrentText('20')
        self.size_btn.currentTextChanged.connect(self.on_size_changed)
        self.size_btn.activated.connect(self._on_style_btn_pressed)
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
            dpr = cropped_pixmap.devicePixelRatio()
            w = int(cropped_pixmap.width() * dpr)
            h = int(cropped_pixmap.height() * dpr)
            edit_img = QImage(w, h, QImage.Format_ARGB32)
            edit_img.fill(Qt.transparent)
            self.edit_layer = QPixmap.fromImage(edit_img)
            self.edit_layer.setDevicePixelRatio(dpr)
        
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
        
        self._update_undo_redo_buttons()
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
        self.end_edit_btn.hide()
        self.doodle_color_combo.hide()
        self.doodle_width_combo.hide()
    
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
        self.end_edit_btn.hide()
        self.doodle_color_combo.hide()
        self.doodle_width_combo.hide()
    
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
                self.save_undo_state()
                self.finalize_text()
            self.is_text_editing = False
            self.setCursor(Qt.ArrowCursor)
            self._hide_text_style_buttons()
            self.show_buttons()
            return
        if self.is_screenshot_doodle:
            self.is_screenshot_doodle = False
            self.doodle_last_pos = None
            self.doodle_btn.setText('涂鸦')
            self.setCursor(Qt.ArrowCursor)
        self.is_text_editing = True
        self.hide_buttons()
        self._show_text_style_buttons()
        self.setCursor(Qt.IBeamCursor)
    
    def on_end_edit(self):
        """结束编辑按钮：结束文本编辑，返回到截图区域并显示按钮"""
        if self.is_text_editing:
            if self.text_input and self.text_input.isVisible():
                self._finalizing = True
                try:
                    self.save_undo_state()
                    self.finalize_text()
                finally:
                    self._finalizing = False
            self.is_text_editing = False
            self.setCursor(Qt.ArrowCursor)
            self._hide_text_style_buttons()
            self.show_buttons()
    
    def finalize_text(self):
        text = self.text_input.text()
        if text and self.text_input_pos:
            # 使用与 text_input 相同的位置和尺寸绘制文字，确保对齐
            text_rect = QRectF(self.text_input_pos.x(), self.text_input_pos.y(),
                               self.text_input.width(), self.text_input.height())
            painter = QPainter(self.cropped_pixmap)
            painter.setFont(self.text_font)
            painter.setPen(QPen(self.text_color))
            painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter | Qt.TextWordWrap, text)
            painter.end()
            if self.edit_layer:
                painter = QPainter(self.edit_layer)
                painter.setFont(self.text_font)
                painter.setPen(QPen(self.text_color))
                painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter | Qt.TextWordWrap, text)
                painter.end()
        self.cropped_pixmap_original = None
        self.text_input.hide()
        self.update()
    
    def on_text_input_finished(self):
        self._finalizing = True
        try:
            self.save_undo_state()
            self.finalize_text()
        finally:
            self._finalizing = False
    
    def on_text_input_changed(self, text):
        # 不再实时在截图上预览文字，只在编辑框中显示
        pass
    
    def on_font_changed(self, font):
        """字体选择框变化时立即生效"""
        self.text_font = QFont(font)
        self.text_font.setPixelSize(self.text_size)
        self._apply_text_style()
    
    def on_size_changed(self, text):
        """字号选择框变化时立即生效"""
        if text:
            self.text_size = int(text)
            self.text_font.setPixelSize(self.text_size)
            self._apply_text_style()
    
    def on_color_changed(self, name):
        """颜色选择框变化时立即生效"""
        if name:
            for cname, hex_color in self._preset_colors:
                if cname == name:
                    self.text_color = QColor(hex_color)
                    self._apply_text_style()
                    break
    
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
        btn_height = 36
        spacing = 5
        
        if btn_y + btn_height * 2 + spacing > self.height():
            btn_y = select_rect.top() - btn_height * 2 - spacing - 10
        
        font_width = 140
        color_width = 70
        size_width = 60
        total_width = font_width + color_width + size_width + spacing * 2
        start_x = select_rect.center().x() - total_width // 2
        
        row2_y = btn_y + btn_height + spacing
        
        self.font_btn.setGeometry(start_x, row2_y, font_width, btn_height)
        self.color_btn.setGeometry(start_x + font_width + spacing, row2_y, color_width, btn_height)
        self.size_btn.setGeometry(start_x + font_width + color_width + spacing * 2, row2_y, size_width, btn_height)
        self.font_btn.show()
        self.color_btn.show()
        self.size_btn.show()
        
        # 结束编辑按钮放在第一行居中
        end_edit_width = 120
        end_edit_x = select_rect.center().x() - end_edit_width // 2
        self.end_edit_btn.setGeometry(end_edit_x, btn_y, end_edit_width, btn_height)
        self.end_edit_btn.show()
    
    def _hide_text_style_buttons(self):
        self.font_btn.hide()
        self.color_btn.hide()
        self.size_btn.hide()
        self.end_edit_btn.hide()
    
    def save_undo_state(self):
        if self.cropped_pixmap:
            edit_copy = self.edit_layer.copy() if self.edit_layer else None
            self.history.append((self.cropped_pixmap.copy(), edit_copy))
            if len(self.history) > self.max_history:
                self.history.pop(0)
            self.future.clear()
            self._update_undo_redo_buttons()
    
    def undo(self):
        if not self.history:
            return
        edit_copy = self.edit_layer.copy() if self.edit_layer else None
        self.future.append((self.cropped_pixmap.copy(), edit_copy))
        self.cropped_pixmap, self.edit_layer = self.history.pop()
        self.is_text_editing = False
        if self.text_input and self.text_input.isVisible():
            self.text_input.hide()
        self._update_undo_redo_buttons()
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
        self._update_undo_redo_buttons()
        self.update()
    
    def _update_undo_redo_buttons(self):
        """更新后退/前进按钮的颜色状态"""
        gray_style = "background-color: #555555; color: white; border: none; padding: 8px 16px; font-size: 14px;"
        if self.history:
            self.undo_btn.setStyleSheet("background-color: #CC3333; color: white; border: none; padding: 8px 16px; font-size: 14px;")
        else:
            self.undo_btn.setStyleSheet(gray_style)
        if self.future:
            self.redo_btn.setStyleSheet("background-color: #33AA33; color: white; border: none; padding: 8px 16px; font-size: 14px;")
        else:
            self.redo_btn.setStyleSheet(gray_style)
    
    def eventFilter(self, obj, event):
        if obj == self.text_input:
            from PyQt5.QtCore import QEvent
            if event.type() == QEvent.FocusOut:
                if not self._style_btn_active:
                    if not self._finalizing:
                        self.save_undo_state()
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
            
            # 隐藏按钮，显示涂鸦按钮和下拉框
            self.hide_buttons()
            self.doodle_btn.show()
            
            # 定位并显示颜色和粗细下拉框
            select_rect = self.get_rect()
            doodle_geo = self.doodle_btn.geometry()
            combo_y = doodle_geo.y()
            combo_x = doodle_geo.x() + doodle_geo.width() + 5
            self.doodle_color_combo.setGeometry(combo_x, combo_y, 70, 36)
            self.doodle_width_combo.setGeometry(combo_x + 75, combo_y, 55, 36)
            self.doodle_color_combo.show()
            self.doodle_width_combo.show()
            
            self.setCursor(self.create_pen_cursor())
        else:
            # 结束涂鸦
            self.is_screenshot_doodle = False
            self.doodle_btn.setText('涂鸦')
            self.doodle_last_pos = None
            self.doodle_color_combo.hide()
            self.doodle_width_combo.hide()
            self.show_buttons()
    
    def _on_doodle_color_changed(self, index):
        _, hex_color = self._doodle_colors[index]
        self._doodle_pen_color = QColor(hex_color)
        self.setCursor(self.create_pen_cursor())
    
    def _on_doodle_width_changed(self, index):
        self._doodle_pen_width = index + 1
    
    def create_pen_cursor(self):
        cursor_size = 40
        cursor_pixmap = QPixmap(cursor_size, cursor_size)
        cursor_pixmap.fill(Qt.transparent)
        
        painter = QPainter(cursor_pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        pen_color = QColor(self._doodle_pen_color)
        body_color = pen_color.lighter(160)
        
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
        
        painter.setBrush(QBrush(pen_color.lighter(130)))
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
        
        if doodle_pixmap:
            doodle_crop = _copy_pixmap_rect(doodle_pixmap, select_rect)
            painter = QPainter(self.cropped_pixmap)
            painter.drawPixmap(0, 0, doodle_crop)
            painter.end()
            if self.edit_layer:
                painter = QPainter(self.edit_layer)
                painter.drawPixmap(0, 0, doodle_crop)
                painter.end()
        
        self.is_screenshot_doodle = False
        self.doodle_last_pos = None
        self.doodle_btn.setText('涂鸦')
        self.doodle_window = None
        
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
                painter.setPen(QPen(Qt.red, 2))
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
                    self.text_input_pos = QPoint(event.pos().x() - select_rect.x(), event.pos().y() - select_rect.y())
                    self.text_input.move(event.pos())
                    self.text_input.clear()
                    self.text_input.show()
                    self.text_input.setFocus()
                    self._apply_text_style()
                    return
                self.cropped_pixmap_original = self.cropped_pixmap.copy()
                self.text_input_pos = QPoint(event.pos().x() - select_rect.x(), event.pos().y() - select_rect.y())
                self.text_input.move(event.pos())
                self.text_input.clear()
                self.text_input.show()
                self.text_input.setFocus()
                self._apply_text_style()
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
                new_screen = _copy_pixmap_rect(self.screenshot, new_rect)
                dpr = new_screen.devicePixelRatio()
                w = int(new_screen.width() * dpr)
                h = int(new_screen.height() * dpr)
                edit_img = QImage(w, h, QImage.Format_ARGB32)
                edit_img.fill(Qt.transparent)
                self.edit_layer = QPixmap.fromImage(edit_img)
                self.edit_layer.setDevicePixelRatio(dpr)
                self.show_preview(new_screen, reset_edit_layer=False)
            return
        if self.is_screenshot_doodle and self.cropped_pixmap and self.doodle_last_pos:
            select_rect = self.get_rect()
            if select_rect.contains(event.pos()):
                current_pos = QPoint(event.pos().x() - select_rect.x(), event.pos().y() - select_rect.y())
                pen = QPen(self._doodle_pen_color, self._doodle_pen_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
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
            new_screen = _copy_pixmap_rect(self.screenshot, new_rect)
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
                cropped_pixmap = _copy_pixmap_rect(self.screenshot, rect)
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
        self.setCursor(Qt.ArrowCursor)
        event.accept()


class DoodleToolbar(QWidget):
    """涂鸦工具栏：封装颜色和线条粗细下拉框，支持拖动和光标切换
    
    作为 DoodleWindow 的子控件，始终渲染在涂鸦画布之上，不会被点击涂鸦时的窗口激活压到下层。
    """
    color_changed = pyqtSignal(QColor)
    width_changed = pyqtSignal(int)
    
    _DOODLE_COLORS = [
        ('赤', '#E60000'), ('橙', '#FF7F00'), ('黄', '#FFFF00'),
        ('绿', '#00FF00'), ('青', '#00FFFF'), ('蓝', '#0000FF'),
        ('紫', '#8B00FF'), ('粉', '#FFC0CB'), ('黑', '#000000'),
        ('白', '#FFFFFF'), ('棕', '#8B4513'), ('砖红', '#B22222'),
        ('大红', '#FF0000'), ('酒红', '#8B0000'),
    ]
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # 作为普通子控件，不需要窗口标志
        self.setStyleSheet("background-color: #2A2A2A; border-radius: 4px;")
        self.setCursor(Qt.ArrowCursor)
        self._drag_offset = None
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)
        
        # 颜色下拉框
        self.color_combo = QComboBox()
        self.color_combo.setStyleSheet(
            "QComboBox { background-color: #333; color: white; border: 1px solid #555; "
            "padding: 4px 8px; font-size: 12px; min-width: 80px; }"
            "QComboBox::drop-down { border: none; }"
            "QComboBox QAbstractItemView { background-color: #333; color: white; selection-background-color: #555; }"
        )
        for name, hex_color in self._DOODLE_COLORS:
            pixmap = QPixmap(16, 16)
            pixmap.fill(QColor(hex_color))
            self.color_combo.addItem(QIcon(pixmap), name)
        self.color_combo.setCurrentIndex(0)
        self.color_combo.currentIndexChanged.connect(self._on_color_changed)
        layout.addWidget(self.color_combo)
        
        # 线条粗细下拉框
        self.width_combo = QComboBox()
        self.width_combo.setStyleSheet(
            "QComboBox { background-color: #333; color: white; border: 1px solid #555; "
            "padding: 4px 8px; font-size: 12px; min-width: 60px; }"
            "QComboBox::drop-down { border: none; }"
            "QComboBox QAbstractItemView { background-color: #333; color: white; selection-background-color: #555; }"
        )
        self.width_combo.addItems([str(i) for i in range(1, 21)])
        self.width_combo.setCurrentIndex(4)
        self.width_combo.currentIndexChanged.connect(self._on_width_changed)
        layout.addWidget(self.width_combo)
        
        self.adjustSize()
    
    def _on_color_changed(self, index):
        _, hex_color = self._DOODLE_COLORS[index]
        self.color_changed.emit(QColor(hex_color))
    
    def _on_width_changed(self, index):
        self.width_changed.emit(index + 1)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_offset = event.pos()
    
    def mouseMoveEvent(self, event):
        if self._drag_offset is not None and self.parent() is not None:
            # 转换为父控件（DoodleWindow）的本地坐标
            parent_pos = self.parent().mapFromGlobal(event.globalPos())
            self.move(parent_pos - self._drag_offset)
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_offset = None
    
    def show_at_mouse_screen(self):
        """定位到当前鼠标所在屏幕的右上角（父控件本地坐标）"""
        cursor_pos = QCursor.pos()
        screen = QApplication.screenAt(cursor_pos)
        if screen is None:
            screen = QApplication.primaryScreen()
        geo = screen.geometry()
        margin = 10
        # 目标屏幕坐标
        sx = geo.right() - self.width() - margin
        sy = geo.top() + margin
        # 转换为父控件（DoodleWindow）的本地坐标
        if self.parent() is not None:
            parent_pos = self.parent().mapFromGlobal(QPoint(sx, sy))
            self.move(parent_pos)
        else:
            self.move(sx, sy)
        self.show()


class DoodleWindow(QWidget):
    doodle_finished = pyqtSignal(QPixmap)
    
    def __init__(self, screen_shot=None, transparent_mode=False):
        super().__init__()
        self.screen_shot = screen_shot
        self.transparent_mode = transparent_mode
        self.initUI()
        self.last_pos = None
        self.drawing = False
        self.history = []
        self.future = []
        self.max_history = 50
    
    def initUI(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setStyleSheet("background-color: transparent;")
        
        if self.transparent_mode:
            # 透明模式：画布只包含涂鸦笔迹，窗口透明显示下层内容
            w = self.screen_shot.width() if self.screen_shot else 1920
            h = self.screen_shot.height() if self.screen_shot else 1080
            self.canvas = QPixmap(w, h)
            self.canvas.fill(Qt.transparent)
        elif self.screen_shot:
            self.canvas = self.screen_shot.copy()
        else:
            # 使用 mss 捕获整个虚拟桌面，正确处理多屏 DPI
            self.canvas = _capture_full_desktop()
        
        self.pen_color = Qt.red
        self.pen_width = 5
        
        # 创建涂鸦工具栏（作为子控件，始终渲染在画布之上）
        self.toolbar = DoodleToolbar(self)
        self.toolbar.color_changed.connect(self._on_toolbar_color_changed)
        self.toolbar.width_changed.connect(self._on_toolbar_width_changed)
        
        self.setCursor(self.create_pen_cursor())
    
    def _on_toolbar_color_changed(self, color):
        self.pen_color = color
        self.setCursor(self.create_pen_cursor())
    
    def _on_toolbar_width_changed(self, width):
        self.pen_width = width
        self.setCursor(self.create_pen_cursor())
    
    def create_pen_cursor(self):
        # 创建一个更大更形象的画笔形状自定义光标
        cursor_size = 40
        cursor_pixmap = QPixmap(cursor_size, cursor_size)
        cursor_pixmap.fill(Qt.transparent)
        
        painter = QPainter(cursor_pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 画笔主体颜色
        pen_color = QColor(self.pen_color)
        body_color = pen_color.lighter(160)  # 笔杆使用选中颜色的浅色版本
        
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
        highlight_color = pen_color.lighter(150)
        painter.setBrush(QBrush(highlight_color))
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
            self.history.append(self.canvas.copy())
            if len(self.history) > self.max_history:
                self.history.pop(0)
            self.future.clear()
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
    
    def undo(self):
        if not self.history:
            return
        self.future.append(self.canvas.copy())
        self.canvas = self.history.pop()
        self.update()
    
    def redo(self):
        if not self.future:
            return
        self.history.append(self.canvas.copy())
        self.canvas = self.future.pop()
        self.update()
    
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
        manager = HotkeyManager()
        manager.register_hotkeys()
        print("全局快捷键已注册，程序在后台运行...")
        print("ALT+1: 截图 | ALT+2: 粘贴 | ALT+3: 取消 | ALT+Q: 涂鸦 | ALT+W: 结束涂鸦 | ALT+A: 撤销 | ALT+S: 重做")
        sys.exit(app.exec_())
    except Exception as e:
        print(f"错误：{str(e)}")
        import traceback
        traceback.print_exc()

