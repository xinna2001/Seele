from threading import Thread
import sounddevice as sd
import soundfile as sf
#1.0不使用实时text转语音
def main(file_path):
    data, fs = sf.read(file_path)
    sd.play(data, fs)
    sd.wait()  # 阻塞直到播放完成


def run() -> None:
    Start = Thread(target=main)
    Start.start()