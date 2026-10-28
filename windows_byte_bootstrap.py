"""Resumable, current-user Windows -> WSL2 installer for Seele windows_byte."""

from __future__ import annotations

import base64
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import time
from pathlib import Path, PurePosixPath

from botmux_install import BOTMUX_VERSION
from platform_utils import app_path, hidden_subprocess_kwargs

DISTRO = "Ubuntu-24.04"
RESUME_TASK = "Seele-WindowsByte-Resume"
SERVICE_TASK = "Seele-Botmux-WSL"
RUN_VALUE = "SeeleWindowsByteResume"
TERMINAL_STATES = {"completed", "failed", "waiting_reboot"}


def is_windows_byte() -> bool:
    if sys.platform != "win32":
        return False
    from mac_byte_bootstrap import current_edition
    return current_edition() == "windows_byte"


def state_dir() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local")) / "Seele/windows_byte"


def read_status() -> dict:
    try:
        data = json.loads((state_dir() / "status.json").read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def installation_is_current(status: dict | None = None) -> bool:
    status = read_status() if status is None else status
    return (
        status.get("state") == "completed"
        and status.get("botmux_version") == BOTMUX_VERSION
    )


def save_status(status: dict, **updates) -> dict:
    status.update(updates, updated_at=time.time())
    root = state_dir()
    root.mkdir(parents=True, exist_ok=True)
    target = root / "status.json"
    temporary = target.with_suffix(".tmp")
    temporary.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, target)
    return status


class InstallLock:
    """Kernel-owned lock: a killed installer never leaves a stale six-hour lock."""

    def __enter__(self):
        state_dir().mkdir(parents=True, exist_ok=True)
        self.file = (state_dir() / "installer.lock").open("a+b")
        if os.fstat(self.file.fileno()).st_size == 0:
            self.file.write(b"0")
            self.file.flush()
        self.file.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.file.close()
            raise InstallerAlreadyRunning("已有 Windows 字节版安装终端在运行。") from None
        return self

    def __exit__(self, *args):
        self.file.close()


class InstallerAlreadyRunning(RuntimeError):
    pass


def ps_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def powershell_command(script: str) -> list[str]:
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    return ["powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive",
            "-ExecutionPolicy", "Bypass", "-EncodedCommand", encoded]


def run_ps(script: str, *, timeout: int = 45) -> str:
    result = subprocess.run(powershell_command(
        "[Console]::OutputEncoding = [Text.UTF8Encoding]::new();\n"
        "$ErrorActionPreference = 'Stop';\n" + script
    ), capture_output=True, timeout=timeout, **hidden_subprocess_kwargs())
    if result.returncode:
        # No captured output in status files: auth URLs and secrets can appear there.
        raise RuntimeError("Windows 系统命令失败，请检查当前用户权限或企业策略。")
    return result.stdout.decode("utf-8-sig", errors="replace").strip()


def windows_identity() -> str:
    return run_ps("[Security.Principal.WindowsIdentity]::GetCurrent().User.Value")


def boot_id() -> str:
    return run_ps("(Get-CimInstance Win32_OperatingSystem).LastBootUpTime.ToUniversalTime().ToString('o')")


def list_distros() -> list[dict]:
    import winreg
    rows = []
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Lxss") as root:
            for index in range(winreg.QueryInfoKey(root)[0]):
                with winreg.OpenKey(root, winreg.EnumKey(root, index)) as entry:
                    rows.append({
                        "name": winreg.QueryValueEx(entry, "DistributionName")[0],
                        "version": winreg.QueryValueEx(entry, "Version")[0],
                    })
    except OSError:
        pass
    return rows


def choose_distro(rows: list[dict], preferred: str = "") -> dict | None:
    explicit = os.environ.get("SEELE_WSL_DISTRO", "").strip() or preferred
    if explicit:
        return next((row for row in rows if row["name"] == explicit), None)
    for name in (DISTRO, "Ubuntu"):
        match = next((row for row in rows if row["name"] == name), None)
        if match:
            return match
    return next((row for row in rows if row["name"].lower().startswith("ubuntu")
                 and row["version"] == 2), None)


