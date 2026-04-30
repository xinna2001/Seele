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
from PyQt5.QtWidgets import QFrame, QScrollArea, QSizePolicy


def get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def _json_path(name: str) -> str:
    return os.path.join(get_base_dir(), name)


class ManageWakeWordsWindow(QWidget):
    """
    Manage (edit/delete) existing wake words.
    mode:
      - "uid": edit uid.json (slow startup mode)
      - "file": edit file_name.json (fast startup mode)
    """
    # Built-in workflows shipped with the app. These should NOT be shown in the
    # "manage user wake words" view. Only user-added items are listed.
    _DEFAULT_UID_KEYS = {
        "初始化",
        "下载ppt",
        "执行代码",
        "调研ppt",
        "生成视频",
        "生成网页",
        "查询动漫",
        "部署项目一",
        "京东数据抓取",
        "点星",
    }
    _DEFAULT_FILE_KEYS = {
        "下载ppt",
        "工资邮件",
        "执行代码",
        "调研ppt",
        "生成视频",
        "生成网页",
        "查询动漫",
        "部署项目一",
        "京东数据抓取",
        "点星",
    }
    _PROTECTED_KEYS = {"初始化"}

    def __init__(self, mode: str) -> None:
        super().__init__()
        self._mode = mode if mode in ("uid", "file") else "uid"
        self._drag_pos = None
        self._bg = QPixmap(os.path.join(get_base_dir(), "image", "bs.png"))
        self.setWindowTitle("修改已有唤醒词")
        self.setWindowIcon(QIcon(os.path.join(get_base_dir(), "image", "bs_icon.ico")))
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        # Wider than the add-config window so the "uid" and operation buttons fit.
        self.resize(1180, 820)
        self.setMinimumSize(1180, 820)
        self._row_widgets = []
        self.ui()

    def _hidden_default_keys(self) -> set:
        if self._mode == "uid":
            return set(self._DEFAULT_UID_KEYS)
        return set(self._DEFAULT_FILE_KEYS)

    def _data_file(self) -> str:
        return _json_path("uid.json") if self._mode == "uid" else _json_path("file_name.json")

    def _value_label(self) -> str:
        return "uid" if self._mode == "uid" else "txt文件名称"

    def _read_data(self) -> dict:
        data = wf.read_dict_from_json(self._data_file()) or {}
        if not isinstance(data, dict):
            return {}
        return data

    def _write_data(self, data: dict) -> None:
        wf.write_dict_to_json(data, self._data_file())

    def ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(18, 18, 18, 18)
        root_layout.setSpacing(14)

        self.card = QFrame(self)
        self.card.setObjectName("manage_card")
        self.card.setStyleSheet(
            "#manage_card { background-color: rgba(255, 255, 255, 210); border-radius: 22px; }"
            "QLabel { color: #111; }"
            "QPushButton { border-radius: 18px; padding: 12px 18px; font-size: 24px; }"
        )

        main_layout = QVBoxLayout(self.card)
        main_layout.setContentsMargins(32, 28, 32, 28)
        main_layout.setSpacing(16)

        title = QLabel("修改已有唤醒词", self.card)
        title.setStyleSheet("font-size: 28px; font-weight: 600;")
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        tip = QLabel("这里只显示用户新增的唤醒词（预设工作流不会出现在这里）", self.card)
        tip.setStyleSheet("font-size: 24px;")
        tip.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(tip)

        header = QHBoxLayout()
        header.setSpacing(12)
        h_word = QLabel("唤醒词", self.card)
        h_word.setStyleSheet("font-size: 24px; font-weight: 600;")
        h_val = QLabel(self._value_label(), self.card)
        h_val.setStyleSheet("font-size: 24px; font-weight: 600;")
        h_ops = QLabel("操作", self.card)
        h_ops.setStyleSheet("font-size: 24px; font-weight: 600;")
        # Keep the operations area visible; let value column expand/shrink.
        h_word.setFixedWidth(260)
        h_ops.setFixedWidth(280)
        header.addWidget(h_word)
        header.addWidget(h_val)
        header.addStretch(1)
        header.addWidget(h_ops)
        main_layout.addLayout(header)

        self.scroll = QScrollArea(self.card)
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        # Allow horizontal scrolling as a safety net (prevents clipped buttons).
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.list_container = QWidget(self.scroll)
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(10)
        self.list_layout.addStretch(1)
        self.scroll.setWidget(self.list_container)
        main_layout.addWidget(self.scroll, 1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(18)
        close_btn = QPushButton("关闭", self.card)
        close_btn.setMinimumHeight(72)
        close_btn.clicked.connect(self.close)
        btn_row.addStretch(1)
        btn_row.addWidget(close_btn)
        main_layout.addLayout(btn_row)

        # Do not hard-fix the card size: on smaller screens fixed width can clip
        # the operation buttons. Let it expand with the window.
        self.card.setMinimumSize(980, 700)
        self.card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        root_layout.addStretch(2)
        root_layout.addWidget(self.card, 0, Qt.AlignCenter)
        root_layout.addStretch(2)
        self.setLayout(root_layout)

        self.refresh()

    def refresh(self) -> None:
        # Clear existing row widgets (keep the final stretch).
        for w in self._row_widgets:
            try:
                w.setParent(None)
                w.deleteLater()
            except Exception:
                pass
        self._row_widgets = []

        data = self._read_data()
        hidden = self._hidden_default_keys().union(self._PROTECTED_KEYS)
        items = [(k, data.get(k)) for k in sorted(data.keys()) if k not in hidden]

        # Remove last stretch, then re-add after rows.
        try:
            last_item = self.list_layout.takeAt(self.list_layout.count() - 1)
            if last_item is not None and last_item.spacerItem() is None:
                # Put it back if it wasn't the stretch.
                self.list_layout.addItem(last_item)
        except Exception:
            pass

        if not items:
            empty = QLabel("暂无可修改的唤醒词（只显示用户新增项）。", self.list_container)
            empty.setStyleSheet("font-size: 24px; color: #333;")
            self.list_layout.addWidget(empty)
            self._row_widgets.append(empty)
            self.list_layout.addStretch(1)
            return

        for word, val in items:
            row = QFrame(self.list_container)
            row.setStyleSheet("QFrame { background-color: rgba(255,255,255,210); border-radius: 16px; }")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(16, 12, 16, 12)
            row_layout.setSpacing(12)

            word_lbl = QLabel(str(word), row)
            word_lbl.setStyleSheet("font-size: 24px;")
            word_lbl.setFixedWidth(260)

            full_val = "" if val is None else str(val)
            val_lbl = QLabel(full_val, row)
            val_lbl.setStyleSheet("font-size: 24px;")
            # Let the value column shrink; show full value on hover.
            val_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            val_lbl.setToolTip(full_val)
            val_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)

            edit_btn = QPushButton("修改", row)
            edit_btn.setMinimumHeight(56)
            del_btn = QPushButton("删除", row)
            del_btn.setMinimumHeight(56)
            # Keep operation buttons visible and easy to click.
            edit_btn.setMinimumWidth(120)
            del_btn.setMinimumWidth(120)

            edit_btn.clicked.connect(lambda _=False, w=word: self._edit_item(w))
            del_btn.clicked.connect(lambda _=False, w=word: self._delete_item(w))

            row_layout.addWidget(word_lbl, 0)
            row_layout.addWidget(val_lbl, 1)
            row_layout.addWidget(edit_btn, 0)
            row_layout.addWidget(del_btn, 0)

            self.list_layout.addWidget(row)
            self._row_widgets.append(row)

        self.list_layout.addStretch(1)

    def _edit_item(self, old_word: str) -> None:
        data = self._read_data()
        if old_word not in data:
            QMessageBox.information(self, "提示", "该唤醒词不存在，可能已被删除。")
            self.refresh()
            return
        dlg = _EditWakeWordDialog(
            mode=self._mode,
            old_word=old_word,
            old_value=str(data.get(old_word, "")),
            parent=self,
        )
        dlg.saved.connect(lambda new_word, new_val: self._apply_edit(old_word, new_word, new_val))
        dlg.deleted.connect(lambda: self._delete_item(old_word))
        dlg.show()

    def _apply_edit(self, old_word: str, new_word: str, new_val: str) -> None:
        new_word = (new_word or "").strip()
        new_val = (new_val or "").strip()
        if not new_word or not new_val:
            QMessageBox.warning(self, "警告", "唤醒词和内容都不能为空。")
            return
        if new_word in self._PROTECTED_KEYS:
            QMessageBox.warning(self, "警告", f"唤醒词「{new_word}」为系统保留项，不能修改为该名称。")
            return

        data = self._read_data()
        if old_word not in data:
            QMessageBox.information(self, "提示", "该唤醒词不存在，可能已被删除。")
            self.refresh()
            return

        # Rename key if needed.
        if new_word != old_word and new_word in data:
            ret = QMessageBox.question(self, "确认覆盖", f"唤醒词「{new_word}」已存在，是否覆盖？")
            if ret != QMessageBox.Yes:
                return

        if new_word != old_word:
            try:
                del data[old_word]
            except KeyError:
                pass
        data[new_word] = new_val
        self._write_data(data)
        QMessageBox.information(self, "提示", "修改成功！", QMessageBox.Yes)
        self.refresh()

    def _delete_item(self, word: str) -> None:
        if word in self._PROTECTED_KEYS:
            QMessageBox.warning(self, "警告", "该唤醒词为系统保留项，不能删除。")
            return
        data = self._read_data()
        if word not in data:
            self.refresh()
            return
        ret = QMessageBox.question(self, "确认删除", f"确定删除唤醒词「{word}」吗？")
        if ret != QMessageBox.Yes:
            return
        try:
            del data[word]
        except KeyError:
            pass
        self._write_data(data)
        QMessageBox.information(self, "提示", "已删除。", QMessageBox.Yes)
        self.refresh()

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


