# mac_byte 自动安装命令清单

本文记录 Seele `v2.0.3` 中 `mac_byte` 首次启动实际执行的命令。权威实现位于
`mac_byte_bootstrap.py` 和 `botmux_setup_coach.py`。

## 触发模式

Seele 仅在 macOS 且 `EDITION=mac_byte` 时运行安装检测：

- `full`：找不到 `botmux`，执行完整安装、登录和配置；
- `setup`：已安装 `botmux`，但 `~/.botmux/bots.json` 没有有效配置；
- `ready`：Botmux 已安装并配置，不打开 Terminal。

生成的 `~/.seele/mac_byte/bootstrap-<UUID>.command` 权限为 `0700`，通过
`/usr/bin/open -a Terminal` 启动。脚本使用 `set -e`、`set -u` 和
`set -o pipefail`；任何安装或校验命令失败都会停止后续步骤并写入失败状态。

## 完整安装

### Node.js

```bash
export NVM_DIR="$HOME/.nvm"
if [ ! -s "$NVM_DIR/nvm.sh" ]; then
  curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
fi
source "$NVM_DIR/nvm.sh"
nvm install --lts
nvm use --lts
node -v
npm -v
```

### CLI 工具

```bash
curl -fsSL https://code.byted.org/api/tos-proxy/download/traex_install.sh |
  env TRAEX_INSTALL_ASSUME_YES=1 \
      TRAEX_INSTALL_REMOVE_COCO=1 \
      TRAEX_INSTALL_REMOVE_BREW=0 \
      sh

npm install -g @larksuite/cli@latest --registry https://bnpm.byted.org/
npm install -g agentbuddy@latest --registry https://bnpm.byted.org/
npm install -g botmux@latest --registry https://registry.npmjs.org/
```

内部 npm 源只传给对应安装命令，不执行 `npm config set registry`，因此不会永久
修改用户的全局 npm 配置。

## 登录与状态校验

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
  lark-cli config init --new --lang zh_cn --name seele
fi

if ! lark-cli auth status --json --verify >/dev/null 2>&1; then
  lark-cli auth login --recommend
fi
lark-cli auth status --json --verify
```

应用初始化和用户 OAuth 都由官方命令阻塞等待本人授权。已有有效配置或登录态时直接
跳过对应步骤。

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

仅配置模式直接从该 PTY 配置步骤开始，不重复安装或登录前三个工具。

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
- Botmux 以 PTY 中出现的精确提示作为自动输入信号；
- 超时仅用于外围启动失败保护，不作为“进入下一步”的判断依据。
