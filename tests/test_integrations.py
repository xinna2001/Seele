import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import botmux_client
import botmux_setup_coach
import falseIntent
import mac_byte_bootstrap
import platform_utils
import rpa_bridge
import rpa_service
import run_exe


class BotmuxConfigTests(unittest.TestCase):
    def test_load_config_merges_file_and_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "botmux.json"
            path.write_text(
                json.dumps({
                    "enabled": True,
                    "dashboard_url": "http://file:7891",
                    "bridge": {"enabled": True, "port": 9000},
                }),
                encoding="utf-8",
            )
            with patch.dict(os.environ, {"BOTMUX_DASHBOARD_URL": "http://env:7891"}):
                config = botmux_client.load_config(path)
        self.assertTrue(config["enabled"])
        self.assertEqual(config["dashboard_url"], "http://env:7891")
        self.assertEqual(config["bridge"]["port"], 9000)
        self.assertEqual(config["bridge"]["host"], "127.0.0.1")

    def test_trigger_uses_async_idempotent_contract(self):
        client = botmux_client.BotmuxClient({
            "dashboard_url": "http://127.0.0.1:7891",
            "dashboard_token": "token",
            "bot_id": "cli_test",
            "request_timeout_seconds": 3,
        })
        with patch.object(client, "_request_json", return_value={"ok": True}) as request:
            client.trigger("检查任务", idempotency_key="local-request-1")
        method, path, body = request.call_args.args
        self.assertEqual((method, path), ("POST", "/api/trigger"))
        self.assertEqual(body["source"]["type"], "webhook")
        self.assertEqual(body["target"], {"kind": "turn", "botId": "cli_test"})
        self.assertEqual(body["instruction"], "检查任务")
        self.assertEqual(body["options"]["idempotencyKey"], "local-request-1")
        self.assertTrue(body["options"]["asyncReturnSessionId"])


class BotmuxSessionStateTests(unittest.TestCase):
    def test_snapshot_and_events_produce_attention_summary(self):
        state = botmux_client.BotmuxSessionState("cli_test")
        state.replace([
            {
                "sessionId": "one",
                "larkAppId": "cli_test",
                "status": "working",
                "title": "first",
            },
            {
                "sessionId": "ignored",
                "larkAppId": "another_bot",
                "status": "working",
            },
        ])
        self.assertEqual(state.summary()["kind"], "working")
        state.apply("session.update", {
            "sessionId": "one",
            "patch": {"agentAttention": {"kind": "ask", "reason": "请选择目录"}},
        })
        summary = state.summary()
        self.assertEqual(summary["kind"], "attention")
        self.assertEqual(summary["active"], 1)
        self.assertEqual(summary["attention"], 1)
        state.apply("session.exited", {"sessionId": "one"})
        self.assertEqual(state.summary()["active"], 0)


