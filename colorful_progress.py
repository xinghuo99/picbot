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
        self.setFixedSize(700, 200)

        self.dot_count = 1
        self._drag_pos = None

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)

        self.label = QLabel()
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setFont(QFont("Arial", 36))
        layout.addWidget(self.label)

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

    def update_progress(self):
        dots = ""
        for i in range(self.dot_count):
            color = COLORS[i % len(COLORS)]
            dots += f'<span style="color:{color};">●</span>'

        self.label.setText(dots)

        self.dot_count += 1
        if self.dot_count > 9:
            self.dot_count = 1


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ColorfulProgress()
    window.show()
    sys.exit(app.exec_())