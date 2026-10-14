# mac_byte 自动安装命令清单

本文记录 Seele `v2.2.2` 中 `mac_byte` 首次启动实际执行的命令。权威实现位于
`mac_byte_bootstrap.py` 和 `botmux_setup_coach.py`。

## 触发模式

Seele 仅在 macOS 且 `EDITION=mac_byte` 时运行安装检测。启动时分别解析
`node`、`npm`、`tmux`、`traex`、`lark-cli`、`agentbuddy` 和 `botmux`：

- `full`：缺少普通工具或 Botmux 本体，进入完整流程，但每个已安装组件都会独立跳过；
- `setup`：七个命令均存在，但 `~/.botmux/bots.json` 没有有效配置；
- `repair`：已有有效 Botmux 配置，但只缺少 `tmux`，或全部命令已存在但 Botmux
  supervisor 没有运行；
- `ready`：七个命令均存在、Botmux 已配置且 supervisor 在线，不打开 Terminal。

生成的 `~/.seele/mac_byte/bootstrap-<UUID>.command` 权限为 `0700`，通过
`/usr/bin/open -a Terminal` 启动。脚本使用 `set -e`、`set -u` 和
`set -o pipefail`；任何安装或校验命令失败都会停止后续步骤并写入失败状态。

## 完整安装

### Node.js

```bash
if command -v node >/dev/null 2>&1 &&
   command -v npm >/dev/null 2>&1; then
  # 保留现有 Node.js 和 npm
else
  export NVM_DIR="$HOME/.nvm"
  if [ ! -s "$NVM_DIR/nvm.sh" ]; then
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
  fi
  source "$NVM_DIR/nvm.sh"
  nvm install --lts
  nvm use --lts
fi
node -v
npm -v
```

### Homebrew 与 tmux

```bash
if ! command -v tmux >/dev/null 2>&1; then
  if ! command -v brew >/dev/null 2>&1; then
    installer="$(
      curl -fsSL \
        https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh
    )"
    /bin/bash -c "$installer"
    # 按 Apple Silicon / Intel 实际路径加载 brew shellenv。
  fi
  HOMEBREW_NO_AUTO_UPDATE=1 brew install tmux
fi
tmux -V
```

Homebrew 已存在或 `tmux` 已存在时直接跳过对应安装。全新 Mac 首次安装 Homebrew
通常需要管理员密码和一次确认，因此保留官方交互流程，不模拟密码或回车。权限确认完成
后脚本自动继续安装 tmux；安装失败则保留终端错误，不会启动缺少 tmux 的 Botmux daemon。

## Botmux 运行恢复

如果上一轮已经安装并配置好 Botmux，只因缺少 `tmux` 导致 `botmux start` 失败，
下一次双击 Seele 会进入 `repair`，而不是重新执行完整安装。该模式只执行：

```bash
# 缺少时安装 tmux；已有时直接跳过。
HOMEBREW_NO_AUTO_UPDATE=1 brew install tmux

botmux plugin install "<APP_RESOURCES>/botmux-skill" --link
botmux plugin enable seele
botmux start
botmux autostart enable
botmux status
botmux autostart status
```

它保留现有 `bots.json`，不重复安装 Node.js、Trae CLI、Lark CLI、AgentBuddy 或
Botmux，不重复登录，也不进入 `botmux setup`。如果 `tmux` 已经补好但 Botmux 仍未
启动，启动检测同样进入 `repair`，重新执行插件、启动和开机自启命令。

### CLI 工具

```bash
if ! command -v traex >/dev/null 2>&1; then
  curl -fsSL https://code.byted.org/api/tos-proxy/download/traex_install.sh |
    env TRAEX_INSTALL_ASSUME_YES=1 \
        TRAEX_INSTALL_REMOVE_COCO=1 \
        TRAEX_INSTALL_REMOVE_BREW=0 \
        sh
fi

if ! command -v lark-cli >/dev/null 2>&1; then
  npm install -g @larksuite/cli@latest --registry https://bnpm.byted.org/
fi
if ! command -v agentbuddy >/dev/null 2>&1; then
  npm install -g agentbuddy@latest --registry https://bnpm.byted.org/
fi
if ! command -v botmux >/dev/null 2>&1; then
  npm install -g botmux@latest --registry https://registry.npmjs.org/
fi
```

内部 npm 源只传给对应安装命令，不执行 `npm config set registry`，因此不会永久
修改用户的全局 npm 配置。安装后再次检查全部七个命令；任何一项仍无法解析都会停止，
不会带着不完整环境进入登录阶段。

## 登录与状态校验

Trae、Lark CLI 和 AgentBuddy 尚未完成、确实需要用户扫码或授权时，脚本执行：

