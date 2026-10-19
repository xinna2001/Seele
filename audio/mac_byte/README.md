# mac_byte 安装语音

所有语音均为 16 kHz、Int16、双声道 WAV。安装程序通过 macOS
`/usr/bin/afplay` 播放；固定阶段语音缺失时显示终端文字，PTY 动态语音缺失时
回退到 `/usr/bin/say`，均不阻断安装。

## 现有固定流程语音

| 文件名 | 触发时机 | 建议逐字播报文案 |
| --- | --- | --- |
| `mac_byte_install_16k.wav` | 开始安装 | 开始安装 Botmux 及字节内部依赖，请稍候。 |
| `mac_byte_homebrew_password_16k.wav` | Homebrew 输出 `Password:` | 安装 tmux 需要管理员权限。请输入这台电脑的开机密码，输入时屏幕不会显示字符，输入完成后按回车。 |
| `mac_byte_traex_login_16k.wav` | Trae CLI 等待登录 | 请使用字节账号完成 Trae CLI 登录。登录成功后无需返回终端操作，安装会自动继续。 |
| `mac_byte_lark_config_16k.wav` | Lark CLI 等待应用初始化 | 请使用飞书扫描二维码，并在网页完成飞书 CLI 应用初始化。完成后安装会自动继续。 |
| `mac_byte_lark_login_16k.wav` | Lark CLI 等待用户授权 | 请完成飞书 CLI 权限授权。授权成功后无需返回终端操作，安装会自动继续。 |
| `mac_byte_agentbuddy_login_16k.wav` | AgentBuddy 等待登录 | 请打开终端中的登录链接，输入验证码并完成 Skill 空间登录。登录成功后安装会自动继续。 |
| `mac_byte_botmux_setup_16k.wav` | 进入 Botmux 原生配置 | 现在开始配置 Botmux。后续每出现一个选项，希儿都会告诉你该怎么操作。 |

## Homebrew 自动确认

管理员密码只由用户直接输入，PTY helper 不读取、不保存也不代填。Homebrew 官方安装器
输出 `Press RETURN/ENTER to continue or any other key to abort:` 时，程序自动按回车；
出现明确的 `[Y/n]` 或 `[y/N]` 提示时自动输入 `y`。这里不能给官方的
`RETURN/ENTER` 提示输入 `Y`，否则安装器会按“任意其他键”中止。

## Botmux 正常路径动态语音

Botmux 保留需要用户决定的原生交互，希儿根据当前提示播放说明，不会替用户回答。
飞书应用来源、失效登录态重新扫码、失败后返回应用来源、飞书中国版租户、CLI
适配器和工作目录均由程序按提示文字选择默认项，不依赖可能随版本变化的菜单序号。

| 文件名 | Botmux 触发提示 | 建议逐字播报文案 |
| --- | --- | --- |
| `mac_byte_botmux_name_16k.wav` | `机器人名称 [botmux-N]:` | 请为你的机器人取一个想要的名字。输入后按回车 |
| `mac_byte_botmux_account_16k.wav` | `确认飞书账号` | 请确认屏幕显示的飞书账号是不是你自己的账号。正确请选择“确认并免扫码添加”；不正确请选择“更换账号”。 |
| `mac_byte_botmux_scan_16k.wav` | 显示飞书登录二维码 | 请打开飞书，扫描终端中的二维码，并确认当前账号和企业正确。 |
| `mac_byte_botmux_owner_16k.wav` | `管理员 (owner):` | 请输入你自己的完整字节邮箱，不要只输入邮箱前缀，输入后按回车。 |

已安装 Homebrew 的正常首次安装包含 6 个用户交互点：

1. Trae CLI 登录。
2. Lark CLI 应用初始化。
3. Lark CLI 用户授权。
4. AgentBuddy 登录。
5. 输入机器人名称。
6. 扫描 Botmux 飞书二维码，或确认本机缓存的飞书账号。

全新 Mac 还会增加一次管理员密码输入。如果 Botmux 无法从扫码账号自动确认管理员，
还会增加一次管理员邮箱输入。

## Botmux 异常或高级分支动态语音

这些文件不会在正常首次安装中播放，但应随安装包提供，避免用户选择已有应用、
手动凭证或进入失败回退分支时失去指导。

| 文件名 | Botmux 触发提示 | 建议逐字播报文案 |
| --- | --- | --- |
| `mac_byte_botmux_existing_app_16k.wav` | `选择已有应用` | 请选择你要绑定的已有飞书应用。 |
| `mac_byte_botmux_app_id_16k.wav` | `AppID (cli_xxx):` | 请输入已有飞书应用的 App ID，格式通常以 cli 下划线开头。 |
| `mac_byte_botmux_app_secret_16k.wav` | `AppSecret:` 或要求手动粘贴 AppSecret | 请输入同一个飞书应用的 App Secret。请不要把密钥发送给他人。 |

应用来源、重新扫码、兼容模式返回和中国飞书租户的 4 个旧语音文件继续保留在资源包中，
但当前版本会直接自动选择，不再播放要求用户操作的提示。

## 文件数量

- 固定流程语音：7 个，其中 1 个是 Homebrew 管理员密码提醒。
- Botmux 当前用户交互动态语音：7 个。
- 已自动化选项的兼容语音：4 个。
- 完整语音包：18 个 WAV 文件。

18 个 WAV 文件均已提供。当前使用的文件名必须与 `mac_byte_bootstrap.py` 和
`botmux_setup_coach.py` 中的映射保持一致；4 个兼容语音保留原文件名。