class _EditWakeWordDialog(QWidget):
    """
    Lightweight edit dialog for a single wake word entry.
    Emits:
      - saved(new_word, new_value)
      - deleted()
    """
    # Avoid importing PyQt5.QtCore.pyqtSignal at top-level if not needed elsewhere.
    from PyQt5.QtCore import pyqtSignal
    saved = pyqtSignal(str, str)
    deleted = pyqtSignal()

    def __init__(self, mode: str, old_word: str, old_value: str, parent=None) -> None:
        super().__init__(parent)
        self._mode = mode if mode in ("uid", "file") else "uid"
        self._drag_pos = None
        self._bg = QPixmap(os.path.join(get_base_dir(), "image", "bs.png"))
        self.setWindowTitle("修改唤醒词")
        self.setWindowIcon(QIcon(os.path.join(get_base_dir(), "image", "bs_icon.ico")))
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(800, 750)
        self.setMinimumSize(800, 750)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(18, 18, 18, 18)
        root_layout.setSpacing(14)

        self.card = QFrame(self)
        self.card.setObjectName("edit_card")
        self.card.setStyleSheet(
            "#edit_card { background-color: rgba(255, 255, 255, 210); border-radius: 22px; }"
            "QLabel { color: #111; }"
            "QLineEdit { border-radius: 16px; padding: 12px 14px; font-size: 24px; }"
            "QPushButton { border-radius: 18px; padding: 14px 22px; font-size: 24px; }"
        )

        main_layout = QVBoxLayout(self.card)
        main_layout.setContentsMargins(32, 28, 32, 28)
        main_layout.setSpacing(22)

        title = QLabel("修改唤醒词", self.card)
        title.setStyleSheet("font-size: 28px; font-weight: 600;")
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        tip = QLabel("你可以修改或删除该唤醒词。", self.card)
        tip.setStyleSheet("font-size: 24px;")
        tip.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(tip)

        form_layout = QVBoxLayout()
        form_layout.setSpacing(16)

        self.word_text = QLineEdit(self.card)
        self.word_text.setPlaceholderText("唤醒词")
        self.word_text.setMinimumHeight(62)
        self.word_text.setText(old_word or "")

        self.value_text = QLineEdit(self.card)
        self.value_text.setPlaceholderText("uid" if self._mode == "uid" else "txt文件名称")
        self.value_text.setMinimumHeight(62)
        self.value_text.setText(old_value or "")

        form_layout.addWidget(self.word_text)
        form_layout.addWidget(self.value_text)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(18)
        save_btn = QPushButton("保存", self.card)
        save_btn.setMinimumHeight(78)
        del_btn = QPushButton("删除", self.card)
        del_btn.setMinimumHeight(78)
        close_btn = QPushButton("关闭", self.card)
        close_btn.setMinimumHeight(78)

        save_btn.clicked.connect(self._on_save)
        del_btn.clicked.connect(self._on_delete)
        close_btn.clicked.connect(self.close)

        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(del_btn)
        btn_layout.addWidget(close_btn)

        main_layout.addStretch(1)
        main_layout.addLayout(form_layout)
        main_layout.addLayout(btn_layout)
        main_layout.addStretch(1)

        self.card.setFixedSize(720, 520)
        root_layout.addStretch(2)
        root_layout.addWidget(self.card, 0, Qt.AlignCenter)
        root_layout.addStretch(2)
        self.setLayout(root_layout)

    def _on_save(self) -> None:
        self.saved.emit(self.word_text.text().strip(), self.value_text.text().strip())
        self.close()

    def _on_delete(self) -> None:
        self.deleted.emit()
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
            "QLineEdit { border-radius: 16px; padding: 12px 14px; font-size: 24px; }"
            "QPushButton { border-radius: 18px; padding: 14px 22px; font-size: 24px; }"
        )

        main_layout = QVBoxLayout(self.card)
        main_layout.setContentsMargins(32, 28, 32, 28)
        main_layout.setSpacing(22)

        title = QLabel("自定义语音唤醒", self.card)
        title.setStyleSheet("font-size: 26px; font-weight: 600;")
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        tip = QLabel("输入 uid 和唤醒词，留空则不记录", self.card)
        tip.setStyleSheet("font-size: 24px;")
        tip.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(tip)

        form_layout = QVBoxLayout()
        form_layout.setSpacing(16)

        label = QLabel("输入 uid 和唤醒词", self.card)
        label.setStyleSheet("font-size: 24px; font-weight: 600;")
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
        manage_btn = QPushButton("修改已有唤醒词", self.card)
        manage_btn.setMinimumHeight(78)
        manage_btn.clicked.connect(self.OpenManage)
        cancel_btn = QPushButton("关闭", self.card)
        cancel_btn.setMinimumHeight(78)
        cancel_btn.clicked.connect(self.close)
        btn_layout.addWidget(confirm_btn)
        btn_layout.addWidget(manage_btn)
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

    def OpenManage(self) -> None:
        self.ManageWindow = ManageWakeWordsWindow(mode="uid")
        self.ManageWindow.show()

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
            "QLineEdit { border-radius: 16px; padding: 12px 14px; font-size: 24px; }"
            "QPushButton { border-radius: 18px; padding: 14px 22px; font-size: 24px; }"
        )

        main_layout = QVBoxLayout(self.card)
        main_layout.setContentsMargins(32, 28, 32, 28)
        main_layout.setSpacing(22)

        title = QLabel("自定义语音唤醒", self.card)
        title.setStyleSheet("font-size: 26px; font-weight: 600;")
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        tip = QLabel("输入文件名和唤醒词，留空则不记录", self.card)
        tip.setStyleSheet("font-size: 24px;")
        tip.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(tip)

        form_layout = QVBoxLayout()
        form_layout.setSpacing(16)

        label = QLabel("输入 txt 文件名称和唤醒词", self.card)
        label.setStyleSheet("font-size: 24px; font-weight: 600;")
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
        manage_btn = QPushButton("修改已有唤醒词", self.card)
        manage_btn.setMinimumHeight(78)
        manage_btn.clicked.connect(self.OpenManage)
        cancel_btn = QPushButton("关闭", self.card)
        cancel_btn.setMinimumHeight(78)
        cancel_btn.clicked.connect(self.close)
        btn_layout.addWidget(confirm_btn)
        btn_layout.addWidget(manage_btn)
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

    def OpenManage(self) -> None:
        self.ManageWindow = ManageWakeWordsWindow(mode="file")
        self.ManageWindow.show()

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
