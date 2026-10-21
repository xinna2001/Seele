"""GitHub release updates and an independent, rollback-capable installer.

No Qt dependency: the copied helper must remain runnable after the old app exits.
"""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import platform
import re
import shutil
import ssl
import stat
import subprocess
import sys
import tempfile
import time
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import URLError

from platform_utils import (
    app_path, atomic_json, get_data_dir, get_edition, hidden_subprocess_kwargs,
    migrate_settings,
)

REPO = "xinna2001/Seele"
LATEST_URL = f"https://api.github.com/repos/{REPO}/releases/latest"
MAX_ARCHIVE = 1024 * 1024 * 1024
MAX_EXPANDED = 3 * MAX_ARCHIVE


class UpdateError(RuntimeError):
    pass


def version_tuple(version: str) -> tuple[int, int, int]:
    match = re.fullmatch(r"v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", version)
    if not match:
        raise UpdateError("版本号无效")
    return tuple(map(int, match.groups()))


def current_version() -> str:
    return app_path("VERSION").read_text(encoding="utf-8-sig").strip()


def update_platform() -> str:
    if sys.platform == "darwin" and platform.machine().lower() in ("arm64", "aarch64"):
        return "macos-arm64"
    if sys.platform == "win32" and platform.machine().lower() in ("amd64", "x86_64"):
        return "windows-x64"
    raise UpdateError("当前平台暂未提供自动更新包")


def trusted_asset_url(url: str) -> bool:
    parsed = urlparse(url)
    return (parsed.scheme == "https" and parsed.hostname == "github.com"
            and parsed.port in (None, 443) and not parsed.username
            and not parsed.password
            and parsed.path.startswith(f"/{REPO}/releases/download/"))


