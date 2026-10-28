"""Linux half of the Windows byte installer. Runs in the selected WSL account."""

from __future__ import annotations

import configparser
import json
import os
import pathlib
import shlex
import subprocess
import sys
import time


def configure_wsl(path: pathlib.Path, user: str) -> bool:
    config = configparser.ConfigParser(interpolation=None, strict=False)
    config.optionxform = str
    if path.exists():
        config.read(path, encoding="utf-8")
    changed = False
    for section, key, value in (("boot", "systemd", "true"), ("user", "default", user)):
        if not config.has_section(section):
            config.add_section(section)
        if config.get(section, key, fallback="") != value:
            config.set(section, key, value)
            changed = True
    if changed:
        temporary = path.with_name(path.name + ".seele.tmp")
        with temporary.open("w", encoding="utf-8") as stream:
            config.write(stream)
        os.replace(temporary, path)
    return changed


def shell(script: str, *, timeout: int = 1800) -> None:
    subprocess.run(["/bin/bash", "-lc", script], check=True, timeout=timeout)


def environment_script() -> str:
    return r"""
set -euo pipefail
export NVM_DIR="$HOME/.nvm"
if [ -s "$NVM_DIR/nvm.sh" ]; then
  set +u
  source "$NVM_DIR/nvm.sh"
  set -u
fi
export PATH="$HOME/.botmux/bin:$HOME/.local/bin:$PATH"
export XDG_RUNTIME_DIR="/run/user/$(id -u)"
export DBUS_SESSION_BUS_ADDRESS="unix:path=$XDG_RUNTIME_DIR/bus"
"""


def has_bots(path: pathlib.Path) -> bool:
    try:
        bots = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(bots, list):
            return any(isinstance(bot, dict) for bot in bots)
        if isinstance(bots, dict):
            return bool(bots)
    except (OSError, ValueError):
        pass
    return False


def build_install_script(runtime: pathlib.Path, *, configured: bool) -> str:
    # configure_linux executes this source alone as root before staging resources.
    from botmux_install import official_install_commands, pinned_install_commands

    coach = shlex.join(["python3", str(runtime / "botmux_setup_coach.py")])
    login = coach + " --login-command -- "
    setup = "printf '\\n保留已有 Botmux 配置。\\n'" if configured else f"""
python3 {shlex.quote(str(runtime / 'windows_byte_linux.py'))} --voice botmux_setup
{coach}
"""
    return environment_script() + f"""
{pinned_install_commands(
    official_install_commands(),
    after_install='if systemctl --user is-active --quiet botmux.service; then systemctl --user stop botmux.service; fi',
)}
if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1 ||
   ! node -e 'process.exit(Number(process.versions.node.split(".")[0]) >= 22 ? 0 : 1)'; then
  if [ ! -s "$NVM_DIR/nvm.sh" ]; then
    curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
  fi
  set +u
  source "$NVM_DIR/nvm.sh"
  nvm install 22
  nvm use 22
  set -u
fi
node -v
npm -v
if ! command -v traex >/dev/null 2>&1 || ! traex backend cn --help >/dev/null 2>&1; then
  curl -fsSL https://code.byted.org/api/tos-proxy/download/traex_install.sh |
    env TRAEX_INSTALL_ASSUME_YES=1 TRAEX_INSTALL_REMOVE_COCO=1 TRAEX_INSTALL_REMOVE_BREW=0 sh
  hash -r
fi
traex backend cn --help >/dev/null
for profile in "$HOME/.profile" "$HOME/.bashrc"; do
  if ! grep -F '# Seele Windows byte CLI PATH' "$profile" >/dev/null 2>&1; then
    printf '\\n# Seele Windows byte CLI PATH\\nexport PATH="$HOME/.botmux/bin:$HOME/.local/bin:$PATH"\\n' >> "$profile"
  fi
done
if ! command -v lark-cli >/dev/null 2>&1; then
  npm install -g @larksuite/cli@latest --registry https://bnpm.byted.org/
fi
if ! command -v agentbuddy >/dev/null 2>&1; then
  npm install -g agentbuddy@latest --registry https://bnpm.byted.org/
fi
for tool in botmux tmux node npm traex lark-cli agentbuddy; do
  command -v "$tool" >/dev/null
done
traex backend cn
if ! traex login status >/dev/null 2>&1; then
  python3 {shlex.quote(str(runtime / 'windows_byte_linux.py'))} --voice traex_login
  {login}traex login --sso-device
fi
traex login status >/dev/null
if ! lark-cli config show >/dev/null 2>&1; then
  python3 {shlex.quote(str(runtime / 'windows_byte_linux.py'))} --voice lark_config
  {login}lark-cli config init --new --lang zh_cn --name seele
fi
lark-cli config show >/dev/null
if ! lark-cli auth status --json --verify >/dev/null 2>&1; then
  python3 {shlex.quote(str(runtime / 'windows_byte_linux.py'))} --voice lark_login
  {login}lark-cli auth login --recommend
fi
lark-cli auth status --json --verify >/dev/null
if ! agentbuddy status --json >/dev/null 2>&1; then
  python3 {shlex.quote(str(runtime / 'windows_byte_linux.py'))} --voice agentbuddy_login
  {login}agentbuddy login --region cn --login-mode device --json --yes
fi
agentbuddy status --json >/dev/null
{setup}
botmux plugin install {shlex.quote(str(runtime / 'botmux-skill'))} --link
botmux plugin enable seele
botmux autostart enable
systemctl --user is-enabled botmux.service
systemctl --user start botmux.service
systemctl --user is-active botmux.service
systemctl --user is-enabled botmux-watchdog.timer
systemctl --user is-active botmux-watchdog.timer
test "$(loginctl show-user "$(id -un)" -p Linger --value)" = yes
"""


