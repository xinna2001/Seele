import keyboard
from threading import Thread
import pyautogui
import os
import subprocess

def stt():
# 模拟按下 Win + R 组合键
    pyautogui.hotkey('win', 'h')
def cmd_yingdao(uid):
    # 获取桌面路径
    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")

    # 要执行的命令
    command = f'cd /d "{desktop_path}" && "影刀.lnk" shadowbot:Run?robot-uuid='+uid

    # 创建启动信息对象以隐藏窗口
    startup_info = subprocess.STARTUPINFO()
    startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup_info.wShowWindow = subprocess.SW_HIDE

    try:
        # 执行命令并隐藏窗口
        result = subprocess.run(command, shell=True, check=True, text=True, capture_output=True, startupinfo=startup_info)
    except subprocess.CalledProcessError as e:
        pass

def main():
    keyboard.add_hotkey('`',stt)
    keyboard.wait()


# def run() -> None:
#     Start = Thread(target=main)
#     Start.start()
main()