import json
import write_file as wf
from PyQt5.QtWidgets import QWidget
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout
from PyQt5.QtWidgets import QLineEdit, QMessageBox
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt

class main(QWidget):
    def __init__(self) -> None:
        super(main, self).__init__()
        self.setWindowTitle("自定义语音唤醒")
        self.setWindowIcon(QIcon(".\\image\\bs_icon.ico"))
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
                color: black;
            }
            QLineEdit:hover {
                background-color: #f0f0f0;
            }
            QLineEdit:focus {
                background-color: white;
                color: black;
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
        self.resize(400, 100)
        self.ui()
    
    def ui(self) -> None:
        __MainLayout = QVBoxLayout(self)

        __BaiDuYunHLayout = QVBoxLayout()
        __BaiDuYunLabel = QLabel(self)
        __BaiDuYunLabel.setText("输入uid和唤醒词")

        self.uid_text = QLineEdit(self)
        self.uid_text.setPlaceholderText("uid")

        self.word_text = QLineEdit(self)
        self.word_text.setPlaceholderText("唤醒词")

        __BaiDuYunHLayout.addWidget(__BaiDuYunLabel)
        __BaiDuYunHLayout.addWidget(self.uid_text)
        __BaiDuYunHLayout.addWidget(self.word_text)
        __BaiDuYunHLayout.setSpacing(0)

        __Yes_NoLayout = QHBoxLayout()
        __Yes = QPushButton(self)
        __Yes.setText("确认")
        __Yes.clicked.connect(self.YesEvent)
        __Yes_NoLayout.addWidget(__Yes)

        __MainLayout.addLayout(__BaiDuYunHLayout)
        __MainLayout.addLayout(__Yes_NoLayout)
        self.setLayout(__MainLayout)
    
    def YesEvent(self) -> None:
        uid = self.uid_text.text()
        word = self.word_text.text()
        if uid == "" or word == "":
            QMessageBox.warning(self, "警告", "uid和唤醒词不能为空")
            return
        else:
            uid_json = wf.read_dict_from_json("uid.json")
            uid_json[word] = uid
            wf.write_dict_to_json(uid_json, "uid.json")
            # 关闭当前窗口
            QMessageBox.information(self, "Programs Config Message", "自定义语音已设置成功！", QMessageBox.Yes)


class main2(QWidget):
    def __init__(self) -> None:
        super(main2, self).__init__()
        self.setWindowTitle("自定义语音唤醒")
        self.setWindowIcon(QIcon(".\\image\\bs_icon.ico"))
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
                color: black;
            }
            QLineEdit:hover {
                background-color: #f0f0f0;
            }
            QLineEdit:focus {
                background-color: white;
                color: black;
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
        self.resize(400, 100)
        self.ui()
    
    def ui(self) -> None:
        __MainLayout = QVBoxLayout(self)

        __BaiDuYunHLayout = QVBoxLayout()
        __BaiDuYunLabel = QLabel(self)
        __BaiDuYunLabel.setText("输入txt文件名称和唤醒词")

        self.uid_text = QLineEdit(self)
        self.uid_text.setPlaceholderText("txt文件名称")

        self.word_text = QLineEdit(self)
        self.word_text.setPlaceholderText("唤醒词")

        __BaiDuYunHLayout.addWidget(__BaiDuYunLabel)
        __BaiDuYunHLayout.addWidget(self.uid_text)
        __BaiDuYunHLayout.addWidget(self.word_text)
        __BaiDuYunHLayout.setSpacing(0)

        __Yes_NoLayout = QHBoxLayout()
        __Yes = QPushButton(self)
        __Yes.setText("确认")
        __Yes.clicked.connect(self.YesEvent)
        __Yes_NoLayout.addWidget(__Yes)

        __MainLayout.addLayout(__BaiDuYunHLayout)
        __MainLayout.addLayout(__Yes_NoLayout)
        self.setLayout(__MainLayout)
    
    def YesEvent(self) -> None:
        uid = self.uid_text.text()
        word = self.word_text.text()
        if uid == "" or word == "":
            QMessageBox.warning(self, "警告", "文件名称和唤醒词不能为空")
            return
        else:
            uid_json = wf.read_dict_from_json("file_name.json")
            uid_json[word] = uid
            wf.write_dict_to_json(uid_json, "file_name.json")
            # 关闭当前窗口
            QMessageBox.information(self, "Programs Config Message", "自定义语音已设置成功！", QMessageBox.Yes)
