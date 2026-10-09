"""Cross-platform paths and operating-system helpers for Seele."""

from __future__ import annotations

import os
import subprocess
import sys
import webbrowser
from pathlib import Path
from typing import Iterable


def get_base_dir() -> Path:
    source_dir = Path(__file__).resolve().parent
    if not getattr(sys, "frozen", False):
        return source_dir

    executable_dir = Path(sys.executable).resolve().parent
    frozen_dir = Path(getattr(sys, "_MEIPASS", executable_dir))
    bundle_resources = executable_dir.parent / "Resources"
    if executable_dir.name == "MacOS" and executable_dir.parent.name == "Contents":
        candidates = [bundle_resources, frozen_dir, executable_dir, source_dir]
    else:
        candidates = [frozen_dir, executable_dir, bundle_resources, source_dir]
    for candidate in candidates:
        if (candidate / "state.json").is_file():
            return candidate
    return candidates[0]


def app_path(*parts: str) -> Path:
    return get_base_dir().joinpath(*parts)


def get_tools_dir() -> Path:
    configured = os.environ.get("SEELE_TOOLS_DIR", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    if sys.platform == "win32":
        drive_d = Path("D:/")
        return Path("D:/SeeleTools") if drive_d.is_dir() else Path("C:/SeeleTools")
    return Path.home() / ".seele" / "tools"


def hidden_subprocess_kwargs() -> dict:
    if sys.platform != "win32":
        return {}
    startup_info = subprocess.STARTUPINFO()
    startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup_info.wShowWindow = subprocess.SW_HIDE
    return {
        "startupinfo": startup_info,
        "creationflags": subprocess.CREATE_NO_WINDOW,
    }


def process_is_running(names: Iterable[str]) -> bool:
    needles = tuple(name.lower() for name in names if name)
    if not needles:
        return False
    try:
        if sys.platform == "win32":
            result = subprocess.run(
                ["tasklist", "/FO", "CSV", "/NH"],
                capture_output=True,
                text=True,
                errors="replace",
                timeout=8,
                **hidden_subprocess_kwargs(),
            )
            output = result.stdout.lower()
            return result.returncode == 0 and any(name in output for name in needles)

        result = subprocess.run(
            ["ps", "-ax", "-o", "command="],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=8,
        )
        output = result.stdout.lower()
        return result.returncode == 0 and any(name in output for name in needles)
    except (OSError, subprocess.SubprocessError):
        return False


def open_external(target: str) -> bool:
    try:
        if sys.platform == "win32" and hasattr(os, "startfile"):
            os.startfile(target)  # type: ignore[attr-defined]
            return True
        if sys.platform == "darwin":
            if subprocess.run(["open", target], check=False).returncode == 0:
                return True
        if sys.platform.startswith("linux"):
            if subprocess.run(["xdg-open", target], check=False).returncode == 0:
                return True
        return bool(webbrowser.open(target))
    except OSError:
        return bool(webbrowser.open(target))


def platform_label() -> str:
    if sys.platform == "win32":
        return "Windows"
    if sys.platform == "darwin":
        return "macOS"
    if sys.platform.startswith("linux"):
        return "Linux"
    return sys.platform
