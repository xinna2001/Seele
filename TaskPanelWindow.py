"""Botmux task panel: live view of who started what, where, and its status.

The panel lists Botmux sessions active within the last 24 hours. Each row shows
the chat, bot, title and a human-friendly status group (进行中 / 等你回复 / 空闲).
Clicking a row opens Feishu at the exact thread so the user can recover context.

Data comes from ``botmux_client`` (Dashboard REST). This window never patches
Botmux itself; it only renders what the Dashboard already exposes.
"""

from __future__ import annotations

import os

import botmux_client
from platform_utils import get_base_dir as _platform_base_dir, open_external

from PyQt5.QtCore import Qt, QSize, QThread, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QCursor, QPainter, QPainterPath, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


def get_base_dir() -> str:
    return str(_platform_base_dir())


# Accent colors per status group, shared by the dot and the pill label.
GROUP_COLORS = {
    "attention": "#ef6c3b",  # 等你回复 - warm, asks for action
    "working": "#2c8be6",    # 进行中 - active blue
    "idle": "#8a94a6",       # 空闲 - muted grey
}


def _responsive_panel_size(
    available_width: int,
    available_height: int,
    *,
    preferred_width: int = 560,
    preferred_height: int = 620,
    minimum_width: int = 380,
    minimum_height: int = 360,
    margin: int = 32,
) -> tuple[int, int]:
    usable_width = max(320, available_width - margin)
    usable_height = max(320, available_height - margin)
    width = min(preferred_width, int(available_width * 0.5), usable_width)
    height = min(preferred_height, int(available_height * 0.8), usable_height)
    width = max(min(minimum_width, usable_width), width)
    height = max(min(minimum_height, usable_height), height)
    return width, height


def _screen_for_anchor(anchor=None):
    if anchor is not None:
        screen_method = getattr(anchor, "screen", None)
        if callable(screen_method):
            screen = screen_method()
            if screen is not None:
                return screen
    screen = QApplication.screenAt(QCursor.pos())
    return screen or QApplication.primaryScreen()


class _SessionFetcher(QThread):
    """Fetch sessions off the Qt main thread so the UI never blocks on network."""

    loaded = pyqtSignal(list)
    failed = pyqtSignal(str)

    def __init__(self, config: dict, parent=None) -> None:
        super().__init__(parent)
        self._config = config

    def run(self) -> None:
        try:
            client = botmux_client.BotmuxClient(self._config)
            rows = client.get_sessions()
        except botmux_client.BotmuxError as exc:
            self.failed.emit(str(exc))
            return
        except Exception as exc:  # noqa: BLE001 - never let a thread crash the app
            self.failed.emit(str(exc))
            return
        tasks = botmux_client.build_active_tasks(
            rows,
            bot_id=str(self._config.get("bot_id") or ""),
        )
        self.loaded.emit(tasks)


