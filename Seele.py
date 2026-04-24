import sys
import os
import Tray
import OutVoice
import initialize
import VoiceToText
import StartupMode
import write_file as wf
import ProgramsConfigWindow
import RoleSwitchWindow
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QRectF
from PyQt5.QtGui import QPixmap
from PyQt5.QtGui import QRegion
from PyQt5.QtGui import QCursor
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QMenu
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QWidget
from PyQt5.QtWidgets import QAction
from PyQt5.QtGui import QPainterPath
from PyQt5.QtGui import QIcon, QMovie
from PyQt5.QtWidgets import QDesktopWidget
from PyQt5.QtWidgets import QMessageBox, QApplication

def get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def _json_path(name):
    return os.path.join(get_base_dir(), name)

dic = wf.read_dict_from_json(_json_path('state.json')) or {}
if dic.get("initialize", "0") == "0":
    initialize.run(get_base_dir())

class DesktopWife(QWidget):
    """
    Main Window
    """
    def resize_movie(self, frame_number):
        """根据当前帧调整 GIF 大小"""
        if not getattr(self, "movie", None) or not self.movie.isValid():
            return
        pixmap = self.movie.currentPixmap()
        if pixmap.isNull() or pixmap.width() <= 0 or pixmap.height() <= 0:
            return
        if not hasattr(self, "PlayLabel"):
            return
        screen = QDesktopWidget().screenGeometry()
        target_h = int(min(max(screen.height() * 0.15, 200), 720))
        target_w = int(min(max(screen.width() * 0.15, 200), 720))
        aspect = pixmap.width() / max(1, pixmap.height())
        if target_w / max(1, target_h) > aspect:
            new_height = target_h
            new_width = int(target_h * aspect)
        else:
            new_width = target_w
            new_height = int(target_w / aspect)
        if new_width <= 0 or new_height <= 0:
            return
        if not getattr(self, "_scaled_initialized", False):
            self.movie.setScaledSize(QSize(new_width, new_height))
            self.PlayLabel.setFixedSize(new_width, new_height)
            self.setFixedSize(new_width, new_height)
            self._scaled_initialized = True
        self._position_message()
    def __init__(self):
        super(DesktopWife, self).__init__()
        self.m_flag = False
        self.m_Position = None
        # 加载 GIF 动画
        self.movie = QMovie(os.path.join(get_base_dir(), "image", "bss.gif"))
        # # 设置播放速度为原始速度的 X%
        self.movie.setSpeed(95)
        self._scaled_initialized = False

        self.WindowSize = QDesktopWidget().screenGeometry()

        # 设置窗口标题和大小
        self.setWindowTitle("DesktopWife")
        screen = QDesktopWidget().screenGeometry()
        init_size = int(min(max(screen.height() * 0.35, 320), 720))
        self.resize(init_size, init_size)
        self.move(
            int((screen.width() - self.width()) / 2),
            int((screen.height() - self.height()) / 2)
        )

        # 设置窗口属性
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.SubWindow)
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        # 创建显示 GIF 的标签
        self.PlayLabel = QLabel(self)
        self.PlayLabel.setMovie(self.movie)  # 将电影设置到标签上
        self.WindowSize = QDesktopWidget().screenGeometry()

        self.setWindowTitle("DesktopWife")
        self.WindowMessage = QLabel("哥哥，欢迎回来~", self)
        self.WindowMessage.setStyleSheet("color: white;")
        self.WindowMessage.adjustSize()
        self._position_message()
        self.movie.frameChanged.connect(self.resize_movie)
        self.movie.start()  # 开始播放 GIF

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._WindowMenu)

        self.Timer = QTimer()
        self.Timer.start(5000)
        self.Timer.timeout.connect(self.RandomWindowMessage)

        self._Tray = Tray.TrayIcon(self)
        self.outvoice = OutVoice.main()

    def set_character_gif(self, gif_path: str) -> bool:
        if not gif_path or not os.path.exists(gif_path):
            return False
        movie = QMovie(gif_path)
        if not movie.isValid():
            return False
        old_movie = getattr(self, "movie", None)
        if old_movie:
            try:
                old_movie.frameChanged.disconnect(self.resize_movie)
            except TypeError:
                pass
            old_movie.stop()
        self.movie = movie
        self.movie.setSpeed(95)
        self._scaled_initialized = False
        if hasattr(self, "PlayLabel"):
            self.PlayLabel.setMovie(self.movie)
        self.movie.frameChanged.connect(self.resize_movie)
        self.movie.start()
        self.resize_movie(0)
        return True

    def _position_message(self):
        if not hasattr(self, "WindowMessage"):
            return
        self.WindowMessage.adjustSize()
        self.WindowMessage.move(self.width() - self.WindowMessage.width() - 20, 20)

    def _WindowMenu(self) -> None:
        """
        右键菜单
        :return: None
        """
        self.Menu = QMenu(self)
        self.Menu.setStyleSheet("background-color: black; color: white;")

        self.custom_voice = QAction(QIcon(os.path.join(get_base_dir(), "image", "bs_icon.png")), u"自定义语音唤醒", self)
        self.Menu.addAction(self.custom_voice)

        self.out_voice = QAction(QIcon(os.path.join(get_base_dir(), "image", "bs_icon.png")), u"语音输入设置", self)
        self.Menu.addAction(self.out_voice)

        self.change_role = QAction(QIcon(os.path.join(get_base_dir(), "image", "bs_icon.png")), u"换个角色", self)
        self.Menu.addAction(self.change_role)

        self.startup = QAction(QIcon(os.path.join(get_base_dir(), "image", "bs_icon.png")), u"启动方式", self)
        self.Menu.addAction(self.startup)

        self.StartTray = QAction(QIcon(os.path.join(get_base_dir(), "image", "bs_icon.png")), u"退置托盘", self)
        self.Menu.addAction(self.StartTray)

        self.CloseWindowAction = QAction(QIcon(os.path.join(get_base_dir(), "image", "Quit.png")), u"退出程序", self)
        self.Menu.addAction(self.CloseWindowAction)

        self.out_voice.triggered.connect(self.WeatherForecast)
        self.custom_voice.triggered.connect(self.ProgramsConfig)
        self.change_role.triggered.connect(self.ChangeRole)
        self.StartTray.triggered.connect(self.SetTray)
        self.startup.triggered.connect(self.Startup)
        self.CloseWindowAction.triggered.connect(self.CloseWindowActionEvent)
        self.Menu.popup(QCursor.pos())

        # 圆角
        rect = QRectF(0, 0, self.Menu.width(), self.Menu.height())
        path = QPainterPath()
        path.addRoundedRect(rect, 10, 10)
        polygon = path.toFillPolygon().toPolygon()
        region = QRegion(polygon)
        self.Menu.setMask(region)

    def ProgramsConfig(self) -> None:
        """
        自定义语音唤醒
        :return: None
        """
        if (wf.read_dict_from_json(_json_path("state.json")) or {}).get('startup_mode') == "fast":
            self.ConfigWindow = ProgramsConfigWindow.main2()
            self.ConfigWindow.show()
        else:
            self.ConfigWindow = ProgramsConfigWindow.main()
            self.ConfigWindow.show()

    def ChangeRole(self) -> None:
        self.ChangeRoleWindow = RoleSwitchWindow.main(self)
        self.ChangeRoleWindow.show()

    def CloseWindowActionEvent(self) -> None:
        """
        关闭界面并提出后台进程
        :return: None
        """
        self.close()
        VoiceToText.CONTROLLER = False
        QApplication.instance().quit()
    def Startup(self) -> None:
        """
        启动方式
        :return: None
        """
        self.ConfigWindow = StartupMode.main()
        self.ConfigWindow.show()

    def SetTray(self) -> None:
        """
        系统托盘
        :return: None
        """
        self._Tray.show()
        self.hide()

    def RandomWindowMessage(self) -> None:
        """
        获取机器人回答，同步到右上角位置
        :return: None
        """
        
        if not hasattr(self, "WindowMessage"):
            return
        self.WindowMessage.setText("希儿在工作呢~")
        self._position_message()

    def WeatherForecast(self) -> None:
        """
        
        :return: None
        """
        self.outvoice.show()

    def mousePressEvent(self, event) -> None:
        """
        重写移动事假，更改鼠标图标
        :param event:
        :return:
        """
        if event.button() == Qt.LeftButton:
            self.m_flag = True
            self.m_Position = event.globalPos() - self.pos()  # 获取鼠标相对窗口的位置
            event.accept()
            self.setCursor(QCursor(Qt.OpenHandCursor))  # 更改鼠标图标

    def mouseMoveEvent(self, event) -> None:
        if Qt.LeftButton and self.m_flag:
            self.move(event.globalPos() - self.m_Position)
            event.accept()

    def mouseReleaseEvent(self, event) -> None:
        self.m_flag = False
        self.setCursor(QCursor(Qt.ArrowCursor))
        event.accept()

    def resizeEvent(self, event):
        self._position_message()
        super(DesktopWife, self).resizeEvent(event)

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    Window = DesktopWife()
    Window.show()
    ready_file = os.environ.get("SEELE_READY_FILE")
    if ready_file:
        try:
            os.makedirs(os.path.dirname(ready_file), exist_ok=True)
            with open(ready_file, "w", encoding="utf-8"):
                pass
        except OSError:
            pass
    VoiceToText.run()
    app.exec_()

if __name__ == "__main__":
    main()
