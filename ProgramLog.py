import time
import os

class ProgramLog:
    def __init__(self):
        self._time = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
        self.FileName = f".\\Log\\{time.strftime('%Y-%m-%d', time.gmtime())}.log"
        if os.path.isfile(self.FileName):
            pass
        else:
            open(self.FileName, "w", encoding="utf-8").close()

    def output(self, state, _msg):
        with open(self.FileName, "a+", encoding="utf-8") as wfp:
            wfp.write(f"[{self._time}] | [{state}] | [{_msg}]\n")
        print(f"[{self._time}] | [{state}] | [{_msg}]")