def fetch(url: str, *, limit: int = 2 * 1024 * 1024,
          destination: Path | None = None, progress=None, deadline: int = 120) -> bytes:
    """Bound both individual socket stalls and total transfer time."""
    request = Request(url, headers={"User-Agent": "Seele-Updater", "Accept": "application/json"})
    started = time.monotonic()
    content = bytearray()
    file = destination.open("wb") if destination else None
    try:
        # Frozen macOS cannot rely on this build host's Homebrew CA path.
        try:
            import certifi
            context = ssl.create_default_context(cafile=certifi.where())
        except ImportError:
            context = ssl.create_default_context()
        with urlopen(request, timeout=20, context=context) as response:
            expected = int(response.headers.get("Content-Length", "0"))
            if expected > limit:
                raise UpdateError("下载文件过大")
            total = 0
            while True:
                if time.monotonic() - started > deadline:
                    raise UpdateError("下载超时，请稍后重试")
                chunk = response.read(256 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > limit:
                    raise UpdateError("下载文件过大")
                if file:
                    file.write(chunk)
                else:
                    content.extend(chunk)
                if progress and expected:
                    progress(min(99, total * 100 // expected))
            if expected and total != expected:
                raise UpdateError("下载不完整")
    finally:
        if file:
            file.close()
    return bytes(content)


@dataclass(frozen=True)
class Release:
    version: str
    edition: str
    platform: str
    archive_name: str
    archive_url: str
    manifest_url: str
    checksums_url: str


def check_release(current: str | None = None, edition: str | None = None,
                  target_platform: str | None = None) -> Release | None:
    current = current or current_version()
    edition = edition or get_edition()
    target_platform = target_platform or update_platform()
    if (target_platform, edition) not in {
        ("macos-arm64", "mac_byte"), ("windows-x64", "windows"),
        ("windows-x64", "windows_byte"),
    }:
        raise UpdateError("当前版本类型暂未提供更新包")
    try:
        payload = json.loads(fetch(LATEST_URL))
    except (URLError, TimeoutError):
        # Public API anonymous limits are shared by NAT users. The official
        # latest/download endpoint does not require API tokens or login.
        url = f"https://github.com/{REPO}/releases/latest/download/release-manifest-{edition}.json"
        manifest = json.loads(fetch(url).decode("utf-8-sig"))
        version = str(manifest.get("version", ""))
        version_tuple(version)
        if any(manifest.get(key) != value for key, value in
               (("product", "Seele"), ("edition", edition), ("platform", target_platform))):
            raise UpdateError("官方版本清单与当前平台不一致")
        suffix = "macos-arm64.zip" if target_platform == "macos-arm64" else "x64-portable.zip"
        names = (f"Seele-{version}-{edition}-{suffix}",
                 f"release-manifest-{edition}.json", f"SHA256SUMS-{edition}.txt")
        payload = {"tag_name": "v" + version, "assets": [
            {"name": name, "browser_download_url":
             f"https://github.com/{REPO}/releases/download/v{version}/{name}"}
            for name in names]}
    if payload.get("draft") or payload.get("prerelease"):
        return None
    version = str(payload.get("tag_name", "")).removeprefix("v")
    if version_tuple(version) <= version_tuple(current):
        return None
    suffix = "macos-arm64.zip" if target_platform == "macos-arm64" else "x64-portable.zip"
    name = f"Seele-{version}-{edition}-{suffix}"
    assets = {asset["name"]: asset["browser_download_url"]
              for asset in payload.get("assets", [])}
    names = (name, f"release-manifest-{edition}.json", f"SHA256SUMS-{edition}.txt")
    if any(key not in assets for key in names):
        raise UpdateError("新版安装包尚未准备完成，请稍后重试")
    urls = [assets[key] for key in names]
    if not all(trusted_asset_url(url) for url in urls):
        raise UpdateError("更新包来源校验失败")
    return Release(version, edition, target_platform, name, *urls)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_digest(path: Path, sums: str, name: str) -> None:
    found = []
    for line in sums.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1].lstrip("*") == name:
            found.append(parts[0].lower())
    if len(found) != 1 or not re.fullmatch("[0-9a-f]{64}", found[0]):
        raise UpdateError("缺少有效的 SHA256 校验值")
    if sha256(path) != found[0]:
        raise UpdateError("安装包完整性校验失败")


def safe_extract(archive: Path, output: Path, target_platform: str) -> Path:
    """Validate all paths before writing, including macOS framework symlinks."""
    windows = target_platform.startswith("windows")
    with zipfile.ZipFile(archive) as file:
        entries = []
        seen = set()
        links = set()
        expanded = 0
        roots = set()
        if len(file.infolist()) > 50000:
            raise UpdateError("安装包文件数量异常")
        for item in file.infolist():
            raw = item.filename
            # Apple's ditto stores UTF-8 filenames without always setting ZIP
            # bit 11. zipfile otherwise decodes them as CP437, breaking seals.
            if target_platform == "macos-arm64" and not item.flag_bits & 0x800:
                try:
                    raw = raw.encode("cp437").decode("utf-8")
                except (UnicodeEncodeError, UnicodeDecodeError):
                    pass
            path = PurePosixPath(raw)
            if (not raw or "\\" in raw or "\x00" in raw or path.is_absolute()
                    or ".." in path.parts or ":" in raw):
                raise UpdateError("安装包包含不安全路径")
            if path.parts[0] == "__MACOSX":
                continue
            if windows and any(part.endswith((" ", ".")) or
                               part.split(".")[0].upper() in
                               {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)),
                                *(f"LPT{i}" for i in range(1, 10))}
                               for part in path.parts):
                raise UpdateError("安装包包含无效 Windows 路径")
            key = str(path).casefold() if windows else str(path)
            if key in seen:
                raise UpdateError("安装包包含重复路径")
            seen.add(key)
            roots.add(path.parts[0])
            expanded += item.file_size
            if expanded > MAX_EXPANDED or item.flag_bits & 1:
                raise UpdateError("安装包大小或加密格式异常")
            mode = item.external_attr >> 16
            kind = stat.S_IFMT(mode)
            if kind not in (0, stat.S_IFREG, stat.S_IFDIR, stat.S_IFLNK):
                raise UpdateError("安装包包含特殊文件")
            if stat.S_ISLNK(mode):
                if windows or item.file_size > 4096:
                    raise UpdateError("安装包包含无效链接")
                links.add(path)
            entries.append((item, path, mode))
        if len(roots) != 1:
            raise UpdateError("安装包目录结构异常")
        root = output / next(iter(roots))
        for item, path, mode in entries:
            if any(parent in links for parent in path.parents):
                raise UpdateError("安装包试图写入链接目录")
            if path in links:
                link = file.read(item).decode("utf-8")
                if "\\" in link or "\x00" in link or PurePosixPath(link).is_absolute():
                    raise UpdateError("安装包链接目标无效")
                resolved = (output / Path(str(path)).parent / link).resolve()
                if not resolved.is_relative_to(root.resolve()):
                    raise UpdateError("安装包链接超出应用目录")
        output.mkdir(mode=0o700, parents=True, exist_ok=False)
        # Materialize links last so subsequent writes cannot traverse a symlink.
        for item, path, mode in entries:
            destination = output / Path(str(path))
            destination.parent.mkdir(parents=True, exist_ok=True)
            if item.is_dir():
                destination.mkdir(exist_ok=True)
            elif path not in links:
                with file.open(item) as source, destination.open("wb") as target:
                    shutil.copyfileobj(source, target)
                destination.chmod((mode & 0o777) or 0o644)
        for item, path, mode in entries:
            if path in links:
                os.symlink(file.read(item).decode("utf-8"), output / Path(str(path)))
    return root