def wsl_command(distro: str, user: str, *command: str) -> list[str]:
    return ["wsl.exe", "--distribution", distro, "--user", user, "--exec", *command]


def run_wsl(distro: str, user: str, *command: str, data: bytes | None = None,
            timeout: int = 120, interactive: bool = False) -> subprocess.CompletedProcess:
    kwargs = {} if interactive else hidden_subprocess_kwargs()
    result = subprocess.run(wsl_command(distro, user, *command), input=data,
                            capture_output=not interactive, timeout=timeout, **kwargs)
    if result.returncode:
        raise RuntimeError(
            "WSL 命令未完成。请检查终端提示、网络与 CPU 虚拟化；"
            "修复后从桌宠菜单继续安装，已有数据不会删除。"
        )
    return result


def elevate_components() -> bool:
    """Only fixed OS component commands run elevated; never launch a user script."""
    script = r"""
$ErrorActionPreference = 'Stop'
$reboot = $false
foreach ($feature in @('Microsoft-Windows-Subsystem-Linux', 'VirtualMachinePlatform')) {
  $before = Get-WindowsOptionalFeature -Online -FeatureName $feature
  if ($before.State -eq 'EnablePending') { $reboot = $true; continue }
  if ($before.State -ne 'Enabled') {
    $result = Enable-WindowsOptionalFeature -Online -FeatureName $feature -All -NoRestart
    if ($result.RestartNeeded) { $reboot = $true }
  }
}
if ($reboot) { exit 3010 }
& "$env:SystemRoot\System32\wsl.exe" --install --no-distribution
$code = $LASTEXITCODE
if ($code -eq 3010) { $reboot = $true }
elseif ($code -ne 0) { exit 1 }
if ($reboot) { exit 3010 }
exit 0
"""
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    wrapper = f"""
$process = Start-Process -FilePath "$env:SystemRoot\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" `
  -Verb RunAs -Wait -PassThru -ArgumentList '-NoProfile -NonInteractive -ExecutionPolicy Bypass -EncodedCommand {encoded}'
$process.ExitCode
"""
    code = int(run_ps(wrapper, timeout=1800).splitlines()[-1])
    if code not in (0, 3010):
        raise RuntimeError("WSL 系统组件安装未完成，请查看管理员窗口提示后重试。")
    return code == 3010


def gui_command() -> list[str]:
    if getattr(sys, "frozen", False):
        return [str(app_path("Seele.exe")), "--windows-byte"]
    executable = Path(sys.executable).with_name("pythonw.exe")
    return [str(executable if executable.is_file() else Path(sys.executable)),
            str(app_path("run_exe.py")), "--windows-byte"]


def task_script(name: str, command: list[str], sid: str, *, keepalive: bool = False) -> str:
    argument = subprocess.list2cmdline(command[1:])
    return f"""
$action = New-ScheduledTaskAction -Execute {ps_string(command[0])} -Argument {ps_string(argument)}
$trigger = New-ScheduledTaskTrigger -AtLogOn -User {ps_string(sid)}
{"$recovery = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(5) -RepetitionInterval (New-TimeSpan -Minutes 5); $trigger = @($trigger, $recovery)" if keepalive else ""}
$principal = New-ScheduledTaskPrincipal -UserId {ps_string(sid)} -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew `
  -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) `
  -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName {ps_string(name)} -Action $action -Trigger $trigger `
  -Principal $principal -Settings $settings -Force | Out-Null
{"Start-ScheduledTask -TaskName " + ps_string(name) if keepalive else ""}
if (-not (Get-ScheduledTask -TaskName {ps_string(name)})) {{ throw 'Task readback failed' }}
"""


def set_resume(sid: str) -> str:
    try:
        run_ps(task_script(RESUME_TASK, gui_command(), sid))
        return "scheduled_task"
    except RuntimeError:
        import winreg
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                              r"Software\Microsoft\Windows\CurrentVersion\Run") as key:
            winreg.SetValueEx(key, RUN_VALUE, 0, winreg.REG_SZ,
                             subprocess.list2cmdline(gui_command()))
        return "hkcu_run"


