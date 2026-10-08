# mac_byte 安装语音

所有语音均为 16 kHz、Int16、双声道 WAV。安装程序通过 macOS
`/usr/bin/afplay` 播放；固定阶段语音缺失时显示终端文字，Botmux 动态语音缺失时
回退到 `/usr/bin/say`，均不阻断安装。

## 现有固定流程语音

| 文件名 | 触发时机 | 建议逐字播报文案 |
| --- | --- | --- |
| `mac_byte_install_16k.wav` | 开始安装 | 开始安装 Botmux 及字节内部依赖，请稍候。 |
| `mac_byte_traex_login_16k.wav` | Trae CLI 等待登录 | 请使用字节账号完成 Trae CLI 登录。登录成功后无需返回终端操作，安装会自动继续。 |
| `mac_byte_lark_config_16k.wav` | Lark CLI 等待应用初始化 | 请使用飞书扫描二维码，并在网页完成飞书 CLI 应用初始化。完成后安装会自动继续。 |
| `mac_byte_lark_login_16k.wav` | Lark CLI 等待用户授权 | 请完成飞书 CLI 权限授权。授权成功后无需返回终端操作，安装会自动继续。 |
| `mac_byte_agentbuddy_login_16k.wav` | AgentBuddy 等待登录 | 请打开终端中的登录链接，输入验证码并完成 Skill 空间登录。登录成功后安装会自动继续。 |
| `mac_byte_botmux_setup_16k.wav` | 进入 Botmux 原生配置 | 现在开始配置 Botmux。后续每出现一个选项，希儿都会告诉你该怎么操作。 |

## Botmux 正常路径动态语音

Botmux 保留需要用户决定的原生交互，希儿根据当前提示播放说明，不会替用户回答。
固定的 CLI 适配器步骤由程序按菜单文字自动选择 `TRAE (CoCo) -> traex`，不依赖
可能随版本变化的菜单序号。工作目录模式、默认工作目录和仓库扫描根目录均自动按
回车使用 Botmux 默认值，不要求用户操作。

| 文件名 | Botmux 触发提示 | 建议逐字播报文案 |
| --- | --- | --- |
| `mac_byte_botmux_app_source_16k.wav` | `飞书应用来源` | 请选择飞书应用来源。建议选择“一次扫码创建新应用”。 |
| `mac_byte_botmux_name_16k.wav` | `机器人名称 [botmux-N]:` | 请为你的机器人取一个想要的名字。输入后按回车 |
| `mac_byte_botmux_account_16k.wav` | `确认飞书账号` | 请确认屏幕显示的飞书账号是不是你自己的账号。正确请选择“确认并免扫码添加”；不正确请选择“更换账号”。 |
| `mac_byte_botmux_scan_16k.wav` | 显示飞书登录二维码 | 请打开飞书，扫描终端中的二维码，并确认当前账号和企业正确。 |
| `mac_byte_botmux_owner_16k.wav` | `管理员 (owner):` | 请输入你自己的完整字节邮箱，不要只输入邮箱前缀，输入后按回车。 |

正常首次安装包含 7 个用户交互点：

1. Trae CLI 登录。
2. Lark CLI 应用初始化。
3. Lark CLI 用户授权。
4. AgentBuddy 登录。
5. 选择飞书应用来源。
6. 输入机器人名称。
7. 扫描 Botmux 飞书二维码。

CLI 适配器由程序自动选择 `traex`，不需要用户操作或语音提示。
工作目录模式和目录输入由程序直接按回车使用默认值，也不需要语音提示。
如果 Botmux 无法从扫码账号自动确认管理员，还会出现第 8 个交互：输入管理员。
如果本机已有可复用的飞书登录态，“扫描二维码”会替换为“确认飞书账号”，交互总数
仍为 7 个。

## Botmux 异常或高级分支动态语音

这些文件不会在正常首次安装中播放，但应随安装包提供，避免用户选择已有应用、
手动凭证或进入失败回退分支时失去指导。

| 文件名 | Botmux 触发提示 | 建议逐字播报文案 |
| --- | --- | --- |
| `mac_byte_botmux_relogin_16k.wav` | `上次飞书登录态已失效或无法确认账号` | 上次的飞书登录状态已经失效，请选择“重新扫码”。 |
| `mac_byte_botmux_existing_app_16k.wav` | `选择已有应用` | 请选择你要绑定的已有飞书应用。 |
| `mac_byte_botmux_compatibility_16k.wav` | `是否使用兼容模式？` | 自动创建应用失败。建议先选择“返回应用来源”并重试；只有普通方式持续失败时，再选择兼容模式。 |
| `mac_byte_botmux_tenant_16k.wav` | `租户类型` | 请选择租户类型。字节员工请选择“飞书中国版”。 |
| `mac_byte_botmux_app_id_16k.wav` | `AppID (cli_xxx):` | 请输入已有飞书应用的 App ID，格式通常以 cli 下划线开头。 |
| `mac_byte_botmux_app_secret_16k.wav` | `AppSecret:` 或要求手动粘贴 AppSecret | 请输入同一个飞书应用的 App Secret。请不要把密钥发送给他人。 |

## 文件数量

- 现有固定流程语音：6 个，其中 4 个需要用户登录或授权。
- Botmux 正常路径新增动态语音：5 个。
- Botmux 异常或高级分支新增动态语音：6 个。
- 完整语音包：17 个 WAV 文件。

17 个 WAV 文件均已提供。文件名必须与 `mac_byte_bootstrap.py` 和
`botmux_setup_coach.py` 中的映射保持一致。
