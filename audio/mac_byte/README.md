# mac_byte 语音占位符

将最终语音文件放在本目录，并保持以下文件名：

- `mac_byte_install.wav`：检测到未安装 Botmux，准备执行安装。
- `mac_byte_traex_login.wav`：提醒用户完成 Trae CLI 登录。
- `mac_byte_lark_config.wav`：提醒用户初始化飞书 CLI 应用。
- `mac_byte_lark_login.wav`：提醒用户完成飞书 CLI 授权。
- `mac_byte_agentbuddy_login.wav`：提醒用户登录 Skill 空间。
- `mac_byte_botmux_setup.wav`：提醒用户扫描二维码并配置 Botmux。

音频不存在时，安装终端会输出 `[语音占位符]` 文本，不会阻断安装。
