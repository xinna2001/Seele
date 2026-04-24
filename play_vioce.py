
import sounddevice as sd
import soundfile as sf
import write_file as wf
#1.0不使用实时text转语音
def main(file_name):
    data, fs = sf.read(".\\audio\\"+file_name)
    sd.play(data, fs)
    sd.wait()  # 阻塞直到播放完成

def yingdao_main(yingdao_name,file_name,is_finish=False):
    dic=wf.read_dict_from_json("state.json")
    if dic.get(yingdao_name)=="0":
        main(file_name)
    if is_finish:
        dic[yingdao_name]="1"
        wf.write_dict_to_json(dic,"state.json")
