import write_file as wf
import os
import subprocess
import threading
import time
import pyautogui
import keyboard
import play_vioce as pv
import tkinter as tk
from tkinter import simpledialog
from tkinter import ttk
import falseIntent as fi
CONTROLLER = True

def run_tasklist():
    # 使用 cmd 执行 tasklist 命令
    cmd = 'tasklist /fi "imagename eq ShadowBotBrowser*"'
    # 使用 subprocess 执行命令
    result = subprocess.run(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    # 获取标准输出和错误输出
    stdout = result.stdout
    return stdout

def get_user_input():
    root = tk.Tk()
    root.withdraw()

    # 创建自定义的对话框
    dialog = tk.Toplevel(root)
    dialog.title("想跟希儿说点什么呢~")

    # 设置对话框的样式
    style = ttk.Style()
    style.theme_use('clam')
    style.configure("Rounded.TEntry", borderwidth=0, relief="flat", padding=5,
                    background="white", foreground="black", fieldbackground="white")
    style.configure("Rounded.TButton", borderwidth=0, relief="flat", padding=5,
                    background="#007BFF", foreground="white", focuscolor="none")
    style.map("Rounded.TButton",
              background=[('active', '#0056b3'), ('pressed', '#003d80')])

    # 创建 StringVar 来存储输入框内容
    input_var = tk.StringVar()

    # 创建输入框
    entry = ttk.Entry(dialog, style="Rounded.TEntry", textvariable=input_var)
    entry.pack(pady=20, padx=20, ipadx=10, ipady=5)
    entry.focus()

    # 定义输入完成的函数
    def on_input_complete():
        dialog.destroy()
        root.destroy()

    # 创建输入完成按钮
    button = ttk.Button(dialog, text="输入完成", style="Rounded.TButton", command=on_input_complete)
    button.pack(pady=10, padx=20, ipadx=10, ipady=5)

    # 定义执行 Win + H 的函数
    def execute_win_h():
        try:
            if wf.read_dict_from_json("state.json").get('stt_state') == "True":
                pyautogui.hotkey('win', 'h')
        except NameError:
            print("wf 未定义，请检查代码。")

    # 定义点击输入框的事件处理函数
    def on_entry_click(event):
        dialog.after(300, execute_win_h)

    # 绑定输入框的点击事件
    entry.bind("<Button-1>", on_entry_click)

    # 运行对话框
    root.wait_window(dialog)
    return input_var.get()
def file_yingdao(text):
    if ".txt" in text:
        text = text[:-4]
    text = text.replace(" ", "")
    command = f"cmd /c echo . >D:/SeeleTools/"+wf.read_dict_from_json("file_name.json").get(text)+".txt"
    # 创建启动信息对象以隐藏窗口
    startup_info = subprocess.STARTUPINFO()
    startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup_info.wShowWindow = subprocess.SW_HIDE
    try:
        # 执行命令并隐藏窗口
        subprocess.run(command, shell=True, check=True, text=True,
                       capture_output=True, startupinfo=startup_info)
    except subprocess.CalledProcessError:
        pass
def cmd_yingdao(uid):
    uid = str(uid)
    user_profile = os.environ.get("USERPROFILE") or os.path.expanduser("~")
    desktop_dirs = [os.path.join(user_profile, "Desktop")]
    public_profile = os.environ.get("PUBLIC")
    if public_profile:
        desktop_dirs.append(os.path.join(public_profile, "Desktop"))
    for key in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial"):
        onedrive = os.environ.get(key)
        if onedrive:
            desktop_dirs.append(os.path.join(onedrive, "Desktop"))

    link_path = None
    for desktop_dir in desktop_dirs:
        candidate = os.path.join(desktop_dir, "影刀.lnk")
        if os.path.exists(candidate):
            link_path = candidate
            break
    if link_path is None:
        link_path = os.path.join(desktop_dirs[0], "影刀.lnk")

    print(f"\"{link_path}\" shadowbot:Run?robot-uuid={uid}")
    command = f"\"{link_path}\" shadowbot:Run?robot-uuid={uid}"
    # 创建启动信息对象以隐藏窗口
    startup_info = subprocess.STARTUPINFO()
    startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup_info.wShowWindow = subprocess.SW_HIDE
    try:
        # 执行命令并隐藏窗口
        subprocess.run(command, shell=True, check=True, text=True,
                       capture_output=True, startupinfo=startup_info)
    except subprocess.CalledProcessError:
        pass

def text_intent(text):
    pv.main("3.wav")
    text=fi.main(text)
    if text=="创建工作":
        cmd_yingdao("")
    else:
        try:
            if wf.read_dict_from_json("state.json").get('startup_mode') == "fast":
                if "没有运行的任务" in run_tasklist():
                    pv.main("11.wav")
                else:
                    file_yingdao(text)
            else:
                data = wf.read_dict_from_json("uid.json")
                uid=data.get(text,-1)
                if uid==-1:
                    pv.main("4.wav")
                else:
                    cmd_yingdao(uid)
        except :
            pv.main("4.wav")
def main():
    global CONTROLLER
    hotkey = '`'
    # 添加热键（仅添加一次）
    keyboard.add_hotkey(hotkey, lambda: text_intent(get_user_input()))

    try:
        while CONTROLLER:
            time.sleep(0.1)  # 空循环保持线程运行
    finally:
        # 退出时移除热键并停止监听
        keyboard.remove_hotkey(hotkey)
        keyboard.unhook_all()


def run() -> None:
    start = threading.Thread(target=main)
    start.start()