class RpaServiceTests(unittest.TestCase):
    def _write_catalog(self, root: Path):
        (root / "uid.json").write_text(
            json.dumps({"京东数据抓取": "uid-jd", "执行代码": "uid-code"}, ensure_ascii=False),
            encoding="utf-8",
        )
        (root / "file_name.json").write_text(
            json.dumps({"京东数据抓取": "jd", "执行代码": "code"}, ensure_ascii=False),
            encoding="utf-8",
        )
        (root / "state.json").write_text(
            json.dumps({"startup_mode": "fast"}),
            encoding="utf-8",
        )

    def test_fast_workflow_is_allowlisted_and_idempotent(self):
        with tempfile.TemporaryDirectory() as base, tempfile.TemporaryDirectory() as tools:
            root = Path(base)
            tools_dir = Path(tools)
            self._write_catalog(root)
            with patch.object(rpa_service, "is_shadowbot_running", return_value=True):
                first = rpa_service.trigger_workflow(
                    "京东数据抓取",
                    request_id="same-request",
                    base_dir=root,
                    tools_dir=tools_dir,
                )
                second = rpa_service.trigger_workflow(
                    "京东数据抓取",
                    request_id="same-request",
                    base_dir=root,
                    tools_dir=tools_dir,
                )
            self.assertTrue(first.ok)
            self.assertTrue(second.ok)
            self.assertEqual(first.request_id, second.request_id)
            self.assertEqual((tools_dir / "jd.txt").read_text(encoding="utf-8"), ".\n")

    def test_request_id_cannot_be_reused_for_another_workflow(self):
        with tempfile.TemporaryDirectory() as base, tempfile.TemporaryDirectory() as tools:
            root = Path(base)
            tools_dir = Path(tools)
            self._write_catalog(root)
            with patch.object(rpa_service, "is_shadowbot_running", return_value=True):
                rpa_service.trigger_workflow(
                    "京东数据抓取",
                    request_id="same-request",
                    base_dir=root,
                    tools_dir=tools_dir,
                )
                conflict = rpa_service.trigger_workflow(
                    "执行代码",
                    request_id="same-request",
                    base_dir=root,
                    tools_dir=tools_dir,
                )
            self.assertFalse(conflict.ok)
            self.assertEqual(conflict.code, "idempotency_conflict")
            self.assertFalse((tools_dir / "code.txt").exists())

    def test_unknown_workflow_is_rejected(self):
        with tempfile.TemporaryDirectory() as base, tempfile.TemporaryDirectory() as tools:
            root = Path(base)
            self._write_catalog(root)
            result = rpa_service.trigger_workflow(
                "任意 shell 命令",
                base_dir=root,
                tools_dir=Path(tools),
            )
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "workflow_not_found")

    def test_invalid_request_id_is_rejected_before_dispatch(self):
        with tempfile.TemporaryDirectory() as base, tempfile.TemporaryDirectory() as tools:
            root = Path(base)
            self._write_catalog(root)
            with self.assertRaises(ValueError):
                rpa_service.trigger_workflow(
                    "京东数据抓取",
                    request_id="../escape",
                    base_dir=root,
                    tools_dir=Path(tools),
                )


class RpaBridgeTests(unittest.TestCase):
    def test_health_is_public_and_workflow_catalog_requires_token(self):
        bridge = rpa_bridge.RpaBridge({
            "enabled": True,
            "host": "127.0.0.1",
            "port": 0,
            "token": "test-secret",
        })
        self.assertTrue(bridge.start())
        self.addCleanup(bridge.stop)
        base_url = f"http://127.0.0.1:{bridge.server.server_port}"
        with urlopen(f"{base_url}/healthz", timeout=3) as response:
            self.assertEqual(json.load(response)["service"], "seele-rpa-bridge")
        with self.assertRaises(HTTPError) as unauthorized:
            urlopen(f"{base_url}/v1/workflows", timeout=3)
        self.assertEqual(unauthorized.exception.code, 401)
        request = Request(
            f"{base_url}/v1/workflows",
            headers={"authorization": "Bearer test-secret"},
        )
        with urlopen(request, timeout=3) as response:
            self.assertTrue(json.load(response)["ok"])


class IntentTests(unittest.TestCase):
    def test_web_intent_does_not_match_unrelated_character(self):
        self.assertEqual(falseIntent.main("帮我制作一份表格"), "帮我制作一份表格")

    def test_deploy_intent_matches_fast_mode_catalog_name(self):
        self.assertEqual(falseIntent.main("帮我部署项目一"), "部署项目")


