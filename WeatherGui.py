import os

from PyQt5.QtGui import QIcon
from PyQt5.QtGui import QCursor
from PyQt5.QtGui import QRegion
from PyQt5.QtGui import QPainterPath
from PyQt5.QtCore import Qt
from PyQt5.QtCore import QSize
from PyQt5.QtCore import QRectF
from PyQt5.QtWidgets import QWidget
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QPushButton

import requests

class WeatherGUI(QWidget):
    def __init__(self):
        super(WeatherGUI, self).__init__()
        self.setWindowTitle("DesktopWife-WeatherGui")
        self.resize(470, 270)
        # 圆角
        rect = QRectF(0, 0, self.width(), self.height())
        path = QPainterPath()
        path.addRoundedRect(rect, 10, 10)
        polygon = path.toFillPolygon().toPolygon()
        region = QRegion(polygon)
        self.setMask(region)

        self.QuitButton = QPushButton(self)
        self.QuitButton.setIcon(QIcon(".\\image\\Quit.png"))
        self.QuitButton.setIconSize(QSize(40, 40))
        self.QuitButton.setGeometry(400, 10, 40, 40)
        QuitButtonRect = QRectF(0, 0, self.QuitButton.width(), self.QuitButton.height())
        QuitButtonPath = QPainterPath()
        QuitButtonPath.addRoundedRect(QuitButtonRect, 50, 50)
        QuitButtonPolygon = QuitButtonPath.toFillPolygon().toPolygon()
        QuitButtonRegin = QRegion(QuitButtonPolygon)
        self.QuitButton.setMask(QuitButtonRegin)
        self.QuitButton.clicked.connect(self.hide)

        self.WeatherText = QLabel(self)
        self.WeatherText.setGeometry(int((470 - 300) / 2), int((270 - 200) / 2), 300, 200)


    """重写移动事假，更改鼠标图标"""

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.m_flag = True
            self.m_Position = event.globalPos() - self.pos()  # 获取鼠标相对窗口的位置
            event.accept()
            self.setCursor(QCursor(Qt.OpenHandCursor))  # 更改鼠标图标

    def mouseMoveEvent(self, QMouseEvent):
        if Qt.LeftButton and self.m_flag:
            self.move(QMouseEvent.globalPos() - self.m_Position)  # 更改窗口位置
            QMouseEvent.accept()

    def mouseReleaseEvent(self, QMouseEvent):
        self.m_flag = False
        self.setCursor(QCursor(Qt.ArrowCursor))