def keepalive() -> int:
    """Foreground Linux client keeps wsl.exe and the scheduled task alive."""
    import fcntl

    root = pathlib.Path.home() / ".seele/windows_byte"
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (root / "keepalive.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 0
        os.environ["XDG_RUNTIME_DIR"] = f"/run/user/{os.getuid()}"
        os.environ["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path=/run/user/{os.getuid()}/bus"
        failures = 0
        while True:
            try:
                result = subprocess.run(["systemctl", "--user", "start", "botmux.service"],
                                        capture_output=True, timeout=20)
                active = subprocess.run(["systemctl", "--user", "is-active", "--quiet",
                                         "botmux.service"], capture_output=True, timeout=20)
                failures = failures + 1 if result.returncode or active.returncode else 0
            except (OSError, subprocess.SubprocessError):
                failures += 1
            if failures >= 5:
                return 1  # Windows task retries and relaunches the distro.
            time.sleep(30)


def main() -> int:
    if "--keepalive" in sys.argv:
        return keepalive()
    if "--voice" in sys.argv:
        from botmux_setup_coach import VoiceCue, VoicePlayer
        voices = {
            "traex_login": "请登录 Trae CLI，在浏览器中完成本人授权。",
            "lark_config": "请在浏览器初始化飞书 CLI 应用。",
            "lark_login": "请在浏览器登录飞书 CLI。",
            "agentbuddy_login": "请在浏览器完成 Skill 空间登录。",
            "botmux_setup": "请按终端提示设置机器人名称、账号和完整邮箱。",
        }
        key = sys.argv[sys.argv.index("--voice") + 1]
        player = VoicePlayer()
        player.play(VoiceCue(key, f"mac_byte_{key}_16k.wav", voices[key], ()))
        # PowerShell continues asynchronously after this small voice launcher exits.
        return 0
    if os.getuid() == 0:
        raise RuntimeError("不要以 root 运行 Botmux 安装。")
    runtime = pathlib.Path(__file__).resolve().parent
    os.environ["SEELE_RESOURCES_DIR"] = str(runtime)
    os.environ["SEELE_WINDOWS_WSL"] = "1"
    shell(build_install_script(runtime, configured=has_bots(pathlib.Path.home() / ".botmux/bots.json")),
          timeout=14400)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
