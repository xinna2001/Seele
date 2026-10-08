# mac_byte 低感知安装与配置调研

本文评估 Seele `mac_byte` 当前安装链路中的 Node/NVM、Trae CLI、Lark CLI、
AgentBuddy、Botmux 和 Seele 插件，目标是让用户只处理必须由本人完成的扫码、
SSO 或授权，其余安装和配置自动完成。

## 一、结论

技术上可行，但准确目标应是“低感知安装”，不是完全无人值守：

- 安装、固定选项、配置写入、状态检测、失败续跑可以全部自动化；
- SSO、二维码、OAuth 授权和 macOS 系统安全确认必须由用户本人完成；
- 各服务使用不同认证体系，不能可靠合并成一个二维码；
- 前三项工具使用官方脚本化接口；Botmux 原生 setup 通过 PTY 按真实提示协作；
- `/usr/bin/expect` 只应作为版本锁定后的末级兼容方案，默认不使用。

预计用户只会看到按顺序出现的登录或授权页面。每次完成后，Seele 自动验证并
进入下一阶段，不再要求用户回到 Terminal 按回车。

## 二、验证环境

本次核查的本机版本：

| 工具 | 版本 |
| --- | --- |
| Trae CLI | `0.207.1` internal edition |
| Lark CLI | `1.0.94`，检测到可更新至 `1.0.97` |
| AgentBuddy | `1.5.7` |
| Botmux | `3.34.0` |
| Node.js | `24.16.0` |

验证使用独立的临时 `HOME`、`XDG_CONFIG_HOME`、`XDG_DATA_HOME`、
`XDG_CACHE_HOME`、`TRAE_HOME` 和 `AGENTBUDDY_DIR`。没有读取或覆盖当前用户
配置；认证等待超时后主动中止，临时目录已物理删除。

## 三、逐项结论

### 1. NVM、Node.js 和 npm

自动化程度：完全自动。

- NVM 安装脚本支持通过环境变量指定 `NVM_DIR` 和 shell profile；
- `nvm install --lts`、`nvm use --lts` 无需交互；
- npm 全局安装无需交互；
- 不应再执行全局 `npm config set registry`，应给每条内部包安装命令单独传
  `--registry https://bnpm.byted.org/`，避免永久修改用户环境。

### 2. Trae CLI 安装

自动化程度：完全自动。

官方安装脚本支持：

```bash
curl -fsSL https://code.byted.org/api/tos-proxy/download/traex_install.sh |
  env \
    TRAEX_INSTALL_ASSUME_YES=1 \
    TRAEX_INSTALL_REMOVE_COCO=1 \
    TRAEX_INSTALL_REMOVE_BREW=0 \
    sh
```

含义：

- 自动确认升级或重新安装；
- 自动把安装目录加入 shell profile；
- 自动删除旧 Coco/Trae 命令文件，但保留用户数据；
- 默认不卸载 Homebrew 版本，避免未经确认执行破坏性操作。

安装脚本直接读取 `/dev/tty`，因此 `yes | installer` 无法可靠回答提示。

### 3. Trae CLI 登录与首次配置

自动化程度：除用户扫码外全部自动。

不要启动裸 `traex` TUI。改用明确命令：

```bash
traex backend cn
traex login --sso-device
traex login status
```

隔离验证结果：

- `traex backend cn` 无提示完成；
- `traex login --sso-device` 只显示 ByteCloud 二维码、URL 和用户码；
- 用户完成授权前命令保持等待；
- 未登录时 `traex login status` 输出 `Not logged in`，退出码为 `1`；
- 登录后可通过退出码 `0` 自动继续；
- feature、MCP、plugin 均有官方子命令，可按产品预设配置；
- `-c key=value` 可覆盖 TOML 配置，`features enable/disable` 可持久化功能开关。

因此，登录后的首次 TUI 选项可以完全绕过，不需要自动按方向键或回车。

### 4. Lark CLI 应用配置

自动化程度：除用户扫码/网页确认外全部自动。

应用初始化：

```bash
lark-cli config init --new --lang zh_cn --name seele
```

