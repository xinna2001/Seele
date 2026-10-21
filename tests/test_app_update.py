import io
import importlib.util
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import app_update as update
import platform_utils as paths


class SettingsTests(unittest.TestCase):
    def test_migration_survives_replaced_bundle_and_atomic_save(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = root / "bundle"
            bundle.mkdir()
            (bundle / "state.json").write_text('{"character":"furina","initialize":"1"}')
            with patch.dict(os.environ, {"SEELE_DATA_DIR": str(root / "user")}), \
                 patch.object(paths, "get_base_dir", return_value=bundle):
                migrated = paths.data_path("state.json")
                self.assertEqual(json.loads(migrated.read_text())["character"], "furina")
                (bundle / "state.json").write_text('{"character":"xier"}')
                self.assertEqual(paths.data_path("state.json"), migrated)
                self.assertEqual(json.loads(migrated.read_text())["character"], "furina")
                paths.atomic_json(migrated, {"character": "aili"})
                self.assertEqual(json.loads(migrated.read_text())["character"], "aili")
                if sys.platform != "win32":
                    self.assertEqual(stat.S_IMODE(migrated.stat().st_mode), 0o600)

    def test_platform_directories_and_edition_isolation(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(paths.Path, "home", return_value=Path(directory)), \
             patch.dict(os.environ, {"SEELE_EDITION": "mac_byte"}, clear=True), \
             patch.object(paths.sys, "platform", "darwin"):
            self.assertEqual(paths.get_data_dir(), (Path(directory) /
                             "Library/Application Support/Seele/mac_byte").resolve())
            with patch.dict(os.environ, {"SEELE_EDITION": "mac"}):
                self.assertNotEqual(paths.get_data_dir().name, "mac_byte")


class ReleaseTests(unittest.TestCase):
    def payload(self, edition="mac_byte", platform="macos-arm64", version="2.6.0"):
        suffix = "macos-arm64.zip" if platform == "macos-arm64" else "x64-portable.zip"
        names = [f"Seele-{version}-{edition}-{suffix}",
                 f"release-manifest-{edition}.json", f"SHA256SUMS-{edition}.txt"]
        return {"tag_name": "v" + version, "assets": [
            {"name": name, "browser_download_url":
             f"https://github.com/xinna2001/Seele/releases/download/v{version}/{name}"}
            for name in names]}

    def test_only_newer_stable_exact_platform_and_edition(self):
        for edition, platform in (("mac_byte", "macos-arm64"),
                                  ("windows", "windows-x64"), ("windows_byte", "windows-x64")):
            with patch.object(update, "fetch", return_value=json.dumps(
                    self.payload(edition, platform)).encode()):
                release = update.check_release("2.5.0", edition, platform)
                self.assertEqual(release.edition, edition)
                self.assertEqual(release.platform, platform)
                self.assertIsNone(update.check_release("2.6.0", edition, platform))
                self.assertIsNone(update.check_release("2.7.0", edition, platform))
        for key in ("draft", "prerelease"):
            payload = self.payload()
            payload[key] = True
            with patch.object(update, "fetch", return_value=json.dumps(payload).encode()):
                self.assertIsNone(update.check_release("2.5.0", "mac_byte", "macos-arm64"))

    def test_missing_asset_or_untrusted_source_rejected(self):
        payload = self.payload()
        payload["assets"][0]["browser_download_url"] = "https://evil.invalid/update.zip"
        with patch.object(update, "fetch", return_value=json.dumps(payload).encode()):
            with self.assertRaises(update.UpdateError):
                update.check_release("2.5.0", "mac_byte", "macos-arm64")
        payload = self.payload()
        payload["assets"].pop()
        with patch.object(update, "fetch", return_value=json.dumps(payload).encode()):
            with self.assertRaises(update.UpdateError):
                update.check_release("2.5.0", "mac_byte", "macos-arm64")

    def test_anonymous_rate_limit_uses_official_latest_manifest(self):
        from urllib.error import HTTPError
        manifest = {"product": "Seele", "version": "2.6.0", "edition": "mac_byte",
                    "platform": "macos-arm64"}
        with patch.object(update, "fetch", side_effect=[
                HTTPError(update.LATEST_URL, 403, "rate limit", {}, None),
                json.dumps(manifest).encode()]) as fetch:
            release = update.check_release("2.5.0", "mac_byte", "macos-arm64")
            self.assertEqual(release.version, "2.6.0")
            self.assertIn("/releases/latest/download/", fetch.call_args[0][0])
            self.assertIn("/releases/download/v2.6.0/", release.archive_url)

    def test_digest_corruption_duplicate_and_missing_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "app.zip"
            archive.write_bytes(b"good")
            line = f"{update.sha256(archive)}  app.zip\n"
            update.verify_digest(archive, line, "app.zip")
            for sums in ("", line + line, "f" * 64 + "  app.zip"):
                with self.assertRaises(update.UpdateError):
                    update.verify_digest(archive, sums, "app.zip")
            archive.write_bytes(b"broken")
            with self.assertRaises(update.UpdateError):
                update.verify_digest(archive, line, "app.zip")

    def test_staging_full_contract_and_failure_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "source.zip"
            payload = self.payload()
            with patch.object(update, "fetch", return_value=json.dumps(payload).encode()):
                release = update.check_release("2.5.0", "mac_byte", "macos-arm64")
            with zipfile.ZipFile(archive, "w") as file:
                file.writestr("Seele.app/Contents/Resources/VERSION", "2.6.0")
                file.writestr("Seele.app/Contents/Resources/EDITION", "mac_byte")
                file.writestr("Seele.app/Contents/Resources/state.json", "{}")
                file.writestr("Seele.app/Contents/Resources/image/bss.gif", "gif")
                file.writestr("Seele.app/Contents/Resources/image/bs_icon.png", "png")
                file.writestr("Seele.app/Contents/MacOS/Seele", "exe")
            manifest = json.dumps({"product": "Seele", "version": "2.6.0",
                                   "platform": "macos-arm64", "edition": "mac_byte",
                                   "commit": "a" * 40}).encode()
            import hashlib
            sums = (f"{update.sha256(archive)}  {release.archive_name}\n"
                    f"{hashlib.sha256(manifest).hexdigest()}  release-manifest-mac_byte.json")

            def fetch(url, destination=None, **kwargs):
                if url == release.checksums_url:
                    return sums.encode()
                if url == release.manifest_url:
                    return manifest
                destination.write_bytes(archive.read_bytes())
                return b""

            jobs = root / "jobs"
            jobs.mkdir()
            real_validate = update.validate_package
            def validate(package, candidate):
                real_validate(package, candidate, smoke=False)
            with patch.object(update, "fetch", side_effect=fetch), \
                 patch.object(update, "updates_dir", return_value=jobs), \
                 patch.object(update, "current_version", return_value="2.5.0"), \
                 patch.object(update, "validate_package", side_effect=validate):
                work, package = update.stage_release(release)
                self.assertTrue((package / "Contents/MacOS/Seele").is_file())
                self.assertFalse((work / release.archive_name).exists())
                import shutil
                shutil.rmtree(work)
                archive.write_bytes(b"bad download")
                with self.assertRaises(update.UpdateError):
                    update.stage_release(release)
                self.assertEqual(list(jobs.iterdir()), [])


class ArchiveTests(unittest.TestCase):
    def test_ditto_utf8_name_without_zip_unicode_flag(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "app.zip"
            name = "app/设置.txt"
            fake_name = "app/" + "x" * len("设置".encode("utf-8")) + ".txt"
            with zipfile.ZipFile(archive, "w") as file:
                file.writestr(fake_name, "settings")
            raw = archive.read_bytes().replace(fake_name.encode(), name.encode("utf-8"))
            archive.write_bytes(raw)
            package = update.safe_extract(archive, root / "out", "macos-arm64")
            self.assertEqual((package / "设置.txt").read_text(), "settings")

    def extract(self, entries, platform="macos-arm64"):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "app.zip"
            with zipfile.ZipFile(archive, "w") as file:
                for name, content, mode in entries:
                    entry = zipfile.ZipInfo(name)
                    entry.create_system = 3
                    entry.external_attr = mode << 16
                    file.writestr(entry, content)
            return update.safe_extract(archive, root / "out", platform)

    def test_traversal_symlink_escape_and_symlink_parent_are_rejected(self):
        bad = [
            [("../escape", "", 0)],
            [("/tmp/escape", "", 0)],
            [("app\\..\\escape", "", 0)],
            [("Seele.app/link", "../../escape", stat.S_IFLNK | 0o777)],
            [("Seele.app/link", "real", stat.S_IFLNK | 0o777),
             ("Seele.app/link/file", "", stat.S_IFREG | 0o644)],
        ]
        for entries in bad:
            with self.subTest(entries=entries), self.assertRaises(update.UpdateError):
                self.extract(entries)

    @unittest.skipIf(sys.platform == "win32", "Framework symlinks require macOS/POSIX")
    def test_framework_symlink_and_executable_permission_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "app.zip"
            with zipfile.ZipFile(archive, "w") as file:
                for name, data, mode in (
                        ("Seele.app/Contents/MacOS/Seele", b"exe", stat.S_IFREG | 0o755),
                        ("Seele.app/Contents/Frameworks/Qt/Versions/A/Qt", b"lib", stat.S_IFREG | 0o644),
                        ("Seele.app/Contents/Frameworks/Qt/Versions/Current", b"A", stat.S_IFLNK | 0o777)):
                    item = zipfile.ZipInfo(name)
                    item.create_system = 3
                    item.external_attr = mode << 16
                    file.writestr(item, data)
            package = update.safe_extract(archive, root / "out", "macos-arm64")
            self.assertTrue(os.access(package / "Contents/MacOS/Seele", os.X_OK))
            link = package / "Contents/Frameworks/Qt/Versions/Current"
            self.assertTrue(link.is_symlink())
            self.assertEqual((link / "Qt").read_bytes(), b"lib")

    def test_windows_case_collision_and_devices_rejected(self):
        for entries in (
                [("app/CON.txt", "", 0)],
                [("app/test.", "", 0)],
                [("app/A.txt", "", 0), ("app/a.txt", "", 0)]):
            with self.assertRaises(update.UpdateError):
                self.extract(entries, "windows-x64")


class TransactionTests(unittest.TestCase):
    def transaction(self, healthy=True, parent_running=False):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "installed"
            target.mkdir()
            (target / "old.txt").write_text("old")
            (target / "unins000.dat").write_text("inno")
            (target / "启动希儿.vbs").write_text("old launcher", encoding="utf-16")
            staged = root / "staged"
            staged.mkdir()
            (staged / "new.txt").write_text("new")
            data = root / "data"
            data.mkdir()
            (data / "state.json").write_text('{"character":"furina"}')
            work = root / "job"
            work.mkdir()
            job = {"target": str(target), "staged": str(staged), "nonce": "test",
                   "data_dir": str(data), "parent_pid": 1234, "version": "2.6.0",
                   "platform": "windows-x64", "operation": "update",
                   "old_command": ["old"]}
            paths.atomic_json(work / "activate.json", {"nonce": "test"})
            launches = []

            def launch(command, env):
                launches.append(command)
                class Process:
                    pid = 4567
                    def poll(self):
                        return None if healthy else 1
                if healthy and command[0] != "old":
                    paths.atomic_json(work / "health.json", {
                        "version": "2.6.0", "pid": 4567, "nonce": "test"})
                return Process()
            with patch.object(update, "pid_alive", return_value=parent_running):
                result = update.apply_transaction(job, work, launcher=launch,
                                                  wait_parent_seconds=0.01, health_seconds=0.5)
            self.assertEqual(result, healthy and not parent_running)
            self.assertEqual((data / "state.json").read_text(), '{"character":"furina"}')
            self.assertTrue((target / "unins000.dat").exists())
            if result:
                self.assertTrue((target / "new.txt").exists())
                self.assertFalse((target / "old.txt").exists())
                self.assertIn("\\Seele.exe", (target / "启动希儿.vbs").read_text(encoding="utf-16"))
            else:
                self.assertEqual((target / "old.txt").read_text(), "old")
                self.assertFalse((target / "new.txt").exists())
            self.assertEqual(list(root.glob(".installed-*")), [])
            if not healthy and not parent_running:
                self.assertEqual(launches[-1], ["old"])
            if parent_running:
                self.assertEqual(launches, [])

    def test_success_preserves_settings_and_inno_uninstaller(self):
        self.transaction()

    def test_startup_failure_restores_old_application(self):
        self.transaction(healthy=False)

    def test_parent_still_running_never_replaced(self):
        self.transaction(parent_running=True)

    def test_real_child_restart_and_health_handshake(self):
        if sys.platform == "win32":
            self.skipTest("POSIX executable fixture")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "Seele.app"
            target.mkdir()
            (target / "old").touch()
            staged = root / "staged.app"
            exe = staged / "Contents/MacOS/Seele"
            exe.parent.mkdir(parents=True)
            exe.write_text("#!" + sys.executable + "\n"
                           "import json,os,sys,time\n"
                           "json.dump({'pid':os.getpid(),'version':'2.6.0','nonce':sys.argv[3]},"
                           "open(sys.argv[2],'w'))\n"
                           "time.sleep(20)\n")
            exe.chmod(0o755)
            work = root / "job"
            work.mkdir()
            job = {"target": str(target), "staged": str(staged), "nonce": "real",
                   "data_dir": str(root / "data"), "parent_pid": 99999999,
                   "version": "2.6.0", "platform": "macos-arm64", "old_command": []}
            paths.atomic_json(work / "activate.json", {"nonce": "real"})
            children = []
            def launch(command, env):
                child = subprocess.Popen(command, env=env)
                children.append(child)
                return child
            try:
                self.assertTrue(update.apply_transaction(job, work, launcher=launch,
                                                        health_seconds=5))
            finally:
                for child in children:
                    child.terminate()
                    child.wait(timeout=5)


class UpdateUiTests(unittest.TestCase):
    @unittest.skipUnless(importlib.util.find_spec("PyQt5"), "Qt is optional in core test CI")
    def test_hourly_menu_dot_offline_retention_and_download_on_click(self):
        # Qt subprocess avoids global binding/environment changes in other tests.
        code = r'''
import os,tempfile,time
from unittest.mock import patch
with tempfile.TemporaryDirectory() as directory:
    os.environ.update(QT_QPA_PLATFORM="offscreen", SEELE_DISABLE_UPDATES="1",
                      SEELE_EDITION="packaging-smoke", SEELE_DATA_DIR=directory)
    from PyQt5.QtWidgets import QApplication
    import Seele, app_update
    app = QApplication([])
    window = Seele.DesktopWife()
    window._WindowMenu()
    controller = window._updater
    assert controller.timer.interval() == 3600000
    assert window.Menu.actions()[-1].text() == "检查更新"
    assert window._Tray.menu.actions()[-1].text() == "检查更新"
    controller.release = app_update.Release("2.6.0","mac_byte","macos-arm64","","","","")
    controller._refresh()
    image = window.Menu.actions()[-1].icon().pixmap(18,18).toImage()
    assert image.pixelColor(9,9).red() > 200 and image.pixelColor(9,9).alpha() > 0
    controller._checked(None, "offline", False)
    assert controller.release.version == "2.6.0"
    with patch.object(app_update,"stage_release",side_effect=RuntimeError("fixture")) as stage, \
         patch.object(app_update,"install_root",return_value=app_update.Path(directory)):
        controller.clicked()
        deadline = time.monotonic()+3
        while controller.busy and time.monotonic()<deadline:
            app.processEvents()
            time.sleep(.01)
        assert stage.call_count == 1 and not controller.busy
    controller.release = None
    with patch.object(app_update,"check_release",return_value=None) as check:
        controller.check()
        deadline = time.monotonic()+3
        while controller.busy and time.monotonic()<deadline:
            app.processEvents()
            time.sleep(.01)
        assert check.call_count == 1 and not controller.busy
    window.shutdown()
    window.close()
'''
        result = subprocess.run([sys.executable, "-c", code], capture_output=True,
                                text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
