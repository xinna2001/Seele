# mac_byte 安装语音

安装流程使用以下 16 kHz WAV 文件：

- `mac_byte_install_16k.wav`：检测到未安装 Botmux，准备执行安装。
- `mac_byte_traex_login_16k.wav`：提醒用户完成 Trae CLI 登录。
- `mac_byte_lark_config_16k.wav`：提醒用户初始化飞书 CLI 应用。
- `mac_byte_lark_login_16k.wav`：提醒用户完成飞书 CLI 授权。
- `mac_byte_agentbuddy_login_16k.wav`：提醒用户登录 Skill 空间。
- `mac_byte_botmux_setup_16k.wav`：提醒用户扫描二维码并配置 Botmux。

文件名必须与 `mac_byte_bootstrap.py` 中的 `VOICE_FILES` 保持一致。
音频不存在或播放失败时不会阻断安装；终端会继续显示对应的文字提示。
