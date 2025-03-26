"""
用于创建系统托盘
"""
# import sys

from PyQt5.QtGui import QIcon
# from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import qApp
from PyQt5.QtWidgets import QMenu
from PyQt5.QtWidgets import QAction
from PyQt5.QtWidgets import QSystemTrayIcon


class TrayIcon(QSystemTrayIcon):
    def __init__(self, MainWindow, parent=None):
        super(TrayIcon, self).__init__(parent)
        self.ui = MainWindow
        self.createMenu()

    def createMenu(self):
        self.menu = QMenu()
        self.OpenGui = QAction("打开界面", self, triggered=self.show_window)
        self.startWeather = QAction("天气查询", self, triggered=self.ui.WeatherForecast)
        self.quitAction = QAction("退出", self, triggered=self.quit)

        self.menu.addAction(self.OpenGui)
        self.menu.addAction(self.startWeather)
        self.menu.addAction(self.quitAction)
        self.setContextMenu(self.menu)

        # 设置图标
        self.setIcon(QIcon(".\\image\\bs_icon.png"))
        self.icon = self.MessageIcon()

        # 把鼠标点击图标的信号和槽连接
        self.activated.connect(self.onIconClicked)

    def show_window(self):
        # 若是最小化，则先正常显示窗口，再变为活动窗口（暂时显示在最前面）
        self.ui.showNormal()
        self.ui.activateWindow()

    def quit(self):
        self.setVisible(False)  # 托盘图标会自动消失
        qApp.quit()
        self.ui.close()
        exit()

    # 鼠标点击icon传递的信号会带有一个整形的值，1是表示单击右键，2是双击，3是单击左键，4是用鼠标中键点击
    def onIconClicked(self, reason):
        if reason == 2 or reason == 3:
            if self.ui.isMinimized() or not self.ui.isVisible():
                # 若是最小化，则先正常显示窗口，再变为活动窗口（暂时显示在最前面）
                self.ui.showNormal()
                self.ui.activateWindow()
                self.ui.show()
            else:
                # 若不是最小化，则最小化
                self.ui.showMinimized()
                self.ui.show()
                # self.ui.show()