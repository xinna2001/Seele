import os
import sys
import unittest

import botmux_setup_coach


class PromptCoachTests(unittest.TestCase):
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
