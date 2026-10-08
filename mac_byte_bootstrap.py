"""First-run Botmux bootstrap for the internal macOS edition."""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

from platform_utils import app_path


EDITION_NAME = "mac_byte"
BYTE_NPM_REGISTRY = "https://bnpm.byted.org/"
PUBLIC_NPM_REGISTRY = "https://registry.npmjs.org/"
LOCK_TTL_SECONDS = 6 * 60 * 60

VOICE_FILES = {
    "install": "mac_byte_install_16k.wav",
    "traex_login": "mac_byte_traex_login_16k.wav",
    "lark_config": "mac_byte_lark_config_16k.wav",
    "lark_login": "mac_byte_lark_login_16k.wav",
    "agentbuddy_login": "mac_byte_agentbuddy_login_16k.wav",
    "botmux_setup": "mac_byte_botmux_setup_16k.wav",
}


def current_edition(path: str | os.PathLike | None = None) -> str:
    override = os.environ.get("SEELE_EDITION", "").strip()
    if override:
        return override
    edition_path = Path(path) if path else app_path("EDITION")
    try:
        return edition_path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def is_mac_byte() -> bool:
    return sys.platform == "darwin" and current_edition() == EDITION_NAME


def _state_dir(home: str | os.PathLike | None = None) -> Path:
    root = Path(home) if home else Path.home()
    path = root / ".seele" / "mac_byte"
    path.mkdir(parents=True, exist_ok=True)
    try:
        path.chmod(0o700)
    except OSError:
        pass
    return path


