import base64
import configparser
import io
import os
import pathlib
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import botmux_client
import botmux_setup_coach
import windows_byte_bootstrap as host
import windows_byte_linux as linux


class WindowsByteTests(unittest.TestCase):
    def test_english_windows_redirected_console_keeps_chinese_and_reboot_result(self):
        buffer = io.BytesIO()
        output = io.TextIOWrapper(buffer, encoding="cp1252")
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(host, "state_dir", return_value=pathlib.Path(directory)),
            patch.object(host, "windows_identity", return_value="sid-test"),
            patch.object(host, "boot_id", return_value="boot-one"),
            patch.object(host.sys, "platform", "win32"),
            patch.object(host.sys, "stdout", output),
            patch.object(host.sys, "stderr", output),
        ):
            host.save_status({}, state="waiting_reboot", boot_id="boot-one",
                             windows_sid="sid-test", stage="wsl")
            self.assertEqual(host.run_install(), 3010)
            output.flush()
            self.assertIn("需要重启", buffer.getvalue().decode("utf-8"))
        output.close()

    def test_same_boot_waits_without_repeating_install_or_registration(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(host, "state_dir", return_value=pathlib.Path(directory)),
            patch.object(host, "windows_identity", return_value="sid-test"),
            patch.object(host, "boot_id", return_value="boot-one"),
            patch.object(host, "set_resume") as resume,
            patch.object(host, "elevate_components") as elevated,
            patch.object(host, "list_distros") as distros,
        ):
            host.save_status({}, state="waiting_reboot", boot_id="boot-one",
                             windows_sid="sid-test", stage="wsl")
            self.assertEqual(host.run_install(), 3010)
            resume.assert_not_called()
            elevated.assert_not_called()
            distros.assert_not_called()
            self.assertEqual(host.read_status()["stage"], "wsl")

    def test_after_reboot_reuses_saved_distro_user_and_finishes(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(host, "state_dir", return_value=pathlib.Path(directory)),
            patch.object(host, "windows_identity", return_value="sid-test"),
            patch.object(host, "boot_id", return_value="boot-two"),
            patch.object(host, "set_resume", return_value="scheduled_task"),
            patch.object(host, "elevate_components") as elevated,
            patch.object(host, "list_distros", return_value=[{"name": "Ubuntu-work", "version": 2}]),
            patch.object(host, "prepare_user", return_value="original"),
            patch.object(host, "configure_linux") as configure,
            patch.object(host, "stage_runtime", return_value="/home/original"),
            patch.object(host, "run_wsl"),
            patch.object(host, "register_keepalive") as register,
            patch.object(host, "remove_resume") as remove,
        ):
            host.save_status({}, state="waiting_reboot", boot_id="boot-one",
                             windows_sid="sid-test", distro="Ubuntu-work")
            self.assertEqual(host.run_install(), 0)
            elevated.assert_not_called()
            configure.assert_called_once_with("Ubuntu-work", "original")
            register.assert_called_once_with("Ubuntu-work", "original", "/home/original", "sid-test")
            remove.assert_called_once()
            self.assertEqual(host.read_status()["state"], "completed")
            self.assertTrue(host.installation_is_current())

    def test_pre_pin_windows_installation_runs_again(self):
        for version in (None, "3.17.0", "3.55.0"):
            with self.subTest(version=version):
                self.assertFalse(host.installation_is_current({
                    "state": "completed", "botmux_version": version,
                }))
        self.assertFalse(host.installation_is_current({
            "state": "failed", "botmux_version": "3.54.0",
        }))
        self.assertTrue(host.installation_is_current({
            "state": "completed", "botmux_version": "3.54.0",
        }))

    def test_first_install_saves_reboot_boundary_before_distro_download(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(host, "state_dir", return_value=pathlib.Path(directory)),
            patch.object(host, "windows_identity", return_value="sid-test"),
            patch.object(host, "boot_id", return_value="first-boot"),
            patch.object(host, "set_resume", return_value="scheduled_task"),
            patch.object(host, "list_distros", return_value=[]),
            patch.object(host, "elevate_components", return_value=True),
            patch.object(host.subprocess, "run", return_value=subprocess.CompletedProcess([], 1)) as run,
        ):
            self.assertEqual(host.run_install(), 3010)
            status = host.read_status()
            self.assertEqual(status["state"], "waiting_reboot")
            self.assertEqual(status["boot_id"], "first-boot")
            self.assertFalse(any("--distribution" in call.args[0] for call in run.call_args_list))

    def test_different_windows_identity_cannot_install(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(host, "state_dir", return_value=pathlib.Path(directory)),
            patch.object(host, "windows_identity", return_value="different"),
            patch.object(host, "set_resume") as resume,
        ):
            host.save_status({}, windows_sid="original", stage="botmux")
            self.assertEqual(host.run_install(), 1)
            resume.assert_not_called()
            self.assertEqual(host.read_status()["stage"], "botmux")

    def test_contention_does_not_overwrite_active_installer_status(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(
            host, "state_dir", return_value=pathlib.Path(directory),
        ):
            host.save_status({}, state="running", stage="botmux")
            before = host.read_status()
            with host.InstallLock():
                self.assertEqual(host.run_install(), 2)
            self.assertEqual(before, host.read_status())

    def test_resume_gui_command_preserves_byte_edition(self):
        with patch.object(host.sys, "frozen", False, create=True):
            self.assertIn("--windows-byte", host.gui_command())

    def test_lock_contention_and_process_exit_release(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(
            host, "state_dir", return_value=pathlib.Path(directory),
        ):
            with host.InstallLock():
                with self.assertRaises(RuntimeError):
                    with host.InstallLock():
                        pass
            with host.InstallLock():
                pass

    def test_task_registration_keeps_current_identity_and_unlimited_runtime(self):
        command = host.wsl_command("Ubuntu test", "dev", "python3", "/home/dev/keep.py")
        script = host.task_script(host.SERVICE_TASK, command, "sid-test", keepalive=True)
        self.assertIn("-UserId 'sid-test' -LogonType Interactive -RunLevel Limited", script)
        self.assertIn("-MultipleInstances IgnoreNew", script)
        self.assertIn("([TimeSpan]::Zero)", script)
        self.assertIn("Start-ScheduledTask", script)
        self.assertNotIn("SYSTEM", script)
        self.assertNotIn("Password", script)
        self.assertIn('"Ubuntu test"', script)

    def test_existing_distro_choice_is_explicit_and_never_substituted(self):
        rows = [{"name": "Ubuntu", "version": 1}, {"name": "Ubuntu-work", "version": 2}]
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(host.choose_distro(rows, "Ubuntu-work"), rows[1])
            self.assertIsNone(host.choose_distro(rows, "missing"))
            self.assertEqual(host.choose_distro(rows), rows[0])

    def test_wsl_config_preserves_network_mounts_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            target = pathlib.Path(directory) / "wsl.conf"
            target.write_text("[automount]\nroot=/custom\n[network]\ngenerateResolvConf=false\n")
            self.assertTrue(linux.configure_wsl(target, "original"))
            first = target.read_bytes()
            self.assertFalse(linux.configure_wsl(target, "original"))
            self.assertEqual(first, target.read_bytes())
            config = configparser.ConfigParser()
            config.read(target)
            self.assertEqual(config["automount"]["root"], "/custom")
            self.assertEqual(config["network"]["generateResolvConf"], "false")
            self.assertEqual(config["boot"]["systemd"], "true")
            self.assertEqual(config["user"]["default"], "original")

    def test_wsl_configuration_source_runs_before_install_modules_are_staged(self):
        source = pathlib.Path(linux.__file__).read_bytes()
        scope = {"__name__": "seele_wsl_config"}
        real_import = __import__

        def before_staging(name, *args, **kwargs):
            if name == "botmux_install":
                raise ModuleNotFoundError(name)
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=before_staging):
            exec(compile(source, str(linux.__file__), "exec"), scope)
        with tempfile.TemporaryDirectory() as directory:
            self.assertTrue(scope["configure_wsl"](pathlib.Path(directory) / "wsl.conf", "dev"))

    @unittest.skipUnless(os.name == "posix", "bash syntax check requires POSIX")
    def test_linux_generated_shell_is_valid_and_skips_existing_bots(self):
        for configured in (True, False):
            script = linux.build_install_script(pathlib.Path("/home/dev/space ' test"), configured=configured)
            result = subprocess.run(["/bin/bash", "-n"], input=script.encode(), capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            self.assertIn("botmux autostart enable", script)
            self.assertIn("env BOTMUX_VERSION=v3.54.0 sh", script)
            self.assertIn("botmux_matches_pinned_version", script)
            self.assertIn("systemctl --user stop botmux.service", script)
            self.assertIn("botmux-watchdog.timer", script)
            self.assertIn(" --login-command -- ", script)
            if configured:
                self.assertIn("保留已有 Botmux 配置", script)

    @unittest.skipUnless(os.name == "posix", "Linux keepalive uses flock")
    def test_keepalive_checks_service_repeatedly_and_exits_for_windows_retry(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(linux.pathlib.Path, "home", return_value=pathlib.Path(directory)),
            patch.object(linux.subprocess, "run", return_value=subprocess.CompletedProcess([], 1)) as run,
            patch.object(linux.time, "sleep") as sleep,
            patch.dict(os.environ, {}, clear=True),
        ):
            self.assertEqual(linux.keepalive(), 1)
            self.assertEqual(run.call_count, 10)
            self.assertEqual(sleep.call_count, 4)

    def test_powershell_values_with_shell_syntax_are_only_literal_data(self):
        value = "a' ; $(Get-Secret); `&"
        script = f"Write-Output {host.ps_string(value)}"
        command = host.powershell_command(script)
        self.assertEqual(base64.b64decode(command[-1]).decode("utf-16le"),
                         "Write-Output 'a'' ; $(Get-Secret); `&'")

    def test_wsl_browser_uses_windows_and_encoded_url(self):
        with (
            patch.dict(os.environ, {"SEELE_WINDOWS_WSL": "1"}),
            patch.object(botmux_setup_coach.shutil, "which", return_value="/mnt/c/powershell.exe"),
            patch.object(botmux_setup_coach.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)) as run,
        ):
            self.assertTrue(botmux_setup_coach.open_login_url("https://example.com/?a=1&b=$(x)"))
            command = run.call_args.args[0]
            self.assertEqual(command[0], "/mnt/c/powershell.exe")
            script = base64.b64decode(command[-1]).decode("utf-16le")
            self.assertIn("$url = 'https://example.com/?a=1&b=$(x)'", script)
            self.assertIn("Google\\Chrome", script)

    def test_dashboard_uses_selected_linux_home_without_saving_token(self):
        with (
            patch.object(host, "read_status", return_value={"distro": "Ubuntu", "linux_home": "/home/original"}),
            patch.object(botmux_client, "discover_local_dashboard", return_value={"port": 12345, "token": "test"}) as discover,
        ):
            self.assertEqual(botmux_client.discover_wsl_dashboard()["port"], 12345)
            self.assertIn("Ubuntu", str(discover.call_args.args[0]))
            self.assertIn("original", str(discover.call_args.args[0]))

    def test_invalid_unc_selection_does_not_read_other_shares(self):
        for status in ({"distro": r"..\foreign", "linux_home": "/home/dev"},
                       {"distro": "Ubuntu", "linux_home": "/home/../root"}):
            with patch.object(host, "read_status", return_value=status), patch.object(
                botmux_client, "discover_local_dashboard",
            ) as discover:
                self.assertEqual(botmux_client.discover_wsl_dashboard(), {})
                discover.assert_not_called()


if __name__ == "__main__":
    unittest.main()