class MacByteBootstrapTests(unittest.TestCase):
    def test_all_mac_byte_voice_files_exist(self):
        voice_files = {
            **mac_byte_bootstrap.VOICE_FILES,
            **botmux_setup_coach.BOTMUX_VOICE_FILES,
        }
        for voice_name, filename in voice_files.items():
            with self.subTest(voice_name=voice_name, filename=filename):
                path = platform_utils.app_path("audio", "mac_byte", filename)
                self.assertTrue(path.is_file())

    def test_release_edition_can_be_overridden(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "EDITION"
            path.write_text("mac_byte\n", encoding="utf-8")
            with patch.dict(os.environ, {}, clear=True):
                self.assertEqual(mac_byte_bootstrap.current_edition(path), "mac_byte")
            with patch.dict(os.environ, {"SEELE_EDITION": "mac"}, clear=True):
                self.assertEqual(mac_byte_bootstrap.current_edition(path), "mac")

    def test_bootstrap_title_reads_release_version_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "VERSION"
            path.write_text("2.1.0\n", encoding="utf-8")
            self.assertEqual(mac_byte_bootstrap.current_version(path), "2.1.0")

    def test_bootstrap_mode_uses_botmux_install_and_config_state(self):
        with patch.object(
            mac_byte_bootstrap,
            "missing_bootstrap_commands",
            return_value=["botmux"],
        ):
            self.assertEqual(mac_byte_bootstrap.bootstrap_mode(), "full")
        with (
            patch.object(
                mac_byte_bootstrap,
                "missing_bootstrap_commands",
                return_value=[],
            ),
            patch.object(mac_byte_bootstrap, "botmux_is_configured", return_value=False),
        ):
            self.assertEqual(mac_byte_bootstrap.bootstrap_mode(), "setup")
        with (
            patch.object(
                mac_byte_bootstrap,
                "missing_bootstrap_commands",
                return_value=[],
            ),
            patch.object(mac_byte_bootstrap, "botmux_is_configured", return_value=True),
        ):
            self.assertEqual(mac_byte_bootstrap.bootstrap_mode(), "ready")

    def test_bootstrap_commands_are_detected_independently(self):
        installed = {"node", "npm", "lark-cli"}
        with patch.object(
            mac_byte_bootstrap,
            "_command_path",
            side_effect=lambda command: f"/bin/{command}" if command in installed else None,
        ):
            missing = mac_byte_bootstrap.missing_bootstrap_commands()

        self.assertEqual(missing, ["traex", "agentbuddy", "botmux"])

    def test_full_script_uses_official_login_commands_without_manual_pauses(self):
        script = mac_byte_bootstrap.build_bootstrap_script(
            "full",
            script_path=Path("/tmp/bootstrap.command"),
            lock_path=Path("/tmp/bootstrap.lock"),
            status_path=Path("/tmp/bootstrap-status.json"),
        )
        self.assertIn(
            "npm install -g botmux@latest --registry https://registry.npmjs.org/",
            script,
        )
        self.assertIn(
            "if command -v node >/dev/null 2>&1 && command -v npm >/dev/null 2>&1",
            script,
        )
        for command in mac_byte_bootstrap.BOOTSTRAP_COMMANDS:
            self.assertIn(f"command -v {command}", script)
        self.assertIn("TRAEX_INSTALL_ASSUME_YES=1", script)
        self.assertIn("TRAEX_INSTALL_REMOVE_COCO=1", script)
        self.assertIn("traex backend cn", script)
        self.assertIn("traex login --sso-device", script)
        self.assertIn("traex login status", script)
        self.assertIn(
            "lark-cli config init --new --lang zh_cn --name seele",
            script,
        )
        self.assertEqual(
            script.count("lark-cli config init --new --lang zh_cn --name seele"),
            1,
        )
        self.assertGreaterEqual(
            script.count("lark-cli config show >/dev/null 2>&1"),
            2,
        )
        self.assertIn("本轮不会再次执行 config init", script)
        self.assertIn("重新启动 Seele", script)
        self.assertIn("lark-cli auth login --recommend", script)
        self.assertIn("lark-cli auth status --json --verify", script)
        self.assertIn(
            "agentbuddy login --region cn --login-mode device --json --yes",
            script,
        )
        self.assertIn("agentbuddy status --json", script)
        self.assertIn("--botmux-setup-coach", script)
        self.assertNotIn("npm config set registry", script)
        self.assertNotIn("\ntraex\n", script)
        self.assertNotIn("\nbotmux setup\n", script)
        self.assertNotIn("IFS= read -r _", script)
        self.assertIn("[语音占位符]", script)

    @unittest.skipUnless(sys.platform == "darwin", "requires /bin/zsh")
    def test_generated_bootstrap_script_has_valid_zsh_syntax(self):
        script = mac_byte_bootstrap.build_bootstrap_script(
            "full",
            script_path=Path("/tmp/bootstrap.command"),
            lock_path=Path("/tmp/bootstrap.lock"),
            status_path=Path("/tmp/bootstrap-status.json"),
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bootstrap.command"
            path.write_text(script, encoding="utf-8")
            result = mac_byte_bootstrap.subprocess.run(
                ["/bin/zsh", "-n", str(path)],
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipUnless(sys.platform == "darwin", "macOS bundle path test")
    def test_frozen_bootstrap_uses_console_coach_helper(self):
        resources = Path("/Applications/Seele.app/Contents/Resources")
        with (
            patch.object(mac_byte_bootstrap.sys, "frozen", True, create=True),
            patch.object(
                mac_byte_bootstrap,
                "app_path",
                side_effect=lambda *parts: resources.joinpath(*parts),
            ),
        ):
            command = mac_byte_bootstrap._botmux_coach_command()

        self.assertIn("SEELE_RESOURCES_DIR=", command)
        self.assertIn(
            "/Applications/Seele.app/Contents/Resources/bin/SeeleBotmuxCoach",
            command,
        )
        self.assertNotIn("--botmux-setup-coach", command)

    def test_packaged_botmux_coach_smoke_checks_executable_helper(self):
        with tempfile.TemporaryDirectory() as directory:
            helper = Path(directory) / "SeeleBotmuxCoach"
            helper.write_text("", encoding="utf-8")
            helper.chmod(0o755)
            with patch.object(
                mac_byte_bootstrap,
                "_botmux_coach_helper_path",
                return_value=helper,
            ):
                self.assertEqual(run_exe._run_botmux_coach_smoke_test(), 0)

    def test_botmux_configuration_requires_a_nonempty_catalog(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            config = home / ".botmux" / "bots.json"
            config.parent.mkdir(parents=True)
            config.write_text("[]", encoding="utf-8")
            self.assertFalse(mac_byte_bootstrap.botmux_is_configured(home))
            config.write_text('[{"larkAppId":"cli_test"}]', encoding="utf-8")
            self.assertTrue(mac_byte_bootstrap.botmux_is_configured(home))

    def test_launch_bootstrap_opens_a_private_fixed_script(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            with (
                patch.object(mac_byte_bootstrap, "is_mac_byte", return_value=True),
                patch.object(mac_byte_bootstrap.subprocess, "run") as run,
            ):
                run.return_value.returncode = 0
                run.return_value.stderr = ""
                script = mac_byte_bootstrap.launch_bootstrap(mode="setup", home=home)

            self.assertIsNotNone(script)
            if os.name != "nt":
                self.assertEqual(script.stat().st_mode & 0o777, 0o700)
            self.assertIn(
                "--botmux-setup-coach",
                script.read_text(encoding="utf-8"),
            )
            self.assertEqual(
                run.call_args.args[0][:3],
                ["/usr/bin/open", "-a", "Terminal"],
            )
            status = json.loads(
                (home / ".seele" / "mac_byte" / "bootstrap-status.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(status["state"], "running")


class PlatformPathTests(unittest.TestCase):
    def test_frozen_macos_bundle_finds_contents_resources(self):
        with tempfile.TemporaryDirectory() as directory:
            contents = Path(directory) / "Seele.app" / "Contents"
            executable = contents / "MacOS" / "Seele"
            frameworks = contents / "Frameworks"
            resources = contents / "Resources"
            executable.parent.mkdir(parents=True)
            executable.write_text("", encoding="utf-8")
            frameworks.mkdir(parents=True)
            (frameworks / "state.json").write_text("{}", encoding="utf-8")
            helper = resources / "bin" / "SeeleBotmuxCoach"
            helper.parent.mkdir(parents=True)
            helper.write_text("", encoding="utf-8")
            (resources / "state.json").write_text("{}", encoding="utf-8")
            with (
                patch.object(platform_utils.sys, "frozen", True, create=True),
                patch.object(platform_utils.sys, "_MEIPASS", str(frameworks), create=True),
                patch.object(platform_utils.sys, "executable", str(executable)),
            ):
                self.assertEqual(platform_utils.get_base_dir(), resources.resolve())
                command = mac_byte_bootstrap._botmux_coach_command()

            self.assertIn(str(helper.resolve()), command)
            self.assertNotIn(str((frameworks / "bin").resolve()), command)


if __name__ == "__main__":
    unittest.main()