隔离验证结果：

- 命令直接输出二维码和应用配置 URL；
- 没有额外 Terminal 选项；
- 用户在网页完成应用配置前命令保持等待；
- 未配置时 `auth status --json --verify` 返回结构化错误：
  `type=config`、`subtype=not_configured`，退出码为 `3`。

对 Lark CLI `1.0.97` 源码的补充核查：

- `config init --new` 会创建 discovery device code，默认每 5 秒轮询一次，整体有效期
  默认 600 秒；
- 网页显示创建成功不等于 CLI 已收到完整的 App ID/App Secret，也不等于本机配置
  已落盘；
- 只有命令结束后再执行 `lark-cli config show` 成功，才能判定初始化真正完成；
- 当前版本没有可用于 `config init` 的 `--no-wait` 或 `--device-code` 恢复参数；
- 自动再次执行 `config init --new` 会创建新的 device code，可能重复创建应用，不能
  作为无条件重试方案。

已有 App ID/App Secret 时可以完全非交互初始化：

```bash
printf '%s' "$APP_SECRET" |
  lark-cli config init \
    --app-id "$APP_ID" \
    --app-secret-stdin \
    --brand feishu \
    --lang zh_cn \
    --name seele
```

密钥必须通过 stdin 或系统安全存储传递，不能写进命令行、日志或仓库。

### 5. Lark CLI 用户授权

自动化程度：除用户授权外全部自动。

推荐 split-flow：

```bash
lark-cli auth login --recommend --no-wait --json
lark-cli auth qrcode "<verification_url>" --output "<png_path>"
lark-cli auth login --device-code "<device_code>"
lark-cli auth status --json --verify
```

第一条命令立即返回 URL 和 device code；Seele 可以展示二维码并播放语音。
用户授权后，程序使用 device code 完成轮询并验证 `ok == true`。

需要提前确定的产品安全策略：

- 是否请求全部推荐 scope，还是只请求 docs/drive 等最小业务域；
- 默认身份是 `user`、`bot` 还是 `auto`；
- 是否启用 strict mode。

这些属于权限选择，应在 Seele 首次安装说明中一次性告知用户，不能静默扩大权限。

### 6. AgentBuddy

自动化程度：除用户打开链接并授权外全部自动。

推荐命令：

```bash
agentbuddy login \
  --region cn \
  --login-mode device \
  --json \
  --yes

agentbuddy status --json
agentbuddy whoami
```

隔离验证结果：

- 登录命令直接输出授权 URL 和验证码；
- 没有额外配置选项；
- 用户授权前命令保持等待；
- 未登录时 `status --json` 返回
  `{"logged_in":false,"reason":"no_valid_credentials"}`，退出码为 `1`。

### 7. Botmux

自动化程度：保留用户决策，固定选项自动完成。

产品要求保留原生 `botmux setup`，让用户自行选择应用来源、机器人名称、飞书账号
和管理员。Seele 在伪终端中透明代理该命令：

- stdin/stdout 原样转发，不读取或保存用户输入；
- Botmux 自己等待扫码、创建应用并校验凭证；
- Seele 只监听清理 ANSI 控制符后的输出；
- 出现具体交互提示时播放对应 WAV；
- 仅在精确出现 `选择 CLI 适配器` 时自动筛选 `TRAE (CoCo) -> traex`；
- 仅在精确出现工作目录提示时自动回车接受默认值；
- 扫码未完成或失败时不会出现下一步提示，因此不会误发按键；
- 未知提示保持人工交互，不进行猜测。

脚本化 `botmux setup add --cli traecli` 仍可用于已经明确全部字段的无人值守环境，
但不适合本产品需要用户现场命名和确认管理员的首次安装体验。

### 8. Seele Botmux 插件与启动

自动化程度：完全自动。

```bash
botmux plugin install "<APP_RESOURCES>/botmux-skill" --link
botmux plugin enable seele
botmux lang zh
botmux skills injection prompt
botmux start
botmux autostart enable
```

每条命令执行后应增加状态读回，不应只判断命令已提交。

## 四、用户仍需完成的操作

