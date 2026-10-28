"""Build a Windows x64 Python/Qt portable test ZIP from macOS or Linux.

This is a source-based portable package, not a cross-compiled PyInstaller EXE.
The work directory is temporary; no local credentials or runtime configs ship.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEPENDENCIES = ["PyQt5>=5.15.9,<5.16", "qt-material>=2.14,<3",
                "sounddevice>=0.5,<1", "soundfile>=0.13,<1", "certifi>=2024.2"]
SOURCES = [
    "Seele.py", "run_exe.py", "platform_utils.py", "windows_byte_bootstrap.py",
    "windows_byte_linux.py", "mac_byte_bootstrap.py", "botmux_install.py", "botmux_setup_coach.py",
    "Tray.py", "OutVoice.py", "initialize.py", "VoiceToText.py", "StartupMode.py",
    "write_file.py", "ProgramsConfigWindow.py", "RoleSwitchWindow.py", "TaskPanelWindow.py",
    "botmux_client.py", "rpa_bridge.py", "rpa_service.py", "play_stare.py",
    "play_vioce.py", "falseIntent.py", "ProgramLog.py",
    "app_update.py", "app_update_entry.py", "UpdateUi.py",
    "audio_name_dic.json", "botmux_config.example.json", "bubble_texts.json",
    "config.json", "file_name.json", "state.json", "uid.json", "VERSION", "LICENSE",
    "README.md", "CHANGELOG.md", "DEVELOPMENT_LOG.md", "WINDOWS_BYTE_INSTALL.md",
]


def build(output: pathlib.Path) -> pathlib.Path:
    version = (ROOT / "VERSION").read_text().strip()
    output.mkdir(parents=True, exist_ok=True)
    target = output / f"Seele-{version}-vip-test-windows_byte-x64-portable.zip"
    with tempfile.TemporaryDirectory(prefix="seele-windows-vip-") as directory:
        work = pathlib.Path(directory)
        package = work / "Seele-WindowsByte"
        runtime = package / "runtime"
        runtime.mkdir(parents=True)
        archive = work / "python.zip"
        python_url = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip"
        urllib.request.urlretrieve(python_url, archive)
        with zipfile.ZipFile(archive) as file:
            file.extractall(runtime)
        (runtime / "python311._pth").write_text(
            "python311.zip\n.\n..\n../site-packages\nimport site\n", encoding="ascii",
        )
        wheels = work / "wheels"
        subprocess.run([
            sys.executable, "-m", "pip", "download", "--only-binary=:all:",
            "--platform", "win_amd64", "--python-version", "311",
            "--implementation", "cp", "--abi", "cp311",
            "--dest", str(wheels), *DEPENDENCIES,
        ], check=True)
        site = package / "site-packages"
        site.mkdir()
        for wheel in wheels.glob("*.whl"):
            with zipfile.ZipFile(wheel) as file:
                for item in file.infolist():
                    parts = pathlib.PurePosixPath(item.filename).parts
                    if not parts or ".." in parts:
                        raise ValueError("Invalid wheel path")
                    if parts[0].endswith(".data"):
                        if len(parts) < 3 or parts[1] not in ("purelib", "platlib"):
                            continue
                        relative = pathlib.Path(*parts[2:])
                    else:
                        relative = pathlib.Path(*parts)
                    destination = site / relative
                    if item.is_dir():
                        destination.mkdir(parents=True, exist_ok=True)
                    else:
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        destination.write_bytes(file.read(item))
        for name in SOURCES:
            shutil.copy2(ROOT / name, package / name)
        for name in ("audio", "image", "botmux-skill"):
            shutil.copytree(ROOT / name, package / name,
                            ignore=shutil.ignore_patterns("__pycache__", ".DS_Store", "config.json"))
        (package / "EDITION").write_text("windows_byte\n", encoding="ascii")
        # WSH launches pythonw without a terminal; the bootstrap opens its own console.
        (package / "启动希儿.vbs").write_text(
            'Set fso = CreateObject("Scripting.FileSystemObject")\r\n'
            'Set shell = CreateObject("WScript.Shell")\r\n'
            'root = fso.GetParentFolderName(WScript.ScriptFullName)\r\n'
            'shell.CurrentDirectory = root\r\n'
            'shell.Run Chr(34) & root & "\\runtime\\pythonw.exe" & Chr(34) & " " & '
            'Chr(34) & root & "\\run_exe.py" & Chr(34), 0, False\r\n',
            encoding="utf-16",
        )
        (package / "查看启动问题.cmd").write_text(
            '@echo off\r\nchcp 65001 >nul\r\ncd /d "%~dp0"\r\n'
            '"%~dp0runtime\\python.exe" "%~dp0run_exe.py"\r\npause\r\n',
            encoding="utf-8",
        )
        (package / "先读我.txt").write_text(
            "完整解压后双击「启动希儿.vbs」。Windows 主机无需另装 Python。\n"
            "请解压到固定目录，安装与重启续装完成前不要移动。\n"
            "设置保存在 %LOCALAPPDATA%\\Seele\\windows_byte，更新会保留。\n"
            "启动及每小时检查 GitHub 新版；右键最后一项「检查更新」出现红点时点击更新。\n"
            "首次启用 WSL 若要求重启，进度已保存，登录后会自动继续。\n"
            "若双击无窗口，双击「查看启动问题.cmd」。\n"
            "这是内置 Windows Python 与 Qt 的源码便携测试包，不是已验收的 EXE 安装包。\n"
            "本机已做模拟测试与包结构校验；真实 Windows 授权、WSL 重启需验收。\n"
            "详细流程与运维见 WINDOWS_BYTE_INSTALL.md。\n", encoding="utf-8",
        )
        manifest = {
            "product": "Seele", "version": version, "edition": "windows_byte",
            "platform": "windows-x64", "format": "embedded-python-portable",
            "python": "3.11.9", "python_source": python_url,
            "wheels": sorted(wheel.name for wheel in wheels.glob("*.whl")),
            "windows_executed": False, "released": False,
        }
        (package / "test-package-manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8",
        )
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as file:
            for source in sorted(package.rglob("*")):
                if source.is_file():
                    file.write(source, source.relative_to(work))
        with zipfile.ZipFile(target) as file:
            if file.testzip() is not None:
                raise RuntimeError("ZIP validation failed")
            for required in ("runtime/python.exe", "runtime/pythonw.exe", "site-packages/PyQt5/Qt5/bin/Qt5Core.dll",
                             "botmux-skill/dist/mcp/server.js", "windows_byte_linux.py", "botmux_install.py", "EDITION"):
                if "Seele-WindowsByte/" + required not in file.namelist():
                    raise RuntimeError(f"Missing package resource: {required}")
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        target.with_suffix(".zip.sha256").write_text(f"{digest}  {target.name}\n", encoding="ascii")
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=pathlib.Path, default=ROOT / "vip-packages")
    print(build(parser.parse_args().output))
