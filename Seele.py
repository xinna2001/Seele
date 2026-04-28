import sys
import os
import random

# qt-material/qtpy picks the Qt binding at import time.
# Set this as early as possible to ensure PyQt5 is selected.
os.environ.setdefault("QT_API", "pyqt5")

import Tray
import OutVoice
import initialize
import VoiceToText
import StartupMode
import write_file as wf
import ProgramsConfigWindow
import RoleSwitchWindow
from PyQt5.QtCore import Qt, QSize, QPoint
from PyQt5.QtGui import QIcon, QFontMetrics
from PyQt5.QtCore import QRectF
from PyQt5.QtGui import QPixmap
from PyQt5.QtGui import QRegion
from PyQt5.QtGui import QCursor
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QMenu
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QWidget
from PyQt5.QtWidgets import QAction
from PyQt5.QtGui import QPainterPath
from PyQt5.QtGui import QIcon, QMovie
from PyQt5.QtWidgets import QDesktopWidget
from PyQt5.QtWidgets import QMessageBox, QApplication

def _apply_material_theme(app: QApplication) -> None:
    """
    Apply a modern Material theme globally to all PyQt widgets.
    Falls back silently if qt-material is not installed.
    """
    os.environ.setdefault("QT_API", "pyqt5")
    try:
        # Ensure PyQt5 binding modules are loaded before importing qt_material.
        from PyQt5 import QtWidgets  # noqa: F401
    except Exception:
        return
    try:
        # qt_material may emit warnings on import; keep console clean.
        import logging

        root = logging.getLogger()
        old_level = root.level
        root.setLevel(logging.ERROR)
        try:
            import qt_material
        finally:
            root.setLevel(old_level)

        # Some qt_material versions may reference QFontDatabase without importing it.
        try:
            from PyQt5.QtGui import QFontDatabase  # noqa: F401

            if not hasattr(qt_material, "QFontDatabase"):
                qt_material.QFontDatabase = QFontDatabase
        except Exception:
            pass

        apply_stylesheet = getattr(qt_material, "apply_stylesheet", None)
        if not apply_stylesheet:
            return

        theme = os.environ.get("SEELE_QT_THEME", "light_blue.xml")
        apply_stylesheet(app, theme=theme)
    except Exception:
        # Theme is optional; never crash app startup due to styling.
        return

def get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def _json_path(name):
    return os.path.join(get_base_dir(), name)

dic = wf.read_dict_from_json(_json_path('state.json')) or {}
if dic.get("initialize", "0") == "0":
    initialize.run(get_base_dir())

class _SpeechBubble(QWidget):
    """
    A small floating "speech bubble" window displayed above the desktop character.
    It is a separate top-level window so it can appear outside the main widget bounds.
    """
    def __init__(self):
        super().__init__(None)
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.Tool  # keep off taskbar
            | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)

        self._label = QLabel(self)
        self._label.setWordWrap(True)
        self._label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        # NOTE: Use stylesheet font-size to override any global theme (qt-material)
        # that might apply to QLabel and ignore setFont().
        self._label.setStyleSheet(
            "QLabel {"
            "  background-color: rgba(255, 255, 255, 235);"
            "  color: #111;"
            "  border: 1px solid rgba(0, 0, 0, 40);"
            "  border-radius: 12px;"
            "  padding: 10px 12px;"
            "  font-size: 24px;"
            "}"
        )

        # Fixed sizing (per user request).
        f = self._label.font()
        f.setPointSize(30)
        self._label.setFont(f)
        self._text_width = 520
        # Accounts for label padding/border in stylesheet.
        self._extra_h = 44

        # Default size; will be resized based on text.
        self.resize(self._text_width, 110)
        self._label.setGeometry(0, 0, self.width(), self.height())
        self.hide()

    def set_text(self, text: str) -> None:
        t = (text or "").strip()
        self._label.setText(t)

        # Use font metrics to compute a stable height for the current fixed width.
        w = int(self._text_width)
        metrics = QFontMetrics(self._label.font())
        rect = metrics.boundingRect(0, 0, w, 2000, Qt.TextWordWrap, t)
        h = int(max(120, min(320, rect.height() + self._extra_h)))
        self.setFixedSize(w, h)
        self._label.setGeometry(0, 0, w, h)

    def show_at(self, global_pos: QPoint) -> None:
        self.move(global_pos)
        # Show without stealing focus from the desktop pet.
        self.show()
        self.raise_()