在不复用或窃取凭据的前提下，首次安装最多需要以下独立认证：

1. Trae CLI / ByteCloud SSO；
2. Lark CLI 应用创建或绑定；
3. Lark CLI 用户 OAuth 授权；
4. AgentBuddy Skill 空间登录；
5. Botmux 飞书开放平台配置登录。

这些认证属于不同客户端和权限域，无法安全合并成一个二维码。浏览器已有飞书登录态
时，部分步骤可能只需点击确认，但仍必须由用户本人完成。

## 五、已实现的编排

`v2.1.0` 使用前台 Zsh 安装编排与 Python PTY 教练组合，每个阶段遵循：

```text
check -> run -> wait_for_user -> verify -> checkpoint
```

当前阶段：

```text
preflight
node_install
traex_install
traex_login
traex_config
lark_app_config
lark_user_auth
agentbuddy_login
botmux_app_config
seele_plugin
botmux_start
final_verify
done
```

要求：

- Node.js、npm、Trae CLI、Lark CLI、AgentBuddy 和 Botmux 分别检测，已存在的命令
  不重复安装；
- 已登录阶段通过官方 status 命令跳过；
- 运行状态写入 `~/.seele/mac_byte/bootstrap-status.json`；
- 用户授权阶段由 Seele 播放语音、显示二维码并自动等待；
- 成功后自动进入下一步，不要求用户按回车；
- 失败时写入退出码并清理安装锁，可重新启动；
- Lark CLI 应用初始化每轮只发起一次，命令结束后独立检查本地配置；未落盘时停止，
  不在同一轮生成第二个 device code；
- 所有凭据交给官方 CLI 或系统 Keychain 保存，Seele 不读取明文 token；
- Botmux 版本和提示变化时不匹配就不自动发送按键。

## 六、expect 的使用边界

当前核心流程不需要 `expect`。

只有同时满足以下条件时才允许使用：

- 工具没有官方 flag、子命令、配置文件或 JSON 接口；
- 提示文字和工具版本已锁定；
- 只匹配明确完整的 prompt；
- 设置超时、最大步骤数和失败退出；
- 不自动回答密码、验证码、权限扩大、删除数据等问题。

禁止使用：

```bash
yes | command
printf 'y\ny\n' | command
```

这类做法无法判断当前提示，版本变化后可能对错误问题回答 Yes。

## 七、沙箱与云端验证方案

### 当前可执行方案

本机临时 HOME 沙箱最适合验证 macOS 行为：

- 使用真实 macOS、Terminal、Keychain 和浏览器调用路径；
- 配置文件与当前用户隔离；
- 测试结束物理删除临时目录；
- 可以覆盖绝大多数安装、首次运行和状态检测。

### Docker/Colima

本机安装了 Docker CLI、Colima 和 Lima，但 Docker daemon 当前未运行。
即使启动，它们提供的是 Linux VM，适合测试 shell 与 npm 安装，不适合验证 macOS
Keychain、Terminal、launchd、Retina、系统权限和浏览器回调。

### 云端环境

- 公网 GitHub macOS runner 无法稳定访问字节内网，也不适合人工扫码；
- 内部带 GUI、浏览器和字节网络的 macOS 云主机可以进行完整验收；
- 当前会话没有可直接创建内部 macOS 云主机的接口；
- 如提供可访问的内部测试 Mac/EnvX 运行实例，可以继续完成全链路真实登录验收。

### 完全隔离的最终验收

发布前推荐使用以下任一方式：

1. 专用测试 Mac；
2. 临时 macOS 用户账号和独立 Keychain；
3. 内部 macOS GUI 云主机。

真实授权必须使用测试账号，不能在自动化中复制正式用户凭据。

## 八、最终产品选择

`mac_byte` 固定安装完整工具链：Trae CLI、Lark CLI、AgentBuddy、Botmux 和 Seele
插件。前三项只要求用户完成官方登录或授权；Botmux 保留需要用户决定的原生选项，
其余固定配置自动完成。当前不再提供核心版/完整工具版选择，避免新增首次安装选项。
