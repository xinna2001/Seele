"""Local Apple Silicon test package; never commits or publishes."""

from __future__ import annotations

import hashlib
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
RESOURCES = [
    "audio", "image", "botmux-skill", "audio_name_dic.json",
    "botmux_config.example.json", "bubble_texts.json", "config.json",
    "file_name.json", "state.json", "uid.json", "README.md", "CHANGELOG.md",
    "DEVELOPMENT_LOG.md", "MAC_BYTE_AUTO_INSTALL_COMMANDS.md",
    "MAC_BYTE_ZERO_TOUCH_RESEARCH.md", "WINDOWS_BYTE_INSTALL.md",
    "EDITION", "VERSION", "LICENSE",
]


def run(*command: str, **kwargs):
    subprocess.run(list(command), check=True, cwd=ROOT, **kwargs)


def main():
    version = (ROOT / "VERSION").read_text().strip()
    target = ROOT / "vip-packages" / f"Seele-{version}-vip-test-mac_byte-macos-arm64.zip"
    with tempfile.TemporaryDirectory(prefix="seele-mac-vip-") as directory:
        work = pathlib.Path(directory)
        helper = work / "helper"
        run(sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile",
            "--console", "--name", "SeeleBotmuxCoach", "--distpath", str(helper),
            "--workpath", str(work / "coach-work"), "--specpath", str(work),
            "botmux_setup_coach_entry.py")
        run(sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile",
            "--console", "--name", "SeeleUpdater", "--distpath", str(helper),
            "--workpath", str(work / "updater-work"), "--specpath", str(work),
            "app_update_entry.py")
        command = [
            sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--windowed",
            "--name", "Seele", "--icon", str(ROOT / "build/Seele.icns"),
            "--osx-bundle-identifier", "com.xinna2001.seele.mac-byte",
            "--contents-directory", ".", "--collect-all", "qt_material",
            "--distpath", str(work / "dist"), "--workpath", str(work / "app-work"),
            "--specpath", str(work),
        ]
        for name in RESOURCES:
            source = ROOT / name
            if name in ("EDITION", "VERSION"):
                source = work / name
                source.write_text("mac_byte\n" if name == "EDITION" else version + "\n")
            command += ["--add-data", f"{source}:{name if (ROOT / name).is_dir() else '.'}"]
        run(*command, "run_exe.py")
        app = work / "dist/Seele.app"
        resources = app / "Contents/Resources"
        (resources / "bin").mkdir(parents=True, exist_ok=True)
        shutil.copy2(helper / "SeeleBotmuxCoach", resources / "bin/SeeleBotmuxCoach")
        (resources / "bin/SeeleBotmuxCoach").chmod(0o755)
        shutil.copy2(helper / "SeeleUpdater", resources / "bin/SeeleUpdater")
        (resources / "bin/SeeleUpdater").chmod(0o755)
        for key in ("CFBundleShortVersionString", "CFBundleVersion"):
            import plistlib
            plist = app / "Contents/Info.plist"
            info = plistlib.loads(plist.read_bytes())
            info[key] = version
            plist.write_bytes(plistlib.dumps(info))
        run("codesign", "--force", "--deep", "--sign", "-", str(app))
        run("codesign", "--verify", "--deep", "--strict", str(app))
        import os
        run(str(app / "Contents/MacOS/Seele"), "--smoke-test",
            env={**os.environ, "QT_QPA_PLATFORM": "offscreen"})
        run(str(app / "Contents/MacOS/Seele"), "--botmux-coach-smoke-test")
        run(str(app / "Contents/MacOS/Seele"), "--updater-smoke-test")
        target.parent.mkdir(parents=True, exist_ok=True)
        run("ditto", "-c", "-k", "--sequesterRsrc", "--keepParent", str(app), str(target))
        run("unzip", "-tq", str(target))
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        target.with_suffix(".zip.sha256").write_text(f"{digest}  {target.name}\n")
    print(target)


if __name__ == "__main__":
    main()