class DesktopWife(QWidget):
    """
    Main Window
    """
    def resize_movie(self, frame_number):
        """根据当前帧调整 GIF 大小"""
        if not getattr(self, "movie", None) or not self.movie.isValid():
            return
        pixmap = self.movie.currentPixmap()
        if pixmap.isNull() or pixmap.width() <= 0 or pixmap.height() <= 0:
            return
        if not hasattr(self, "PlayLabel"):
            return
        screen = QDesktopWidget().screenGeometry()
        target_h = int(min(max(screen.height() * 0.15, 200), 720))
        target_w = int(min(max(screen.width() * 0.15, 200), 720))
        aspect = pixmap.width() / max(1, pixmap.height())
        if target_w / max(1, target_h) > aspect:
            new_height = target_h
            new_width = int(target_h * aspect)
        else:
            new_width = target_w
            new_height = int(target_w / aspect)
        if new_width <= 0 or new_height <= 0:
            return
        if not getattr(self, "_scaled_initialized", False):
            self.movie.setScaledSize(QSize(new_width, new_height))
            self.PlayLabel.setFixedSize(new_width, new_height)
            self.setFixedSize(new_width, new_height)
            self._scaled_initialized = True
        self._position_message()
    def __init__(self):
        super(DesktopWife, self).__init__()
        self.m_flag = False
        self.m_Position = None
        # Character identity (used by bubble messages)
        character = (wf.read_dict_from_json(_json_path('state.json')) or {}).get("character", "xier")
        self._character_key = character
        self._character_name = self._character_display_name(character)

        # 加载 GIF 动画
        if character == "aili":
            gif_path = os.path.join(get_base_dir(), "image", "aili.gif")
        elif character == "furina":
            import random
            candidates = ["ff1.gif", "ff2.gif", "ff3.gif"]
            gif_name = random.choice(candidates)
            gif_path = os.path.join(get_base_dir(), "image", gif_name)
        else:  # xier 或默认
            gif_path = os.path.join(get_base_dir(), "image", "bss.gif")
        self.movie = QMovie(gif_path)
        # # 设置播放速度为原始速度的 X%
        self.movie.setSpeed(95)
        self._scaled_initialized = False

        self.WindowSize = QDesktopWidget().screenGeometry()

        # 设置窗口标题和大小
        self.setWindowTitle("DesktopWife")
        screen = QDesktopWidget().screenGeometry()
        init_size = int(min(max(screen.height() * 0.35, 320), 720))
        self.resize(init_size, init_size)
        self.move(
            int((screen.width() - self.width()) / 2),
            int((screen.height() - self.height()) / 2)
        )

        # 设置窗口属性
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.SubWindow)
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        # 创建显示 GIF 的标签
        self.PlayLabel = QLabel(self)
        self.PlayLabel.setMovie(self.movie)  # 将电影设置到标签上
        self.WindowSize = QDesktopWidget().screenGeometry()

        self.setWindowTitle("DesktopWife")
        # Old always-visible label is replaced by a timed floating bubble window.
        self.WindowMessage = None
        self._bubble = _SpeechBubble()
        self._bubble_hide_timer = QTimer(self)
        self._bubble_hide_timer.setSingleShot(True)
        self._bubble_hide_timer.timeout.connect(self._hide_bubble)

        # Bubble texts are loaded from bubble_texts.json to keep this file slim.
        # Use "{name}" placeholder in templates, e.g. "{name}正在工作呢~".
        self._bubble_templates = self._load_bubble_templates()
        self.movie.frameChanged.connect(self.resize_movie)
        self.movie.start()  # 开始播放 GIF

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._WindowMenu)

        # Show bubble periodically; not always visible.
        self.BubbleTimer = QTimer(self)
        self.BubbleTimer.setInterval(30000)  # ~30s
        self.BubbleTimer.timeout.connect(self.RandomWindowMessage)
        self.BubbleTimer.start()
        self._first_bubble_done = False

        self._Tray = Tray.TrayIcon(self)
        self.outvoice = OutVoice.main()

    def _warmup_bubble_hidden(self) -> None:
        """
        Aggressive warm-up: create the native top-level bubble window and let Qt/DWM
        do the first-time composition work BEFORE the main window is shown.
        This prevents the first visible bubble popup from hitching.
        """
        bubble = getattr(self, "_bubble", None)
        if bubble is None:
            return
        try:
            templates = getattr(self, "_bubble_templates", None) or ["{name}正在工作呢~"]
            try:
                text = (templates[0] or "{name}正在工作呢~").format(name=self._character_name)
            except Exception:
                text = f"{self._character_name}正在工作呢~"
            bubble.set_text(text)

            # Make sure it never flashes on screen.
            bubble.setWindowOpacity(0.0)
            bubble.move(QPoint(-10000, -10000))
            # Force native window creation.
            _ = bubble.winId()
            bubble.show()
            try:
                app = QApplication.instance()
                if app:
                    app.processEvents()
            finally:
                bubble.hide()
                bubble.setWindowOpacity(1.0)

            # Mark as already warmed up so showEvent doesn't pop a visible bubble.
            self._first_bubble_done = True
        except Exception:
            # Warm-up is best-effort; never break startup.
            return

    def _character_display_name(self, character_key: str) -> str:
        key = (character_key or "").strip().lower()
        if key == "aili":
            return "爱莉希雅"
        if key == "furina":
            return "芙宁娜"
        # default / xier
        return "希儿"

    def _character_key_from_gif_path(self, gif_path: str) -> str:
        name = os.path.basename(gif_path or "").lower()
        if name == "aili.gif":
            return "aili"
        if name.startswith("ff") and name.endswith(".gif"):
            return "furina"
        if name == "bss.gif":
            return "xier"
        return self._character_key or "xier"

    def _load_bubble_templates(self):
        """
        Load bubble templates from bubble_texts.json. Returns a list[str].
        Fallback to a safe default if file is missing/invalid.
        """
        try:
            data = wf.read_dict_from_json(_json_path("bubble_texts.json")) or {}
        except Exception:
            data = {}
        templates = data.get("templates")
        if not isinstance(templates, list):
            templates = []
        cleaned = []
        for t in templates:
            if isinstance(t, str):
                s = t.strip()
                if s:
                    cleaned.append(s)
        if not cleaned:
            cleaned = ["{name}正在工作呢~"]
        return cleaned

    def set_character_gif(self, gif_path: str) -> bool:
        if not gif_path or not os.path.exists(gif_path):
            return False
        movie = QMovie(gif_path)
        if not movie.isValid():
            return False
        old_movie = getattr(self, "movie", None)
        if old_movie:
            try:
                old_movie.frameChanged.disconnect(self.resize_movie)
            except TypeError:
                pass
            old_movie.stop()
        self.movie = movie
        self.movie.setSpeed(95)
        self._scaled_initialized = False
        if hasattr(self, "PlayLabel"):
            self.PlayLabel.setMovie(self.movie)
        self.movie.frameChanged.connect(self.resize_movie)
        self.movie.start()
        self.resize_movie(0)

        # Update character identity for bubble messages.
        self._character_key = self._character_key_from_gif_path(gif_path)
        self._character_name = self._character_display_name(self._character_key)
        return True

    def _position_message(self):
        # Kept for backward compatibility; bubble positioning is handled separately.
        return

    def _bubble_global_pos(self) -> QPoint:
        """
        Compute the bubble window position (global coords) above the character window.
        """
        # Center aligned above the pet window.
        bubble_w = self._bubble.width()
        x = self.x() + int((self.width() - bubble_w) / 2)
        y = self.y() - self._bubble.height() - 10
        # Keep within screen.
        screen = QDesktopWidget().availableGeometry()
        x = max(screen.left(), min(x, screen.right() - bubble_w))
        y = max(screen.top(), y)
        return QPoint(x, y)

    def _hide_bubble(self) -> None:
        try:
            self._bubble.hide()
        except Exception:
            pass

    def _pause_bubble(self) -> None:
        # Hide immediately and stop periodic popups.
        self._hide_bubble()
        try:
            self.BubbleTimer.stop()
        except Exception:
            pass

    def _resume_bubble(self) -> None:
        # Resume periodic popups when main window is visible.
        try:
            if not self.BubbleTimer.isActive():
                self.BubbleTimer.start()
        except Exception:
            pass

    def _WindowMenu(self, _pos=None) -> None:
        """
        右键菜单
        :return: None
        """
        self.Menu = QMenu(self)
        # QMenu.setFont() may be overridden by the global theme, so enforce
        # the item font size through stylesheet to make the change visible.
        self.Menu.setMinimumWidth(320)
        self.Menu.setStyleSheet(
            "QMenu { font-size: 24px; }"
            "QMenu::icon { width: 36px; height: 36px; }"
            "QMenu::item { font-size: 24px; padding: 16px 30px; }"
        )

        self.custom_voice = QAction(QIcon(os.path.join(get_base_dir(), "image", "bs_icon.png")), u"自定义语音唤醒", self)
        self.Menu.addAction(self.custom_voice)

        self.out_voice = QAction(QIcon(os.path.join(get_base_dir(), "image", "bs_icon.png")), u"语音输入设置", self)
        self.Menu.addAction(self.out_voice)

        self.change_role = QAction(QIcon(os.path.join(get_base_dir(), "image", "bs_icon.png")), u"换个角色", self)
        self.Menu.addAction(self.change_role)

        self.startup = QAction(QIcon(os.path.join(get_base_dir(), "image", "bs_icon.png")), u"启动方式", self)
        self.Menu.addAction(self.startup)

        self.StartTray = QAction(QIcon(os.path.join(get_base_dir(), "image", "bs_icon.png")), u"退置托盘", self)
        self.Menu.addAction(self.StartTray)

        self.CloseWindowAction = QAction(QIcon(os.path.join(get_base_dir(), "image", "Quit.png")), u"退出程序", self)
        self.Menu.addAction(self.CloseWindowAction)

        self.out_voice.triggered.connect(self.WeatherForecast)
        self.custom_voice.triggered.connect(self.ProgramsConfig)
        self.change_role.triggered.connect(self.ChangeRole)
        self.StartTray.triggered.connect(self.SetTray)
        self.startup.triggered.connect(self.Startup)
        self.CloseWindowAction.triggered.connect(self.CloseWindowActionEvent)
        # Restore the old feel: popup near the click/cursor position.
        if _pos is not None:
            self.Menu.popup(self.mapToGlobal(_pos))
        else:
            self.Menu.popup(QCursor.pos())

    def ProgramsConfig(self) -> None:
        """
        自定义语音唤醒
        :return: None
        """
        if (wf.read_dict_from_json(_json_path("state.json")) or {}).get('startup_mode') == "fast":
            self.ConfigWindow = ProgramsConfigWindow.main2()
            self.ConfigWindow.show()
        else:
            self.ConfigWindow = ProgramsConfigWindow.main()
            self.ConfigWindow.show()

    def ChangeRole(self) -> None:
        self.ChangeRoleWindow = RoleSwitchWindow.main(self)
        self.ChangeRoleWindow.show()

    def CloseWindowActionEvent(self) -> None:
        """
        关闭界面并提出后台进程
        :return: None
        """
        self.close()
        VoiceToText.CONTROLLER = False
        QApplication.instance().quit()
    def Startup(self) -> None:
        """
        启动方式
        :return: None
        """
        self.ConfigWindow = StartupMode.main()
        self.ConfigWindow.show()

    def SetTray(self) -> None:
        """
        系统托盘
        :return: None
        """
        # When hidden to tray, do not show bubble messages.
        self._pause_bubble()
        self._Tray.show()
        self.hide()

    def RandomWindowMessage(self) -> None:
        """
        Periodically show a short speech bubble above the character.
        :return: None
        """
        # Do not pop up when the pet is hidden/minimized (e.g. in tray).
        if not self.isVisible() or self.isMinimized():
            return
        if getattr(self, "_bubble", None) is None:
            return
        templates = getattr(self, "_bubble_templates", None) or ["{name}正在工作呢~"]
        tmpl = random.choice(templates)
        try:
            text = tmpl.format(name=self._character_name)
        except Exception:
            text = f"{self._character_name}正在工作呢~"
        self._bubble.set_text(text)
        self._bubble.show_at(self._bubble_global_pos())
        # Auto-hide after a short while so it doesn't stay on screen.
        self._bubble_hide_timer.start(6500)

    def WeatherForecast(self) -> None:
        """
        
        :return: None
        """
        self.outvoice.show()

    def mousePressEvent(self, event) -> None:
        """
        重写移动事假，更改鼠标图标
        :param event:
        :return:
        """
        if event.button() == Qt.LeftButton:
            self.m_flag = True
            self.m_Position = event.globalPos() - self.pos()  # 获取鼠标相对窗口的位置
            event.accept()
            self.setCursor(QCursor(Qt.OpenHandCursor))  # 更改鼠标图标

    def mouseMoveEvent(self, event) -> None:
        if Qt.LeftButton and self.m_flag:
            self.move(event.globalPos() - self.m_Position)
            # If the bubble is visible, keep it tracking the character window.
            if getattr(self, "_bubble", None) is not None and self._bubble.isVisible():
                self._bubble.move(self._bubble_global_pos())
            event.accept()

    def mouseReleaseEvent(self, event) -> None:
        self.m_flag = False
        self.setCursor(QCursor(Qt.ArrowCursor))
        event.accept()

    def resizeEvent(self, event):
        # Keep bubble aligned after resize.
        if getattr(self, "_bubble", None) is not None and self._bubble.isVisible():
            self._bubble.move(self._bubble_global_pos())
        super(DesktopWife, self).resizeEvent(event)

    def showEvent(self, event):
        # Restored from tray: resume bubble popups.
        self._resume_bubble()
        # Warm up on first show: pop once immediately so any first-time widget
        # creation/compositing cost happens right away (not on the first 30s tick).
        if not getattr(self, "_first_bubble_done", False):
            self._first_bubble_done = True
            QTimer.singleShot(300, self.RandomWindowMessage)
        super().showEvent(event)

    def hideEvent(self, event):
        # Hidden to tray/minimized: stop bubble popups.
        self._pause_bubble()
        super().hideEvent(event)

    def closeEvent(self, event):
        # Ensure bubble window doesn't leak.
        self._pause_bubble()
        try:
            if getattr(self, "_bubble", None) is not None:
                self._bubble.close()
        except Exception:
            pass
        super().closeEvent(event)

def main():
    app = QApplication(sys.argv)
    _apply_material_theme(app)
    app.setQuitOnLastWindowClosed(False)
    Window = DesktopWife()
    # Aggressive warm-up before showing any UI (no visible flash).
    Window._warmup_bubble_hidden()
    Window.show()
    ready_file = os.environ.get("SEELE_READY_FILE")
    if ready_file:
        try:
            os.makedirs(os.path.dirname(ready_file), exist_ok=True)
            with open(ready_file, "w", encoding="utf-8"):
                pass
        except OSError:
            pass
    VoiceToText.run()
    app.exec_()

if __name__ == "__main__":
    main()