def remove_resume() -> None:
    try:
        run_ps(f"Unregister-ScheduledTask -TaskName {ps_string(RESUME_TASK)} -Confirm:$false -ErrorAction SilentlyContinue")
    except RuntimeError:
        pass
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                           r"Software\Microsoft\Windows\CurrentVersion\Run",
                           0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, RUN_VALUE)
    except OSError:
        pass


def reboot_required(status: dict, current_boot: str) -> bool:
    return status.get("state") == "waiting_reboot" and status.get("boot_id") == current_boot


def prepare_user(distro: str) -> str:
    run_wsl(distro, "root", "/bin/sh", "-c",
            "command -v python3 >/dev/null || (apt-get update && apt-get install -y python3)")
    # wsl without --user reveals the real configured default rather than assuming dev.
    result = subprocess.run(["wsl.exe", "-d", distro, "--exec", "id", "-un"],
                            capture_output=True, timeout=120, **hidden_subprocess_kwargs())
    if result.returncode:
        raise RuntimeError("无法识别 WSL 默认用户。")
    user = result.stdout.decode("utf-8").strip()
    if user == "root":
        print("\nWSL 需要一个普通 Linux 用户。已有用户请输入原用户名；新建建议 dev。")
        user = input("Linux 用户名 [dev]: ").strip() or "dev"
        if not re.fullmatch(r"[a-z_][a-z0-9_-]{0,31}", user) or user == "root":
            raise RuntimeError("Linux 用户名无效，请用小写字母开头的普通用户名。")
        check = subprocess.run(wsl_command(distro, "root", "id", "-u", user),
                               capture_output=True, timeout=30, **hidden_subprocess_kwargs())
        if check.returncode:
            run_wsl(distro, "root", "useradd", "--create-home", "--shell", "/bin/bash",
                    "--groups", "sudo", user)
        password = run_wsl(distro, "root", "passwd", "--status", user).stdout.decode().split()
        if len(password) > 1 and password[1] in {"L", "NP"}:
            print("请设置 Linux 密码，用于以后在 WSL 中执行 sudo；输入不会显示。")
            run_wsl(distro, "root", "passwd", user, timeout=3600, interactive=True)
    return user


def configure_linux(distro: str, user: str) -> None:
    # Execute the same tested configuration function as a root-only WSL step.
    script = (
        "import sys; scope={'__name__':'seele_wsl_config'}; "
        "exec(sys.stdin.read(),scope); "
        "print('changed' if scope['configure_wsl']("
        "scope['pathlib'].Path('/etc/wsl.conf'),sys.argv[1]) else 'unchanged')"
    )
    changed = run_wsl(distro, "root", "python3", "-c", script, user,
                      data=app_path("windows_byte_linux.py").read_bytes()).stdout.strip() == b"changed"
    if changed:
        print("systemd 或默认用户配置已更新，将重启当前发行版，请保存其中的工作。")
        result = subprocess.run(["wsl.exe", "--terminate", distro], capture_output=True,
                                timeout=90, **hidden_subprocess_kwargs())
        if result.returncode:
            raise RuntimeError("无法重启目标 WSL 发行版，请关闭它的终端后重试。")
    # Do not shut down other distributions.
    run_wsl(distro, "root", "/bin/sh", "-c",
            'test "$(cat /proc/1/comm)" = systemd', timeout=120)
    run_wsl(distro, "root", "/bin/sh", "-c",
            "apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y "
            "ca-certificates curl git jq tmux unzip zip python3 sudo", timeout=1800,
            interactive=True)
    run_wsl(distro, "root", "loginctl", "enable-linger", user)
    run_wsl(distro, "root", "systemctl", "start",
            "user@" + run_wsl(distro, "root", "id", "-u", user).stdout.decode().strip() + ".service")


def stage_runtime(distro: str, user: str) -> str:
    home = run_wsl(distro, user, "/bin/sh", "-c", 'printf "%s" "$HOME"').stdout.decode("utf-8")
    if not PurePosixPath(home).is_absolute() or home in ("/", "/root"):
        raise RuntimeError("Botmux 必须部署到普通 Linux 用户的主目录。")
    destination = home + "/.seele/windows_byte"
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        for name in ("windows_byte_linux.py", "botmux_install.py", "botmux_setup_coach.py", "platform_utils.py",
                     "audio/mac_byte", "botmux-skill"):
            source = app_path(name)
            if not source.exists():
                raise RuntimeError(f"安装包缺少资源：{name}")
            archive.add(source, arcname=name)
    script = 'umask 077; mkdir -p "$1"; tar -xf - -C "$1"; chmod 700 "$1"'
    run_wsl(distro, user, "/bin/sh", "-c", script, "seele", destination,
            data=buffer.getvalue(), timeout=180)
    return home


