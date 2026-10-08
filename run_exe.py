import os
import sys
import tempfile
import uuid
import subprocess
from platform_utils import hidden_subprocess_kwargs

if sys.platform == "darwin":
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")
    os.environ.setdefault("QT_SCALE_FACTOR_ROUNDING_POLICY", "PassThrough")


def _pythonw():
    exe = sys.executable
    low = exe.lower()
    if low.endswith("python.exe"):
        candidate = exe[:-10] + "pythonw.exe"
        if os.path.exists(candidate):
            return candidate
    return exe

def _spawn_splash(ready_file):
    if getattr(sys, "frozen", False):
        cmd = [sys.executable, "--splash", ready_file]
    else:
        cmd = [_pythonw(), os.path.abspath(__file__), "--splash", ready_file]
    return subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        **hidden_subprocess_kwargs(),
    )

def _run_splash(ready_file):
    import play_stare
    play_stare.main(ready_file=ready_file, timeout_seconds=600)


def _run_smoke_test():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ["SEELE_EDITION"] = "packaging-smoke"
    from PyQt5.QtWidgets import QApplication
    import Seele

    app = QApplication.instance() or QApplication([])
    window = Seele.DesktopWife()
    window.show()
    app.processEvents()
    valid = bool(window.movie.isValid() and window.width() > 0 and window.height() > 0)
    window.shutdown()
    window.close()
    app.processEvents()
    return 0 if valid else 1


def main():
    argv = sys.argv[1:]
    if argv == ["--smoke-test"]:
        return _run_smoke_test()
    if argv and argv[0] == "--botmux-setup-coach":
        import botmux_setup_coach
        return botmux_setup_coach.main(argv[1:])
    if len(argv) >= 2 and argv[0] == "--splash":
        _run_splash(argv[1])
        return 0

    ready_file = os.path.join(tempfile.gettempdir(), f"seele_ready_{uuid.uuid4().hex}.flag")
    try:
        if os.path.exists(ready_file):
            os.remove(ready_file)
    except OSError:
        pass

    splash = _spawn_splash(ready_file)
    os.environ["SEELE_READY_FILE"] = ready_file
    try:
        import Seele
        Seele.main()
    finally:
        if splash and splash.poll() is None:
            try:
                splash.terminate()
            except OSError:
                pass
        try:
            if os.path.exists(ready_file):
                os.remove(ready_file)
        except OSError:
            pass
    return 0

def run():
    return main()

if __name__ == "__main__":
    raise SystemExit(main())
