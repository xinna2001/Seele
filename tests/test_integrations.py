import json
import importlib.util
import os
import subprocess
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
                return_value=["tmux"],
            ),
            patch.object(mac_byte_bootstrap, "botmux_is_configured", return_value=True),
        ):
            self.assertEqual(mac_byte_bootstrap.bootstrap_mode(), "repair")
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
            patch.object(mac_byte_bootstrap, "botmux_is_running", return_value=False),
        ):
            self.assertEqual(mac_byte_bootstrap.bootstrap_mode(), "repair")
        with (
            patch.object(
                mac_byte_bootstrap,
                "missing_bootstrap_commands",
                return_value=[],
            ),
            patch.object(mac_byte_bootstrap, "botmux_is_configured", return_value=True),
            patch.object(mac_byte_bootstrap, "botmux_is_running", return_value=True),
        ):
            self.assertEqual(mac_byte_bootstrap.bootstrap_mode(), "ready")

    def test_botmux_running_requires_positive_supervisor_status(self):
        running = subprocess.CompletedProcess(
            ["botmux", "status"],
            0,
            stdout="supervisor 在线 (pid 123)\n  botmux-0 online\n",
            stderr="",
        )
        stopped = subprocess.CompletedProcess(
            ["botmux", "status"],
            0,
            stdout="daemon 未在运行。（用 `botmux start` 启动）\n",
            stderr="",
        )
        with (
            patch.object(mac_byte_bootstrap, "_command_path", return_value="/bin/botmux"),
            patch.object(mac_byte_bootstrap.subprocess, "run", return_value=running),
        ):
            self.assertTrue(mac_byte_bootstrap.botmux_is_running())
        with (
            patch.object(mac_byte_bootstrap, "_command_path", return_value="/bin/botmux"),
            patch.object(mac_byte_bootstrap.subprocess, "run", return_value=stopped),
        ):
            self.assertFalse(mac_byte_bootstrap.botmux_is_running())

    def test_bootstrap_commands_are_detected_independently(self):
        installed = {"node", "npm", "lark-cli"}
        with patch.object(
            mac_byte_bootstrap,
            "_command_path",
            side_effect=lambda command: f"/bin/{command}" if command in installed else None,
        ):
            missing = mac_byte_bootstrap.missing_bootstrap_commands()

        self.assertEqual(missing, ["tmux", "traex", "agentbuddy", "botmux"])

    def test_stale_traex_is_treated_as_missing_dependency(self):
        with (
            patch.object(
                mac_byte_bootstrap,
                "_command_path",
                side_effect=lambda command: f"/bin/{command}",
            ),
            patch.object(
                mac_byte_bootstrap,
                "_traex_supports_backend",
                return_value=False,
            ) as supports_backend,
        ):
            missing = mac_byte_bootstrap.missing_bootstrap_commands()

        self.assertEqual(missing, ["traex"])
        supports_backend.assert_called_once_with("/bin/traex")

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
        self.assertIn(mac_byte_bootstrap.HOMEBREW_INSTALL_URL, script)
        self.assertIn('/bin/bash -c "$homebrew_installer"', script)
        self.assertIn(
            "--homebrew-install -- /bin/bash -c \"$homebrew_installer\"",
            script,
        )
        self.assertNotIn("NONINTERACTIVE=1 /bin/bash -c", script)
        self.assertIn("HOMEBREW_NO_AUTO_UPDATE=1 brew install tmux", script)
        self.assertIn("tmux -V", script)
        self.assertEqual(
            script.count("HOMEBREW_NO_AUTO_UPDATE=1 brew install tmux"),
            1,
        )
        self.assertIn(
            "if command -v node >/dev/null 2>&1 && command -v npm >/dev/null 2>&1",
            script,
        )
        for command in mac_byte_bootstrap.BOOTSTRAP_COMMANDS:
            self.assertIn(f"command -v {command}", script)
        self.assertIn("TRAEX_INSTALL_ASSUME_YES=1", script)
        self.assertIn("TRAEX_INSTALL_REMOVE_COCO=1", script)
        self.assertIn("traex backend cn --help", script)
        self.assertIn("trae-code", script)
        self.assertIn("user-local CLI tools", script)
        self.assertIn('export PATH="$HOME/.local/bin:$PATH"', script)
        self.assertIn("当前 Trae CLI 不支持 backend cn", script)
        self.assertIn("当前版本不支持 backend cn", script)
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
        self.assertEqual(script.count("--login-command --"), 4)
        self.assertIn(
            "--login-command -- traex login --sso-device",
            script,
        )
        self.assertIn(
            "--login-command -- lark-cli config init --new",
            script,
        )
        self.assertIn(
            "--login-command -- lark-cli auth login --recommend",
            script,
        )
        self.assertIn(
            "--login-command -- agentbuddy login --region cn",
            script,
        )
        self.assertIn(
            "output volume of (get volume settings)",
            script,
        )
        self.assertIn(
            "output muted of (get volume settings)",
            script,
        )
        self.assertIn(
            "set volume output volume 20 without output muted",
            script,
        )
        self.assertIn(
            'tell application "Terminal" to activate',
            script,
        )
        self.assertIn("printf '\\033[2J\\033[3J\\033[H'", script)
        self.assertIn("restore_login_audio", script)
        finish_body = script[
            script.index("finish() {"):script.index("trap finish EXIT")
        ]
        self.assertIn("restore_login_audio", finish_body)
        self.assertEqual(script.count("prepare_login_attention '"), 1)
        self.assertIn(
            "prepare_login_attention 'Botmux 机器人配置'",
            script,
        )
        for stage_name in (
            "Trae CLI 登录",
            "Lark CLI 应用初始化",
            "Lark CLI 用户授权",
            "AgentBuddy 登录",
        ):
            self.assertNotIn(f"prepare_login_attention '{stage_name}'", script)
        self.assertGreaterEqual(script.count("prepare_login_audio"), 6)
        background_voice_lines = [
            line
            for line in script.splitlines()
            if "/usr/bin/afplay" in line and line.rstrip().endswith("&")
        ]
        self.assertEqual(len(background_voice_lines), 4)
        self.assertLess(
            script.index("prepare_login_audio", script.index("traex backend cn")),
            script.index("traex login --sso-device"),
        )
        botmux_setup_lines = [
            line
            for line in script.splitlines()
            if "--botmux-setup-coach" in line and "--login-command" not in line
            and "--homebrew-install" not in line
        ]
        self.assertEqual(len(botmux_setup_lines), 1)
        self.assertLess(
            script.index("prepare_login_attention 'Botmux 机器人配置'"),
            script.rindex(botmux_setup_lines[0]),
        )
        self.assertNotIn("npm config set registry", script)
        self.assertNotIn("\ntraex\n", script)
        self.assertNotIn("\nbotmux setup\n", script)
        self.assertNotIn("IFS= read -r _", script)
        self.assertIn("[语音占位符]", script)

    @unittest.skipIf(os.name == "nt", "requires a POSIX shell")
    def test_traex_install_upgrades_cli_without_backend_command(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fake_bin = root / "bin"
            fake_bin.mkdir()
            log = root / "commands.log"
            ready = root / "traex-ready"

            traex = fake_bin / "traex"
            traex.write_text(
                "#!/bin/sh\n"
                "printf 'traex %s\\n' \"$*\" >> \"$SEELE_TEST_LOG\"\n"
                "if [ \"$1\" = backend ] && [ \"$2\" = cn ] && "
                "[ \"$3\" = --help ]; then\n"
                "  if [ -f \"$SEELE_TRAEX_READY\" ]; then\n"
                "    exit 0\n"
                "  fi\n"
                "  printf \"error: unexpected argument 'cn' found\\n\" >&2\n"
                "  exit 2\n"
                "fi\n"
                "exit 0\n",
                encoding="utf-8",
            )
            traex.chmod(0o755)

            curl = fake_bin / "curl"
            curl.write_text(
                "#!/bin/sh\n"
                "printf 'curl %s\\n' \"$*\" >> \"$SEELE_TEST_LOG\"\n"
                "printf '%s\\n' \\\n"
                "  'printf \"installer assume=%s remove_coco=%s "
                "remove_brew=%s\\n\" \"$TRAEX_INSTALL_ASSUME_YES\" "
                "\"$TRAEX_INSTALL_REMOVE_COCO\" "
                "\"$TRAEX_INSTALL_REMOVE_BREW\" >> \"$SEELE_TEST_LOG\"' \\\n"
                "  ': > \"$SEELE_TRAEX_READY\"'\n",
                encoding="utf-8",
            )
            curl.chmod(0o755)

            env = os.environ.copy()
            env.update({
                "PATH": f"{fake_bin}:/usr/bin:/bin",
                "SEELE_TEST_LOG": str(log),
                "SEELE_TRAEX_READY": str(ready),
            })
            result = subprocess.run(
                ["/bin/sh", "-c", mac_byte_bootstrap._traex_install_commands()],
                capture_output=True,
                text=True,
                env=env,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(ready.is_file())
            commands = log.read_text(encoding="utf-8")
            self.assertEqual(commands.count("traex backend cn --help"), 2)
            self.assertIn("curl -fsSL", commands)
            self.assertIn(
                "installer assume=1 remove_coco=1 remove_brew=0",
                commands,
            )
            self.assertIn(
                "[待升级] 当前 Trae CLI 不支持 backend cn",
                result.stdout,
            )

    @unittest.skipIf(os.name == "nt", "requires a POSIX shell")
    def test_trae_cli_path_setup_keeps_traex_available_in_new_shells(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fake_bin = root / "bin"
            fake_bin.mkdir()
            log = root / "commands.log"
            traex = fake_bin / "traex"
            traex.write_text(
                "#!/bin/sh\n"
                "printf 'traex %s\\n' \"$*\" >> \"$SEELE_TEST_LOG\"\n",
                encoding="utf-8",
            )
            traex.chmod(0o755)
            env = os.environ.copy()
            env.update({
                "HOME": str(root),
                "PATH": f"{fake_bin}:/usr/bin:/bin",
                "SEELE_TEST_LOG": str(log),
            })

            result = subprocess.run(
                ["/bin/sh", "-c", mac_byte_bootstrap._trae_cli_path_commands()],
                capture_output=True,
                text=True,
                env=env,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

            shim = root / ".local" / "bin" / "trae-code"
            self.assertTrue(shim.is_file())
            self.assertTrue(os.access(shim, os.X_OK))
            self.assertIn(
                'export PATH="$HOME/.local/bin:$PATH"',
                (root / ".zprofile").read_text(encoding="utf-8"),
            )
            result = subprocess.run(
                [str(shim), "login", "status"],
                capture_output=True,
                text=True,
                env=env,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("traex login status", log.read_text(encoding="utf-8"))

    def test_full_script_skips_botmux_setup_when_already_configured(self):
        script = mac_byte_bootstrap.build_bootstrap_script(
            "full",
            script_path=Path("/tmp/bootstrap.command"),
            lock_path=Path("/tmp/bootstrap.lock"),
            status_path=Path("/tmp/bootstrap-status.json"),
            botmux_configured=True,
        )

        self.assertIn("brew install tmux", script)
        self.assertIn("Botmux 已有机器人配置，跳过重复 setup", script)
        self.assertNotIn("prepare_login_attention 'Botmux 机器人配置'", script)
        self.assertNotIn("mac_byte_botmux_setup_16k.wav", script)

    def test_repair_script_only_repairs_tmux_and_botmux_runtime(self):
        script = mac_byte_bootstrap.build_bootstrap_script(
            "repair",
            script_path=Path("/tmp/bootstrap.command"),
            lock_path=Path("/tmp/bootstrap.lock"),
            status_path=Path("/tmp/bootstrap-status.json"),
            botmux_configured=True,
        )

        self.assertIn("brew install tmux", script)
        self.assertIn("跳过工具安装、登录和 botmux setup", script)
        self.assertIn("botmux plugin install", script)
        self.assertIn("botmux plugin enable seele", script)
        self.assertIn("botmux start", script)
        self.assertIn("botmux autostart enable", script)
        self.assertIn("botmux status", script)
        self.assertIn("botmux autostart status", script)
        self.assertNotIn("npm install -g", script)
        self.assertNotIn("traex login", script)
        self.assertNotIn("lark-cli auth", script)
        self.assertNotIn("agentbuddy login", script)
        botmux_setup_lines = [
            line
            for line in script.splitlines()
            if "--botmux-setup-coach" in line
            and "--homebrew-install" not in line
        ]
        self.assertEqual(botmux_setup_lines, [])

    @unittest.skipUnless(sys.platform == "darwin", "requires /bin/zsh")
    def test_repair_script_executes_tmux_install_then_botmux_recovery(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fake_bin = root / "bin"
            fake_bin.mkdir()
            log = root / "commands.log"
            plugin = root / "botmux-skill"
            plugin.mkdir()
            (root / "VERSION").write_text("test\n", encoding="utf-8")

            brew = fake_bin / "brew"
            brew.write_text(
                "#!/bin/sh\n"
                "printf 'brew %s\\n' \"$*\" >> \"$SEELE_TEST_LOG\"\n"
                "if [ \"$1\" = install ] && [ \"$2\" = tmux ]; then\n"
                "  printf '#!/bin/sh\\nprintf \"tmux 3.5a\\\\n\"\\n' > \"$(dirname \"$0\")/tmux\"\n"
                "  chmod 755 \"$(dirname \"$0\")/tmux\"\n"
                "fi\n",
                encoding="utf-8",
            )
            brew.chmod(0o755)
            botmux = fake_bin / "botmux"
            botmux.write_text(
                "#!/bin/sh\n"
                "printf 'botmux %s\\n' \"$*\" >> \"$SEELE_TEST_LOG\"\n",
                encoding="utf-8",
            )
            botmux.chmod(0o755)

            script_path = root / "bootstrap.command"
            lock_path = root / "bootstrap.lock"
            status_path = root / "bootstrap-status.json"
            lock_path.write_text("locked", encoding="ascii")
            with (
                patch.object(
                    mac_byte_bootstrap,
                    "app_path",
                    side_effect=lambda *parts: root.joinpath(*parts),
                ),
                patch.object(
                    mac_byte_bootstrap,
                    "_npm_prelude",
                    return_value=(
                        f'export PATH="{fake_bin}:/usr/bin:/bin"\n'
                        "hash -r"
                    ),
                ),
            ):
                script = mac_byte_bootstrap.build_bootstrap_script(
                    "repair",
                    script_path=script_path,
                    lock_path=lock_path,
                    status_path=status_path,
                    botmux_configured=True,
                )
            script_path.write_text(script, encoding="utf-8")
            script_path.chmod(0o700)
            env = os.environ.copy()
            env.update({
                "HOME": str(root),
                "PATH": f"{fake_bin}:/usr/bin:/bin",
                "SEELE_TEST_LOG": str(log),
                "TERM": "xterm-256color",
            })

            result = subprocess.run(
                ["/bin/zsh", str(script_path)],
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            commands = log.read_text(encoding="utf-8")
            self.assertIn("brew install tmux", commands)
            self.assertIn("botmux plugin install", commands)
            self.assertIn("botmux plugin enable seele", commands)
            self.assertIn("botmux start", commands)
            self.assertIn("botmux autostart enable", commands)
            self.assertIn("botmux status", commands)
            self.assertIn("botmux autostart status", commands)
            self.assertNotIn("traex", commands)
            self.assertNotIn("lark-cli", commands)
            self.assertNotIn("agentbuddy", commands)
            self.assertEqual(
                json.loads(status_path.read_text(encoding="utf-8"))["state"],
                "completed",
            )
            self.assertEqual(
                json.loads(status_path.read_text(encoding="utf-8"))["mode"],
                "repair",
            )
            self.assertFalse(lock_path.exists())
            self.assertFalse(script_path.exists())

    @unittest.skipUnless(sys.platform == "darwin", "requires /bin/zsh")
    def test_generated_bootstrap_script_has_valid_zsh_syntax(self):
        for mode in ("full", "repair"):
            with self.subTest(mode=mode):
                script = mac_byte_bootstrap.build_bootstrap_script(
                    mode,
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

    def test_setup_script_prepares_attention_before_botmux(self):
        script = mac_byte_bootstrap.build_bootstrap_script(
            "setup",
            script_path=Path("/tmp/bootstrap.command"),
            lock_path=Path("/tmp/bootstrap.lock"),
            status_path=Path("/tmp/bootstrap-status.json"),
        )
        attention = script.index("prepare_login_attention 'Botmux 机器人配置'")
        coach = script.index("--botmux-setup-coach")
        self.assertLess(attention, coach)
        self.assertNotIn("prepare_login_attention 'Trae CLI 登录'", script)

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

    @unittest.skipUnless(sys.platform == "darwin", "macOS bundle path test")
    def test_frozen_login_command_uses_console_helper(self):
        resources = Path("/Applications/Seele.app/Contents/Resources")
        with (
            patch.object(mac_byte_bootstrap.sys, "frozen", True, create=True),
            patch.object(
                mac_byte_bootstrap,
                "app_path",
                side_effect=lambda *parts: resources.joinpath(*parts),
            ),
        ):
            command = mac_byte_bootstrap._login_command(
                "traex",
                "login",
                "--sso-device",
            )

        self.assertIn(
            "/Applications/Seele.app/Contents/Resources/bin/SeeleBotmuxCoach",
            command,
        )
        self.assertIn("--login-command -- traex login --sso-device", command)

    @unittest.skipUnless(sys.platform == "darwin", "macOS bundle path test")
    def test_frozen_homebrew_install_uses_console_helper(self):
        resources = Path("/Applications/Seele.app/Contents/Resources")
        with (
            patch.object(mac_byte_bootstrap.sys, "frozen", True, create=True),
            patch.object(
                mac_byte_bootstrap,
                "app_path",
                side_effect=lambda *parts: resources.joinpath(*parts),
            ),
        ):
            command = mac_byte_bootstrap._homebrew_install_command()

        self.assertIn(
            "/Applications/Seele.app/Contents/Resources/bin/SeeleBotmuxCoach",
            command,
        )
        self.assertIn(
            "--homebrew-install -- /bin/bash -c \"$homebrew_installer\"",
            command,
        )

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
            self.assertEqual(status["mode"], "setup")

    def test_read_bootstrap_status_handles_missing_and_invalid_files(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            self.assertEqual(mac_byte_bootstrap.read_bootstrap_status(home), {})
            status = home / ".seele" / "mac_byte" / "bootstrap-status.json"
            status.write_text("not-json", encoding="utf-8")
            self.assertEqual(mac_byte_bootstrap.read_bootstrap_status(home), {})
            status.write_text('{"state":"failed","mode":"full"}', encoding="utf-8")
            self.assertEqual(
                mac_byte_bootstrap.read_bootstrap_status(home),
                {"state": "failed", "mode": "full"},
            )

    def test_close_terminal_window_targets_unique_bootstrap_script_title(self):
        completed = subprocess.CompletedProcess(
            ["/usr/bin/osascript", "-e", ""],
            0,
            stdout="closed\n",
            stderr="",
        )
        with (
            patch.object(mac_byte_bootstrap.sys, "platform", "darwin"),
            patch.object(
                mac_byte_bootstrap.subprocess,
                "run",
                return_value=completed,
            ) as run,
        ):
            closed = mac_byte_bootstrap.close_terminal_window_for_script(
                "/tmp/bootstrap-deadbeef.command"
            )

        self.assertTrue(closed)
        self.assertIn("bootstrap-deadbeef.command", run.call_args.args[0][2])

    def test_runtime_repair_preserves_existing_botmux_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            config = home / ".botmux" / "bots.json"
            config.parent.mkdir(parents=True)
            config.write_text('[{"larkAppId":"cli_test"}]', encoding="utf-8")
            with (
                patch.object(mac_byte_bootstrap, "is_mac_byte", return_value=True),
                patch.object(mac_byte_bootstrap.subprocess, "run") as run,
            ):
                run.return_value.returncode = 0
                run.return_value.stderr = ""
                script = mac_byte_bootstrap.launch_bootstrap(
                    mode="repair",
                    home=home,
                )

            contents = script.read_text(encoding="utf-8")
            self.assertIn("brew install tmux", contents)
            self.assertIn("跳过工具安装、登录和 botmux setup", contents)
            self.assertNotIn("prepare_login_attention 'Botmux 机器人配置'", contents)
            status = json.loads(
                (home / ".seele" / "mac_byte" / "bootstrap-status.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(status["mode"], "repair")


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


@unittest.skipUnless(
    sys.platform == "darwin" and importlib.util.find_spec("PyQt5") is not None,
    "macOS translucent rendering test requires PyQt5",
)
class MacByteRenderingTests(unittest.TestCase):
    def test_role_switch_window_size_scales_with_available_screen(self):
        import RoleSwitchWindow

        self.assertEqual(
            RoleSwitchWindow._responsive_window_size(
                1920,
                1080,
                preferred_width=640,
                preferred_height=460,
                minimum_width=360,
                minimum_height=300,
            ),
            (640, 460),
        )
        compact = RoleSwitchWindow._responsive_window_size(
            480,
            320,
            preferred_width=640,
            preferred_height=460,
            minimum_width=360,
            minimum_height=300,
        )
        self.assertLessEqual(compact[0], 480 - 32)
        self.assertLessEqual(compact[1], 320 - 32)

    def test_role_switch_window_reflows_and_closes_without_selection(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt5.QtWidgets import QApplication
        import RoleSwitchWindow

        app = QApplication.instance() or QApplication([])
        window = RoleSwitchWindow.main()
        window.show()
        app.processEvents()

        available = window.screen().availableGeometry()
        self.assertLessEqual(window.width(), available.width() - 32)
        self.assertLessEqual(window.height(), available.height() - 32)
        self.assertTrue(window.close_button.isVisible())
        self.assertEqual(window.close_button.toolTip(), "关闭")

        window.resize(700, 460)
        app.processEvents()
        self.assertFalse(window._buttons_vertical)
        horizontal_positions = [
            window.buttons_layout.getItemPosition(
                window.buttons_layout.indexOf(button)
            )
            for button in window._role_buttons
        ]
        self.assertEqual([position[0] for position in horizontal_positions], [0, 0, 0])

        window.resize(420, 360)
        app.processEvents()
        self.assertTrue(window._buttons_vertical)
        vertical_positions = [
            window.buttons_layout.getItemPosition(
                window.buttons_layout.indexOf(button)
            )
            for button in window._role_buttons
        ]
        self.assertEqual([position[1] for position in vertical_positions], [0, 0, 0])

        with patch.object(RoleSwitchWindow.wf, "write_dict_to_json") as write_state:
            window.close_button.click()
            app.processEvents()
        self.assertFalse(window.isVisible())
        write_state.assert_not_called()

    def test_movie_label_replaces_transparent_pixels_between_frames(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt5.QtCore import Qt
        from PyQt5.QtGui import QColor, QImage, QPainter, QPixmap
        from PyQt5.QtWidgets import QApplication
        import Seele

        app = QApplication.instance() or QApplication([])
        label = Seele._TransparentMovieLabel()
        label.resize(24, 24)

        first = QPixmap(24, 24)
        first.fill(Qt.transparent)
        painter = QPainter(first)
        painter.fillRect(0, 0, 10, 24, QColor(255, 0, 0, 255))
        painter.end()

        second = QPixmap(24, 24)
        second.fill(Qt.transparent)
        painter = QPainter(second)
        painter.fillRect(14, 0, 10, 24, QColor(0, 0, 255, 255))
        painter.end()

        surface = QImage(24, 24, QImage.Format_ARGB32_Premultiplied)
        surface.fill(Qt.transparent)
        label.setPixmap(first)
        label.render(surface)
        label.setPixmap(second)
        label.render(surface)
        app.processEvents()

        self.assertEqual(QColor.fromRgba(surface.pixel(2, 12)).alpha(), 0)
        self.assertGreater(QColor.fromRgba(surface.pixel(20, 12)).alpha(), 0)


if __name__ == "__main__":
    unittest.main()
