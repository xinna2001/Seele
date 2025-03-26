import sys
from PyQt5.QtGui import QCursor
from PyQt5.QtGui import QIcon
from PyQt5.QtGui import QPainterPath
from PyQt5.QtGui import QRegion
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
from PyQt5.QtCore import QRectF
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QWidget
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QDesktopWidget
from PyQt5.QtWidgets import QMenu
from PyQt5.QtWidgets import QAction
from PyQt5.QtGui import QIcon, QMovie
# from PyQt5.QtWidgets import QFileDialog
# from PyQt5.QtWidgets import QMessageBox
import stt
import WeatherGui
import Tray
import VoiceToText
import ProgramLog
import ProgramsConfigWindow

LOG = ProgramLog.ProgramLog()

stt.run()


class DesktopWife(QWidget):
    """
    Main Window
    """
    def resize_movie(self, frame_number):
        """根据当前帧调整 GIF 大小"""
        if not self.movie.isValid():  # 检查动画是否有效
            return

        pixmap = self.movie.currentPixmap()  # 获取当前帧
        scaled_pixmap = pixmap.scaled(
            pixmap.size() * self.scale_factor,
            Qt.KeepAspectRatio,  # 保持宽高比
            Qt.SmoothTransformation  # 平滑缩放
        )
        self.PlayLabel.setPixmap(scaled_pixmap)  # 更新标签中的图像
        self.adjustSize()  # 调整窗口大小以适应内容
    def __init__(self):
        super(DesktopWife, self).__init__()
        self.m_flag = False
        self.m_Position = None
        # 加载 GIF 动画
        self.movie = QMovie(".\\image\\bss.gif")  # 使用 QMovie 加载 GIF
        # 设置初始缩放比例（例如缩小到原图的 40%）
        self.scale_factor = 0.4
        self.movie.frameChanged.connect(self.resize_movie)
        self.movie.setScaledSize(self.movie.scaledSize())  # 设置初始缩放大小

        self.WindowSize = QDesktopWidget().screenGeometry()

        # 设置窗口标题和大小
        self.setWindowTitle("DesktopWife")
        self.resize(self.movie.frameRect().size())  # 根据 GIF 尺寸调整窗口大小
        self.move(
            int((self.WindowSize.width() - self.movie.frameRect().width()) / 2),
            int((self.WindowSize.height() - self.movie.frameRect().height()) / 2)
        )

        # 设置窗口属性
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.SubWindow)
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        # 创建显示 GIF 的标签
        self.PlayLabel = QLabel(self)
        self.PlayLabel.setMovie(self.movie)  # 将电影设置到标签上
        self.movie.start()  # 开始播放 GIF
        self.WindowSize = QDesktopWidget().screenGeometry()

        self.setWindowTitle("DesktopWife")
        self.WindowMessage = QLabel("哥哥，欢迎回来~", self)
        self.WindowMessage.setStyleSheet("color: white;")

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._WindowMenu)

        self.Timer = QTimer()
        self.Timer.start(5000)
        self.Timer.timeout.connect(self.RandomWindowMessage)

        self._Tray = Tray.TrayIcon(self)
        self.WeatherForecastGUI = WeatherGui.WeatherGUI()


    def _WindowMenu(self) -> None:
        """
        右键菜单
        :return: None
        """
        self.Menu = QMenu(self)
        self.Menu.setStyleSheet("background-color: black; color: white;")

        # self.WeatherForecastQAction = QAction(QIcon(".\\image\\Button.png"), u"查看天气", self)
        # self.Menu.addAction(self.WeatherForecastQAction)

        # self.ConfigQAction = QAction(QIcon(".\\image\\Button.png"), u"查看时间", self)
        # self.Menu.addAction(self.ConfigQAction)

        self.StartTray = QAction(QIcon(".\\image\\bs_icon.png"), u"退置托盘", self)
        self.Menu.addAction(self.StartTray)

        self.CloseWindowAction = QAction(QIcon(".\\image\\Quit.png"), u"退出程序", self)
        self.Menu.addAction(self.CloseWindowAction)

        self.WeatherForecastQAction.triggered.connect(self.WeatherForecast)
        self.ConfigQAction.triggered.connect(self.ProgramsConfig)
        self.StartTray.triggered.connect(self.SetTray)
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
        设置界面
        :return: None
        """
        self.ConfigWindow = ProgramsConfigWindow.main()
        self.ConfigWindow.show()

    def CloseWindowActionEvent(self) -> None:
        """
        关闭界面并提出后台进程
        :return: None
        """
        self.close()
        VoiceToText.CONTROLLER = False
        exit(0)

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
        self.WindowMessage.setText(VoiceToText.RETURNTEXT)

    def WeatherForecast(self) -> None:
        """
        天气预报功能
        :return: None
        """
        self.WeatherForecastGUI.show()

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

    def mouseMoveEvent(self, QMouseEvent) -> None:
        if Qt.LeftButton and self.m_flag:
            self.move(QMouseEvent.globalPos() - self.m_Position)  # 更改窗口位置
            QMouseEvent.accept()

    def mouseReleaseEvent(self, QMouseEvent) -> None:
        self.m_flag = False
        self.setCursor(QCursor(Qt.ArrowCursor))


is_executing = False
app = QApplication(sys.argv)
Window = DesktopWife()
Window.show()
app.exec_()
