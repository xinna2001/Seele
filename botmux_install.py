"""Shared, explicitly pinned Botmux installation policy for byte editions."""

from __future__ import annotations

import re
import subprocess


# Change only when the user explicitly requests another installation version.
BOTMUX_VERSION = "3.52.0"
BOTMUX_INSTALL_URL = (
    "https://raw.githubusercontent.com/deepcoldy/botmux/master/install.sh"
)
_VERSION_RE = re.compile(r"(?:botmux(?: version)?\s+)?v?(\d+\.\d+\.\d+)")


def installed_version(executable: str) -> str | None:
    try:
        result = subprocess.run(
            [executable, "--version"],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    match = _VERSION_RE.fullmatch(result.stdout.strip())
    return match.group(1) if result.returncode == 0 and match else None


def pinned_install_commands(install: str, *, after_install: str) -> str:
    """Install on any mismatch, then check the executable selected by PATH."""
    return f"""
export PATH="$HOME/.botmux/bin:$PATH"
hash -r
botmux_matches_pinned_version() {{
  command -v botmux >/dev/null 2>&1 || return 1
  botmux_detected_version="$(botmux --version 2>/dev/null)" || return 1
  case "$botmux_detected_version" in
    "{BOTMUX_VERSION}"|"v{BOTMUX_VERSION}"|"botmux {BOTMUX_VERSION}"|"botmux v{BOTMUX_VERSION}"|"botmux version {BOTMUX_VERSION}"|"botmux version v{BOTMUX_VERSION}") return 0 ;;
    *) return 1 ;;
  esac
}}
if botmux_matches_pinned_version; then
  printf '[已安装] Botmux {BOTMUX_VERSION}: %s\\n' "$(command -v botmux)"
else
  printf '[待安装] Botmux 固定版本 {BOTMUX_VERSION}\\n'
  {install}
  export PATH="$HOME/.botmux/bin:$PATH"
  hash -r
  if ! botmux_matches_pinned_version; then
    printf '\\nBotmux 安装校验失败：要求 {BOTMUX_VERSION}，当前命令未返回该版本。\\n' >&2
    exit 1
  fi
  # Stop the old supervisor before later login stages, so a resumed run cannot
  # keep an earlier binary alive after the CLI has already been replaced.
  {after_install}
fi
botmux --version
""".strip()


def official_install_commands() -> str:
    return f"""
botmux_installer="$(mktemp)"
trap 'rm -f "$botmux_installer"' EXIT
curl -fsSL {BOTMUX_INSTALL_URL} -o "$botmux_installer"
env BOTMUX_VERSION=v{BOTMUX_VERSION} sh "$botmux_installer"
rm -f "$botmux_installer"
trap - EXIT
""".strip()
