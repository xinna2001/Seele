import errno
import io
import os
import sys
import unittest
from unittest.mock import patch

import botmux_setup_coach


class PromptCoachTests(unittest.TestCase):
    def test_write_all_retries_when_terminal_output_is_temporarily_blocked(self):
        writes = []

        def fake_write(_fd, data):
            if not writes:
                writes.append(b"blocked")
                raise BlockingIOError(errno.EAGAIN, "temporarily unavailable")
            writes.append(bytes(data))
            return len(data)

        with (
            patch.object(botmux_setup_coach.os, "write", side_effect=fake_write),
            patch.object(
                botmux_setup_coach.select,
                "select",
                return_value=([], [7], []),
            ) as wait_for_fd,
        ):
            botmux_setup_coach._write_all(7, b"qr-output")

        self.assertEqual(writes, [b"blocked", b"qr-output"])
        wait_for_fd.assert_called_once()

    def test_login_url_coach_opens_split_json_url_once(self):
        opened = []
        coach = botmux_setup_coach.LoginUrlCoach(
            lambda url: opened.append(url) or True
        )

        coach.feed(b'{"login_url":"https:\\/\\/skills.bytedance.')
        coach.feed(b'net\\/auth?session=abc&region=cn"}\n')
        coach.feed(b'https://skills.bytedance.net/auth?session=another\n')

        self.assertEqual(
            opened,
            ["https://skills.bytedance.net/auth?session=abc&region=cn"],
        )

    def test_login_url_coach_rejects_non_https_and_credentials(self):
        opened = []
        coach = botmux_setup_coach.LoginUrlCoach(
            lambda url: opened.append(url) or True
        )

        coach.feed(b"http://example.com https://user:pass@example.com/path\n")

        self.assertEqual(opened, [])

    def test_login_url_coach_focuses_terminal_only_after_timeout(self):
        now = [10.0]
        fallbacks = []
        coach = botmux_setup_coach.LoginUrlCoach(
            lambda _url: True,
            fallback=lambda: fallbacks.append("shown") or True,
            fallback_seconds=5.0,
            clock=lambda: now[0],
        )

        now[0] = 14.9
        coach.tick()
        self.assertEqual(fallbacks, [])
        now[0] = 15.0
        coach.tick()
        coach.tick()
        self.assertEqual(fallbacks, ["shown"])

    def test_login_url_prevents_terminal_fallback(self):
        now = [10.0]
        opened = []
        fallbacks = []
        coach = botmux_setup_coach.LoginUrlCoach(
            lambda url: opened.append(url) or True,
            fallback=lambda: fallbacks.append("shown") or True,
            fallback_seconds=5.0,
            clock=lambda: now[0],
        )

        coach.feed(b"https://example.com/login\n")
        now[0] = 20.0
        coach.tick()
        coach.finish(0)

        self.assertEqual(opened, ["https://example.com/login"])
        self.assertEqual(fallbacks, [])

    def test_failed_login_command_focuses_terminal_immediately(self):
        fallbacks = []
        coach = botmux_setup_coach.LoginUrlCoach(
            lambda _url: True,
            fallback=lambda: fallbacks.append("shown") or True,
            fallback_seconds=5.0,
        )

        coach.finish(1)
        coach.finish(1)

        self.assertEqual(fallbacks, ["shown"])

    def test_terminal_fallback_preserves_current_qr_output(self):
        succeeded = type("Completed", (), {"returncode": 0})
        output = io.StringIO()
        with (
            patch.object(botmux_setup_coach.sys, "stdout", output),
            patch.object(
                botmux_setup_coach.subprocess,
                "run",
                return_value=succeeded(),
            ) as run,
        ):
            self.assertTrue(botmux_setup_coach.focus_terminal_for_login())

        self.assertNotIn("\033[2J", output.getvalue())
        self.assertIn("请在当前终端继续操作", output.getvalue())
        self.assertIn("Terminal", run.call_args.args[0][-1])

    def test_browser_open_prefers_google_chrome_then_default(self):
        completed = type("Completed", (), {"returncode": 1})
        succeeded = type("Completed", (), {"returncode": 0})
        with patch.object(
            botmux_setup_coach.subprocess,
            "run",
            side_effect=[completed(), succeeded()],
        ) as run:
            self.assertTrue(
                botmux_setup_coach.open_login_url("https://example.com/login")
            )

        self.assertEqual(
            run.call_args_list[0].args[0],
            [
                "/usr/bin/open",
                "-a",
                "Google Chrome",
                "https://example.com/login",
            ],
        )
        self.assertEqual(
            run.call_args_list[1].args[0],
            ["/usr/bin/open", "https://example.com/login"],
        )

    def test_voice_cues_are_deduplicated_and_do_not_answer_for_user(self):
        cues = []
        coach = botmux_setup_coach.PromptCoach(lambda cue: cues.append(cue.key))

        self.assertEqual(
            coach.feed(" 飞书应用来源\n".encode()),
            [],
        )
        self.assertEqual(coach.feed(" 飞书应用来源\n".encode()), [])
        self.assertEqual(coach.feed("请用飞书 App 扫码登录".encode()), [])
        self.assertEqual(cues, ["app_source", "scan"])

    def test_fixed_choices_follow_prompt_text_instead_of_menu_positions(self):
        coach = botmux_setup_coach.PromptCoach()

        self.assertEqual(
            coach.feed(" 选择 CLI 适配器\n 输入可搜索\n".encode()),
            [b"TRAE\r"],
        )
        self.assertEqual(
            coach.feed(
                " 选择 CLI 适配器 › TRAE (CoCo)\n 输入可搜索\n".encode()
            ),
            [b"traex\r"],
        )
        self.assertEqual(
            coach.feed(" 新话题工作目录\n 输入可搜索\n".encode()),
            [b"\r"],
        )
        self.assertEqual(
            coach.feed(
                "默认工作目录（新话题直接在此目录启动）[~]: ".encode()
            ),
            [b"\r"],
        )

    def test_existing_app_cue_does_not_fire_for_source_menu_item(self):
        cues = []
        coach = botmux_setup_coach.PromptCoach(lambda cue: cues.append(cue.key))

        coach.feed(
            (
                " 飞书应用来源\n"
                " 一次扫码创建新应用\n"
                " 选择已有应用  飞书 Web 登录列出应用\n"
            ).encode()
        )
        self.assertEqual(cues, ["app_source"])
        coach.feed("\n 选择已有应用\n 输入可搜索\n".encode())
        self.assertEqual(cues, ["app_source", "existing_app"])


