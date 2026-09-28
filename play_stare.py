import os
import sys
import time
from platform_utils import get_base_dir as _platform_base_dir
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPainter, QPixmap
from PyQt5.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

def get_base_dir():
    return str(_platform_base_dir())



class MainApp(QWidget):
    def __init__(self, ready_file=None, timeout_seconds=300):
        super().__init__()
        self.ready_file = ready_file
        self.deadline = time.time() + max(1, int(timeout_seconds))
        self.setWindowTitle("Seele等待界面")
        self.setFixedSize(800, 500)
        self._background = QPixmap(os.path.join(get_base_dir(), "image", "image.png"))
        self.close_flag = False
        self.create_ui()
        self._timer = QTimer(self)
        self._timer.setInterval(100)
        self._timer.timeout.connect(self.check_close_condition)
        self._timer.start()

    def create_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.addStretch(1)
        label = QLabel("请稍等，希儿马上就好~", self)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet(
            "QLabel {"
            " background: rgba(255, 255, 255, 220);"
            " color: #111;"
            " border-radius: 8px;"
            " padding: 12px 18px;"
            " font-size: 24px;"
            " font-weight: 600;"
            "}"
        )
        layout.addWidget(label, 0, Qt.AlignHCenter)
        layout.addStretch(4)

    def hide_window(self):
        self._timer.stop()
        self.close()
        app = QApplication.instance()
        if app:
            app.quit()

    def check_close_condition(self):
        if self.close_flag:
            self.hide_window()
            return

        if self.ready_file and os.path.exists(self.ready_file):
            self.hide_window()
            return

        if time.time() >= self.deadline:
            self.hide_window()

    def set_close_flag(self, flag: bool):
        self.close_flag = flag


    def paintEvent(self, event):
        painter = QPainter(self)
        if self._background.isNull():
            painter.fillRect(self.rect(), Qt.white)
            return
        scaled = self._background.scaled(
            self.size(),
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation,
        )
        x = int((self.width() - scaled.width()) / 2)
        y = int((self.height() - scaled.height()) / 2)
        painter.drawPixmap(x, y, scaled)


def main(ready_file=None, timeout_seconds=300):
    app = QApplication.instance() or QApplication(sys.argv)
    window = MainApp(ready_file=ready_file, timeout_seconds=timeout_seconds)
    window.show()
    app.exec_()

if __name__ == "__main__":
    ready = None
    timeout = 300
    argv = sys.argv[1:]
    if argv:
        ready = argv[0]
    if len(argv) >= 2:
        try:
            timeout = int(argv[1])
        except ValueError:
            timeout = 300
    main(ready_file=ready, timeout_seconds=timeout)