def executable_in(root: Path, target_platform: str) -> Path:
    return root / ("Contents/MacOS/Seele" if target_platform == "macos-arm64" else "Seele.exe")


def resources_in(root: Path, target_platform: str) -> Path:
    return root / "Contents/Resources" if target_platform == "macos-arm64" else root


def clean_child_env() -> dict:
    env = {key: value for key, value in os.environ.items()
           if not key.startswith("_PYI_") and key not in ("_MEIPASS2", "SEELE_READY_FILE",
                                                          "SEELE_UPDATE_HEALTH")}
    env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    return env


def validate_package(root: Path, release: Release, *, smoke: bool = True) -> None:
    resources = resources_in(root, release.platform)
    exe = executable_in(root, release.platform)
    if not exe.is_file():
        raise UpdateError("安装包缺少主程序")
    for name, expected in (("VERSION", release.version), ("EDITION", release.edition)):
        if (resources / name).read_text(encoding="utf-8-sig").strip() != expected:
            raise UpdateError("安装包版本或类型与发布信息不一致")
    for name in ("state.json", "image/bss.gif", "image/bs_icon.png"):
        if not (resources / name).is_file():
            raise UpdateError("安装包缺少桌宠资源")
    if not smoke:
        return
    if release.platform == "macos-arm64":
        subprocess.run(["codesign", "--verify", "--deep", "--strict", str(root)],
                       check=True, capture_output=True, timeout=90)
    with tempfile.TemporaryDirectory(prefix="seele-update-smoke-") as directory:
        env = {**clean_child_env(), "QT_QPA_PLATFORM": "offscreen",
               "SEELE_DATA_DIR": directory, "SEELE_DISABLE_UPDATES": "1"}
        for argument in ("--smoke-test", "--updater-smoke-test"):
            result = subprocess.run([str(exe), argument], env=env, cwd=root.parent,
                                    capture_output=True, timeout=90, **hidden_subprocess_kwargs())
            if result.returncode:
                raise UpdateError("新版启动自检失败，已保留当前版本")


def stage_release(release: Release, progress=None) -> tuple[Path, Path]:
    """Downloads/staging only; never changes the running application."""
    if version_tuple(release.version) <= version_tuple(current_version()):
        raise UpdateError("禁止安装旧版或当前版本")
    work = Path(tempfile.mkdtemp(prefix="job-", dir=updates_dir()))
    try:
        sums = fetch(release.checksums_url).decode("utf-8-sig")
        manifest_bytes = fetch(release.manifest_url)
        manifest_file = work / f"release-manifest-{release.edition}.json"
        manifest_file.write_bytes(manifest_bytes)
        verify_digest(manifest_file, sums, manifest_file.name)
        manifest = json.loads(manifest_bytes.decode("utf-8-sig"))
        if any(manifest.get(key) != value for key, value in
               (("product", "Seele"), ("version", release.version),
                ("edition", release.edition), ("platform", release.platform))):
            raise UpdateError("发布清单与当前平台不一致")
        if not re.fullmatch("[0-9a-f]{40}", str(manifest.get("commit", ""))):
            raise UpdateError("发布清单缺少提交标识")
        archive = work / release.archive_name
        fetch(release.archive_url, limit=MAX_ARCHIVE, destination=archive,
              progress=progress, deadline=1200)
        verify_digest(archive, sums, release.archive_name)
        root = safe_extract(archive, work / "extracted", release.platform)
        validate_package(root, release)
        archive.unlink()
        return work, root
    except Exception:
        shutil.rmtree(work, ignore_errors=True)
        raise


def updates_dir() -> Path:
    directory = get_data_dir() / "updates"
    directory.mkdir(mode=0o700, exist_ok=True)
    return directory