1. 读取 macOS 当前输出音量和静音状态；
2. 仅在静音或输出音量低于 `20%` 时，临时调整到 `20%` 并取消静音；
3. 在 Terminal 仍处于后台时发送 ANSI `2J + 3J + H`，先清掉上一个阶段的链接；
4. 在后台播放对应语音，不等待语音结束就通过 PTY helper 启动官方登录命令；
5. PTY helper 保留原始终端输出，同时从完整输出行中提取首个有效 HTTPS 登录地址，
   优先使用 Google Chrome 打开，Chrome 不可用时回退系统默认浏览器。
6. 链接在 5 秒内没有出现，或登录命令失败时，才使用 AppleScript 将 Terminal
   激活到前台；不再次清屏，确保当前二维码和错误信息仍然可见。

安装脚本的 `EXIT` trap 会在成功、失败或 Terminal 被关闭时恢复原输出音量和静音
状态。已经登录或配置完成的阶段仍由状态命令直接跳过，不调整音量，也不抢占前台。
自动打开只处理当前受信 CLI 命令输出的 HTTPS 地址，每个命令最多打开一次；终端中的
二维码、链接和用户输入仍原样保留。

Botmux setup 仍在阶段开始时激活并清理 Terminal，初始语音播放完成后再运行原生
交互流程；这是因为用户仍需在终端输入机器人名称、管理员邮箱并处理菜单选项。

### Trae CLI

```bash
traex backend cn
if ! traex login status >/dev/null 2>&1; then
  traex login --sso-device
fi
traex login status
```

不启动裸 `traex` TUI。用户完成 ByteCloud 授权后，登录命令退出，状态校验成功才
进入下一步。

### Lark CLI

```bash
if ! lark-cli config show >/dev/null 2>&1; then
  init_code=0
  lark-cli config init --new --lang zh_cn --name seele || init_code=$?
  if ! lark-cli config show >/dev/null 2>&1; then
    # 输出恢复说明并退出，不在同一轮再次执行 config init
    if [ "$init_code" -eq 0 ]; then
      init_code=1
    fi
    exit "$init_code"
  fi
fi

if ! lark-cli auth status --json --verify >/dev/null 2>&1; then
  lark-cli auth login --recommend
fi
lark-cli auth status --json --verify
```

应用初始化和用户 OAuth 都由官方命令阻塞等待本人授权。已有有效配置或登录态时直接
跳过对应步骤。

Lark CLI `config init --new` 的网页“创建成功”只表示服务端流程完成，只有
`lark-cli config show` 能确认 App ID 和 App Secret 已写入本机。当前 Lark CLI 会为
每次初始化生成新的 device code，因此 Seele 不自动重跑同一命令。初始化命令退出后，
Seele 独立执行一次只读配置检查；如果仍未落盘，脚本失败退出并清理锁文件。用户关闭
Terminal、重新启动 Seele 后，所有已安装组件会被跳过，并从未完成的配置阶段续跑。

### AgentBuddy

```bash
if ! agentbuddy status --json >/dev/null 2>&1; then
  agentbuddy login --region cn --login-mode device --json --yes
fi
agentbuddy status --json
```

## Botmux PTY 配置

源码模式执行：

```bash
python run_exe.py --botmux-setup-coach
```

安装包模式执行：

```bash
SEELE_RESOURCES_DIR="<APP_RESOURCES>" \
  "<APP_RESOURCES>/bin/SeeleBotmuxCoach"
```

主程序为 windowed `.app`，不直接占用 Terminal stdin；安装包内独立的 console helper
负责在伪终端中运行原生 `botmux setup`：

- 用户输入原样转发，不记录邮箱、验证码或 App Secret；
- 根据当前真实提示播放对应的 16 kHz WAV；
- 扫码由 Botmux 自己轮询，只有 Botmux 输出下一步提示后才继续；
- 检测到 CLI 菜单后按文字筛选并选择 `TRAE (CoCo) -> traex`；
- 检测到工作目录模式和目录输入后，自动回车接受 Botmux 默认值；
- 不使用固定等待秒数，不对未知提示自动输入。

仅配置模式直接从该 PTY 配置步骤开始，不重复安装或登录前三个工具。若已有有效
`~/.botmux/bots.json` 且只缺少 tmux，或 Botmux supervisor 离线，则进入独立运行
恢复模式，不经过 PTY 配置步骤。

## 插件、启动和读回

```bash
botmux plugin install "<APP_RESOURCES>/botmux-skill" --link
botmux plugin enable seele
botmux start
botmux autostart enable
botmux status
botmux autostart status
```

配置完成后不再等待用户按回车。脚本退出时原子更新
`~/.seele/mac_byte/bootstrap-status.json`，并删除锁文件和临时 `.command` 文件。

## 等待机制

安装过程没有用固定秒数串联步骤：

- 下载和安装以前台进程退出作为完成信号；
- 登录以官方命令退出和状态命令返回码作为完成信号；
- Lark CLI 网页初始化结束后以本机 `config show` 作为唯一落盘成功判据；
- Botmux 以 PTY 中出现的精确提示作为自动输入信号；
- 超时仅用于外围启动失败保护，不作为“进入下一步”的判断依据。
