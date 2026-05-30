import sys
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont

COLORS = [
    "#FF0000", "#FF4500", "#FF8C00", "#FFD700",
    "#32CD32", "#00CED1", "#1E90FF", "#8A2BE2",
    "#FF1493",
]

class ColorfulProgress(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(700, 280)

        self.dot_count = 1
        self._drag_pos = None

        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        font = QFont("Arial", 36)

        self.label_center = QLabel()
        self.label_center.setAlignment(Qt.AlignCenter)
        self.label_center.setFont(font)
        layout.addWidget(self.label_center)

        self.label_left = QLabel()
        self.label_left.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.label_left.setFont(font)
        layout.addWidget(self.label_left)

        self.label_right = QLabel()
        self.label_right.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.label_right.setFont(font)
        layout.addWidget(self.label_right)

        self.setLayout(layout)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_progress)
        self.timer.start(200)

        self.update_progress()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self._drag_pos is not None:
            self.move(event.globalPos() - self._drag_pos)

    def mouseDoubleClickEvent(self, event):
        self.close()

    def _build_dots(self):
        dots = ""
        for i in range(self.dot_count):
            color = COLORS[i % len(COLORS)]
            dots += f'<span style="color:{color};">●</span>'
        return dots

    def update_progress(self):
        dots = self._build_dots()
        self.label_center.setText(dots)
        self.label_left.setText(dots)
        self.label_right.setText(dots)

        self.dot_count += 1
        if self.dot_count > 9:
            self.dot_count = 1


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ColorfulProgress()
    window.show()
    sys.exit(app.exec_())