@unittest.skipUnless(os.name == "posix", "PTY integration requires POSIX")
class PtyCoachTests(unittest.TestCase):
    def test_child_output_reaches_coach_before_terminal_write(self):
        import pty

        class RecordingCoach:
            def __init__(self):
                self.seen = []

            def feed(self, data):
                self.seen.append(data)
                return []

        input_master, input_slave = pty.openpty()
        output_read, output_write = os.pipe()
        self.addCleanup(os.close, input_master)
        self.addCleanup(os.close, input_slave)
        self.addCleanup(os.close, output_read)
        self.addCleanup(os.close, output_write)
        coach = RecordingCoach()

        with patch.object(
            botmux_setup_coach,
            "_write_all",
            side_effect=TimeoutError("blocked output"),
        ):
            with self.assertRaises(TimeoutError):
                botmux_setup_coach.run_coached_command(
                    [
                        sys.executable,
                        "-c",
                        "import sys; sys.stdout.write('https://example.com/login\\n'); sys.stdout.flush()",
                    ],
                    coach=coach,
                    stdin_fd=input_slave,
                    stdout_fd=output_write,
                )

        self.assertIn(b"https://example.com/login", b"".join(coach.seen))

    def test_fake_child_receives_only_fixed_automatic_answers(self):
        import pty

        child_script = r"""
import sys

def ask(screen):
    sys.stdout.write(screen)
    sys.stdout.flush()
    return sys.stdin.readline().strip()

top = ask("\x1b[1m 选择 CLI 适配器\x1b[0m\n 输入可搜索\n")
sub = ask("\x1b[1m 选择 CLI 适配器 › TRAE (CoCo)\x1b[0m\n 输入可搜索\n")
mode = ask("\x1b[1m 新话题工作目录\x1b[0m\n 输入可搜索\n")
directory = ask("默认工作目录（新话题直接在此目录启动）[~]: ")
print(f"RESULT={top}|{sub}|{mode}|{directory}")
"""
        input_master, input_slave = pty.openpty()
        output_read, output_write = os.pipe()
        self.addCleanup(os.close, input_master)
        self.addCleanup(os.close, input_slave)
        self.addCleanup(os.close, output_read)

        code = botmux_setup_coach.run_coached_command(
            [sys.executable, "-c", child_script],
            coach=botmux_setup_coach.PromptCoach(),
            stdin_fd=input_slave,
            stdout_fd=output_write,
        )
        os.close(output_write)
        output = os.read(output_read, 65536).decode("utf-8", errors="replace")

        self.assertEqual(code, 0)
        self.assertIn("RESULT=TRAE|traex||", output)


if __name__ == "__main__":
    unittest.main()
