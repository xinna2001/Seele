import write_file as wf
import os
import sys
import subprocess
import threading
import time
from queue import Queue, Empty
import pyautogui
import keyboard
import play_vioce as pv
import falseIntent as fi
CONTROLLER = True


def get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


# Cross-thread input requests: keyboard callback thread -> Qt main thread.
_INPUT_REQUESTS: "Queue[Queue]" = Queue()
_QT_POLL_TIMER = None
_ACTIVE_INPUT_DIALOG = None

def run_tasklist():
    # 使用 cmd 执行 tasklist 命令
    # 使用 cmd 执行 tasklist 命令
    cmd = 'tasklist /fi "imagename eq ShadowBotBrowser*"'
    # 使用 subprocess 执行命令
    result = subprocess.run(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    # 获取标准输出和错误输出
    stdout = result.stdout
    return stdout

def _execute_win_h_if_enabled():
    try:
        if (wf.read_dict_from_json("state.json") or {}).get("stt_state") == "True":
            pyautogui.hotkey("win", "h")
    except Exception:
        pass


def _create_input_dialog_qt():
    """Create the input dialog. Must run on Qt main thread."""
    from PyQt5.QtCore import Qt, QRectF, QTimer
    from PyQt5.QtGui import QPixmap, QPainter, QPainterPath, QTextOption
    from PyQt5.QtWidgets import (
        QApplication,
        QDialog,
        QFrame,
        QHBoxLayout,
        QLabel,
        QPushButton,
        QPlainTextEdit,
        QSizePolicy,
        QVBoxLayout,
    )

    class SeeleInputDialog(QDialog):
        def __init__(self):
            super().__init__()
            self._drag_pos = None
            self._bg = QPixmap(os.path.join(get_base_dir(), "image", "bs.png"))
            self.setWindowTitle("想跟希儿说点什么呢~")
            # Non-modal window: keep desktop wife draggable/right-clickable while dialog is open.
            self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
            self.setAttribute(Qt.WA_TranslucentBackground, True)
            self.resize(800, 750)

            root = QVBoxLayout(self)
            root.setContentsMargins(18, 18, 18, 18)
            root.setSpacing(14)

            card = QFrame(self)
            card.setObjectName("input_card")
            card.setStyleSheet(
                "#input_card { background-color: rgba(255, 255, 255, 210); border-radius: 22px; }"
                "QLabel { color: #111; }"
                "QPlainTextEdit { border-radius: 16px; padding: 18px 18px; font-size: 26px; }"
                "QPushButton { border-radius: 18px; padding: 14px 22px; font-size: 22px; }"
            )

            main = QVBoxLayout(card)
            main.setContentsMargins(32, 22, 32, 22)
            main.setSpacing(10)

            # Make the content block compact and vertically centered.
            main.addStretch(1)
            title = QLabel("想跟希儿说点什么呢~", card)
            title.setStyleSheet("font-size: 26px; font-weight: 600;")
            title.setAlignment(Qt.AlignCenter)
            main.addWidget(title)

            tip = QLabel("支持多行输入，Ctrl+Enter快速提交", card)
            tip.setStyleSheet("font-size: 18px;")
            tip.setAlignment(Qt.AlignCenter)
            main.addWidget(tip)

            self.edit = QPlainTextEdit(card)
            self.edit.setPlaceholderText("在这里输入...")
            # Auto wrap at widget width, no horizontal scrollbar.
            self.edit.setLineWrapMode(QPlainTextEdit.WidgetWidth)
            self.edit.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
            self.edit.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            # Layout stretch can override minimumHeight; fix the height explicitly.
            self.edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.edit.setFixedHeight(180)
            main.addWidget(self.edit, 0)

            btn_row = QHBoxLayout()
            btn_row.setSpacing(18)
            cancel_btn = QPushButton("关闭", card)
            cancel_btn.setStyleSheet(
                "QPushButton { background-color: #e9edf5; color: #111; }"
                "QPushButton:hover { background-color: #dfe5ee; }"
            )
            ok_btn = QPushButton("确认", card)
            ok_btn.setStyleSheet(
                "QPushButton { background-color: #4f8cff; color: white; }"
                "QPushButton:hover { background-color: #3b74df; }"
            )
            cancel_btn.clicked.connect(self.reject)
            ok_btn.clicked.connect(self.accept)
            btn_row.addWidget(cancel_btn)
            btn_row.addWidget(ok_btn)
            main.addLayout(btn_row)

            main.addStretch(1)

            card.setFixedSize(720, 420)
            root.addStretch(2)
            root.addWidget(card, 0, Qt.AlignCenter)
            root.addStretch(2)

            # Focus + optional Win+H trigger
            self.edit.setFocus()
            QTimer.singleShot(300, _execute_win_h_if_enabled)

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

        def mousePressEvent(self, event):
            if event.button() == Qt.LeftButton:
                self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
                event.accept()

        def mouseMoveEvent(self, event):
            if (event.buttons() & Qt.LeftButton) and self._drag_pos is not None:
                self.move(event.globalPos() - self._drag_pos)
                event.accept()

        def mouseReleaseEvent(self, event):
            self._drag_pos = None
            event.accept()

        def keyPressEvent(self, event):
            if event.key() == Qt.Key_Escape:
                self.reject()
                return
            if event.key() in (Qt.Key_Return, Qt.Key_Enter) and (event.modifiers() & Qt.ControlModifier):
                self.accept()
                return
            super().keyPressEvent(event)

    app = QApplication.instance()
    if not app:
        return None

    return SeeleInputDialog()


def get_user_input() -> str:
    """
    Thread-safe request for user input.
    Keyboard callback runs in a non-Qt thread; UI must be shown on Qt main thread.
    """
    # If Qt isn't available, just return empty (no action).
    try:
        from PyQt5.QtWidgets import QApplication
    except Exception:
        return ""
    if not QApplication.instance():
        return ""
    reply: "Queue[str]" = Queue(maxsize=1)
    _INPUT_REQUESTS.put(reply)
    # Block until UI completes.
    return reply.get()


def _poll_input_requests():
    # Runs on Qt main thread via QTimer.
    global _ACTIVE_INPUT_DIALOG
    while True:
        try:
            reply = _INPUT_REQUESTS.get_nowait()
        except Empty:
            return
        # If the dialog is already open, don't open another one; just focus it
        # and return empty to the new request so the hotkey handler can exit.
        if _ACTIVE_INPUT_DIALOG is not None:
            try:
                _ACTIVE_INPUT_DIALOG.raise_()
                _ACTIVE_INPUT_DIALOG.activateWindow()
            except Exception:
                pass
            try:
                reply.put_nowait("")
            except Exception:
                pass
            continue

        dlg = None
        try:
            dlg = _create_input_dialog_qt()
        except Exception:
            dlg = None

        if dlg is None:
            try:
                reply.put_nowait("")
            except Exception:
                pass
            continue

        _ACTIVE_INPUT_DIALOG = dlg

        def _finish(accepted: bool):
            nonlocal reply, dlg
            global _ACTIVE_INPUT_DIALOG
            text = ""
            if accepted:
                try:
                    text = (dlg.edit.toPlainText() or "").strip()
                except Exception:
                    text = ""
            try:
                reply.put_nowait(text)
            except Exception:
                pass
            try:
                dlg.close()
                dlg.deleteLater()
            except Exception:
                pass
            _ACTIVE_INPUT_DIALOG = None

        dlg.accepted.connect(lambda: _finish(True))
        dlg.rejected.connect(lambda: _finish(False))
        dlg.show()
        try:
            dlg.raise_()
            dlg.activateWindow()
        except Exception:
            pass
def file_yingdao(text):
    if ".txt" in text:
        text = text[:-4]
    text = text.replace(" ", "")
    command = f"cmd /c echo . >D:/SeeleTools/"+wf.read_dict_from_json("file_name.json").get(text)+".txt"
    # 创建启动信息对象以隐藏窗口
    startup_info = subprocess.STARTUPINFO()
    startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup_info.wShowWindow = subprocess.SW_HIDE
    try:
        # 执行命令并隐藏窗口
        subprocess.run(command, shell=True, check=True, text=True,
                       capture_output=True, startupinfo=startup_info)
    except subprocess.CalledProcessError:
        pass
def cmd_yingdao(uid):
    uid = str(uid)
    user_profile = os.environ.get("USERPROFILE") or os.path.expanduser("~")
    desktop_dirs = [os.path.join(user_profile, "Desktop")]
    public_profile = os.environ.get("PUBLIC")
    if public_profile:
        desktop_dirs.append(os.path.join(public_profile, "Desktop"))
    for key in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial"):
        onedrive = os.environ.get(key)
        if onedrive:
            desktop_dirs.append(os.path.join(onedrive, "Desktop"))

    link_path = None
    for desktop_dir in desktop_dirs:
        candidate = os.path.join(desktop_dir, "影刀.lnk")
        if os.path.exists(candidate):
            link_path = candidate
            break
    if link_path is None:
        link_path = os.path.join(desktop_dirs[0], "影刀.lnk")

    print(f"\"{link_path}\" shadowbot:Run?robot-uuid={uid}")
    command = f"\"{link_path}\" shadowbot:Run?robot-uuid={uid}"
    # 创建启动信息对象以隐藏窗口
    startup_info = subprocess.STARTUPINFO()
    startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup_info.wShowWindow = subprocess.SW_HIDE
    try:
        # 执行命令并隐藏窗口
        subprocess.run(command, shell=True, check=True, text=True,
                       capture_output=True, startupinfo=startup_info)
    except subprocess.CalledProcessError:
        pass

def text_intent(text):
    if not text or not str(text).strip():
        return
    pv.main("3.wav")
    text=fi.main(text)
    if text=="创建工作":
        cmd_yingdao("")
    else:
        try:
            if wf.read_dict_from_json("state.json").get('startup_mode') == "fast":
                if "没有运行的任务" in run_tasklist():
                    pv.main("11.wav")
                else:
                    file_yingdao(text)
            else:
                data = wf.read_dict_from_json("uid.json")
                uid=data.get(text,-1)
                if uid==-1:
                    pv.main("4.wav")
                else:
                    cmd_yingdao(uid)
        except :
            pv.main("4.wav")


def _handle_hotkey():
    text = get_user_input()
    if not text or not text.strip():
        return
    text_intent(text.strip())


def main():
    global CONTROLLER
    hotkey = 'ctrl+`'
    # 添加热键（仅添加一次）
    keyboard.add_hotkey(hotkey, _handle_hotkey)

    try:
        while CONTROLLER:
            time.sleep(0.1)  # 空循环保持线程运行
    finally:
        # 退出时移除热键并停止监听
        keyboard.remove_hotkey(hotkey)
        keyboard.unhook_all()


def run() -> None:
    start = threading.Thread(target=main)
    start.start()
    # Install Qt poller timer (main thread) so hotkey thread can request UI safely.
    global _QT_POLL_TIMER
    try:
        from PyQt5.QtCore import QTimer
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance()
        if app and _QT_POLL_TIMER is None:
            _QT_POLL_TIMER = QTimer()
            _QT_POLL_TIMER.setInterval(50)
            _QT_POLL_TIMER.timeout.connect(_poll_input_requests)
            _QT_POLL_TIMER.start()
    except Exception:
        pass
