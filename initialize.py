import os
from threading import Thread
import write_file as wf
import webbrowser
import play_vioce as pv
import sys  # 新增导入shutil模块


def get_tools_folder_path():
    if os.path.isdir(r"D:\\"):
        return r"D:\SeeleTools"
    return r"C:\SeeleTools"


def set_file(current_dir):
    # 获取当前文件所在目录
    # current_dir = os.path.dirname(os.path.abspath(__file__))
    # """ 获取当前脚本所在目录，适用于开发环境、PyInstaller 打包后和 Inno Setup 安装后的环境 """
    # if getattr(sys, 'frozen', False):  # 判断是否是 PyInstaller 打包后的exe
    #     # 打包后运行时，sys.executable 是 exe 文件路径
    #     current_dir = os.path.dirname(sys.executable)
    # else:
    #     # 开发环境下，使用 __file__ 获取脚本所在目录
    #     current_dir = os.path.dirname(os.path.abspath(__file__))
    # 构建语音播放文件的路径
    audio_folder_path = os.path.join(current_dir, 'audio')
    # 获取桌面路径
    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
    # 获取下载路径
    download_path = os.path.join(os.path.expanduser("~"), "Downloads")
    # 实时获取和当前文件同级目录的 state.json 文件路径
    src_file = os.path.join(current_dir, 'state.json')
    installation_package_path = os.path.join(current_dir,'installationPackage')
    # 创建文件夹
    folder_path = get_tools_folder_path()
    try:
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            print(f"文件夹 {folder_path} 创建成功。")
        else:
            print(f"文件夹 {folder_path} 已存在。")
        # 定义文件路径
        download_link_file = os.path.join(folder_path, "DownloadLink.txt")
        voice_playback_link_file = os.path.join(folder_path, "VoicePlaybackLink.txt")
        Desktop_link_file = os.path.join(folder_path, "DesktopLink.txt")
        state_link_file = os.path.join(folder_path, "stateLink.txt")
        installation_ackage = os.path.join(folder_path, "installationPackageLink.txt")
        # 创建文件
        with open(state_link_file, 'w') as file1, open(voice_playback_link_file, 'w') as file2, open(Desktop_link_file, 'w') as file3, open(installation_ackage, 'w') as file4, open(download_link_file, 'w') as file5:
            file1.write(src_file)
            # 将 audio_folder_path 写入 VoicePlaybackLink.txt
            file2.write(audio_folder_path)
            # 将 desktop_path 写入 desktoplink.txt
            file3.write(desktop_path)
            # 将 installationPackageLink 写入 installationPackageLink.txt
            file4.write(installation_package_path)
            # 将 download_path 写入 DownloadLink.txt
            file5.write(download_path)
    except FileExistsError:
        print("文件夹已存在，无需重复创建。")
    except PermissionError:
        print("没有足够的权限创建文件夹或文件。")
    except Exception as e:
        print(f"发生未知错误: {e}")
def open_url(url):
    try:
        # 使用 webbrowser 模块打开网页
        webbrowser.open(url)
    except Exception as e:
        print(f"打开网页时出现错误: {e}")
def main(current_dir):
    pv.main("1.wav")
    set_file(current_dir)
    dic=wf.read_dict_from_json('state.json')
    open_url("https://www.yingdao.com/product/")
    open_url("https://api.winrobot360.com/redirect/robot/share?inviteKey=050edc1539037e9f")
    open_url("https://blog.csdn.net/weixin_58478243/article/details/146606853?spm=1001.2014.3001.5502")
    pv.main("2.wav")
    pv.main("8.wav")
    dic["initialize"]="1"
    wf.write_dict_to_json(dic,'state.json')


# def run() -> None:
#     Start = Thread(target=main)
#     Start.start()

def run(current_exe_path: str) -> None:
    Start = Thread(target=main, args=(current_exe_path,))
    Start.start()

if __name__ == "__main__":
    set_file()
