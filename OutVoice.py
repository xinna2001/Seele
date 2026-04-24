
import sys
import write_file
from PyQt5.QtCore import Qt
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QWidget
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QMessageBox
class main(QWidget):
    def __init__(self) -> None:
        super(main, self).__init__()
        self.setWindowTitle("语音输入")
        self.setWindowIcon(QIcon(".\\image\\bs_icon.ico"))
        # 修改背景颜色，这里将其改为灰色
        self.setStyleSheet("""
            QWidget {
                background-color: gray;
            }
            QLabel {
                color: black;
                background-color: white;
            }
            QLineEdit {
                background-color: white;
            }
            QLineEdit:hover {
                background-color: black;
                color: white;
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
        # 调整页面大小，这里将其改为 400x100
        self.resize(400, 100)
        self.ui()

    def ui(self) -> None:
        __MainLayout = QVBoxLayout(self)

        __Yes_NoLayout = QHBoxLayout()
        __Yes = QPushButton(self)
        __Yes.setText("开启")
        __Yes.clicked.connect(self.YesEvent)
        __No = QPushButton(self)
        __No.setText("关闭")
        __No.clicked.connect(self.hide_event)

        __Yes_NoLayout.addWidget(__Yes)
        __Yes_NoLayout.addWidget(__No)

        __MainLayout.addLayout(__Yes_NoLayout)

    def YesEvent(self) -> None:
        dic = write_file.read_dict_from_json('state.json')
        dic["stt_state"] = "True"
        write_file.write_dict_to_json(dic, 'state.json')
        QMessageBox.information(self, "Programs Config Message", "语音输入已开启！", QMessageBox.Yes)

    def hide_event(self) -> None:
        dic = write_file.read_dict_from_json('state.json')
        dic["stt_state"] = "False"
        write_file.write_dict_to_json(dic, 'state.json')
        QMessageBox.information(self, "Programs Config Message", "语音输入已关闭！", QMessageBox.Yes)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = main()
    win.show()
    sys.exit(app.exec_())
