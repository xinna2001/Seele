import sys
import os
import random
import threading

# qt-material/qtpy picks the Qt binding at import time.
# Set this as early as possible to ensure PyQt5 is selected.
os.environ.setdefault("QT_API", "pyqt5")
if sys.platform == "darwin":
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")
    os.environ.setdefault("QT_SCALE_FACTOR_ROUNDING_POLICY", "PassThrough")

import Tray
import OutVoice
import initialize
import VoiceToText
import StartupMode
import write_file as wf
import ProgramsConfigWindow
import RoleSwitchWindow
import botmux_client
import mac_byte_bootstrap
import rpa_bridge
import rpa_service
from platform_utils import get_base_dir as _platform_base_dir, open_external
from PyQt5.QtCore import Qt, QSize, QPoint, QObject, pyqtSignal
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


def _configure_high_dpi() -> None:
    if QApplication.instance() is not None:
        return
    if hasattr(Qt, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)


_configure_high_dpi()


class _IntegrationSignals(QObject):
    botmux_state = pyqtSignal(dict)
    rpa_event = pyqtSignal(dict)
    bootstrap_event = pyqtSignal(dict)

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
    return str(_platform_base_dir())

def _json_path(name):
    return os.path.join(get_base_dir(), name)

dic = wf.read_dict_from_json(_json_path('state.json')) or {}
if not mac_byte_bootstrap.is_mac_byte() and dic.get("initialize", "0") == "0":
    initialize.run(get_base_dir())

class _SpeechBubble(QWidget):
    """
    A small floating "speech bubble" window displayed above the desktop character.
    It is a separate top-level window so it can appear outside the main widget bounds.
    """
    def __init__(self, owner: QWidget):
        super().__init__(owner)
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.Tool
            | Qt.WindowStaysOnTopHint
            | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        if sys.platform == "darwin" and hasattr(Qt, "WA_MacAlwaysShowToolWindow"):
            self.setAttribute(Qt.WA_MacAlwaysShowToolWindow, True)

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
            "  border-radius: 8px;"
            "  padding: 8px 10px;"
            "  font-size: 14px;"
            "}"
        )

        self._text_width = 320
        self._content_width = 296
        self._extra_h = 24

        # Default size; will be resized based on text.
        self.resize(self._text_width, 64)
        self._label.setGeometry(0, 0, self.width(), self.height())
        self.hide()

    def set_text(self, text: str) -> None:
        t = (text or "").strip()
        self._label.setText(t)

        # Use font metrics to compute a stable height for the current fixed width.
        metrics = QFontMetrics(self._label.font())
        rect = metrics.boundingRect(
            0,
            0,
            self._content_width,
            1000,
            Qt.TextWordWrap,
            t,
        )
        w = int(self._text_width)
        h = int(max(56, min(160, rect.height() + self._extra_h)))
        self.setFixedSize(w, h)
        self._label.setGeometry(0, 0, w, h)

    def show_at(self, global_pos: QPoint) -> None:
        self.move(global_pos)
        # Show without stealing focus from the desktop pet.
        self.show()

