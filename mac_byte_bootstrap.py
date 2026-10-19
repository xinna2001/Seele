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
HOMEBREW_INSTALL_URL = (
    "https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh"
)
LOCK_TTL_SECONDS = 6 * 60 * 60
BOOTSTRAP_COMMANDS = (
    "node",
    "npm",
    "tmux",
    "traex",
    "lark-cli",
    "agentbuddy",
    "botmux",
)

VOICE_FILES = {
    "install": "mac_byte_install_16k.wav",
    "homebrew_password": "mac_byte_homebrew_password_16k.wav",
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


def current_version(path: str | os.PathLike | None = None) -> str:
    version_path = Path(path) if path else app_path("VERSION")
    try:
        return version_path.read_text(encoding="utf-8").strip()
    except OSError:
        return "unknown"


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


def status_path(home: str | os.PathLike | None = None) -> Path:
    return _state_dir(home) / "bootstrap-status.json"


def read_bootstrap_status(home: str | os.PathLike | None = None) -> dict:
    try:
        data = json.loads(status_path(home).read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def wait_for_bootstrap_result(
    *,
    home: str | os.PathLike | None = None,
    poll_seconds: float = 1.0,
) -> dict:
    while True:
        status = read_bootstrap_status(home)
        if status.get("state") in {"completed", "failed"}:
            return status
        time.sleep(poll_seconds)


def _applescript_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def close_terminal_window_for_script(script_path: str | os.PathLike) -> bool:
    if sys.platform != "darwin":
        return False
    title_fragment = Path(script_path).name
    script = f"""
tell application "Terminal"
  repeat with terminalWindow in windows
    if name of terminalWindow contains {_applescript_string(title_fragment)} then
      close terminalWindow
      return "closed"
    end if
  end repeat
end tell
return "not_found"
""".strip()
    try:
        result = subprocess.run(
            ["/usr/bin/osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0 and "closed" in result.stdout


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


def _traex_supports_backend(path: str) -> bool:
    try:
        result = subprocess.run(
            [path, "backend", "cn", "--help"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=8,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def missing_bootstrap_commands() -> list[str]:
    missing = []
    for command in BOOTSTRAP_COMMANDS:
        path = _command_path(command)
        if path is None or (
            command == "traex" and not _traex_supports_backend(path)
        ):
            missing.append(command)
    return missing


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


def botmux_is_running(home: str | os.PathLike | None = None) -> bool:
    botmux = _command_path("botmux")
    if not botmux:
        return False
    env = os.environ.copy()
    if home is not None:
        env["HOME"] = str(Path(home))
    try:
        result = subprocess.run(
            [botmux, "status"],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
            env=env,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    output = f"{result.stdout}\n{result.stderr}".lower()
    if "未在运行" in output or "not running" in output:
        return False
    return result.returncode == 0 and (
        "supervisor 在线" in output
        or "supervisor online" in output
        or "daemon is running" in output
    )


def bootstrap_mode(home: str | os.PathLike | None = None) -> str:
    missing = missing_bootstrap_commands()
    configured = botmux_is_configured(home)
    if missing:
        if configured and missing == ["tmux"]:
            return "repair"
        return "full"
    if not configured:
        return "setup"
    if not botmux_is_running(home):
        return "repair"
    return "ready"


def _voice_path(name: str) -> Path:
    return app_path("audio", "mac_byte", VOICE_FILES[name])


def _shell_voice(
    name: str,
    fallback_text: str,
    *,
    background: bool = False,
) -> str:
    path = shlex.quote(str(_voice_path(name)))
    message = shlex.quote(fallback_text)
    suffix = " &" if background else " || true"
    return f"""
if [ -f {path} ]; then
  /usr/bin/afplay {path} >/dev/null 2>&1{suffix}
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
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$HOME/.botmux/bin:$PATH"
if command -v brew >/dev/null 2>&1; then
  eval "$(brew shellenv)"
fi
hash -r
""".strip()


def _tmux_install_commands() -> str:
    return f"""
if command -v tmux >/dev/null 2>&1; then
  printf '[已安装] tmux: %s\\n' "$(command -v tmux)"
else
  printf '[待安装] tmux\\n'
  if ! command -v brew >/dev/null 2>&1; then
    printf '[待安装] Homebrew（tmux 的 macOS 包管理器）\\n'
    homebrew_installer="$(curl -fsSL {HOMEBREW_INSTALL_URL})" || {{
      printf '\\nHomebrew 安装脚本下载失败，请检查网络后重试。\\n' >&2
      exit 1
    }}
    ensure_login_audio
    {_homebrew_install_command()}
    unset homebrew_installer
    export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
    if [ -x /opt/homebrew/bin/brew ]; then
      eval "$(/opt/homebrew/bin/brew shellenv)"
    elif [ -x /usr/local/bin/brew ]; then
      eval "$(/usr/local/bin/brew shellenv)"
    fi
    hash -r
  fi
  if ! command -v brew >/dev/null 2>&1; then
    printf '\\nHomebrew 安装校验失败，无法继续安装 tmux。\\n' >&2
    exit 1
  fi
  HOMEBREW_NO_AUTO_UPDATE=1 brew install tmux
  hash -r
fi
tmux -V
""".strip()


def _traex_install_commands() -> str:
    return """
traex_requires_install=0
if command -v traex >/dev/null 2>&1; then
  printf '[已安装] Trae CLI: %s\\n' "$(command -v traex)"
  if ! traex backend cn --help >/dev/null 2>&1; then
    printf '[待升级] 当前 Trae CLI 不支持 backend cn，开始升级。\\n'
    traex_requires_install=1
  fi
else
  printf '[待安装] Trae CLI\\n'
  traex_requires_install=1
fi

if [ "$traex_requires_install" -eq 1 ]; then
  curl -fsSL https://code.byted.org/api/tos-proxy/download/traex_install.sh |
    env TRAEX_INSTALL_ASSUME_YES=1 TRAEX_INSTALL_REMOVE_COCO=1 TRAEX_INSTALL_REMOVE_BREW=0 sh
  hash -r
fi
unset traex_requires_install

if ! command -v traex >/dev/null 2>&1 ||
   ! traex backend cn --help >/dev/null 2>&1; then
  printf '\\nTrae CLI 安装校验失败：当前版本不支持 backend cn。\\n' >&2
  exit 1
fi
""".strip()


def _trae_cli_path_commands() -> str:
    return """
ensure_user_local_bin_path() {
  mkdir -p "$HOME/.local/bin"
  case ":$PATH:" in
    *":$HOME/.local/bin:"*) ;;
    *) export PATH="$HOME/.local/bin:$PATH" ;;
  esac
  for profile in "$HOME/.zprofile" "$HOME/.zshrc"; do
    if [ -f "$profile" ]; then
      if grep -F '$HOME/.local/bin' "$profile" >/dev/null 2>&1 ||
         grep -F "$HOME/.local/bin" "$profile" >/dev/null 2>&1; then
        continue
      fi
    fi
    if [ -e "$profile" ] && [ ! -w "$profile" ]; then
      printf '[提醒] 无法写入 %s；手动打开的终端可能需要先执行 export PATH="$HOME/.local/bin:$PATH"。\\n' "$profile" >&2
      continue
    fi
    {
      printf '\\n# Added by Seele mac_byte bootstrap: user-local CLI tools\\n'
      printf 'export PATH="$HOME/.local/bin:$PATH"\\n'
    } >> "$profile" 2>/dev/null || true
  done
}

ensure_user_local_bin_path
if command -v traex >/dev/null 2>&1; then
  cat > "$HOME/.local/bin/trae-code" <<'EOF'
#!/bin/sh
if command -v traex >/dev/null 2>&1; then
  exec traex "$@"
fi
if [ -x "$HOME/.local/bin/traex" ]; then
  exec "$HOME/.local/bin/traex" "$@"
fi
printf '%s\\n' 'traex command not found. Please reopen Terminal or add $HOME/.local/bin to PATH.' >&2
exit 127
EOF
  chmod 755 "$HOME/.local/bin/trae-code" 2>/dev/null || true
  printf '[兼容] Trae CLI 旧命令 trae-code -> traex: %s\\n' "$HOME/.local/bin/trae-code"
fi
unset -f ensure_user_local_bin_path
""".strip()


def _shell_login_attention(stage_name: str) -> str:
    return f"prepare_login_attention {shlex.quote(stage_name)}"


def _shell_login_audio() -> str:
    return "prepare_login_audio"


def _botmux_coach_helper_path() -> Path:
    return app_path("bin", "SeeleBotmuxCoach")


def _coach_helper_base_command() -> list[str]:
    if getattr(sys, "frozen", False):
        resources = app_path()
        helper = _botmux_coach_helper_path()
        return [
            "/usr/bin/env",
            f"SEELE_RESOURCES_DIR={resources}",
            str(helper),
        ]
    return [
        sys.executable,
        str(Path(__file__).with_name("run_exe.py")),
        "--botmux-setup-coach",
    ]


def _botmux_coach_command() -> str:
    return shlex.join(_coach_helper_base_command())


def _homebrew_install_command() -> str:
    command = shlex.join([
        *_coach_helper_base_command(),
        "--homebrew-install",
        "--",
        "/bin/bash",
        "-c",
    ])
    return f'{command} "$homebrew_installer"'


def _login_command(*command: str) -> str:
    return shlex.join([
        *_coach_helper_base_command(),
        "--login-command",
        "--",
        *command,
    ])


def _full_install_commands(*, run_botmux_setup: bool = True) -> str:
    botmux_setup = (
        f"""
{_shell_login_attention("Botmux 机器人配置")}
{_shell_voice("botmux_setup", "请扫描终端二维码，完成 Botmux 机器人配置")}
{_botmux_coach_command()}
""".strip()
        if run_botmux_setup
        else "printf '\\nBotmux 已有机器人配置，跳过重复 setup。\\n'"
    )
    return f"""
{_shell_voice("install", "开始安装 Botmux 及字节内部依赖")}

{_npm_prelude()}

if command -v node >/dev/null 2>&1 && command -v npm >/dev/null 2>&1; then
  printf '\\n[已安装] Node.js: %s\\n' "$(command -v node)"
  printf '[已安装] npm: %s\\n' "$(command -v npm)"
else
  printf '\\n[待安装] 未同时检测到 Node.js 和 npm，开始安装。\\n'
  export NVM_DIR="$HOME/.nvm"
  if [ ! -s "$NVM_DIR/nvm.sh" ]; then
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
  fi
  source "$NVM_DIR/nvm.sh"
  nvm install --lts
  nvm use --lts
  hash -r
fi
node -v
npm -v

{_tmux_install_commands()}

{_traex_install_commands()}
{_trae_cli_path_commands()}

if command -v lark-cli >/dev/null 2>&1; then
  printf '[已安装] Lark CLI: %s\\n' "$(command -v lark-cli)"
else
  printf '[待安装] Lark CLI\\n'
  npm install -g @larksuite/cli@latest --registry {BYTE_NPM_REGISTRY}
  hash -r
fi

if command -v agentbuddy >/dev/null 2>&1; then
  printf '[已安装] AgentBuddy: %s\\n' "$(command -v agentbuddy)"
else
  printf '[待安装] AgentBuddy\\n'
  npm install -g agentbuddy@latest --registry {BYTE_NPM_REGISTRY}
  hash -r
fi

if command -v botmux >/dev/null 2>&1; then
  printf '[已安装] Botmux: %s\\n' "$(command -v botmux)"
else
  printf '[待安装] Botmux\\n'
  npm install -g botmux@latest --registry {PUBLIC_NPM_REGISTRY}
  hash -r
fi

{_npm_prelude()}
for required_command in node npm tmux traex lark-cli agentbuddy botmux; do
  if ! command -v "$required_command" >/dev/null 2>&1; then
    printf '\\n安装校验失败：找不到命令 %s。\\n' "$required_command" >&2
    exit 1
  fi
done
printf '\\n安装完成，开始逐项登录。\\n'

traex backend cn
if ! traex login status >/dev/null 2>&1; then
  {_shell_login_audio()}
  {_shell_voice("traex_login", "请登录 Trae CLI，并查看终端中的登录链接", background=True)}
  {_login_command("traex", "login", "--sso-device")}
fi
traex login status

if ! lark-cli config show >/dev/null 2>&1; then
  {_shell_login_audio()}
  {_shell_voice("lark_config", "请初始化飞书 CLI 应用，并在浏览器完成配置", background=True)}
  lark_config_init_code=0
  {_login_command("lark-cli", "config", "init", "--new", "--lang", "zh_cn", "--name", "seele")} || lark_config_init_code=$?
  if lark-cli config show >/dev/null 2>&1; then
    printf '\\n已在本机检测到飞书 CLI 应用配置。\\n'
  else
    printf '\\n飞书网页流程已结束，但本机仍未检测到应用配置。\\n' >&2
    printf '为避免重复创建应用，本轮不会再次执行 config init。\\n' >&2
    printf '请关闭此终端并重新启动 Seele；已安装组件会被保留，只会续跑未完成阶段。\\n' >&2
    if [ "$lark_config_init_code" -eq 0 ]; then
      lark_config_init_code=1
    fi
    exit "$lark_config_init_code"
  fi
fi

if ! lark-cli auth status --json --verify >/dev/null 2>&1; then
  {_shell_login_audio()}
  {_shell_voice("lark_login", "请登录飞书 CLI，并在浏览器完成权限授权", background=True)}
  {_login_command("lark-cli", "auth", "login", "--recommend")}
fi
lark-cli auth status --json --verify

if ! agentbuddy status --json >/dev/null 2>&1; then
  {_shell_login_audio()}
  {_shell_voice("agentbuddy_login", "请登录 Skill 空间，并查看终端中的登录链接", background=True)}
  {_login_command("agentbuddy", "login", "--region", "cn", "--login-mode", "device", "--json", "--yes")}
fi
agentbuddy status --json

{botmux_setup}
""".strip()


def _setup_only_commands() -> str:
    return f"""
{_npm_prelude()}
{_shell_login_attention("Botmux 机器人配置")}
{_shell_voice("botmux_setup", "请扫描终端二维码，完成 Botmux 机器人配置")}
{_botmux_coach_command()}
""".strip()


def _runtime_repair_commands() -> str:
    return f"""
{_npm_prelude()}
printf '\\n检测到已有 Botmux 配置，开始修复运行环境。\\n'

{_tmux_install_commands()}

if ! command -v botmux >/dev/null 2>&1; then
  printf '\\n运行恢复失败：找不到 Botmux 命令。\\n' >&2
  exit 1
fi
printf '\\n保留现有机器人配置，跳过工具安装、登录和 botmux setup。\\n'
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
    botmux_configured: bool = False,
) -> str:
    if mode not in {"full", "setup", "repair"}:
        raise ValueError("bootstrap mode must be full, setup or repair")
    if mode == "full":
        workflow = _full_install_commands(
            run_botmux_setup=not botmux_configured
        )
    elif mode == "setup":
        workflow = _setup_only_commands()
    else:
        workflow = _runtime_repair_commands()
    version = current_version()
    title = (
        "Botmux 运行恢复"
        if mode == "repair"
        else "Botmux 安装与登录"
    )
    intro = (
        "将保留现有配置，只修复缺失环境并恢复 Botmux 运行。"
        if mode == "repair"
        else "安装命令需要字节内网。登录阶段会展示链接或二维码。"
    )
    completion = (
        "Botmux 运行环境已修复，并已重新启动和设置开机自启。"
        if mode == "repair"
        else "Botmux 已安装、配置并启动。"
    )
    return f"""#!/bin/zsh
set -u
set -o pipefail
SCRIPT_FILE={shlex.quote(str(script_path))}
LOCK_FILE={shlex.quote(str(lock_path))}
STATUS_FILE={shlex.quote(str(status_path))}
TMP_STATUS="${{STATUS_FILE}}.tmp.$$"
BOOTSTRAP_MODE={shlex.quote(mode)}
ORIGINAL_OUTPUT_VOLUME=""
ORIGINAL_OUTPUT_MUTED=""
LOGIN_AUDIO_SNAPSHOT_TAKEN=0
LOGIN_AUDIO_ADJUSTED=0

remember_login_audio() {{
  if [ "$LOGIN_AUDIO_SNAPSHOT_TAKEN" -eq 1 ]; then
    return
  fi
  saved_volume="$(/usr/bin/osascript -e 'output volume of (get volume settings)' 2>/dev/null || true)"
  saved_muted="$(/usr/bin/osascript -e 'output muted of (get volume settings)' 2>/dev/null || true)"
  case "$saved_volume" in
    ""|*[!0-9]*) return ;;
  esac
  case "$saved_muted" in
    true|false) ;;
    *) return ;;
  esac
  ORIGINAL_OUTPUT_VOLUME="$saved_volume"
  ORIGINAL_OUTPUT_MUTED="$saved_muted"
  LOGIN_AUDIO_SNAPSHOT_TAKEN=1
}}

ensure_login_audio() {{
  remember_login_audio
  current_volume="$(/usr/bin/osascript -e 'output volume of (get volume settings)' 2>/dev/null || true)"
  current_muted="$(/usr/bin/osascript -e 'output muted of (get volume settings)' 2>/dev/null || true)"
  case "$current_volume" in
    ""|*[!0-9]*) return ;;
  esac
  if [ "$current_muted" = "true" ] || [ "$current_volume" -lt 20 ]; then
    if /usr/bin/osascript -e 'set volume output volume 20 without output muted' >/dev/null 2>&1; then
      LOGIN_AUDIO_ADJUSTED=1
    fi
  fi
}}

restore_login_audio() {{
  if [ "$LOGIN_AUDIO_ADJUSTED" -ne 1 ] || [ "$LOGIN_AUDIO_SNAPSHOT_TAKEN" -ne 1 ]; then
    return
  fi
  if [ "$ORIGINAL_OUTPUT_MUTED" = "true" ]; then
    /usr/bin/osascript \
      -e "set volume output volume ${{ORIGINAL_OUTPUT_VOLUME}} with output muted" \
      >/dev/null 2>&1 || true
  else
    /usr/bin/osascript \
      -e "set volume output volume ${{ORIGINAL_OUTPUT_VOLUME}} without output muted" \
      >/dev/null 2>&1 || true
  fi
}}

prepare_login_attention() {{
  stage_name="$1"
  prepare_login_audio
  /usr/bin/osascript -e 'tell application "Terminal" to activate' >/dev/null 2>&1 || true
  printf '\\033[2J\\033[3J\\033[H'
  printf '\\nSeele {version} 登录引导 - %s\\n' "$stage_name"
  printf '请完成当前页面显示的扫码或授权步骤。\\n\\n'
}}

prepare_login_audio() {{
  ensure_login_audio
  printf '\\033[2J\\033[3J\\033[H'
}}

finish() {{
  code=$?
  restore_login_audio
  finished_at="$(date +%s)"
  if [ "$code" -eq 0 ]; then
    printf '{{"state":"completed","code":0,"mode":"%s","updated_at":%s}}\\n' "$BOOTSTRAP_MODE" "$finished_at" > "$TMP_STATUS"
  else
    printf '{{"state":"failed","code":%s,"mode":"%s","updated_at":%s}}\\n' "$code" "$BOOTSTRAP_MODE" "$finished_at" > "$TMP_STATUS"
  fi
  mv -f "$TMP_STATUS" "$STATUS_FILE" 2>/dev/null || true
  rm -f -- "$LOCK_FILE" "$SCRIPT_FILE" "$TMP_STATUS"
}}
trap finish EXIT

clear
printf '\\nSeele {version} mac_byte - {title}\\n'
printf '{intro}\\n\\n'

set -e
{workflow}

{_npm_prelude()}
{_seele_plugin_commands()}
botmux start
botmux autostart enable
botmux status
botmux autostart status

printf '\\n{completion}\\n'
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
    if selected_mode not in {"full", "setup", "repair"}:
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
            botmux_configured=botmux_is_configured(home),
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
