import os
import random
import sys
import write_file as wf
from platform_utils import get_base_dir as _platform_base_dir

from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QIcon, QPainter, QPainterPath, QPixmap
from PyQt5.QtWidgets import QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout, QMessageBox, QFrame, QDialog
from PyQt5.QtCore import QRectF


def get_base_dir():
    return str(_platform_base_dir())


def _json_path(name):
    return os.path.join(get_base_dir(), name)


class NonXierVoiceTipDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("音色说明")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self._drag_pos = None
        self._bg = QPixmap(os.path.join(get_base_dir(), "image", "bs.png"))
        self.resize(800, 750)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(18, 18, 18, 18)
        root_layout.setSpacing(14)

        card = QFrame(self)
        card.setObjectName("voice_tip_card")
        card.setStyleSheet(
            "#voice_tip_card {"
            "  background-color: rgba(255, 255, 255, 220);"
            "  border-radius: 22px;"
            "}"
            "QLabel { color: #111; }"
            "QPushButton {"
            "  border-radius: 18px;"
            "  padding: 14px 22px;"
            "  font-size: 24px;"
            "}"
        )

        main_layout = QVBoxLayout(card)
        main_layout.setContentsMargins(34, 30, 34, 30)
        main_layout.setSpacing(22)

        title = QLabel("音色说明", card)
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 28px; font-weight: 600;")

        content = QLabel(
            "兄弟，你知道的，真的是因为精力不够，所以没有训练 爱莉希雅呀和 芙宁娜的音色。"
            "绝对不是因为喜欢希儿，故意只用了这一个音色的",
            card,
        )
        content.setWordWrap(True)
        content.setAlignment(Qt.AlignCenter)
        content.setStyleSheet("font-size: 24px; line-height: 1.5;")

        ok_btn = QPushButton("知道了", card)
        ok_btn.setMinimumHeight(72)
        ok_btn.setStyleSheet(
            "QPushButton { background-color: #4f8cff; color: white; }"
            "QPushButton:hover { background-color: #3b74df; }"
        )
        ok_btn.clicked.connect(self.accept)

        main_layout.addWidget(title)
        main_layout.addWidget(content)
        main_layout.addWidget(ok_btn)

        card.setFixedSize(720, 390)
        root_layout.addStretch(2)
        root_layout.addWidget(card, 0, Qt.AlignCenter)
        root_layout.addStretch(2)

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
            self.accept()
            return
        super().keyPressEvent(event)


class main(QWidget):
    def __init__(self, desktop_wife=None) -> None:
        super(main, self).__init__()
        self.desktop_wife = desktop_wife
        self.setWindowTitle("换个角色")
        self.setWindowIcon(QIcon(os.path.join(get_base_dir(), "image", "bs_icon.ico")))

        # Rounded + background image needs a frameless translucent window.
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self._drag_pos = None
        self._bg = QPixmap(os.path.join(get_base_dir(), "image", "bs.png"))

        # Standard window size
        self.resize(800, 750)
        self.setMinimumSize(800, 750)
        self.ui()

    def ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(18, 18, 18, 18)
        root_layout.setSpacing(14)

        # Foreground rounded panel for readability
        self.card = QFrame(self)
        self.card.setObjectName("role_card")
        self.card.setStyleSheet(
            "#role_card {"
            "  background-color: rgba(255, 255, 255, 210);"
            "  border-radius: 22px;"
            "}"
            "QLabel { color: #111; }"
            "QPushButton {"
            "  border-radius: 18px;"
            "  padding: 14px 22px;"
            "}"
        )

        main_layout = QVBoxLayout(self.card)
        main_layout.setContentsMargins(32, 28, 32, 28)
        main_layout.setSpacing(24)

        title = QLabel(self)
        title.setText("选择一个角色")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 26px; font-weight: 600;")

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(18)
        self.btn_aili = QPushButton(self)
        self.btn_aili.setText("爱莉希雅")
        self.btn_aili.clicked.connect(self.select_aili)
        self.btn_aili.setMinimumHeight(82)
        self.btn_aili.setStyleSheet("font-size: 24px;")

        self.btn_furina = QPushButton(self)
        self.btn_furina.setText("芙宁娜")
        self.btn_furina.clicked.connect(self.select_furina)
        self.btn_furina.setMinimumHeight(82)
        self.btn_furina.setStyleSheet("font-size: 24px;")

        self.btn_xier = QPushButton(self)
        self.btn_xier.setText("希儿")
        self.btn_xier.clicked.connect(self.select_xier)
        self.btn_xier.setMinimumHeight(82)
        self.btn_xier.setStyleSheet("font-size: 24px;")

        buttons_layout.addWidget(self.btn_aili)
        buttons_layout.addWidget(self.btn_furina)
        buttons_layout.addWidget(self.btn_xier)

        main_layout.addWidget(title)
        main_layout.addLayout(buttons_layout)
        # Keep the content compact and centered in the larger window.
        self.card.setFixedSize(720, 320)
        root_layout.addStretch(2)
        root_layout.addWidget(self.card, 0, Qt.AlignCenter)
        root_layout.addStretch(2)
        self.setLayout(root_layout)

    def paintEvent(self, event):
        # Draw rounded window with background image.
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect())
        radius = 22
        path = QPainterPath()
        path.addRoundedRect(rect.adjusted(0, 0, -1, -1), float(radius), float(radius))
        painter.setClipPath(path)

        if not self._bg.isNull():
            # Cover-fill
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

    def _apply_gif(self, gif_path: str, role_name: str, role_key: str) -> None:
        if not self.desktop_wife or not hasattr(self.desktop_wife, "set_character_gif"):
            QMessageBox.warning(self, "换个角色", "主界面未就绪，无法切换角色")
            return
        ok = self.desktop_wife.set_character_gif(gif_path)
        if not ok:
            QMessageBox.warning(self, "换个角色", f"动图加载失败：{gif_path}")
            return
        # 保存角色设置到 state.json
        dic = wf.read_dict_from_json(_json_path('state.json')) or {}
        if role_key != "xier" and dic.get("non_xier_voice_tip_shown") != "1":
            NonXierVoiceTipDialog(self).exec_()
            dic["non_xier_voice_tip_shown"] = "1"
        dic["character"] = role_key
        wf.write_dict_to_json(dic, _json_path('state.json'))
        self.close()

    def select_aili(self) -> None:
        gif_path = os.path.join(get_base_dir(), "image", "aili.gif")
        self._apply_gif(gif_path, "爱莉希雅", "aili")

    def select_furina(self) -> None:
        candidates = ["ff1.gif", "ff2.gif", "ff3.gif"]
        gif_name = random.choice(candidates)
        gif_path = os.path.join(get_base_dir(), "image", gif_name)
        self._apply_gif(gif_path, f"芙宁娜（{gif_name}）", "furina")

    def select_xier(self) -> None:
        gif_path = os.path.join(get_base_dir(), "image", "bss.gif")
        self._apply_gif(gif_path, "希儿", "xier")