class DesktopWife(QWidget):
    """
    Main Window
    """
    def resize_movie(self, frame_number):
        """按当前屏幕像素密度平滑渲染 GIF 帧。"""
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
            self.PlayLabel.setFixedSize(new_width, new_height)
            self.setFixedSize(new_width, new_height)
            self._movie_target_size = QSize(new_width, new_height)
            self._scaled_initialized = True

        target = getattr(self, "_movie_target_size", QSize(new_width, new_height))
        pixel_ratio = max(1.0, float(self.devicePixelRatioF()))
        physical_size = QSize(
            max(1, round(target.width() * pixel_ratio)),
            max(1, round(target.height() * pixel_ratio)),
        )
        rendered = pixmap.scaled(
            physical_size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        rendered.setDevicePixelRatio(pixel_ratio)
        self.PlayLabel.setPixmap(rendered)
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
        self._base_gif_path = gif_path
        self._current_gif_path = gif_path
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
        window_type = Qt.SubWindow if sys.platform == "win32" else Qt.Tool
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | window_type)
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        if sys.platform == "darwin" and hasattr(Qt, "WA_MacAlwaysShowToolWindow"):
            self.setAttribute(Qt.WA_MacAlwaysShowToolWindow, True)

        # 创建显示 GIF 的标签
        self.PlayLabel = QLabel(self)
        self.PlayLabel.setAlignment(Qt.AlignCenter)
        self.WindowSize = QDesktopWidget().screenGeometry()

        self.setWindowTitle("DesktopWife")
        # Old always-visible label is replaced by a timed floating bubble window.
        self.WindowMessage = None
        self._bubble = _SpeechBubble(self)
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
        self.outvoice = None
        if not mac_byte_bootstrap.is_mac_byte():
            self.outvoice = OutVoice.main()
        self._botmux_config = botmux_client.load_config()
        self._botmux_state = {
            "connected": False,
            "kind": "offline",
            "active": 0,
            "attention": 0,
            "session": None,
            "error": "",
        }
        self._rpa_state = None
        self._botmux_signature = None
        self._integration_signals = _IntegrationSignals(self)
        self._integration_signals.botmux_state.connect(self._handle_botmux_state)
        self._integration_signals.rpa_event.connect(self._handle_rpa_event)
        self._integration_signals.bootstrap_event.connect(self._handle_bootstrap_event)
        self._unsubscribe_rpa_events = rpa_service.subscribe_job_events(
            self._integration_signals.rpa_event.emit,
        )
        self._botmux_monitor = botmux_client.BotmuxMonitor(
            self._integration_signals.botmux_state.emit,
            self._botmux_config,
        )
        self._rpa_bridge = rpa_bridge.RpaBridge(
            self._botmux_config.get("bridge") or {},
            self._integration_signals.rpa_event.emit,
        )
        self._bootstrap_thread = None
        QTimer.singleShot(0, self._start_integrations)
        QTimer.singleShot(1200, self.StartMacByteBootstrap)

    def _start_integrations(self) -> None:
        self._botmux_monitor.start()
        try:
            self._rpa_bridge.start()
        except (OSError, RuntimeError, ValueError) as exc:
            self._handle_rpa_event({
                "type": "rpa.bridge",
                "state": "error",
                "message": str(exc),
            })

    def _handle_botmux_state(self, state: dict) -> None:
        self._botmux_state = state
        session = state.get("session") if isinstance(state.get("session"), dict) else {}
        signature = (
            state.get("connected"),
            state.get("kind"),
            state.get("active"),
            state.get("attention"),
            session.get("sessionId"),
            session.get("status"),
            session.get("title"),
            str(session.get("agentAttention") or ""),
        )
        changed = signature != self._botmux_signature
        self._botmux_signature = signature
        self._apply_activity_animation()
        if changed and state.get("connected") and state.get("kind") in {"working", "attention"}:
            self.ShowBotmuxStatus()

    def _handle_rpa_event(self, event: dict) -> None:
        if event.get("type") != "rpa.job":
            if event.get("state") == "error":
                self._show_bubble_text(f"影刀桥接启动失败：{event.get('message', '未知错误')}")
            return
        job = event.get("job")
        if not isinstance(job, dict):
            return
        self._rpa_state = job
        self._apply_activity_animation()
        workflow = job.get("workflow") or "影刀工作流"
        state = job.get("state")
        if state in {"accepted", "running"}:
            text = f"{workflow}正在执行，请暂时不要操作鼠标。"
        elif state == "completed":
            text = f"{workflow}已经完成。"
        elif state in {"failed", "cancelled"}:
            text = f"{workflow}执行未完成：{job.get('message') or state}"
        else:
            text = str(job.get("message") or workflow)
        self._show_bubble_text(text)

    def _activity_kind(self) -> str:
        if isinstance(self._rpa_state, dict) and self._rpa_state.get("state") in {"accepted", "running"}:
            return "working"
        return str(self._botmux_state.get("kind") or "offline")

    def _apply_activity_animation(self) -> None:
        if self._character_key != "xier":
            return
        kind = self._activity_kind()
        if kind == "working":
            gif_name = "bss_write.gif"
        elif kind == "attention":
            gif_name = "bss_next.gif"
        else:
            gif_name = "bss.gif"
        self.set_character_gif(
            os.path.join(get_base_dir(), "image", gif_name),
            update_identity=False,
        )

    def _botmux_status_text(self) -> str:
        state = self._botmux_state
        if not self._botmux_config.get("enabled"):
            return "Botmux 尚未启用，请配置 botmux_config.json。"
        if not state.get("connected"):
            detail = state.get("error") or "服务未连接"
            return f"Botmux 当前离线：{detail}"
        active = int(state.get("active") or 0)
        attention = int(state.get("attention") or 0)
        session = state.get("session") if isinstance(state.get("session"), dict) else {}
        bot_name = session.get("botName") or "机器人"
        title = (
            session.get("title")
            or session.get("previewUserText")
            or session.get("chatDisplayName")
            or ""
        )
        if state.get("kind") == "attention":
            attention_info = session.get("agentAttention")
            reason = attention_info.get("reason") if isinstance(attention_info, dict) else ""
            return f"{bot_name}需要你处理：{reason or title or '等待确认'}"
        if state.get("kind") == "working":
            return f"{bot_name}正在处理：{title or '当前任务'}"
        if active:
            latest = session.get("previewBotText")
            if latest:
                return f"{bot_name}刚刚回复：{latest}"
            return f"{active} 个机器人会话在线，当前等待新任务。"
        if attention:
            return f"有 {attention} 个任务需要处理。"
        return "Botmux 已连接，目前没有活跃任务。"

    def _show_bubble_text(self, text: str) -> None:
        if not text or not self.isVisible() or self.isMinimized():
            return
        self._bubble.set_text(str(text))
        self._bubble.show_at(self._bubble_global_pos())
        self._bubble_hide_timer.start(7000)

    def ShowBotmuxStatus(self) -> None:
        self._show_bubble_text(self._botmux_status_text())

    def OpenBotmuxDashboard(self) -> None:
        url = str(self._botmux_config.get("dashboard_url") or "").strip()
        if not url or not open_external(url):
            QMessageBox.warning(self, "Botmux", "无法打开 Botmux Dashboard。")

    def StartMacByteBootstrap(self) -> None:
        if not mac_byte_bootstrap.is_mac_byte():
            return
        if self._bootstrap_thread and self._bootstrap_thread.is_alive():
            self._show_bubble_text("Botmux 安装终端已经打开。")
            return
        self._bootstrap_thread = threading.Thread(
            target=self._run_mac_byte_bootstrap,
            name="seele-mac-byte-bootstrap",
            daemon=True,
        )
        self._bootstrap_thread.start()

    def _run_mac_byte_bootstrap(self) -> None:
        try:
            mode = mac_byte_bootstrap.bootstrap_mode()
            script = mac_byte_bootstrap.launch_bootstrap(mode=mode)
            if script is None:
                state = "ready" if mode == "ready" else "running"
                self._integration_signals.bootstrap_event.emit({"state": state})
                return
            self._integration_signals.bootstrap_event.emit({
                "state": "launched",
                "mode": mode,
            })
        except (OSError, RuntimeError, ValueError) as exc:
            self._integration_signals.bootstrap_event.emit({
                "state": "error",
                "message": str(exc),
            })

    def _handle_bootstrap_event(self, event: dict) -> None:
        state = event.get("state")
        if state == "launched":
            if event.get("mode") == "full":
                text = "未检测到 Botmux，已打开安装终端。登录时请按终端提示操作。"
            else:
                text = "Botmux 尚未配置，已打开扫码配置终端。"
            self._show_bubble_text(text)
        elif state == "running":
            self._show_bubble_text("Botmux 安装终端已经打开。")
        elif state == "error":
            self._show_bubble_text(f"Botmux 安装启动失败：{event.get('message') or '未知错误'}")

    def OpenInput(self) -> None:
        VoiceToText.request_input()

    def shutdown(self) -> None:
        VoiceToText.stop()
        self._botmux_monitor.stop()
        self._rpa_bridge.stop()
        unsubscribe = getattr(self, "_unsubscribe_rpa_events", None)
        if callable(unsubscribe):
            unsubscribe()
            self._unsubscribe_rpa_events = None

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

    def set_character_gif(self, gif_path: str, update_identity: bool = True) -> bool:
        if not gif_path or not os.path.exists(gif_path):
            return False
        normalized_path = os.path.abspath(gif_path)
        if os.path.abspath(getattr(self, "_current_gif_path", "")) == normalized_path:
            return True
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
        self.movie.frameChanged.connect(self.resize_movie)
        self.movie.start()
        self.resize_movie(0)
        self._current_gif_path = normalized_path

        # Update character identity for bubble messages.
        if update_identity:
            self._base_gif_path = normalized_path
            self._character_key = self._character_key_from_gif_path(gif_path)
            self._character_name = self._character_display_name(self._character_key)
            if hasattr(self, "_botmux_state"):
                QTimer.singleShot(0, self._apply_activity_animation)
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
        self.Menu.setStyleSheet(
            "QMenu { padding: 4px; }"
            "QMenu::icon { width: 18px; height: 18px; }"
            "QMenu::item { padding: 6px 14px; }"
        )

        show_legacy_controls = not mac_byte_bootstrap.is_mac_byte()
        if show_legacy_controls:
            self.custom_voice = QAction(QIcon(os.path.join(get_base_dir(), "image", "bs_icon.png")), u"自定义语音唤醒", self)
            self.Menu.addAction(self.custom_voice)

            self.out_voice = QAction(QIcon(os.path.join(get_base_dir(), "image", "bs_icon.png")), u"语音输入设置", self)
            self.Menu.addAction(self.out_voice)

        self.change_role = QAction(QIcon(os.path.join(get_base_dir(), "image", "bs_icon.png")), u"换个角色", self)
        self.Menu.addAction(self.change_role)

        if show_legacy_controls:
            self.startup = QAction(QIcon(os.path.join(get_base_dir(), "image", "bs_icon.png")), u"启动方式", self)
            self.Menu.addAction(self.startup)

            self.open_input = QAction(QIcon(os.path.join(get_base_dir(), "image", "bs_icon.png")), u"唤醒输入", self)
            self.Menu.addAction(self.open_input)

        self.botmux_status = QAction(QIcon(os.path.join(get_base_dir(), "image", "bs_icon.png")), u"机器人状态", self)
        self.Menu.addAction(self.botmux_status)

        self.botmux_dashboard = QAction(QIcon(os.path.join(get_base_dir(), "image", "bs_icon.png")), u"打开 Botmux", self)
        self.Menu.addAction(self.botmux_dashboard)

        self.StartTray = QAction(QIcon(os.path.join(get_base_dir(), "image", "bs_icon.png")), u"退置托盘", self)
        self.Menu.addAction(self.StartTray)

        self.CloseWindowAction = QAction(QIcon(os.path.join(get_base_dir(), "image", "Quit.png")), u"退出程序", self)
        self.Menu.addAction(self.CloseWindowAction)

        if show_legacy_controls:
            self.out_voice.triggered.connect(self.WeatherForecast)
            self.custom_voice.triggered.connect(self.ProgramsConfig)
            self.open_input.triggered.connect(self.OpenInput)
            self.startup.triggered.connect(self.Startup)
        self.change_role.triggered.connect(self.ChangeRole)
        self.botmux_status.triggered.connect(self.ShowBotmuxStatus)
        self.botmux_dashboard.triggered.connect(self.OpenBotmuxDashboard)
        self.StartTray.triggered.connect(self.SetTray)
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
        self.shutdown()
        self.close()
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
        if self._activity_kind() in {"working", "attention"}:
            if isinstance(self._rpa_state, dict) and self._rpa_state.get("state") in {"accepted", "running"}:
                workflow = self._rpa_state.get("workflow") or "影刀工作流"
                self._show_bubble_text(f"{workflow}正在执行，请暂时不要操作鼠标。")
            else:
                self.ShowBotmuxStatus()
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
        if self.outvoice is not None:
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
        self.shutdown()
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
    app.aboutToQuit.connect(Window.shutdown)
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
    if not mac_byte_bootstrap.is_mac_byte():
        VoiceToText.run()
    app.exec_()

if __name__ == "__main__":
    main()