def install_root() -> Path | None:
    exe = Path(sys.executable).resolve()
    if getattr(sys, "frozen", False):
        if sys.platform == "darwin" and exe.parent.name == "MacOS":
            return exe.parents[2]
        if sys.platform == "win32":
            return exe.parent
    # The Windows VIP contains an embedded Python, and can move to official EXE.
    if sys.platform == "win32" and exe.parent.name == "runtime":
        root = exe.parent.parent
        if (root / "run_exe.py").is_file() and (root / "EDITION").is_file():
            return root
    return None


def helper_path() -> Path:
    name = "SeeleUpdater.exe" if sys.platform == "win32" else "SeeleUpdater"
    return app_path("bin", name)


def old_launch_command(root: Path) -> list[str]:
    if (root / "runtime/pythonw.exe").is_file():
        return [str(root / "runtime/pythonw.exe"), str(root / "run_exe.py")]
    return [str(executable_in(root, update_platform()))]


def start_helper(work: Path, staged: Path, release: Release, *,
                 target: Path | None = None, operation: str = "update") -> Path:
    target = target or install_root()
    if target is None:
        raise UpdateError("源码运行仅支持检查更新，请使用安装包")
    if target.is_symlink() or not os.access(target.parent, os.W_OK):
        raise UpdateError("应用目录不可写，请将 Seele 安装到当前用户可写的目录")
    migrate_settings()
    binary = helper_path()
    if binary.is_file():
        copied = work / binary.name
        shutil.copy2(binary, copied)
        copied.chmod(0o755)
        command = [str(copied)]
    elif sys.platform == "win32" and not getattr(sys, "frozen", False):
        # Copy the independent runtime: the installed Python may be replaced.
        runtime = work / "runtime"
        shutil.copytree(Path(sys.executable).parent, runtime)
        for name in ("app_update.py", "platform_utils.py", "app_update_entry.py"):
            shutil.copy2(app_path(name), work / name)
        (runtime / "python311._pth").write_text("python311.zip\n.\n..\n", encoding="ascii")
        command = [str(runtime / "python.exe"), str(work / "app_update_entry.py")]
    else:
        raise UpdateError("安装包缺少独立更新程序")
    job = {
        "target": str(target), "staged": str(staged), "parent_pid": os.getpid(),
        "version": release.version, "platform": release.platform,
        "edition": release.edition, "operation": operation,
        "data_dir": str(get_data_dir()), "nonce": uuid.uuid4().hex,
        "old_command": old_launch_command(install_root() or target),
    }
    atomic_json(work / "job.json", job)
    subprocess.Popen([*command, "--apply", str(work / "job.json")], cwd=work,
                     env=clean_child_env(), stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True,
                     **hidden_subprocess_kwargs())
    ready = work / "ready.json"
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        if ready.is_file():
            payload = json.loads(ready.read_text(encoding="utf-8"))
            if payload.get("ok"):
                atomic_json(work / "activate.json", {"nonce": job["nonce"]})
                return work
            raise UpdateError(str(payload.get("error", "更新程序准备失败")))
        time.sleep(0.1)
    raise UpdateError("更新程序准备超时，当前版本保持运行")


def pid_alive(pid: int) -> bool:
    if sys.platform == "win32":
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.restype = ctypes.c_void_p
        handle = kernel.OpenProcess(0x1000, False, pid)
        if not handle:
            return False
        try:
            code = ctypes.c_ulong()
            return bool(kernel.GetExitCodeProcess(ctypes.c_void_p(handle), ctypes.byref(code))
                        and code.value == 259)
        finally:
            kernel.CloseHandle(ctypes.c_void_p(handle))
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def replace_with_retry(source: Path, target: Path) -> None:
    deadline = time.monotonic() + 30
    while True:
        try:
            os.replace(source, target)
            return
        except PermissionError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(0.25)