class _TaskRow(QFrame):
    """A single clickable task entry."""

    def __init__(self, task: dict, on_open, parent=None) -> None:
        super().__init__(parent)
        self._task = task
        self._on_open = on_open
        self._link = task.get("link") or ""
        self.setObjectName("task_row")
        self.setCursor(Qt.PointingHandCursor if self._link else Qt.ArrowCursor)
        color = GROUP_COLORS.get(task.get("group"), GROUP_COLORS["idle"])
        self.setStyleSheet(
            "#task_row {"
            "  background-color: rgba(255, 255, 255, 235);"
            "  border: 1px solid rgba(20, 30, 50, 28);"
            "  border-radius: 14px;"
            "}"
            "#task_row:hover { background-color: rgba(238, 245, 255, 245); }"
        )

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 11, 14, 11)
        outer.setSpacing(6)

        # Top line: status pill + chat name (left), relative time (right).
        top = QHBoxLayout()
        top.setSpacing(8)
        pill = QLabel(task.get("groupLabel") or "", self)
        pill.setStyleSheet(
            "QLabel {"
            f"  background-color: {color};"
            "  color: white;"
            "  border-radius: 9px;"
            "  padding: 1px 10px;"
            "  font-size: 12px;"
            "  font-weight: 600;"
            "}"
        )
        pill.setFixedHeight(20)
        chat = QLabel(task.get("chat") or "", self)
        chat.setStyleSheet("QLabel { color: #5a6475; font-size: 12px; }")
        chat.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        when = QLabel(task.get("lastActiveText") or "", self)
        when.setStyleSheet("QLabel { color: #9aa3b2; font-size: 12px; }")
        when.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        top.addWidget(pill)
        top.addWidget(chat, 1)
        top.addWidget(when)
        outer.addLayout(top)

        # Title line: bot name + task title.
        bot_name = task.get("botName") or "机器人"
        title_text = task.get("title") or "未命名任务"
        title = QLabel(f"{bot_name} · {title_text}", self)
        title.setWordWrap(True)
        title.setStyleSheet("QLabel { color: #1a2233; font-size: 14px; font-weight: 600; }")
        outer.addWidget(title)

        preview = (task.get("preview") or "").strip()
        if preview:
            sub = QLabel(preview, self)
            sub.setWordWrap(True)
            sub.setStyleSheet("QLabel { color: #6b7585; font-size: 12px; }")
            sub.setMaximumHeight(34)
            outer.addWidget(sub)

        if not self._link:
            hint = QLabel("（无可跳转的飞书话题）", self)
            hint.setStyleSheet("QLabel { color: #b4bcc8; font-size: 11px; }")
            outer.addWidget(hint)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.LeftButton and self._link:
            self._on_open(self._link)
        super().mouseReleaseEvent(event)


