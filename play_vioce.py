import write_file as wf
from platform_utils import app_path

try:
    import sounddevice as sd
    import soundfile as sf
except (ImportError, OSError):
    sd = None
    sf = None

#1.0不使用实时text转语音
def main(file_name):
    if sd is None or sf is None:
        return
    try:
        data, fs = sf.read(str(app_path("audio", file_name)))
        sd.play(data, fs)
        sd.wait()
    except (OSError, RuntimeError):
        return

def yingdao_main(yingdao_name,file_name,is_finish=False):
    state_path = app_path("state.json")
    dic = wf.read_dict_from_json(state_path) or {}
    if dic.get(yingdao_name)=="0":
        main(file_name)
    if is_finish:
        dic[yingdao_name]="1"
        wf.write_dict_to_json(dic, state_path)
