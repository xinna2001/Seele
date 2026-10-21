import os
import random
import sys
import write_file as wf
from platform_utils import data_path, get_base_dir as _platform_base_dir

from PyQt5.QtCore import Qt, QPoint, QRectF, QSize
from PyQt5.QtGui import QCursor, QIcon, QPainter, QPainterPath, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


def get_base_dir():
    return str(_platform_base_dir())


def _json_path(name):
    return str(data_path(name))


def _responsive_window_size(
    available_width: int,
    available_height: int,
    *,
    preferred_width: int,
    preferred_height: int,
    minimum_width: int,
    minimum_height: int,
    margin: int = 32,
) -> tuple[int, int]:
    usable_width = max(240, available_width - margin)
    usable_height = max(220, available_height - margin)
    target_width = min(
        preferred_width,
        int(available_width * 0.62),
        usable_width,
    )
    target_height = min(
        preferred_height,
        int(available_height * 0.68),
        usable_height,
    )
    lower_width = min(minimum_width, usable_width)
    lower_height = min(minimum_height, usable_height)
    return (
        max(lower_width, target_width),
        max(lower_height, target_height),
    )


def _screen_for_anchor(anchor=None):
    if anchor is not None:
        screen_method = getattr(anchor, "screen", None)
        if callable(screen_method):
            screen = screen_method()
            if screen is not None:
                return screen
        window_handle = anchor.windowHandle()
        if window_handle is not None and window_handle.screen() is not None:
            return window_handle.screen()
    screen = QApplication.screenAt(QCursor.pos())
    return screen or QApplication.primaryScreen()