class TaskPanelWindow(QWidget):
    REFRESH_INTERVAL_MS = 15000

    def __init__(self, desktop_wife=None, config: dict | None = None) -> None:
        super().__init__()
        self.desktop_wife = desktop_wife
        self._config = config or botmux_client.load_config()
        self._fetcher: _SessionFetcher | None = None
        self._drag_pos = None
        self._bg = QPixmap(os.path.join(get_base_dir(), "image", "bs.png"))

        self.setWindowTitle("任务面板")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self._build_ui()
        self._fit_to_screen()

        self._timer = QTimer(self)
        self._timer.setInterval(self.REFRESH_INTERVAL_MS)
        self._timer.timeout.connect(self.refresh)

    # --- UI construction -------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 16)
        root.setSpacing(10)

        header = QHBoxLayout()
        header.setSpacing(8)
        title = QLabel("任务面板", self)
        title.setStyleSheet("QLabel { color: white; font-size: 20px; font-weight: 700; }")
        self._status_label = QLabel("", self)
        self._status_label.setStyleSheet("QLabel { color: rgba(255,255,255,210); font-size: 12px; }")
        self._status_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        refresh_btn = QToolButton(self)
        refresh_btn.setText("刷新")
        refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.setStyleSheet(
            "QToolButton {"
            "  background-color: rgba(255,255,255,235);"
            "  border: none; border-radius: 15px;"
            "  padding: 4px 14px; color: #1677d2; font-size: 13px; font-weight: 600;"
            "}"
            "QToolButton:hover { background-color: white; }"
        )
        refresh_btn.clicked.connect(self.refresh)

        close_btn = QToolButton(self)
        close_btn.setObjectName("panel_close_button")
        close_btn.setIcon(self.style().standardIcon(QStyle.SP_TitleBarCloseButton))
        close_btn.setIconSize(QSize(16, 16))
        close_btn.setFixedSize(30, 30)
        close_btn.setToolTip("关闭")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(
            "QToolButton {"
            "  background-color: rgba(255, 255, 255, 220);"
            "  border: none; border-radius: 15px;"
            "}"
            "QToolButton:hover { background-color: white; }"
        )
        close_btn.clicked.connect(self.close)
        self.close_button = close_btn

        header.addWidget(title)
        header.addWidget(self._status_label, 1)
        header.addWidget(refresh_btn)
        header.addWidget(close_btn)
        root.addLayout(header)

        subtitle = QLabel("显示最近 24 小时内有活动的任务，点击任意一条即可跳转到对应飞书话题。", self)
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("QLabel { color: rgba(255,255,255,205); font-size: 12px; }")
        root.addWidget(subtitle)

        self._scroll = QScrollArea(self)
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet(
            "QScrollArea { background: transparent; }"
            "QScrollBar:vertical { background: transparent; width: 8px; margin: 2px; }"
            "QScrollBar::handle:vertical { background: rgba(255,255,255,120); border-radius: 4px; }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
        )
        self._list_host = QWidget()
        self._list_host.setStyleSheet("background: transparent;")
        self._list_layout = QVBoxLayout(self._list_host)
        self._list_layout.setContentsMargins(2, 2, 2, 2)
        self._list_layout.setSpacing(10)
        self._list_layout.addStretch(1)
        self._scroll.setWidget(self._list_host)
        root.addWidget(self._scroll, 1)

        self._empty_label = QLabel("", self._list_host)
        self._empty_label.setAlignment(Qt.AlignCenter)
        self._empty_label.setWordWrap(True)
        self._empty_label.setStyleSheet("QLabel { color: rgba(255,255,255,235); font-size: 14px; }")
        self._empty_label.hide()
        self._list_layout.insertWidget(0, self._empty_label)

    def _fit_to_screen(self) -> None:
        screen = _screen_for_anchor(self.desktop_wife)
        if screen is None:
            self.resize(560, 620)
            return
        available = screen.availableGeometry()
        width, height = _responsive_panel_size(available.width(), available.height())
        self.setMinimumSize(min(380, width), min(360, height))
        self.resize(width, height)
        self.move(
            available.x() + max(0, (available.width() - width) // 2),
            available.y() + max(0, (available.height() - height) // 2),
        )

    # --- Data flow -------------------------------------------------------

    def refresh(self) -> None:
        if self._fetcher is not None and self._fetcher.isRunning():
            return
        if not self._config.get("enabled"):
            self._render_error("Botmux 未启用或未检测到本地服务。")
            return
        self._status_label.setText("正在刷新…")
        self._fetcher = _SessionFetcher(self._config, self)
        self._fetcher.loaded.connect(self._render_tasks)
        self._fetcher.failed.connect(self._render_error)
        self._fetcher.start()

    def _clear_rows(self) -> None:
        for index in reversed(range(self._list_layout.count())):
            item = self._list_layout.itemAt(index)
            widget = item.widget()
            if isinstance(widget, _TaskRow):
                widget.setParent(None)
                widget.deleteLater()

    def _render_tasks(self, tasks: list) -> None:
        self._clear_rows()
        if not tasks:
            self._empty_label.setText("最近 24 小时内没有活动的任务。")
            self._empty_label.show()
            self._status_label.setText("共 0 条")
            return
        self._empty_label.hide()
        for position, task in enumerate(tasks):
            row = _TaskRow(task, self._open_link, self._list_host)
            # Insert before the trailing stretch.
            self._list_layout.insertWidget(position, row)
        self._status_label.setText(f"共 {len(tasks)} 条")

    def _render_error(self, message: str) -> None:
        self._clear_rows()
        self._empty_label.setText(f"无法获取任务列表：\n{message}")
        self._empty_label.show()
        self._status_label.setText("离线")

    def _open_link(self, link: str) -> None:
        if link:
            open_external(link)

    # --- Window behavior -------------------------------------------------

    def showEvent(self, event) -> None:
        self._fit_to_screen()
        self.refresh()
        self._timer.start()
        super().showEvent(event)

    def closeEvent(self, event) -> None:
        self._timer.stop()
        fetcher = self._fetcher
        if fetcher is not None and fetcher.isRunning():
            fetcher.wait(2000)
        super().closeEvent(event)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_Escape:
            self.close()
            return
        super().keyPressEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        from PyQt5.QtCore import QRectF

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
            painter.fillRect(rect, QColor(32, 42, 64))
        # Darken slightly so white text on the artwork stays readable.
        painter.fillRect(rect, QColor(20, 28, 48, 150))
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


def main(desktop_wife=None, config: dict | None = None) -> TaskPanelWindow:
    return TaskPanelWindow(desktop_wife, config)