def register_keepalive(distro: str, user: str, home: str, sid: str) -> None:
    wsl = wsl_command(distro, user, "/bin/bash", "-lc",
                     "exec python3 " + __import__("shlex").quote(
                         home + "/.seele/windows_byte/windows_byte_linux.py") + " --keepalive")
    # Hidden PowerShell stays in the foreground of the task while WSL stays alive.
    script = "& " + " ".join(ps_string(arg) for arg in wsl) + "; exit $LASTEXITCODE"
    command = powershell_command(script)
    command[1:1] = ["-WindowStyle", "Hidden"]
    run_ps(task_script(SERVICE_TASK, command, sid, keepalive=True))


def configure_console() -> None:
    """Redirected Windows output defaults to CP1252 on English systems."""
    if sys.platform == "win32":
        for stream in (sys.stdout, sys.stderr):
            if stream is not None and hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8", errors="replace")


def run_install() -> int:
    configure_console()
    status = read_status()
    try:
        with InstallLock():
            sid = windows_identity()
            if status.get("windows_sid") and status["windows_sid"] != sid:
                raise RuntimeError("请用首次安装 WSL 的同一个 Windows 账号继续。")
            current_boot = boot_id()
            if reboot_required(status, current_boot):
                print("WSL 系统组件需要重启 Windows。进度已保存，登录后会自动继续。")
                return 3010
            save_status(status, state="running", stage="wsl", windows_sid=sid,
                        resume=set_resume(sid), message="正在检查 WSL2。")
            rows = list_distros()
            preferred = os.environ.get("SEELE_WSL_DISTRO", "").strip() or status.get("distro", "")
            row = choose_distro(rows, preferred)
            if preferred and not row:
                raise RuntimeError("指定的 WSL 发行版不存在，请检查 SEELE_WSL_DISTRO。")
            if not row:
                try:
                    ready = subprocess.run(["wsl.exe", "--status"], capture_output=True,
                                           timeout=120, **hidden_subprocess_kwargs()).returncode == 0
                except FileNotFoundError:
                    ready = False
                if not ready and elevate_components():
                    save_status(status, state="waiting_reboot", boot_id=current_boot,
                                message="请重启 Windows；同一用户登录后自动继续安装。")
                    print(status["message"])
                    return 3010
                version = subprocess.run(["wsl.exe", "--set-default-version", "2"], timeout=120)
                if version.returncode:
                    raise RuntimeError("无法设置 WSL2 默认版本，请检查 WSL 内核和 CPU 虚拟化。")
                result = subprocess.run(["wsl.exe", "--install", "--distribution", DISTRO,
                                         "--no-launch"], timeout=1800)
                if result.returncode == 3010:
                    save_status(status, state="waiting_reboot", boot_id=current_boot,
                                message="Ubuntu 安装需要重启 Windows，登录后继续。")
                    return 3010
                if result.returncode:
                    raise RuntimeError("Ubuntu 下载或注册未完成，请检查网络并重启后续装。")
                row = choose_distro(list_distros())
                if not row:
                    raise RuntimeError("Ubuntu 尚未注册，请从开始菜单打开 Ubuntu 后继续安装。")
            distro = row["name"]
            save_status(status, distro=distro)
            if row["version"] != 2:
                # Conversion must retain the existing distribution and files.
                if elevate_components():
                    save_status(status, state="waiting_reboot", boot_id=current_boot,
                                message="请重启 Windows，之后继续将现有发行版转换为 WSL2。")
                    return 3010
                result = subprocess.run(["wsl.exe", "--set-version", distro, "2"], timeout=3600)
                if result.returncode == 3010:
                    save_status(status, state="waiting_reboot", boot_id=current_boot,
                                message="WSL2 转换需要重启 Windows，登录后继续。")
                    return 3010
                if result.returncode:
                    raise RuntimeError("WSL2 转换失败，请检查虚拟化与 WSL 内核。")
            # A registered distro may still have pending Windows features.
            try:
                run_wsl(distro, "root", "/bin/true")
            except RuntimeError:
                if elevate_components():
                    save_status(status, state="waiting_reboot", boot_id=current_boot,
                                message="请重启 Windows；登录后从已保存进度继续。")
                    return 3010
                run_wsl(distro, "root", "/bin/true")
            user = prepare_user(distro)
            save_status(status, stage="linux", linux_user=user,
                        message="正在安装 Linux 依赖并启用 systemd。")
            configure_linux(distro, user)
            home = stage_runtime(distro, user)
            save_status(status, linux_home=home, stage="botmux",
                        message="请在安装终端完成 CLI 登录和机器人配置。")
            run_wsl(distro, user, "/bin/bash", "-lc",
                    "exec python3 " + __import__("shlex").quote(
                        home + "/.seele/windows_byte/windows_byte_linux.py"),
                    timeout=14400, interactive=True)
            save_status(status, stage="autostart", message="正在注册登录自启与 WSL 保活。")
            register_keepalive(distro, user, home, sid)
            remove_resume()
            save_status(status, state="completed", stage="ready",
                        botmux_version=BOTMUX_VERSION,
                        message="Botmux 已安装，已启用当前用户登录后自启。")
            print("\n" + status["message"])
            return 0
    except InstallerAlreadyRunning as exc:
        print(str(exc))
        return 2
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError, KeyboardInterrupt, EOFError) as exc:
        # Preserve last completed stage and avoid capturing interactive command output.
        message = str(exc) if isinstance(exc, RuntimeError) else "安装已中断，可从桌宠菜单继续。"
        save_status(status, state="failed", message=message)
        print("\n" + message)
        return 1


