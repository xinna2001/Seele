import os
import sys
import time
import tkinter as tk
from tkinter import ttk

def get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

class MainApp:
    def __init__(self, root, ready_file=None, timeout_seconds=300):
        self.root = root
        self.ready_file = ready_file
        self.deadline = time.time() + max(1, int(timeout_seconds))
        self.root.title("Seele等待界面")

        # 设置窗口大小
        self.root.geometry("800x500")
        self.root.configure(bg="white")  # 默认背景颜色为白色

        # 加载背景图片
        try:
            self.bg_image = tk.PhotoImage(file=os.path.join(get_base_dir(), "image", "image.png"))
        except Exception as e:
            print(f"加载背景图片失败: {e}")
            self.bg_image = None

        # 创建主布局
        self.create_ui()

        # 控制窗口关闭的标志（改为类内属性）
        self.close_flag = False

    def create_ui(self):
        # 添加背景图片到 Label
        if self.bg_image:
            bg_label = tk.Label(self.root, image=self.bg_image)
            bg_label.place(x=0, y=0, relwidth=1, relheight=1)  # 背景图片铺满整个窗口

        # 添加提示文字
        label = tk.Label(
            self.root,
            text="请稍等，希儿马上就好~",
            font=("Arial", 18, "bold"),
            bg="white",  # 如果没有背景图片，则使用白色背景
            fg="black"
        )
        label.pack(pady=20)

    def hide_window(self):
        """隐藏窗口并显示提示消息"""
        self.root.withdraw()  # 隐藏窗口
        self.root.quit()  # 退出程序

    def check_close_condition(self):
        """
        定期检查关闭条件是否满足
        """
        if self.close_flag:
            self.hide_window()
            return

        if self.ready_file and os.path.exists(self.ready_file):
            self.hide_window()
            return

        if time.time() >= self.deadline:
            self.hide_window()
            return

        self.root.after(100, self.check_close_condition)

    def set_close_flag(self, flag: bool):
        """
        设置关闭标志
        :param flag: 是否关闭窗口的标志 (True/False)
        """
        self.close_flag = flag

def main(ready_file=None, timeout_seconds=300):
    root = tk.Tk()
    app = MainApp(root, ready_file=ready_file, timeout_seconds=timeout_seconds)
    app.check_close_condition()
    root.mainloop()

if __name__ == "__main__":
    ready = None
    timeout = 300
    argv = sys.argv[1:]
    if argv:
        ready = argv[0]
    if len(argv) >= 2:
        try:
            timeout = int(argv[1])
        except ValueError:
            timeout = 300
    main(ready_file=ready, timeout_seconds=timeout)
