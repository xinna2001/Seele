import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import botmux_client
import falseIntent
import rpa_bridge
import rpa_service


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


if __name__ == "__main__":
    unittest.main()
