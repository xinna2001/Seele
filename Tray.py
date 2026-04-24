"""
用于创建系统托盘
"""
# import sys

from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QTimer
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
        # self.startWeather = QAction("天气查询", self, triggered=self.ui.WeatherForecast)
        self.quitAction = QAction("退出", self, triggered=self.quit)

        self.menu.addAction(self.OpenGui)
        # self.menu.addAction(self.startWeather)
        self.menu.addAction(self.quitAction)
        self.setContextMenu(self.menu)

        # 设置图标
        self.setIcon(QIcon(".\\image\\bs_icon.png"))
        self.icon = self.MessageIcon()

        # 把鼠标点击图标的信号和槽连接
        self.activated.connect(self.onIconClicked)

    def show_window(self):
        self._restore_window()

    def _restore_window(self):
        self.ui.showNormal()
        self.ui.raise_()
        self.ui.activateWindow()
        QTimer.singleShot(0, self.ui.update)
        QTimer.singleShot(0, self.ui.repaint)

    def _hide_window(self):
        self.ui.hide()

    def quit(self):
        self.setVisible(False)  # 托盘图标会自动消失
        qApp.quit()
        self.ui.close()
        exit()

    def onIconClicked(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self._restore_window()
            return
        if reason == QSystemTrayIcon.Trigger:
            if self.ui.isVisible() and not self.ui.isMinimized():
                self._hide_window()
            else:
                self._restore_window()
