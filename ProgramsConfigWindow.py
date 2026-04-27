import json
import os
import sys
import write_file as wf
from PyQt5.QtWidgets import QWidget
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout
from PyQt5.QtWidgets import QLineEdit, QMessageBox
from PyQt5.QtGui import QIcon, QPixmap, QPalette, QBrush
from PyQt5.QtCore import Qt


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
        self.setWindowTitle("自定义语音唤醒")
        self.setWindowIcon(QIcon(".\\image\\bs_icon.ico"))
        self.resize(800, 500)
        self.setMinimumSize(800, 500)
        _apply_bg(self)
        self.ui()
    
    def ui(self) -> None:
        __MainLayout = QVBoxLayout(self)
        __MainLayout.setContentsMargins(40, 40, 40, 40)
        __MainLayout.setSpacing(18)

        __BaiDuYunHLayout = QVBoxLayout()
        __BaiDuYunLabel = QLabel(self)
        __BaiDuYunLabel.setText("输入uid和唤醒词")
        __BaiDuYunLabel.setStyleSheet("font-size: 20px; font-weight: 600; color: #111;")

        self.uid_text = QLineEdit(self)
        self.uid_text.setPlaceholderText("uid")
        self.uid_text.setMinimumHeight(52)
        self.uid_text.setStyleSheet("font-size: 16px; padding: 8px 12px;")

        self.word_text = QLineEdit(self)
        self.word_text.setPlaceholderText("唤醒词")
        self.word_text.setMinimumHeight(52)
        self.word_text.setStyleSheet("font-size: 16px; padding: 8px 12px;")

        __BaiDuYunHLayout.addWidget(__BaiDuYunLabel)
        __BaiDuYunHLayout.addWidget(self.uid_text)
        __BaiDuYunHLayout.addWidget(self.word_text)
        __BaiDuYunHLayout.setSpacing(12)

        __Yes_NoLayout = QHBoxLayout()
        __Yes = QPushButton(self)
        __Yes.setText("确认")
        __Yes.setMinimumHeight(64)
        __Yes.setStyleSheet("font-size: 18px;")
        __Yes.clicked.connect(self.YesEvent)
        __Yes_NoLayout.addWidget(__Yes)

        __MainLayout.addLayout(__BaiDuYunHLayout)
        __MainLayout.addLayout(__Yes_NoLayout)
        __MainLayout.addStretch(1)
        self.setLayout(__MainLayout)

    def resizeEvent(self, event):
        _apply_bg(self)
        return super().resizeEvent(event)
    
    def YesEvent(self) -> None:
        uid = self.uid_text.text()
        word = self.word_text.text()
        if uid == "" or word == "":
            QMessageBox.warning(self, "警告", "uid和唤醒词不能为空")
            return
        else:
            uid_json = wf.read_dict_from_json("uid.json")
            uid_json[word] = uid
            wf.write_dict_to_json(uid_json, "uid.json")
            # 关闭当前窗口
            QMessageBox.information(self, "Programs Config Message", "自定义语音已设置成功！", QMessageBox.Yes)


class main2(QWidget):
    def __init__(self) -> None:
        super(main2, self).__init__()
        self.setWindowTitle("自定义语音唤醒")
        self.setWindowIcon(QIcon(".\\image\\bs_icon.ico"))
        self.resize(800, 500)
        self.setMinimumSize(800, 500)
        _apply_bg(self)
        self.ui()
    
    def ui(self) -> None:
        __MainLayout = QVBoxLayout(self)
        __MainLayout.setContentsMargins(40, 40, 40, 40)
        __MainLayout.setSpacing(18)

        __BaiDuYunHLayout = QVBoxLayout()
        __BaiDuYunLabel = QLabel(self)
        __BaiDuYunLabel.setText("输入txt文件名称和唤醒词")
        __BaiDuYunLabel.setStyleSheet("font-size: 20px; font-weight: 600; color: #111;")

        self.uid_text = QLineEdit(self)
        self.uid_text.setPlaceholderText("txt文件名称")
        self.uid_text.setMinimumHeight(52)
        self.uid_text.setStyleSheet("font-size: 16px; padding: 8px 12px;")

        self.word_text = QLineEdit(self)
        self.word_text.setPlaceholderText("唤醒词")
        self.word_text.setMinimumHeight(52)
        self.word_text.setStyleSheet("font-size: 16px; padding: 8px 12px;")

        __BaiDuYunHLayout.addWidget(__BaiDuYunLabel)
        __BaiDuYunHLayout.addWidget(self.uid_text)
        __BaiDuYunHLayout.addWidget(self.word_text)
        __BaiDuYunHLayout.setSpacing(12)

        __Yes_NoLayout = QHBoxLayout()
        __Yes = QPushButton(self)
        __Yes.setText("确认")
        __Yes.setMinimumHeight(64)
        __Yes.setStyleSheet("font-size: 18px;")
        __Yes.clicked.connect(self.YesEvent)
        __Yes_NoLayout.addWidget(__Yes)

        __MainLayout.addLayout(__BaiDuYunHLayout)
        __MainLayout.addLayout(__Yes_NoLayout)
        __MainLayout.addStretch(1)
        self.setLayout(__MainLayout)

    def resizeEvent(self, event):
        _apply_bg(self)
        return super().resizeEvent(event)
    
    def YesEvent(self) -> None:
        uid = self.uid_text.text()
        word = self.word_text.text()
        if uid == "" or word == "":
            QMessageBox.warning(self, "警告", "文件名称和唤醒词不能为空")
            return
        else:
            uid_json = wf.read_dict_from_json("file_name.json")
            uid_json[word] = uid
            wf.write_dict_to_json(uid_json, "file_name.json")
            # 关闭当前窗口
            QMessageBox.information(self, "Programs Config Message", "自定义语音已设置成功！", QMessageBox.Yes)
