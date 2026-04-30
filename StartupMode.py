import sys
import os
import write_file
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QPainterPath
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QMessageBox, QLabel, QFrame


def get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


class main(QWidget):
    def __init__(self) -> None:
        super(main, self).__init__()
        self.setWindowTitle("启动方式")
        self.setWindowIcon(QIcon(os.path.join(get_base_dir(), "image", "bs_icon.ico")))
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self._drag_pos = None
        self._bg = QPixmap(os.path.join(get_base_dir(), "image", "bs.png"))
        self.resize(800, 750)
        self.setMinimumSize(800, 750)
        self.ui()

    def ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(18, 18, 18, 18)
        root_layout.setSpacing(14)

        self.card = QFrame(self)
        self.card.setObjectName("startup_card")
        self.card.setStyleSheet(
            "#startup_card { background-color: rgba(255, 255, 255, 210); border-radius: 22px; }"
            "QLabel { color: #111; }"
            "QPushButton { border-radius: 18px; padding: 14px 22px; font-size: 24px; }"
        )

        main_layout = QVBoxLayout(self.card)
        main_layout.setContentsMargins(32, 28, 32, 28)
        main_layout.setSpacing(24)

        title = QLabel("启动方式", self.card)
        title.setStyleSheet("font-size: 26px; font-weight: 600;")
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        tip = QLabel("请选择默认启动模式", self.card)
        tip.setStyleSheet("font-size: 24px;")
        tip.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(tip)

        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(20)
        fast_btn = QPushButton("快启动", self.card)
        fast_btn.setMinimumHeight(88)
        fast_btn.clicked.connect(self.YesEvent)
        slow_btn = QPushButton("慢启动", self.card)
        slow_btn.setMinimumHeight(88)
        slow_btn.clicked.connect(self.hide_event)
        btn_layout.addWidget(fast_btn)
        btn_layout.addWidget(slow_btn)

        main_layout.addStretch(1)
        main_layout.addLayout(btn_layout)
        main_layout.addStretch(1)

        self.card.setFixedSize(720, 420)
        root_layout.addStretch(2)
        root_layout.addWidget(self.card, 0, Qt.AlignCenter)
        root_layout.addStretch(2)
        self.setLayout(root_layout)

    def YesEvent(self) -> None:
        dic = write_file.read_dict_from_json('state.json')
        dic["startup_mode"] = "fast"
        write_file.write_dict_to_json(dic, 'state.json')
        self.close()

    def hide_event(self) -> None:
        dic = write_file.read_dict_from_json('state.json')
        dic["startup_mode"] = "slow"
        write_file.write_dict_to_json(dic, 'state.json')
        self.close()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect())
        path = QPainterPath()
        path.addRoundedRect(rect.adjusted(0, 0, -1, -1), 22.0, 22.0)
        painter.setClipPath(path)
        if not self._bg.isNull():
            scaled = self._bg.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            x = int((rect.width() - scaled.width()) / 2)
            y = int((rect.height() - scaled.height()) / 2)
            painter.drawPixmap(x, y, scaled)
        else:
            painter.fillRect(rect, Qt.white)
        super().paintEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        if (event.buttons() & Qt.LeftButton) and self._drag_pos is not None:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event) -> None:
        self._drag_pos = None
        event.accept()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_Escape:
            self.close()
            return
        super().keyPressEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = main()
    win.show()
    sys.exit(app.exec_())
