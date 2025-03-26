import json

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
        self.setWindowTitle("ProgramsConfig")
        self.setWindowIcon(QIcon(".\\image\\bs_icon.ico"))
        self.setWindowFlags(Qt.WindowMinMaxButtonsHint)
        self.setStyleSheet("""
            QWidget {
                background-color: black;
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
        self.resize(550, 150)
        self.ui()
    
    def ui(self) -> None:
        __MainLayout = QVBoxLayout(self)

        __BaiDuYunHLayout = QVBoxLayout()
        __BaiDuYunLabel = QLabel(self)
        __BaiDuYunLabel.setText("设置百度云请求参数")

        self.APIKeyLineEdit = QLineEdit(self)
        self.APIKeyLineEdit.setPlaceholderText("ApiKey")

        self.SecretKeyLineEdit = QLineEdit(self)
        self.SecretKeyLineEdit.setPlaceholderText("SecretKey")

        __BaiDuYunHLayout.addWidget(__BaiDuYunLabel)
        __BaiDuYunHLayout.addWidget(self.APIKeyLineEdit)
        __BaiDuYunHLayout.addWidget(self.SecretKeyLineEdit)
        __BaiDuYunHLayout.setSpacing(0)

        __Yes_NoLayout = QHBoxLayout()
        __Yes = QPushButton(self)
        __Yes.setText("确认")
        __Yes.clicked.connect(self.YesEvent)
        __No = QPushButton(self)
        __No.setText("取消")
        __No.clicked.connect(self.hide)
        __Yes_NoLayout.addWidget(__Yes)
        __Yes_NoLayout.addWidget(__No)

        __MainLayout.addLayout(__BaiDuYunHLayout)
        __MainLayout.addLayout(__Yes_NoLayout)
        self.setLayout(__MainLayout)
    
    def YesEvent(self) -> None:
        __APIKey = self.APIKeyLineEdit.text()
        __SecretKey = self.SecretKeyLineEdit.text()
        with open(".\\config.json", "r") as rfp:
            __SourceData = json.loads(rfp.read())
        with open(".\\config.json", "w+") as wfp:
            if __SourceData['APIKey'] != __APIKey:
                if len(__APIKey) > 1:
                    __SourceData['APIKey'] = __APIKey
            if __SourceData['SecretKey'] != __SecretKey:
                if len(__SecretKey) > 1:
                    __SourceData['SecretKey'] = __SecretKey
            wfp.write(json.dumps(__SourceData, indent=4, ensure_ascii=False))
        QMessageBox.information(self, "Programs Config Message", "已写入配置,重启后生效!", QMessageBox.Yes)


# if __name__ in "__main__":
#     import sys
#     from PyQt5.QtWidgets import QApplication
#     app = QApplication(sys.argv)
#     window = main()
#     window.show()
#     app.exec_()