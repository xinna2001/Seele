"""Qt main-thread controller for background checks and user-triggered updates."""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import threading
from pathlib import Path

from PyQt5.QtCore import QObject, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QIcon, QPainter, QPixmap
from PyQt5.QtWidgets import QAction, QApplication, QMessageBox

import app_update
from platform_utils import get_edition, migrate_settings


class UpdateController(QObject):
    result = pyqtSignal(object, str, bool)
    prepared = pyqtSignal(str)
    progress = pyqtSignal(int)
    failed = pyqtSignal(str)

    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.release = None
        self.busy = False
        self.stopped = False
        self.actions = []
        self._last_progress = -1
        self.result.connect(self._checked)
        self.prepared.connect(self._restart)
        self.failed.connect(self._failed)
        self.progress.connect(self._progress)
        self.timer = QTimer(self)
        self.timer.setInterval(60 * 60 * 1000)
        self.timer.timeout.connect(self.check)
        if os.environ.get("SEELE_DISABLE_UPDATES") != "1":
            self.timer.start()
            QTimer.singleShot(5000, self.check)
            QTimer.singleShot(1000, self._install_offer)
            QTimer.singleShot(2000, self._previous_result)

    def stop(self):
        self.stopped = True
        self.timer.stop()

    def action(self, parent) -> QAction:
        action = QAction("检查更新", parent)
        action.triggered.connect(self.clicked)
        action.destroyed.connect(lambda: self._forget(action))
        self.actions.append(action)
        self._decorate(action)
        return action

    def _forget(self, action):
        if action in self.actions:
            self.actions.remove(action)

    def _decorate(self, action):
        pixmap = QPixmap(18, 18)
        pixmap.fill(QColor(0, 0, 0, 0))
        if self.release:
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(QColor("#e74b53"))
            painter.setBrush(QColor("#e74b53"))
            painter.drawEllipse(5, 5, 8, 8)
            painter.end()
        action.setIcon(QIcon(pixmap))
        action.setEnabled(not self.busy)
        action.setToolTip(f"发现新版 {self.release.version}，点击安装"
                          if self.release else "检查 GitHub 上的最新正式版本")

    def _refresh(self):
        for action in self.actions:
            self._decorate(action)

    def _notify(self, message):
        self.window._show_bubble_text(message)
        if not self.window.isVisible():
            self.window._Tray.showMessage("Seele 更新", message)

    def _worker(self, function):
        threading.Thread(target=function, name="seele-updater", daemon=True).start()

    def check(self, manual=False):
        if self.stopped or self.busy:
            return
        self.busy = True
        self._refresh()

        def run():
            try:
                release = app_update.check_release()
                self.result.emit(release, "", manual)
            except Exception:
                self.result.emit(None, "暂时无法检查更新，请检查网络后重试。", manual)
        self._worker(run)

    def _checked(self, release, error, manual):
        if self.stopped:
            return
        self.busy = False
        if not error:
            self.release = release
        self._refresh()
        if manual:
            self._notify(error or (f"发现新版 {release.version}，再点「检查更新」即可安装。"
                                   if release else f"当前已是最新版本 {app_update.current_version()}。"))

    def clicked(self):
        if self.stopped or self.busy:
            return
        if self.release is None:
            self.check(manual=True)
            return
        thread = getattr(self.window, "_bootstrap_thread", None)
        if thread and thread.is_alive():
            self._notify("Botmux 安装正在进行，请完成后再更新 Seele。")
            return
        if app_update.install_root() is None:
            self._notify("当前为源码运行，请使用安装包体验自动更新。")
            return
        self.busy = True
        self._last_progress = -1
        self._refresh()
        self._notify(f"正在下载 Seele {self.release.version}…")
        release = self.release

        def run():
            work = None
            helper_started = False
            try:
                work, staged = app_update.stage_release(release, self.progress.emit)
                # Do not replace an application after the user has closed it.
                if self.stopped:
                    shutil.rmtree(work, ignore_errors=True)
                    return
                app_update.start_helper(work, staged, release)
                helper_started = True
                self.prepared.emit("新版校验完成，正在更新并重启…")
            except Exception as exc:
                if work and not helper_started and not (work / "job.json").exists():
                    shutil.rmtree(work, ignore_errors=True)
                self.failed.emit(f"更新未完成：{exc}")
        self._worker(run)

    def _progress(self, percent):
        if self.stopped:
            return
        bucket = percent // 25
        if bucket > self._last_progress:
            self._last_progress = bucket
            self._notify(f"正在下载更新：{percent}%")

    def _failed(self, error):
        if self.stopped:
            return
        self.busy = False
        self._refresh()
        self._notify(error)

    def _restart(self, message):
        if self.stopped:
            return
        self._notify(message)
        QApplication.instance().quit()

    def _previous_result(self):
        def run():
            app_update.cleanup_completed()
        self._worker(run)
        path = app_update.get_data_dir() / "update-status.json"
        try:
            import json
            status = json.loads(path.read_text())
            if not status.get("ok"):
                self._notify(status.get("error", "更新失败，已恢复原版本。"))
            path.unlink()
        except (OSError, ValueError):
            pass

    def _install_offer(self):
        if (self.stopped or self.busy or sys.platform != "darwin"
                or not getattr(sys, "frozen", False)
                or os.environ.get("QT_QPA_PLATFORM") == "offscreen"):
            return
        root = app_update.install_root()
        if root is None or root.parent in (Path("/Applications"), Path.home() / "Applications"):
            return
        try:
            migrate_settings()
            import json
            marker = app_update.get_data_dir() / "install-choice.json"
            if marker.exists() and json.loads(marker.read_text()).get("source") == str(root):
                return
            parent = Path("/Applications")
            if not os.access(parent, os.W_OK):
                parent = Path.home() / "Applications"
            target = parent / "Seele.app"
            text = f"将 Seele 安装到 {parent}？\n安装后会自动重启，以后可从「应用程序」打开。"
            if target.exists():
                text += "\n该位置已有 Seele，将替换应用并保留用户设置。"
            self.busy = True
            self._refresh()
            answer = QMessageBox.question(self.window, "安装 Seele", text,
                                          QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            if answer != QMessageBox.Yes:
                app_update.atomic_json(marker, {"source": str(root)})
                self.busy = False
                self._refresh()
                return
            if target.exists():
                resources = app_update.resources_in(target, "macos-arm64")
                existing = (resources / "VERSION").read_text().strip()
                if app_update.version_tuple(existing) > app_update.version_tuple(app_update.current_version()):
                    self.busy = False
                    self._refresh()
                    self._notify("应用程序中已有更高版本，已取消替换。")
                    return
                if (resources / "EDITION").read_text().strip() != get_edition():
                    self.busy = False
                    self._refresh()
                    self._notify("应用程序中已有不同类型的 Seele，请使用独立目录安装。")
                    return
            parent.mkdir(parents=True, exist_ok=True)
            work = Path(tempfile.mkdtemp(prefix="job-", dir=app_update.updates_dir()))
            release = app_update.Release(app_update.current_version(), get_edition(),
                                         "macos-arm64", "", "", "", "")
            self.busy = True
            self._refresh()
            self._notify("正在安装到应用程序…")

            def run():
                try:
                    app_update.start_helper(work, root, release, target=target, operation="install")
                    self.prepared.emit("安装完成，正在重启…")
                except Exception as exc:
                    self.failed.emit(f"安装未完成：{exc}")
            self._worker(run)
        except Exception as exc:
            self._failed(f"暂时无法安装：{exc}")
