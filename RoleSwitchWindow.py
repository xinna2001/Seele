import os
import random
import sys
import write_file as wf

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout, QMessageBox


def get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _json_path(name):
    return os.path.join(get_base_dir(), name)


class main(QWidget):
    def __init__(self, desktop_wife=None) -> None:
        super(main, self).__init__()
        self.desktop_wife = desktop_wife
        self.setWindowTitle("换个角色")
        self.setWindowIcon(QIcon(".\image\bs_icon.ico"))
        self.setStyleSheet("""
            QWidget {
                background-color: gray;
            }
            QLabel {
                color: black;
                background-color: white;
            }
            QPushButton {
                background-color: white;
            }
            QPushButton:hover {
                background-color: green;
            }
            QVBoxLayout {
                background-color: white;
            }
            QMessageBox {
                background-color: white;
                color: black;
            }
        """)
        self.resize(480, 120)
        self.ui()

    def ui(self) -> None:
        main_layout = QVBoxLayout(self)

        title = QLabel(self)
        title.setText("选择一个角色")
        title.setAlignment(Qt.AlignCenter)

        buttons_layout = QHBoxLayout()
        self.btn_aili = QPushButton(self)
        self.btn_aili.setText("爱莉希雅")
        self.btn_aili.clicked.connect(self.select_aili)

        self.btn_furina = QPushButton(self)
        self.btn_furina.setText("芙宁娜")
        self.btn_furina.clicked.connect(self.select_furina)

        self.btn_xier = QPushButton(self)
        self.btn_xier.setText("希儿")
        self.btn_xier.clicked.connect(self.select_xier)

        buttons_layout.addWidget(self.btn_aili)
        buttons_layout.addWidget(self.btn_furina)
        buttons_layout.addWidget(self.btn_xier)

        main_layout.addWidget(title)
        main_layout.addLayout(buttons_layout)
        self.setLayout(main_layout)

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

