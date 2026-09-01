import time
from platform_utils import app_path

class ProgramLog:
    def __init__(self):
        self._time = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
        log_dir = app_path("Log")
        log_dir.mkdir(parents=True, exist_ok=True)
        self.FileName = log_dir / f"{time.strftime('%Y-%m-%d', time.gmtime())}.log"
        self.FileName.touch(exist_ok=True)

    def output(self, state, _msg):
        with open(self.FileName, "a+", encoding="utf-8") as wfp:
            wfp.write(f"[{self._time}] | [{state}] | [{_msg}]\n")
        print(f"[{self._time}] | [{state}] | [{_msg}]")