def helper_command() -> list[str]:
    if getattr(sys, "frozen", False):
        helper = app_path("bin", "SeeleWindowsBootstrap.exe")
        if not helper.is_file():
            raise RuntimeError("安装包缺少 Windows 安装终端。")
        return [str(helper), "--resources", str(app_path())]
    executable = Path(sys.executable).with_name("python.exe")
    return [str(executable if executable.is_file() else Path(sys.executable)),
            str(app_path("windows_byte_bootstrap.py"))]


def launch_and_wait(callback) -> None:
    started = time.time()
    process = subprocess.Popen(helper_command(), creationflags=subprocess.CREATE_NEW_CONSOLE)
    callback({"state": "launched", "mode": "full"})
    last = None
    while process.poll() is None:
        status = read_status()
        if status.get("state") in TERMINAL_STATES and status.get("updated_at", 0) < started:
            time.sleep(1)
            continue
        key = (status.get("state"), status.get("stage"), status.get("message"))
        if status and key != last:
            last = key
            callback(dict(status))
        if status.get("state") in TERMINAL_STATES:
            return
        time.sleep(1)
    status = read_status()
    if status.get("state") not in TERMINAL_STATES or status.get("updated_at", 0) < started:
        status = {"state": "failed", "message": "安装终端已关闭，可从菜单继续安装。"}
    callback(status)


def main() -> int:
    if "--resources" in sys.argv:
        index = sys.argv.index("--resources")
        # Explicit resource location passed from the frozen GUI, not from cwd.
        import platform_utils
        root = Path(sys.argv[index + 1]).resolve()
        platform_utils.get_base_dir = lambda: root
    if "--self-check" in sys.argv:
        return 0 if all(app_path(name).exists() for name in (
            "windows_byte_linux.py", "botmux_install.py", "botmux_setup_coach.py", "platform_utils.py",
            "botmux-skill/dist", "audio/mac_byte")) else 1
    if sys.platform != "win32":
        raise RuntimeError("此安装入口仅支持 Windows。")
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    code = run_install()
    if code in (1, 3010) and sys.stdin.isatty():
        print("WSL 系统组件需要重启 Windows。" if code == 3010 else "安装未完成。")
        try:
            input("\n按回车关闭安装窗口。")
        except (EOFError, KeyboardInterrupt):
            pass
    return code


if __name__ == "__main__":
    raise SystemExit(main())
