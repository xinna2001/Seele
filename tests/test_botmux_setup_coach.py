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

    def test_user_decision_voice_cues_are_deduplicated(self):
        cues = []
        coach = botmux_setup_coach.PromptCoach(lambda cue: cues.append(cue.key))

        self.assertEqual(coach.feed("机器人名称 [botmux-1]: ".encode()), [])
        self.assertEqual(coach.feed("机器人名称 [botmux-1]: ".encode()), [])
        self.assertEqual(coach.feed("请用飞书 App 扫码登录".encode()), [])
        self.assertEqual(cues, ["name", "scan"])

    def test_homebrew_coach_voices_password_and_accepts_known_prompts(self):
        cues = []
        coach = botmux_setup_coach.HomebrewInstallCoach(
            lambda cue: cues.append(cue.key)
        )

        self.assertEqual(coach.feed(b"Pass"), [])
        self.assertEqual(coach.feed(b"word:"), [])
        self.assertEqual(cues, ["homebrew_password"])
        self.assertEqual(
            coach.feed(
                b"\nPress RETURN/ENTER to continue or any other key to abort:"
            ),
            [b"\r"],
        )
        self.assertEqual(
            coach.feed(b"\nContinue installation? [Y/n] "),
            [b"Y\r"],
        )
        self.assertEqual(coach.feed(b" "), [])
        self.assertEqual(coach.feed(b"\nContinue installation? [Y/n] "), [b"Y\r"])

    def test_homebrew_screenshot_prompt_handles_split_ansi_and_repetitions(self):
        prompt = b"\n\x1b[1m==> Do you want to proceed with the installation? [y/n]\x1b[0m "
        coach = botmux_setup_coach.HomebrewInstallCoach()
        for _ in range(2):
            actions = []
            for byte in prompt:
                actions.extend(coach.feed(bytes([byte])))
            self.assertEqual(actions, [b"Y\r"])
        self.assertEqual(coach.feed(b"\ninstallation complete\n"), [])

    def test_homebrew_installation_confirmation_accepts_all_yes_no_capitalizations(self):
        for choices in ("y/n", "Y/n", "y/N", "Y/N"):
            with self.subTest(choices=choices):
                coach = botmux_setup_coach.HomebrewInstallCoach()
                self.assertEqual(
                    coach.feed(f"==> Do you want to proceed with the installation? [{choices}] ".encode()),
                    [b"Y\r"],
                )

    def test_homebrew_coach_does_not_answer_unknown_questions(self):
        coach = botmux_setup_coach.HomebrewInstallCoach()

        self.assertEqual(coach.feed(b"Continue installation? (yes/no): "), [])
        self.assertEqual(coach.feed(b"Delete existing files? [yes/no]: "), [])
        self.assertEqual(coach.feed(b"\nDelete existing files? [y/n]: "), [])
        self.assertEqual(coach.feed(b"\nSend credentials? [Y/n]: "), [])

    def test_fixed_choices_follow_prompt_text_instead_of_menu_positions(self):
        coach = botmux_setup_coach.PromptCoach()

        self.assertEqual(
            coach.feed(
                (
                    " 飞书应用来源\n"
                    " 一次扫码创建新应用（推荐）\n"
                    " 输入可搜索\n"
                ).encode()
            ),
            [b"\r"],
        )
        self.assertEqual(
            coach.feed(
                (
                    " 上次飞书登录态已失效或无法确认账号\n"
                    " 重新扫码\n"
                    " 输入可搜索\n"
                ).encode()
            ),
            [b"\r"],
        )
        self.assertEqual(
            coach.feed(
                (
                    " 是否使用兼容模式？\n"
                    " 返回应用来源\n"
                    " 输入可搜索\n"
                ).encode()
            ),
            [b"\r"],
        )
        self.assertEqual(
            coach.feed(
                " 租户类型\n 飞书（中国版）\n 输入可搜索\n".encode()
            ),
            [b"\r"],
        )
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

    def test_prompt_coach_leaves_identity_and_secrets_to_user(self):
        coach = botmux_setup_coach.PromptCoach()

        for prompt in (
            "机器人名称 [botmux-1]: ",
            "确认飞书账号：张三 · 字节跳动\n 输入可搜索\n",
            "管理员 (owner): ",
            "AppID (cli_xxx): ",
            "AppSecret: ",
        ):
            with self.subTest(prompt=prompt):
                self.assertEqual(coach.feed(prompt.encode()), [])

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
        self.assertEqual(cues, [])
        coach.feed("\n 选择已有应用\n 输入可搜索\n".encode())
        self.assertEqual(cues, ["existing_app"])


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

source = ask("\x1b[1m 飞书应用来源\x1b[0m\n 一次扫码创建新应用（推荐）\n 输入可搜索\n")
relogin = ask("\x1b[1m 上次飞书登录态已失效或无法确认账号\x1b[0m\n 重新扫码\n 输入可搜索\n")
compatibility = ask("\x1b[1m 是否使用兼容模式？\x1b[0m\n 返回应用来源\n 输入可搜索\n")
tenant = ask("\x1b[1m 租户类型\x1b[0m\n 飞书（中国版）\n 输入可搜索\n")
top = ask("\x1b[1m 选择 CLI 适配器\x1b[0m\n 输入可搜索\n")
sub = ask("\x1b[1m 选择 CLI 适配器 › TRAE (CoCo)\x1b[0m\n 输入可搜索\n")
mode = ask("\x1b[1m 新话题工作目录\x1b[0m\n 输入可搜索\n")
directory = ask("默认工作目录（新话题直接在此目录启动）[~]: ")
print(f"RESULT={source}|{relogin}|{compatibility}|{tenant}|{top}|{sub}|{mode}|{directory}")
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
        self.assertIn("RESULT=||||TRAE|traex||", output)

    def test_homebrew_child_receives_only_known_confirmations(self):
        import pty

        child_script = r"""
import signal
import sys
signal.alarm(5)

def ask(screen):
    sys.stdout.write(screen)
    sys.stdout.flush()
    return sys.stdin.readline().strip()

enter = ask("Press RETURN/ENTER to continue or any other key to abort:")
yes = ask("\x1b[1m==> Do you want to proceed with the installation? [y/n]\x1b[0m ")
again = ask("\n==> Do you want to proceed with the installation? [y/n] ")
print(f"RESULT={enter}|{yes}|{again}")
"""
        input_master, input_slave = pty.openpty()
        output_read, output_write = os.pipe()
        self.addCleanup(os.close, input_master)
        self.addCleanup(os.close, input_slave)
        self.addCleanup(os.close, output_read)

        code = botmux_setup_coach.run_coached_command(
            [sys.executable, "-c", child_script],
            coach=botmux_setup_coach.HomebrewInstallCoach(),
            stdin_fd=input_slave,
            stdout_fd=output_write,
        )
        os.close(output_write)
        output = os.read(output_read, 65536).decode("utf-8", errors="replace")

        self.assertEqual(code, 0)
        self.assertIn("RESULT=|Y|Y", output)


if __name__ == "__main__":
    unittest.main()