def _command_path(command: str) -> str | None:
    direct = shutil.which(command)
    if direct:
        return direct
    try:
        result = subprocess.run(
            ["/bin/zsh", "-lic", f"command -v {shlex.quote(command)}"],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    lines = result.stdout.strip().splitlines()
    return lines[-1] if lines else None


def botmux_is_installed() -> bool:
    return _command_path("botmux") is not None


def botmux_is_configured(home: str | os.PathLike | None = None) -> bool:
    root = Path(home) if home else Path.home()
    path = root / ".botmux" / "bots.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return False
    if isinstance(data, list):
        return any(isinstance(item, dict) for item in data)
    return isinstance(data, dict) and bool(data)


def bootstrap_mode(home: str | os.PathLike | None = None) -> str:
    if not botmux_is_installed():
        return "full"
    if not botmux_is_configured(home):
        return "setup"
    return "ready"


def _voice_path(name: str) -> Path:
    return app_path("audio", "mac_byte", VOICE_FILES[name])


def _shell_voice(name: str, fallback_text: str) -> str:
    path = shlex.quote(str(_voice_path(name)))
    message = shlex.quote(fallback_text)
    return f"""
if [ -f {path} ]; then
  /usr/bin/afplay {path} >/dev/null 2>&1 || true
else
  printf '\\n[语音占位符] %s\\n' {message}
fi
""".strip()


def _npm_prelude() -> str:
    return """
export NVM_DIR="$HOME/.nvm"
if [ -s "$NVM_DIR/nvm.sh" ]; then
  source "$NVM_DIR/nvm.sh"
fi
export PATH="$HOME/.local/bin:$HOME/.botmux/bin:$PATH"
hash -r
""".strip()


def _botmux_coach_command() -> str:
    if getattr(sys, "frozen", False):
        resources = app_path()
        command = [
            "/usr/bin/env",
            f"SEELE_RESOURCES_DIR={resources}",
            str(resources / "bin" / "SeeleBotmuxCoach"),
        ]
    else:
        command = [
            sys.executable,
            str(Path(__file__).with_name("run_exe.py")),
            "--botmux-setup-coach",
        ]
    return shlex.join(command)


def _full_install_commands() -> str:
    return f"""
{_shell_voice("install", "开始安装 Botmux 及字节内部依赖")}

export NVM_DIR="$HOME/.nvm"
if [ ! -s "$NVM_DIR/nvm.sh" ]; then
  curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
fi
source "$NVM_DIR/nvm.sh"
nvm install --lts
nvm use --lts
node -v
npm -v

curl -fsSL https://code.byted.org/api/tos-proxy/download/traex_install.sh |
  env TRAEX_INSTALL_ASSUME_YES=1 TRAEX_INSTALL_REMOVE_COCO=1 TRAEX_INSTALL_REMOVE_BREW=0 sh
npm install -g @larksuite/cli@latest --registry {BYTE_NPM_REGISTRY}
npm install -g agentbuddy@latest --registry {BYTE_NPM_REGISTRY}
npm install -g botmux@latest --registry {PUBLIC_NPM_REGISTRY}

{_npm_prelude()}
printf '\\n安装完成，开始逐项登录。\\n'

traex backend cn
if ! traex login status >/dev/null 2>&1; then
  {_shell_voice("traex_login", "请登录 Trae CLI，并查看终端中的登录链接")}
  traex login --sso-device
fi
traex login status

if ! lark-cli config show >/dev/null 2>&1; then
  {_shell_voice("lark_config", "请初始化飞书 CLI 应用，并在浏览器完成配置")}
  lark-cli config init --new --lang zh_cn --name seele
fi

if ! lark-cli auth status --json --verify >/dev/null 2>&1; then
  {_shell_voice("lark_login", "请登录飞书 CLI，并在浏览器完成权限授权")}
  lark-cli auth login --recommend
fi
lark-cli auth status --json --verify

if ! agentbuddy status --json >/dev/null 2>&1; then
  {_shell_voice("agentbuddy_login", "请登录 Skill 空间，并查看终端中的登录链接")}
  agentbuddy login --region cn --login-mode device --json --yes
fi
agentbuddy status --json

{_shell_voice("botmux_setup", "请扫描终端二维码，完成 Botmux 机器人配置")}
{_botmux_coach_command()}
""".strip()


def _setup_only_commands() -> str:
    return f"""
{_npm_prelude()}
{_shell_voice("botmux_setup", "请扫描终端二维码，完成 Botmux 机器人配置")}
{_botmux_coach_command()}
""".strip()


def _seele_plugin_commands() -> str:
    plugin_dir = app_path("botmux-skill")
    if not plugin_dir.is_dir():
        return "printf '\\n未找到 Seele Botmux 插件目录，跳过插件安装。\\n'"
    quoted = shlex.quote(str(plugin_dir))
    return f"""
botmux plugin install {quoted} --link
botmux plugin enable seele
""".strip()


def build_bootstrap_script(
    mode: str,
    *,
    script_path: Path,
    lock_path: Path,
    status_path: Path,
) -> str:
    if mode not in {"full", "setup"}:
        raise ValueError("bootstrap mode must be full or setup")
    workflow = _full_install_commands() if mode == "full" else _setup_only_commands()
    return f"""#!/bin/zsh
set -u
set -o pipefail
SCRIPT_FILE={shlex.quote(str(script_path))}
LOCK_FILE={shlex.quote(str(lock_path))}
STATUS_FILE={shlex.quote(str(status_path))}
TMP_STATUS="${{STATUS_FILE}}.tmp.$$"

finish() {{
  code=$?
  finished_at="$(date +%s)"
  if [ "$code" -eq 0 ]; then
    printf '{{"state":"completed","code":0,"updated_at":%s}}\\n' "$finished_at" > "$TMP_STATUS"
  else
    printf '{{"state":"failed","code":%s,"updated_at":%s}}\\n' "$code" "$finished_at" > "$TMP_STATUS"
  fi
  mv -f "$TMP_STATUS" "$STATUS_FILE" 2>/dev/null || true
  rm -f -- "$LOCK_FILE" "$SCRIPT_FILE" "$TMP_STATUS"
}}
trap finish EXIT

clear
printf '\\nSeele 2.0 mac_byte - Botmux 安装与登录\\n'
printf '安装命令需要字节内网。登录阶段会展示链接或二维码。\\n\\n'

set -e
{workflow}

{_npm_prelude()}
{_seele_plugin_commands()}
botmux start
botmux autostart enable
botmux status
botmux autostart status

printf '\\nBotmux 已安装、配置并启动。\\n'
"""


def _lock_is_active(lock_path: Path) -> bool:
    try:
        age = time.time() - lock_path.stat().st_mtime
    except OSError:
        return False
    if age <= LOCK_TTL_SECONDS:
        return True
    try:
        lock_path.unlink()
    except OSError:
        pass
    return False


def launch_bootstrap(
    *,
    mode: str | None = None,
    home: str | os.PathLike | None = None,
) -> Path | None:
    if not is_mac_byte():
        return None
    selected_mode = mode or bootstrap_mode(home)
    if selected_mode == "ready":
        return None
    if selected_mode not in {"full", "setup"}:
        raise ValueError("unsupported bootstrap mode")

    directory = _state_dir(home)
    lock_path = directory / "bootstrap.lock"
    status_path = directory / "bootstrap-status.json"
    if _lock_is_active(lock_path):
        return None

    script_path = directory / f"bootstrap-{uuid.uuid4().hex}.command"
    script_path.write_text(
        build_bootstrap_script(
            selected_mode,
            script_path=script_path,
            lock_path=lock_path,
            status_path=status_path,
        ),
        encoding="utf-8",
    )
    script_path.chmod(0o700)
    lock_path.write_text(str(int(time.time())), encoding="ascii")
    status_path.write_text(
        json.dumps(
            {
                "state": "running",
                "mode": selected_mode,
                "updated_at": int(time.time()),
            }
        ),
        encoding="utf-8",
    )

    try:
        result = subprocess.run(
            ["/usr/bin/open", "-a", "Terminal", str(script_path)],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        result = None
        error = str(exc)
    else:
        error = result.stderr.strip()

    if result is None or result.returncode != 0:
        try:
            script_path.unlink()
        except OSError:
            pass
        try:
            lock_path.unlink()
        except OSError:
            pass
        status_path.write_text(
            json.dumps(
                {
                    "state": "failed",
                    "code": 1 if result is None else result.returncode,
                    "message": error or "Terminal failed to open",
                    "updated_at": int(time.time()),
                }
            ),
            encoding="utf-8",
        )
        raise RuntimeError(error or "无法打开 Terminal")
    return script_path


def launch_first_run_bootstrap() -> Path | None:
    return launch_bootstrap()
