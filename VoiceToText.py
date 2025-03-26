import os
import json
import wave
import base64
import pyaudio
import pyttsx3
import requests
import keyboard
import subprocess
import ProgramLog
from threading import Thread
#log用来记录日志，暂时删除
LOG = ProgramLog.ProgramLog()
CONTROLLER = True
RETURNTEXT = ""

TTS_ENGINE = pyttsx3.init()     # 初始化pyttsx3模块，为后面调用做准备
TTS_RATE: int = 150     # 语速
TTS_VOLUME: float = 1.0     # 音量:0-1

import speech_recognition as sr
 
#用的谷歌的api，需要联网，需要科学上网
def SpeechToText():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("请说些什么吧...")
        # 设置 phrase_time_limit 为 None 表示不限制单次语音时长
        audio = r.listen(source, timeout=None, phrase_time_limit=None)
        try:
            print("Google Speech Recognition thinks you said:")
            text = r.recognize_google(audio, language='zh-CN')
            print(text)
        except sr.UnknownValueError:
            print("Google Speech Recognition could not understand audio")
        except sr.RequestError as e:
            print(f"Could not request results from Google Speech Recognition service; {e}")
    return text


def TTS(
        Test: str,
        rate: int = TTS_RATE,
        volume: float = TTS_VOLUME
) -> bool:
    """
    使用pyttsx3库，将Test的字符串内容转换为音频并播放
    :param Test: str
    :param rate: int = TTS_RATE
    :param volume: float = TTS_VOLUME
    :return: bool
    """
    global RETURNTEXT
    RETURNTEXT = Test
    LOG.output(
        "正常运行",
        f"TTS {Test}"
        )
    # 设置语音属性
    # setProperty 方法用于设置语音引擎的属性。
    # "rate" 表示语音的语速，单位是每分钟的单词数，rate 参数就是用来指定语速的。
    # "volume" 表示语音的音量，取值范围是 0 到 1，volume 参数用来指定音量大小。
    TTS_ENGINE.setProperty("rate", rate)
    TTS_ENGINE.setProperty("volume", volume)
    #say 方法会把传入的字符串 Test 转换为语音，并将其添加到语音引擎的播放队列中。不过，这时语音还未实际播放
    TTS_ENGINE.say(Test)
    # runAndWait 方法会阻塞程序，直到所有的语音播放完成。
    TTS_ENGINE.runAndWait()
    # 停止播放
    TTS_ENGINE.stop()

    return True


def Scanning(
        Path: str = "C:\\ProgramData\\Microsoft\\Windows\\Start Menu\\Programs\\"
) -> list:
    """
    Windows系统下扫描桌面快捷方式
    :param Path:  str
    :return: list
    """
    LOG.output("正常运行", "扫描快捷方式 VoiceToText --> def Scanning")
    __DIRList = []
    __Files = []
    for paths, dirs, files in os.walk(Path):
        if dirs:
            for i in dirs:
                __DIRList.append(paths+"\\" + i)
        if files:
            for j in files:
                __Files.append(paths+"\\" + j)
    return __Files


