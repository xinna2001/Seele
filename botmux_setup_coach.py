"""Transparent PTY coach for the interactive ``botmux setup`` flow."""

from __future__ import annotations

import codecs
import os
import re
import shutil
import signal
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from platform_utils import app_path


@dataclass(frozen=True)
class VoiceCue:
    key: str
    filename: str
    text: str
    patterns: tuple[str, ...]


VOICE_CUES = (
    VoiceCue(
        "app_source",
        "mac_byte_botmux_app_source_16k.wav",
        "请选择飞书应用来源。建议选择“一次扫码创建新应用”。",
        ("飞书应用来源",),
    ),
    VoiceCue(
        "name",
        "mac_byte_botmux_name_16k.wav",
        "请为你的机器人取一个想要的名字。输入后按回车",
        ("机器人名称 [",),
    ),
    VoiceCue(
        "account",
        "mac_byte_botmux_account_16k.wav",
        "请确认屏幕显示的飞书账号是不是你自己的账号。正确请选择“确认并免扫码添加”；不正确请选择“更换账号”。",
        ("确认飞书账号：",),
    ),
    VoiceCue(
        "scan",
        "mac_byte_botmux_scan_16k.wav",
        "请打开飞书，扫描终端中的二维码，并确认当前账号和企业正确。",
        ("请用飞书 App 扫码登录",),
    ),
    VoiceCue(
        "owner",
        "mac_byte_botmux_owner_16k.wav",
        "请输入你自己的完整字节邮箱，不要只输入邮箱前缀，输入后按回车。",
        ("管理员 (owner):",),
    ),
    VoiceCue(
        "relogin",
        "mac_byte_botmux_relogin_16k.wav",
        "上次的飞书登录状态已经失效，请选择“重新扫码”。",
        ("上次飞书登录态已失效或无法确认账号",),
    ),
    VoiceCue(
        "existing_app",
        "mac_byte_botmux_existing_app_16k.wav",
        "请选择你要绑定的已有飞书应用。",
        ("\n 选择已有应用\n",),
    ),
    VoiceCue(
        "compatibility",
        "mac_byte_botmux_compatibility_16k.wav",
        "自动创建应用失败。建议先选择“返回应用来源”并重试；只有普通方式持续失败时，再选择兼容模式。",
        ("是否使用兼容模式？",),
    ),
    VoiceCue(
        "tenant",
        "mac_byte_botmux_tenant_16k.wav",
        "请选择租户类型。字节员工请选择“飞书中国版”。",
        ("租户类型",),
    ),
    VoiceCue(
        "app_id",
        "mac_byte_botmux_app_id_16k.wav",
        "请输入已有飞书应用的 App ID，格式通常以 cli 下划线开头。",
        ("AppID (cli_xxx):",),
    ),
    VoiceCue(
        "app_secret",
        "mac_byte_botmux_app_secret_16k.wav",
        "请输入同一个飞书应用的 App Secret。请不要把密钥发送给他人。",
        ("AppSecret:", "的 AppSecret（留空返回上一步）:"),
    ),
)

BOTMUX_VOICE_FILES = {cue.key: cue.filename for cue in VOICE_CUES}

_ANSI_ESCAPE_RE = re.compile(
    r"(?:\x1B\][^\x07]*(?:\x07|\x1B\\)|\x1B[@-_][0-?]*[ -/]*[@-~])"
)


def strip_terminal_control(text: str) -> str:
    return _ANSI_ESCAPE_RE.sub("", text).replace("\r", "")


class PromptCoach:
    """Turn Botmux output into voice cues and narrowly scoped automatic input."""

    def __init__(self, on_cue: Callable[[VoiceCue], None] | None = None):
        self._decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        self._buffer = ""
        self._fired_cues: set[str] = set()
        self._fired_actions: set[str] = set()
        self._on_cue = on_cue or (lambda cue: None)

    def feed(self, data: bytes) -> list[bytes]:
        decoded = self._decoder.decode(data)
        self._buffer = strip_terminal_control((self._buffer + decoded)[-24000:])

        for cue in VOICE_CUES:
            if cue.key in self._fired_cues:
                continue
            if any(pattern in self._buffer for pattern in cue.patterns):
                self._fired_cues.add(cue.key)
                self._on_cue(cue)

        actions: list[bytes] = []
        submenu = "选择 CLI 适配器 › TRAE (CoCo)"
        if (
            "cli_traex" not in self._fired_actions
            and submenu in self._buffer
            and "输入可搜索" in self._buffer
        ):
            self._fired_actions.add("cli_traex")
            actions.append(b"traex\r")
        elif (
            "cli_group" not in self._fired_actions
            and "选择 CLI 适配器" in self._buffer
            and submenu not in self._buffer
            and "输入可搜索" in self._buffer
        ):
            self._fired_actions.add("cli_group")
            actions.append(b"TRAE\r")

        if (
            "directory_mode" not in self._fired_actions
            and "新话题工作目录" in self._buffer
            and "输入可搜索" in self._buffer
        ):
            self._fired_actions.add("directory_mode")
            actions.append(b"\r")

        if (
            "default_directory" not in self._fired_actions
            and "默认工作目录（新话题直接在此目录启动）[~]:" in self._buffer
        ):
            self._fired_actions.add("default_directory")
            actions.append(b"\r")

        if (
            "repository_root" not in self._fired_actions
            and "仓库扫描根目录（卡片会列出其下的 git 仓库" in self._buffer
        ):
            self._fired_actions.add("repository_root")
            actions.append(b"\r")

        return actions


