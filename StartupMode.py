import sys
import os
import write_file
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QPixmap, QPalette, QBrush
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QMessageBox, QLabel


def get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _apply_bg(widget: QWidget) -> None:
    bg = QPixmap(os.path.join(get_base_dir(), "image", "bs.png"))
    if bg.isNull():
        return
    scaled = bg.scaled(widget.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
    pal = widget.palette()
    pal.setBrush(QPalette.Window, QBrush(scaled))
    widget.setAutoFillBackground(True)
    widget.setPalette(pal)


class main(QWidget):
    def __init__(self) -> None:
        super(main, self).__init__()
        self.setWindowTitle("启动方式")
        self.setWindowIcon(QIcon(os.path.join(get_base_dir(), "image", "bs_icon.ico")))
        self.resize(800, 500)
        self.setMinimumSize(800, 500)
        _apply_bg(self)
        self.ui()

    def ui(self) -> None:
        __MainLayout = QVBoxLayout(self)
        __MainLayout.setContentsMargins(40, 40, 40, 40)
        __MainLayout.setSpacing(24)

        title = QLabel("启动方式", self)
        title.setStyleSheet("font-size: 22px; font-weight: 600; color: #111;")
        title.setAlignment(Qt.AlignHCenter)
        __MainLayout.addWidget(title)

        __Yes_NoLayout = QHBoxLayout()
        __Yes_NoLayout.setSpacing(24)
        __Yes = QPushButton(self)
        __Yes.setText("快启动")
        __Yes.setMinimumHeight(72)
        __Yes.setStyleSheet("font-size: 18px;")
        __Yes.clicked.connect(self.YesEvent)
        __No = QPushButton(self)
        __No.setText("慢启动")
        __No.setMinimumHeight(72)
        __No.setStyleSheet("font-size: 18px;")
        __No.clicked.connect(self.hide_event)

        __Yes_NoLayout.addWidget(__Yes)
        __Yes_NoLayout.addWidget(__No)

        __MainLayout.addLayout(__Yes_NoLayout)
        __MainLayout.addStretch(1)

    def YesEvent(self) -> None:
        dic = write_file.read_dict_from_json('state.json')
        dic["startup_mode"] = "fast"
        write_file.write_dict_to_json(dic, 'state.json')
        QMessageBox.information(self, "Programs Config Message", "快启动已开启！重新打开软件生效", QMessageBox.Yes)

    def hide_event(self) -> None:
        dic = write_file.read_dict_from_json('state.json')
        dic["startup_mode"] = "slow"
        write_file.write_dict_to_json(dic, 'state.json')
        QMessageBox.information(self, "Programs Config Message", "慢启动已开启！重新打开软件生效", QMessageBox.Yes)

    def resizeEvent(self, event):
        _apply_bg(self)
        return super().resizeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = main()
    win.show()
    sys.exit(app.exec_())
