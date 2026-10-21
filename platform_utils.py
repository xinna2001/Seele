"""Cross-platform paths and operating-system helpers for Seele."""

from __future__ import annotations

import os
import json
import re
import subprocess
import sys
import tempfile
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


def get_edition() -> str:
    edition = os.environ.get("SEELE_EDITION", "").strip()
    if not edition:
        try:
            edition = app_path("EDITION").read_text(encoding="utf-8").strip()
        except OSError:
            edition = "windows" if sys.platform == "win32" else "mac_byte"
    return edition if re.fullmatch(r"[a-zA-Z0-9_-]+", edition) else "default"


def atomic_json(path: Path, value: dict) -> None:
    """Replace a complete JSON document; never truncate the last good copy."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix="." + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(value, file, ensure_ascii=False, indent=2)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def get_data_dir() -> Path:
    override = os.environ.get("SEELE_DATA_DIR", "").strip()
    if override:
        root = Path(override).expanduser()
    elif sys.platform == "darwin":
        root = Path.home() / "Library/Application Support/Seele" / get_edition()
    elif sys.platform == "win32":
        root = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local")))
        root = root / "Seele" / get_edition()
    else:
        root = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share")))
        root = root / "Seele" / get_edition()
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    return root.resolve()


def data_path(name: str) -> Path:
    """Migrate each bundled legacy setting once, retaining the user's copy."""
    if Path(name).name != name:
        raise ValueError("Setting name must be a filename")
    target = get_data_dir() / name
    if target.exists():
        return target
    source = app_path(name)
    # A freshly downloaded macOS ZIP may be opened before replacing an older
    # installed app. Import that app's settings before initializing defaults.
    if sys.platform == "darwin" and getattr(sys, "frozen", False):
        for installed in (Path("/Applications/Seele.app"),
                          Path.home() / "Applications/Seele.app"):
            resources = installed / "Contents/Resources"
            try:
                if (resources / "EDITION").read_text().strip() == get_edition():
                    if (resources / name).is_file() and resources.resolve() != get_base_dir().resolve():
                        source = resources / name
                        break
            except OSError:
                pass
    try:
        value = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            return target
        # Publish a complete file without replacing a concurrent first-run copy.
        fd, temporary = tempfile.mkstemp(prefix=".migrate-", dir=target.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as file:
                json.dump(value, file, ensure_ascii=False, indent=2)
                file.flush()
                os.fsync(file.fileno())
            os.link(temporary, target)
        finally:
            os.unlink(temporary)
    except (FileExistsError, FileNotFoundError, json.JSONDecodeError):
        pass
    return target


def migrate_settings() -> None:
    for name in ("state.json", "uid.json", "file_name.json", "config.json",
                 "botmux_config.json"):
        data_path(name)


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