def apply_transaction(job: dict, work: Path, *, wait_parent_seconds=120,
                      health_seconds=75, launcher=None) -> bool:
    """Prepare before quit, atomically replace, restart, or restore the backup."""
    target = Path(job["target"])
    staged = Path(job["staged"])
    nonce = job["nonce"]
    prepared = target.with_name(f".{target.name}-new-{nonce}")
    backup = target.with_name(f".{target.name}-old-{nonce}")
    health = work / "health.json"
    status = Path(job["data_dir"]) / "update-status.json"
    launch = launcher or (lambda command, env: subprocess.Popen(
        command, env=env, cwd=target.parent, **hidden_subprocess_kwargs()))
    moved_old = False
    installed = False
    success = False
    child = None
    lock = None
    try:
        lock_path = target.parent / f".{target.name}.update.lock"
        fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
        lock = os.fdopen(fd, "r+b")
        if sys.platform == "win32":
            import msvcrt
            if lock_path.stat().st_size == 0:
                lock.write(b"0")
                lock.flush()
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        if prepared.exists() or backup.exists():
            raise UpdateError("更新目录冲突")
        shutil.copytree(staged, prepared, symlinks=True)
        if job.get("operation") == "update":
            # Retain Inno Setup's uninstall entry and registry integration.
            for file in target.glob("unins000*"):
                if file.is_file() and not file.is_symlink():
                    shutil.copy2(file, prepared / file.name)
            if job["platform"] == "windows-x64" and (target / "启动希儿.vbs").is_file():
                # Keep the VIP's familiar launcher when moving to official EXE.
                (prepared / "启动希儿.vbs").write_text(
                    'Set fso = CreateObject("Scripting.FileSystemObject")\r\n'
                    'Set shell = CreateObject("WScript.Shell")\r\n'
                    'root = fso.GetParentFolderName(WScript.ScriptFullName)\r\n'
                    'shell.Run Chr(34) & root & "\\Seele.exe" & Chr(34), 0, False\r\n',
                    encoding="utf-16")
        atomic_json(work / "ready.json", {"ok": True})
        deadline = time.monotonic() + wait_parent_seconds
        while pid_alive(job["parent_pid"]) or not (work / "activate.json").is_file():
            if time.monotonic() >= deadline:
                raise UpdateError("旧程序未退出，更新已取消")
            time.sleep(0.1)
        if json.loads((work / "activate.json").read_text()).get("nonce") != nonce:
            raise UpdateError("更新授权状态无效")
        if target.exists():
            replace_with_retry(target, backup)
            moved_old = True
        replace_with_retry(prepared, target)
        installed = True
        command = [str(executable_in(target, job["platform"])),
                   "--update-health", str(health), nonce]
        env = {**clean_child_env(), "SEELE_DATA_DIR": job["data_dir"]}
        child = launch(command, env)
        deadline = time.monotonic() + health_seconds
        while time.monotonic() < deadline:
            if health.exists():
                result = json.loads(health.read_text(encoding="utf-8"))
                if (result.get("nonce") == nonce and result.get("version") == job["version"]
                        and result.get("pid") == child.pid and child.poll() is None):
                    success = True
                    atomic_json(status, {"ok": True, "version": job["version"]})
                    break
            if child.poll() is not None:
                break
            time.sleep(0.1)
        if not success:
            raise UpdateError("新版启动失败，已恢复原版本")
    except Exception as exc:
        if child and child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=15)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=15)
        if installed and target.exists():
            shutil.rmtree(target)
        if moved_old and backup.exists():
            replace_with_retry(backup, target)
        atomic_json(status, {"ok": False, "error": str(exc)})
        if not (work / "ready.json").exists():
            atomic_json(work / "ready.json", {"ok": False, "error": str(exc)})
        elif installed or moved_old:
            try:
                launch(job["old_command"], clean_child_env())
            except OSError:
                pass
    finally:
        if prepared.exists():
            shutil.rmtree(prepared, ignore_errors=True)
        if success and backup.exists():
            shutil.rmtree(backup, ignore_errors=True)
        if lock:
            lock.close()
    return success


def write_health(path: str, nonce: str) -> None:
    atomic_json(Path(path), {"pid": os.getpid(), "version": current_version(), "nonce": nonce})


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--apply", type=Path)
    args = parser.parse_args(argv)
    if args.self_check:
        return 0
    if not args.apply:
        return 2
    work = args.apply.resolve().parent
    job = json.loads(args.apply.read_text(encoding="utf-8"))
    result = apply_transaction(job, work)
    # Windows locks the helper/runtime until process exit. The next startup
    # removes completed work directories once that process is gone.
    atomic_json(work / "completed.json", {"helper_pid": os.getpid()})
    return 0 if result else 1


def cleanup_completed() -> None:
    for work in updates_dir().glob("job-*"):
        marker = work / "completed.json"
        try:
            if marker.is_file() and not pid_alive(json.loads(marker.read_text())["helper_pid"]):
                shutil.rmtree(work)
        except (OSError, ValueError, KeyError):
            pass


if __name__ == "__main__":
    raise SystemExit(main())