class VoicePlayer:
    """Play only the cue for the prompt currently visible on screen."""

    def __init__(self):
        self._process: subprocess.Popen | None = None

    def _stop_current(self) -> None:
        if self._process is not None and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait()
        self._process = None

    def play(self, cue: VoiceCue) -> None:
        self._stop_current()
        resources = os.environ.get("SEELE_RESOURCES_DIR", "").strip()
        if resources:
            path = Path(resources) / "audio" / "mac_byte" / cue.filename
        else:
            path = app_path("audio", "mac_byte", cue.filename)
        if path.is_file() and Path("/usr/bin/afplay").is_file():
            command = ["/usr/bin/afplay", str(path)]
        elif Path("/usr/bin/say").is_file():
            command = ["/usr/bin/say", cue.text]
        else:
            return
        try:
            self._process = subprocess.Popen(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError:
            self._process = None

    def stop(self) -> None:
        self._stop_current()


def _copy_window_size(source_fd: int, target_fd: int) -> None:
    import fcntl
    import termios

    try:
        size = fcntl.ioctl(source_fd, termios.TIOCGWINSZ, b"\0" * 8)
        fcntl.ioctl(target_fd, termios.TIOCSWINSZ, size)
    except OSError:
        pass


def run_coached_command(
    command: Sequence[str],
    *,
    coach: PromptCoach | None = None,
    stdin_fd: int | None = None,
    stdout_fd: int | None = None,
) -> int:
    if os.name != "posix":
        raise RuntimeError("Botmux PTY coach requires a POSIX terminal")

    import errno
    import fcntl
    import pty
    import select
    import termios
    import tty

    input_fd = sys.stdin.fileno() if stdin_fd is None else stdin_fd
    output_fd = sys.stdout.fileno() if stdout_fd is None else stdout_fd
    if not os.isatty(input_fd):
        raise RuntimeError("Botmux setup must run in an interactive terminal")

    child_pid, master_fd = pty.fork()
    if child_pid == 0:
        env = os.environ.copy()
        env.setdefault("TERM", "xterm-256color")
        os.execvpe(command[0], list(command), env)

    prompt_coach = coach or PromptCoach()
    original_attrs = termios.tcgetattr(input_fd)
    original_flags = fcntl.fcntl(input_fd, fcntl.F_GETFL)
    previous_winch = signal.getsignal(signal.SIGWINCH)
    child_reaped = False

    def resize(_signum=None, _frame=None):
        _copy_window_size(input_fd, master_fd)

    try:
        tty.setraw(input_fd)
        fcntl.fcntl(input_fd, fcntl.F_SETFL, original_flags | os.O_NONBLOCK)
        resize()
        signal.signal(signal.SIGWINCH, resize)

        while True:
            readable, _, _ = select.select([input_fd, master_fd], [], [], 0.5)
            if input_fd in readable:
                try:
                    user_data = os.read(input_fd, 4096)
                except BlockingIOError:
                    user_data = b""
                if user_data:
                    os.write(master_fd, user_data)

            if master_fd in readable:
                try:
                    output = os.read(master_fd, 8192)
                except OSError as exc:
                    if exc.errno != errno.EIO:
                        raise
                    output = b""
                if output:
                    os.write(output_fd, output)
                    for automatic_input in prompt_coach.feed(output):
                        os.write(master_fd, automatic_input)
                else:
                    break

        _, status = os.waitpid(child_pid, 0)
        child_reaped = True
        return os.waitstatus_to_exitcode(status)
    finally:
        signal.signal(signal.SIGWINCH, previous_winch)
        termios.tcsetattr(input_fd, termios.TCSADRAIN, original_attrs)
        fcntl.fcntl(input_fd, fcntl.F_SETFL, original_flags)
        os.close(master_fd)
        if not child_reaped:
            try:
                os.kill(child_pid, signal.SIGHUP)
            except ProcessLookupError:
                pass
            try:
                os.waitpid(child_pid, 0)
            except ChildProcessError:
                pass


def main(argv: Sequence[str] | None = None) -> int:
    args = list(argv or ())
    if args:
        command = args
    else:
        botmux = shutil.which("botmux")
        if not botmux:
            raise RuntimeError("未找到 botmux 命令")
        command = [botmux, "setup"]

    player = VoicePlayer()
    try:
        return run_coached_command(command, coach=PromptCoach(player.play))
    finally:
        player.stop()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