def _fit_window_to_screen(
    window,
    anchor,
    *,
    preferred_width: int,
    preferred_height: int,
    minimum_width: int,
    minimum_height: int,
) -> None:
    screen = _screen_for_anchor(anchor)
    if screen is None:
        window.resize(preferred_width, preferred_height)
        return
    available = screen.availableGeometry()
    width, height = _responsive_window_size(
        available.width(),
        available.height(),
        preferred_width=preferred_width,
        preferred_height=preferred_height,
        minimum_width=minimum_width,
        minimum_height=minimum_height,
    )
    window.setMinimumSize(
        min(minimum_width, width),
        min(minimum_height, height),
    )
    window.resize(width, height)
    window.move(
        available.x() + max(0, (available.width() - width) // 2),
        available.y() + max(0, (available.height() - height) // 2),
    )


def _create_close_button(parent, callback) -> QToolButton:
    button = QToolButton(parent)
    button.setObjectName("window_close_button")
    button.setIcon(parent.style().standardIcon(QStyle.SP_TitleBarCloseButton))
    button.setIconSize(QSize(16, 16))
    button.setFixedSize(34, 34)
    button.setToolTip("关闭")
    button.setAccessibleName("关闭")
    button.setStyleSheet(
        "QToolButton {"
        "  background-color: rgba(255, 255, 255, 210);"
        "  border: 1px solid rgba(20, 20, 20, 45);"
        "  border-radius: 17px;"
        "}"
        "QToolButton:hover { background-color: rgba(235, 235, 235, 235); }"
        "QToolButton:pressed { background-color: rgba(215, 215, 215, 235); }"
    )
    button.clicked.connect(callback)
    return button


class NonXierVoiceTipDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("音色说明")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self._drag_pos = None
        self._bg = QPixmap(os.path.join(get_base_dir(), "image", "bs.png"))

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(10)

        top_layout = QHBoxLayout()
        top_layout.addStretch(1)
        self.close_button = _create_close_button(self, self.reject)
        top_layout.addWidget(self.close_button)
        root_layout.addLayout(top_layout)

        card = QFrame(self)
        card.setObjectName("voice_tip_card")
        card.setMaximumWidth(560)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        card.setStyleSheet(
            "#voice_tip_card {"
            "  background-color: rgba(255, 255, 255, 220);"
            "  border-radius: 22px;"
            "}"
            "QLabel { color: #111; }"
            "QPushButton {"
            "  border-radius: 18px;"
            "  padding: 10px 18px;"
            "  font-size: 17px;"
            "}"
        )

        main_layout = QVBoxLayout(card)
        main_layout.setContentsMargins(28, 24, 28, 24)
        main_layout.setSpacing(18)

        title = QLabel("音色说明", card)
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-weight: 600;")

        content = QLabel(
            "兄弟，你知道的，真的是因为精力不够，所以没有训练 爱莉希雅呀和 芙宁娜的音色。"
            "绝对不是因为喜欢希儿，故意只用了这一个音色的",
            card,
        )
        content.setWordWrap(True)
        content.setAlignment(Qt.AlignCenter)
        content.setStyleSheet("font-size: 17px;")

        ok_btn = QPushButton("知道了", card)
        ok_btn.setMinimumHeight(52)
        ok_btn.setStyleSheet(
            "QPushButton { background-color: #4f8cff; color: white; }"
            "QPushButton:hover { background-color: #3b74df; }"
        )
        ok_btn.clicked.connect(self.accept)

        main_layout.addWidget(title)
        main_layout.addWidget(content)
        main_layout.addWidget(ok_btn)

        card_row = QHBoxLayout()
        card_row.addStretch(1)
        card_row.addWidget(card)
        card_row.addStretch(1)
        root_layout.addStretch(1)
        root_layout.addLayout(card_row)
        root_layout.addStretch(1)

        _fit_window_to_screen(
            self,
            parent,
            preferred_width=640,
            preferred_height=480,
            minimum_width=360,
            minimum_height=300,
        )

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
            self.reject()
            return
        super().keyPressEvent(event)

    def showEvent(self, event) -> None:
        _fit_window_to_screen(
            self,
            self.parentWidget(),
            preferred_width=640,
            preferred_height=480,
            minimum_width=360,
            minimum_height=300,
        )
        super().showEvent(event)


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
        self._buttons_vertical = None

        self.ui()
        _fit_window_to_screen(
            self,
            desktop_wife,
            preferred_width=640,
            preferred_height=460,
            minimum_width=360,
            minimum_height=300,
        )

    def ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(10)

        top_layout = QHBoxLayout()
        top_layout.addStretch(1)
        self.close_button = _create_close_button(self, self.close)
        top_layout.addWidget(self.close_button)
        root_layout.addLayout(top_layout)

        # Foreground rounded panel for readability
        self.card = QFrame(self)
        self.card.setObjectName("role_card")
        self.card.setMaximumWidth(600)
        self.card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.card.setStyleSheet(
            "#role_card {"
            "  background-color: rgba(255, 255, 255, 210);"
            "  border-radius: 22px;"
            "}"
            "QLabel { color: #111; }"
            "QPushButton {"
            "  background-color: rgba(255, 255, 255, 205);"
            "  border: 2px solid #2c8be6;"
            "  border-radius: 18px;"
            "  color: #1677d2;"
            "  padding: 10px 12px;"
            "  font-size: 18px;"
            "}"
            "QPushButton:hover { background-color: rgba(230, 243, 255, 230); }"
            "QPushButton:pressed { background-color: rgba(205, 229, 252, 235); }"
        )

        main_layout = QVBoxLayout(self.card)
        main_layout.setContentsMargins(24, 22, 24, 22)
        main_layout.setSpacing(18)

        title = QLabel(self.card)
        title.setText("选择一个角色")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-weight: 600;")

        self.buttons_layout = QGridLayout()
        self.buttons_layout.setHorizontalSpacing(12)
        self.buttons_layout.setVerticalSpacing(10)
        self.btn_aili = QPushButton(self.card)
        self.btn_aili.setText("爱莉希雅")
        self.btn_aili.clicked.connect(self.select_aili)
        self.btn_aili.setMinimumHeight(58)

        self.btn_furina = QPushButton(self.card)
        self.btn_furina.setText("芙宁娜")
        self.btn_furina.clicked.connect(self.select_furina)
        self.btn_furina.setMinimumHeight(58)

        self.btn_xier = QPushButton(self.card)
        self.btn_xier.setText("希儿")
        self.btn_xier.clicked.connect(self.select_xier)
        self.btn_xier.setMinimumHeight(58)
        self._role_buttons = (
            self.btn_aili,
            self.btn_furina,
            self.btn_xier,
        )

        main_layout.addWidget(title)
        main_layout.addLayout(self.buttons_layout)
        self._update_button_layout()

        card_row = QHBoxLayout()
        card_row.addStretch(1)
        card_row.addWidget(self.card)
        card_row.addStretch(1)
        root_layout.addStretch(1)
        root_layout.addLayout(card_row)
        root_layout.addStretch(1)
        self.setLayout(root_layout)

    def _update_button_layout(self) -> None:
        vertical = self.width() < 480
        if self._buttons_vertical is vertical:
            return
        self._buttons_vertical = vertical
        while self.buttons_layout.count():
            self.buttons_layout.takeAt(0)
        for index, button in enumerate(self._role_buttons):
            button.setMinimumHeight(48 if vertical else 58)
            row, column = (index, 0) if vertical else (0, index)
            self.buttons_layout.addWidget(button, row, column)
        self.card.setMinimumHeight(258 if vertical else 166)
        self.buttons_layout.invalidate()
        self.card.layout().invalidate()
        self.card.updateGeometry()

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
            scaled = self._bg.scaled(
                self.size(),
                Qt.KeepAspectRatioByExpanding,
                Qt.SmoothTransformation,
            )
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

    def resizeEvent(self, event) -> None:
        if hasattr(self, "_role_buttons"):
            self._update_button_layout()
        super().resizeEvent(event)

    def showEvent(self, event) -> None:
        _fit_window_to_screen(
            self,
            self.desktop_wife,
            preferred_width=640,
            preferred_height=460,
            minimum_width=360,
            minimum_height=300,
        )
        self._update_button_layout()
        super().showEvent(event)

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
