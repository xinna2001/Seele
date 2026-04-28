import json
import os
import sys
import write_file as wf
from PyQt5.QtWidgets import QWidget
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout
from PyQt5.QtWidgets import QLineEdit, QMessageBox
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QPainterPath
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtWidgets import QFrame


def get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


class main(QWidget):
    def __init__(self) -> None:
        super(main, self).__init__()
        self.setWindowTitle("自定义语音唤醒")
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
        self.card.setObjectName("config_card")
        self.card.setStyleSheet(
            "#config_card { background-color: rgba(255, 255, 255, 210); border-radius: 22px; }"
            "QLabel { color: #111; }"
            "QLineEdit { border-radius: 16px; padding: 12px 14px; font-size: 18px; }"
            "QPushButton { border-radius: 18px; padding: 14px 22px; font-size: 22px; }"
        )

        main_layout = QVBoxLayout(self.card)
        main_layout.setContentsMargins(32, 28, 32, 28)
        main_layout.setSpacing(22)

        title = QLabel("自定义语音唤醒", self.card)
        title.setStyleSheet("font-size: 26px; font-weight: 600;")
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        tip = QLabel("输入 uid 和唤醒词，留空则不记录", self.card)
        tip.setStyleSheet("font-size: 18px;")
        tip.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(tip)

        form_layout = QVBoxLayout()
        form_layout.setSpacing(16)

        label = QLabel("输入 uid 和唤醒词", self.card)
        label.setStyleSheet("font-size: 20px; font-weight: 600;")
        form_layout.addWidget(label)

        self.uid_text = QLineEdit(self.card)
        self.uid_text.setPlaceholderText("uid")
        self.uid_text.setMinimumHeight(52)
        self.uid_text.setMinimumHeight(62)

        self.word_text = QLineEdit(self.card)
        self.word_text.setPlaceholderText("唤醒词")
        self.word_text.setMinimumHeight(62)

        form_layout.addWidget(self.uid_text)
        form_layout.addWidget(self.word_text)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(18)
        confirm_btn = QPushButton("确认", self.card)
        confirm_btn.setMinimumHeight(78)
        confirm_btn.clicked.connect(self.YesEvent)
        cancel_btn = QPushButton("关闭", self.card)
        cancel_btn.setMinimumHeight(78)
        cancel_btn.clicked.connect(self.close)
        btn_layout.addWidget(confirm_btn)
        btn_layout.addWidget(cancel_btn)

        main_layout.addStretch(1)
        main_layout.addLayout(form_layout)
        main_layout.addLayout(btn_layout)
        main_layout.addStretch(1)

        self.card.setFixedSize(720, 520)
        root_layout.addStretch(2)
        root_layout.addWidget(self.card, 0, Qt.AlignCenter)
        root_layout.addStretch(2)
        self.setLayout(root_layout)
    
    def YesEvent(self) -> None:
        uid = self.uid_text.text().strip()
        word = self.word_text.text().strip()
        if uid == "" and word == "":
            QMessageBox.information(self, "提示", "uid 和唤醒词都为空，未记录。", QMessageBox.Yes)
            self.close()
            return
        if uid == "" or word == "":
            QMessageBox.warning(self, "警告", "uid和唤醒词需要同时填写。")
            return
        else:
            uid_json = wf.read_dict_from_json("uid.json")
            uid_json[word] = uid
            wf.write_dict_to_json(uid_json, "uid.json")
            QMessageBox.information(self, "提示", "自定义语音已设置成功！", QMessageBox.Yes)
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


class main2(QWidget):
    def __init__(self) -> None:
        super(main2, self).__init__()
        self.setWindowTitle("自定义语音唤醒")
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
        self.card.setObjectName("config_card")
        self.card.setStyleSheet(
            "#config_card { background-color: rgba(255, 255, 255, 210); border-radius: 22px; }"
            "QLabel { color: #111; }"
            "QLineEdit { border-radius: 16px; padding: 12px 14px; font-size: 18px; }"
            "QPushButton { border-radius: 18px; padding: 14px 22px; font-size: 22px; }"
        )

        main_layout = QVBoxLayout(self.card)
        main_layout.setContentsMargins(32, 28, 32, 28)
        main_layout.setSpacing(22)

        title = QLabel("自定义语音唤醒", self.card)
        title.setStyleSheet("font-size: 26px; font-weight: 600;")
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        tip = QLabel("输入文件名和唤醒词，留空则不记录", self.card)
        tip.setStyleSheet("font-size: 18px;")
        tip.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(tip)

        form_layout = QVBoxLayout()
        form_layout.setSpacing(16)

        label = QLabel("输入 txt 文件名称和唤醒词", self.card)
        label.setStyleSheet("font-size: 20px; font-weight: 600;")
        form_layout.addWidget(label)

        self.uid_text = QLineEdit(self.card)
        self.uid_text.setPlaceholderText("txt文件名称")
        self.uid_text.setMinimumHeight(62)

        self.word_text = QLineEdit(self.card)
        self.word_text.setPlaceholderText("唤醒词")
        self.word_text.setMinimumHeight(62)

        form_layout.addWidget(self.uid_text)
        form_layout.addWidget(self.word_text)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(18)
        confirm_btn = QPushButton("确认", self.card)
        confirm_btn.setMinimumHeight(78)
        confirm_btn.clicked.connect(self.YesEvent)
        cancel_btn = QPushButton("关闭", self.card)
        cancel_btn.setMinimumHeight(78)
        cancel_btn.clicked.connect(self.close)
        btn_layout.addWidget(confirm_btn)
        btn_layout.addWidget(cancel_btn)

        main_layout.addStretch(1)
        main_layout.addLayout(form_layout)
        main_layout.addLayout(btn_layout)
        main_layout.addStretch(1)

        self.card.setFixedSize(720, 520)
        root_layout.addStretch(2)
        root_layout.addWidget(self.card, 0, Qt.AlignCenter)
        root_layout.addStretch(2)
        self.setLayout(root_layout)
    
    def YesEvent(self) -> None:
        uid = self.uid_text.text().strip()
        word = self.word_text.text().strip()
        if uid == "" and word == "":
            QMessageBox.information(self, "提示", "文件名称和唤醒词都为空，未记录。", QMessageBox.Yes)
            self.close()
            return
        if uid == "" or word == "":
            QMessageBox.warning(self, "警告", "文件名称和唤醒词需要同时填写。")
            return
        else:
            uid_json = wf.read_dict_from_json("file_name.json")
            uid_json[word] = uid
            wf.write_dict_to_json(uid_json, "file_name.json")
            QMessageBox.information(self, "提示", "自定义语音已设置成功！", QMessageBox.Yes)
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