def main() -> None:
    """
    主函数
    :return: None
    """
    global CONTROLLER
    while CONTROLLER:
        result = SpeechToText()
        if "退出" in result or "关闭" in result:
            break
        LOG.output("正常运行", f"{result} VoiceToText --> def GoogleTranslate")
        if "希儿" in result or "希尔" in result or "曦儿" in result or "西尔" in result:
            LOG.output("正常运行", "语音唤醒成功 VoiceToText --> def GoogleTranslate")
            TTS("哥哥，我在的")
            LOG.output("正常运行", "语音回复")
            SpeechTWO = SpeechToText()

            LOG.output("正常运行", f"{SpeechTWO} VoiceToText --> def main")

            if "微信" in SpeechTWO:
                
                TTS("已为您打开百度")
                LOG.output("正常运行", f"语音回复：已为您打开百度")

            elif "百度搜索" in SpeechTWO:
                TTS("好的, 主人")
                LOG.output("正常运行", "语音回复：好的，主人")
                subprocess.Popen(
                     f"start https://www.baidu.com/s?wd={SpeechTWO.strip('百度搜索')}",
                     shell=True,
                     stdout=subprocess.PIPE,
                     stderr=subprocess.STDOUT,
                     stdin=subprocess.PIPE
                     )
                # popen.stdin.close()
                # popen.wait()
                # stdout.read()
                # popen.stdout.close()
                TTS(f"已为您搜索{SpeechTWO.strip('百度搜索')}")
                LOG.output("正常运行", f"语音回复：已为您搜索{SpeechTWO.strip('百度搜索')}")

            elif "打开命令行" in SpeechTWO:
                TTS("好的, 主人")
                LOG.output("正常运行", "语音回复：好的，主人")
                subprocess.Popen(
                     f"start cmd",
                     shell=True,
                     stdout=subprocess.PIPE,
                     stderr=subprocess.STDOUT,
                     stdin=subprocess.PIPE
                     )
                # popen.stdin.close()
                # popen.wait()
                # stdout.read()
                # popen.stdout.close()
                TTS("已为您打开命令行")
                LOG.output("正常运行", "语音回复：已为您打开命令行")

            elif "关闭语音功能" in SpeechTWO or "关闭语音" in SpeechTWO:
                TTS("好的,主人 下次再见")
                LOG.output("正常运行", "语音回复：好的，主人 下次再见")
                break

            elif "打开" in SpeechTWO:
                TTS("好的, 主人")
                LOG.output("正常运行", "语音回复：好的，主人")
                IsStart = False
                Text = str(SpeechTWO).strip("。").replace("元", "原")
                for _Path in Scanning():
                    if Text.strip("打开") == os.path.split(_Path)[-1].split(".")[0]:
                        popen = subprocess.Popen(
                            f"{_Path}",
                            shell=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            stdin=subprocess.PIPE
                        )
                        popen.stdin.close()
                        # popen.wait()
                        # stdout.read()
                        # popen.stdout.close()
                        print(_Path)
                        TTS(f"已为您打开 {Text.strip('打开')}")
                        LOG.output("正常运行", f"语音回复：已为您打开 {Text.strip('打开')}")
                        IsStart = True
                        break
                if IsStart:
                    continue
                else:
                    TTS(f"主人未找到 {Text.strip('打开')}")
                    LOG.output("正常运行", f"语音回复：主人未找到 {Text.strip('打开')}")

            elif "关机" in SpeechTWO:
                TTS("主人是否确定要关机呢？")
                LOG.output("正常运行", f"语音回复：主人是否确定要关机呢？")
                IsShotDown = SpeechToText()
                if IsShotDown in ["是", "是的", "没错", "要"]:
                    TTS("好的, 主人好好休息！")
                    LOG.output("正常运行", f"语音回复：好的, 主人好好休息！")
                    subprocess.Popen(
                        f"shutdown -s -t 1",
                        shell=True,
                        )
                    # popen.stdin.close()
                    # popen.wait()
                    # stdout.read()
                    # popen.stdout.close()
                elif IsShotDown in ["否", "不", "不要", "不关机"]:
                    TTS("好的, 不进行关机")
                    LOG.output("正常运行", f"语音回复：好的, 不进行关机")
                else:
                    TTS("主人，我没听懂")
                    LOG.output("正常运行", f"语音回复：主人，我没听懂")
            else:
                with requests.get(f"http://www.liulongbin.top:3006/api/robot?spoken={SpeechTWO}") as get:
                    if get.status_code == 200:
                        try:
                            TTS(str(get.json()['data']['info']['text']).replace("小思", "小雨"))
                        except TypeError:
                            continue


def run() -> None:
    Start = Thread(target=main)
    Start.start()