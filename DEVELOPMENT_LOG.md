# Seele 本地开发交接记录

本文件与 `Seele.py` 同级，是后续新话题继续开发时的统一交接入口。
每次修改代码、安装流程、音频、测试或发布配置后，都要同步更新本文件。

## 协作约束

- 当前采用“本地修改 -> 用户实际验收 -> 用户明确确认 -> 提交和发布”的顺序。
- 未经用户确认，不提交、不推送、不创建 Tag、不更新 GitHub Release。
- 不在本文记录 Token、Cookie、账号、内网凭据或其他秘密。
- 不删除远端 Release、Tag 或回退远端分支，除非用户明确批准。

## 远端基线

- 仓库：`https://github.com/xinna2001/Seele`
- 当前分支：`main`
- `v2.1.0` 发布提交：`1c64d7c`
- `v2.0.3` 正式测试发布提交：`ce59731`
- `v2.0.2` Tag 提交：`a82f064`；该版本因 Windows CI 中的 macOS 路径断言失败，
  未生成 GitHub Release，不作为测试包使用。
- `v2.0.1` 发布提交：`a552425`
- `v2.0.0` 发布基线提交：`8588a7d`
- `v1.0.0`：提交 `0619912`
- GitHub 已存在 `v1.0.0`、`v2.0.0`、`v2.0.1`、`v2.0.3` 和 `v2.1.0` Release。
- `v2.1.0` Release：
  `https://github.com/xinna2001/Seele/releases/tag/v2.1.0`。
- `v2.0.3` Release：
  `https://github.com/xinna2001/Seele/releases/tag/v2.0.3`。
- `v2.0.0` 在“所有后续修改先本地验收”的约束提出前已经发布。不要擅自删除或改写。

## 2026-09-29 修复批次

状态：已通过独立分支合并 `main`，并包含在 `v2.0.1` 中。
分支：`fix/mac-byte-bootstrap-audio`。
修复提交：`d7a8ded`。

### 修改内容

1. 删除 `Seele.py` 右键菜单中的“安装或配置 Botmux”入口及信号连接。
2. 保留 `mac_byte` 首次启动自动检测：
   - 未安装 Botmux：运行完整安装流程；
   - 已安装但没有机器人配置：运行 `botmux setup`；
   - 已安装且已配置：不弹 Terminal，不重复安装。
3. 接入用户提供的 6 个 16 kHz WAV 语音文件。
4. 将 `mac_byte_bootstrap.py` 的语音映射改为真实的 `_16k.wav` 文件名。
5. 更新 `audio/mac_byte/README.md` 和根目录 `README.md`，不再把现有音频描述为待补占位符。
6. 增加语音文件存在性回归测试，避免代码引用与实际文件名再次不一致。

### 当前语音映射

| 安装阶段 | 文件名 |
| --- | --- |
| 开始安装 | `mac_byte_install_16k.wav` |
| Trae CLI 登录 | `mac_byte_traex_login_16k.wav` |
| Lark CLI 初始化 | `mac_byte_lark_config_16k.wav` |
| Lark CLI 登录 | `mac_byte_lark_login_16k.wav` |
| AgentBuddy 登录 | `mac_byte_agentbuddy_login_16k.wav` |
| Botmux 配置 | `mac_byte_botmux_setup_16k.wav` |

6 个文件均已用 `afinfo` 确认为 16 kHz、Int16、双声道 WAV。

## 2026-09-29 macOS UI 修复批次

状态：已通过独立分支合并 `main`，并作为 `v2.0.1` 发布。
分支：`fix/mac-byte-ui-retina`。
修复提交：`48cb2e6`。

### 问题证据

1. 右键菜单在代码中被固定为 `24px` 字号、`320px` 最小宽度和
   `16px 30px` 单项内边距；Retina 屏幕上会显示得明显过大。
2. `QMovie.setScaledSize()` 先把 480 x 452 的 GIF 缩到约 200 个物理像素，
   macOS 再将它放大到约 400 个 Retina 像素，导致角色边缘和线条发糊。
3. `mac_byte` 仍显示并启动旧版语音唤醒、语音输入和启动模式能力，
   与 Botmux 为主体的定位不一致。

### 本地修改

1. 启用 Qt 高 DPI 缩放和高 DPI Pixmap 支持。
2. 保留 GIF 原始帧，按窗口设备像素比平滑渲染每一帧，不再调用
   `QMovie.setScaledSize()` 生成低分辨率中间帧。
3. `mac_byte` 菜单仅保留“换个角色、机器人状态、打开 Botmux、退置托盘、退出程序”。
4. Windows 等非 `mac_byte` 版本继续保留原有语音和启动菜单，避免破坏 1.0 历史能力。
5. `mac_byte` 不再创建旧语音设置窗口，也不再启动 `VoiceToText` 全局监听。
6. 主菜单和托盘菜单移除固定大字号，改为系统 DPI 字号与紧凑内边距。
7. 气泡字体由 `24px` 调整为 `14px`，宽度由 `520px` 调整为 `320px`，
   动态高度限制为 `56px` 至 `160px`。
8. 气泡改为希儿的从属顶层浮窗，增加不接收焦点属性，并取消显示时主动
   `raise_()`，避免定时气泡触发整个窗口组突然抢到最前。
9. 希儿和气泡在 macOS 上启用 `WA_MacAlwaysShowToolWindow`，保持应用失去
   焦点后仍浮在普通桌面窗口之上；不覆盖系统安全窗口。

### 本地验证

- Python 单元测试：17 项通过。
- Retina 模拟比例：`2.0833`。
- 角色逻辑尺寸：`200 x 188`；实际渲染帧：`416 x 392`，帧 DPR 为 `2.0833`。
- `mac_byte` 菜单：5 项，逻辑尺寸 `158 x 173`。
- 已生成并人工检查角色与菜单截图，角色边缘清晰、菜单无文字溢出。
- 气泡尺寸：`320 x 58`；从属关系、置顶标志、无焦点标志均验证通过。
- 已人工检查 Retina 气泡截图，字号、换行和边距正常。
- 已重新构建 `dist/Seele.app`，打包后 smoke test和代码签名校验通过。
- 最新本地 `.app` 已启动并完成用户验收。
- 已作为 `v2.0.1` 发布。

## 2026-09-30 自动安装命令审计

状态：仅新增本地说明文档，未修改自动安装代码，尚未提交或推送。

1. 新增 `MAC_BYTE_AUTO_INSTALL_COMMANDS.md`。
2. 按 `mac_byte_bootstrap.py` 当前实现完整记录 `full`、`setup` 和 `ready` 三种路径。
3. 记录 Node.js、Trae CLI、Lark CLI、AgentBuddy、Botmux、Seele 插件、
   Botmux 启动和自启动的全部命令。
4. 记录 6 个语音提示、每个登录步骤后的回车暂停、Terminal 打开方式、
   锁文件、状态文件和退出清理逻辑。
5. 明确记录全局 npm registry 会被改为字节源且不会自动恢复，以及各工具
   使用 `latest` 的版本漂移行为。
6. 在根目录 `README.md` 增加命令清单入口。

## 2026-10-06 低感知安装调研

状态：仅新增本地调研文档，未修改安装代码，尚未提交或推送。

1. 新增 `MAC_BYTE_ZERO_TOUCH_RESEARCH.md`。
2. 核查 Trae CLI `0.207.1`、Lark CLI `1.0.94`、AgentBuddy `1.5.7`、
   Botmux `3.33.0` 的官方安装、登录、配置和状态命令。
3. 使用独立临时 HOME/XDG 目录验证四个 CLI 的首次认证行为，测试结束后已
   物理删除全部临时目录，没有读取或覆盖当前用户配置。
4. 验证 Trae CLI 只需 ByteCloud 二维码，Lark CLI 只需应用配置二维码和
   OAuth，AgentBuddy 只需设备授权链接，Botmux 脚本化 setup 只需开放平台扫码。
5. 确认核心链路不需要 `expect`；推荐使用官方命令、JSON/退出码检测和可恢复
   Python 安装状态机。
6. 记录本机 Docker daemon 未运行，Colima/Lima 只能提供 Linux 环境，不适合
   验证 macOS Keychain、Terminal、launchd 和浏览器回调。
7. 在根目录 `README.md` 增加低感知安装调研入口。
8. 建议产品分为默认 Botmux 核心版和可选字节完整工具版，将默认认证次数由
   最多 5 次减少为 Trae CLI 与 Botmux 两次。

## 2026-10-08 低感知安装实现

状态：已合并 `main` 并发布 `v2.0.3`；本地和线上构建验收通过，待新电脑首次安装验收。
分支：`feat/mac-byte-zero-touch-setup`。
功能提交：`8f51712`。
合并提交：`a82f064`。
Windows CI 兼容修复及 `v2.0.3` Tag 提交：`ce59731`。

### 实现内容

1. Trae CLI 安装增加官方非交互环境变量，登录改为
   `backend cn -> login --sso-device -> login status`，不再启动裸 TUI。
2. Lark CLI 使用 `config show`、`config init --new`、`auth login --recommend`
   和 `auth status --verify` 自动跳过已完成阶段并读回校验。
3. AgentBuddy 使用 device login 和 JSON status，授权完成后自动继续。
4. npm 内部源改为命令级 `--registry`，不再修改用户全局 npm registry。
5. 新增 `botmux_setup_coach.py` 和独立 console helper；windowed 主程序不直接占用
   Terminal stdin，由 helper 在 PTY 中透明代理原生 `botmux setup`。
6. 根据 Botmux 当前真实提示播放 11 条动态语音；用户输入只转发，不落盘、不记录。
7. 固定按菜单文字选择 `TRAE (CoCo) -> traex`，并自动接受默认工作目录；不依赖
   菜单序号或固定等待秒数。
8. 删除全部阶段间人工回车暂停；配置完成后自动安装插件、启动 Botmux、开启自启，
   并执行 `botmux status` 与 `botmux autostart status`。
9. 语音包扩展到 17 个 WAV，均为 16 kHz、Int16、双声道。

### 本地验证

- Python `compileall`：通过。
- Python 单元测试：22 项通过。
- Botmux 插件 build、validate 和 MCP smoke：通过。
- 源码 PTY 与冻结 console helper 均验证自动输入结果为
  `TRAE|traex||`；扫码提示不触发输入。
- 17 个 WAV 均为 16 kHz、Int16、双声道；峰值约 `-8` 至 `-10 dB`，无削波、
  整段静音或末尾截断。
- 新增 11 条语音使用 Whisper `large-v3` 转写，操作语义与清单一致。
- 本地 PyInstaller 构建、版本写入、ad-hoc 签名、严格签名校验和离屏
  smoke test：通过。
- 临时生成的 ZIP 通过 `unzip -t`，DMG 通过 `hdiutil verify`；过程文件已删除。
- `v2.0.2` 首次线上构建仅因 macOS 路径断言未跳过 Windows 而失败；产品测试均通过。
  `v2.0.3` 增加平台条件后重新发布，不改写已推送的旧 Tag。
- 待用户在全新 Apple Silicon 字节电脑完成首次安装验收。

### 线上发布验证

- `v2.0.3` 跨平台测试工作流 `37774249332`：Windows、macOS、Ubuntu 全部成功。
- `main` 跨平台测试工作流 `37774245402`：全部成功。
- `v2.0.3` 打包发布工作流 `37774249352`：成功创建 GitHub Release。
- macOS 在线资产均返回 HTTP 200：
  - `Seele-2.0.3-mac_byte-macos-arm64.dmg`
  - `Seele-2.0.3-mac_byte-macos-arm64.zip`
  - `SHA256SUMS-mac_byte.txt`
  - `release-manifest-mac_byte.json`
- 在线 manifest 确认版本为 `2.0.3`、平台为 `macos-arm64`、构建提交为
  `ce59731db2d27fce24ed4c41c17690bb4039c427`。
- 在线 SHA256：
  - ZIP：`fe84a16b6f973fce597ed48d8fdb5aa028ecd7fcab57d1fe29f4404c561b5dcf`
  - DMG：`508bfa42039a698df2fd3a0f8ea5006c587850dd9683056dc9c0f6581e9fc1bc`
- 已重新下载线上 ZIP 并通过 SHA256 与 `unzip -t` 校验；包内包含 17 个 WAV 和
  可执行的 `Contents/Resources/bin/SeeleBotmuxCoach`。临时下载文件已物理删除。

## 2026-10-08 v2.1.0 安装恢复与独立检测

状态：已合并 `main` 并发布 `v2.1.0`，本地和线上构建验收通过，待新电脑首次安装验收。
分支：`feat/mac-byte-bootstrap-recovery-v2.1.0`。
功能提交：`feb2ca1`。
合并及 Tag 提交：`1c64d7c`。

### 问题结论

1. Lark CLI `1.0.97` 的 `config init --new` 使用 discovery device code 轮询应用
   配置，默认轮询间隔 5 秒、整体有效期 600 秒。
2. 网页显示应用创建成功不代表 CLI 已收到完整凭据，也不代表配置已写入本机；
   `lark-cli config show` 才是本地落盘的独立判据。
3. 当前版本没有供 `config init` 使用的 `--no-wait` 或 `--device-code` 恢复参数。
   同轮自动重跑会生成新的 device code，可能重复创建应用，因此不采用自动二次初始化。

### 实现内容

1. 启动时独立检查 `node`、`npm`、`traex`、`lark-cli`、`agentbuddy` 和 `botmux`；
   任一缺失进入完整流程，所有已存在组件分别跳过安装。
2. Node.js/npm、Trae CLI、Lark CLI、AgentBuddy 和 Botmux 的原安装命令与顺序保留，
   仅增加安装前检测和安装后统一命令解析校验。
3. Lark CLI 应用初始化每轮最多执行一次；命令退出后立即执行只读
   `lark-cli config show`，未落盘则失败退出并提示关闭 Terminal、重启 Seele 续跑。
4. 安装失败退出时仍由原 trap 原子写入失败状态并清理锁文件，下一轮不会重复安装
   已存在的组件。
5. Terminal 标题从 `VERSION` 动态读取，版本升级为 `2.1.0`。
6. 版本规则固定为语义化三段式：小修复递增 PATCH（如 `2.1.1`），较大功能递增
   MINOR（如 `2.2.0`），由改动范围和兼容性判断。

### 回归覆盖

- 独立命令检测结果与 `full/setup/ready` 模式选择。
- 六个组件安装前条件判断和安装后统一校验。
- Lark CLI 初始化命令仅出现一次，结束后执行第二次本地配置检查。
- 生成的完整安装脚本通过 `/bin/zsh -n`。
- Python `compileall`：通过。
- Python 单元测试：25 项通过。
- Botmux 插件 build、validate 和 MCP smoke：通过。
- 本地 arm64 coach 和 `.app` 构建、版本写入、ad-hoc 严格签名与离屏 smoke：通过。
- 本地 ZIP 通过 `unzip -t`，DMG 通过 `hdiutil verify`；临时构建目录已物理删除。

### 线上发布验证

- `main` 跨平台测试工作流 `37784117223`：Windows、macOS、Ubuntu 全部成功。
- `v2.1.0` 跨平台测试工作流 `37784347668`：Windows、macOS、Ubuntu 全部成功。
- `v2.1.0` 打包发布工作流 `37784347976`：Windows、macOS 打包及 Release 发布成功。
- Release 包含 8 个预期资产：Windows 安装版与便携版、macOS DMG 与 ZIP、
  两个平台的 manifest 和 SHA256 文件。
- 在线 macOS manifest 确认版本为 `2.1.0`、平台为 `macos-arm64`、签名为
  `ad-hoc`、提交为 `1c64d7c22ca7297f4b1080b7b4b5144d2e12752e`。
- 在线 SHA256：
  - ZIP：`6a6822bb482ea9b9d71a74ba1fba675fe0e3f32cfb59d928e991d6e99cccea20`
  - DMG：`da371e3f311dbf3add5e9c76611fa9e50f4d87bb3c25aca28fa73a7fd3953cc8`
- 已下载线上 macOS ZIP 并通过发布 SHA256、`unzip -t`、包内版本、17 条 WAV
  和 helper `0755` 权限校验；临时下载文件已物理删除。

## 已实现的 2.0 架构

- `Seele.py`：PyQt 桌宠、托盘菜单、气泡和 Botmux 状态展示。
- `mac_byte_bootstrap.py`：字节内部 macOS 首次启动检测、安装和登录引导。
- `botmux_client.py`：Botmux Dashboard REST、SSE 和任务触发。
- `rpa_service.py`：影刀工作流白名单、幂等和状态管理。
- `rpa_bridge.py`：Botmux 到本地 RPA 的受限 HTTP Bridge。
- `botmux-skill/`：Seele 的 Botmux 插件；不修改 Botmux 内核。

`mac_byte` 完整安装流程使用内网命令安装 Node.js、Trae CLI、Lark CLI 和
AgentBuddy，并从 npm 官方源安装 `botmux@latest`。登录链接或二维码保留在
Terminal 中展示；官方命令和状态校验成功后自动继续。Botmux 原生 setup 由 PTY
教练按提示播放语音并完成固定选择。

## 验证记录

2026-09-29 本地验证：

- `python -m compileall`：通过。
- Python 单元测试：17 项通过。
- 6 个语音文件存在性测试：通过。
- `git diff --check`：通过。
- 该批次当时尚未重新构建 `.app`；最新本地构建状态见下方 macOS UI 修复批次。

常用验证命令：

```bash
.venv/bin/python -m compileall -q Seele.py mac_byte_bootstrap.py tests
.venv/bin/python -m unittest discover -s tests -v
git diff --check
```

## 后续待验收

1. 在全新字节 Apple Silicon 电脑验证 `v2.1.0` 完整安装和失败续跑。
2. 验证 Trae、Lark CLI、AgentBuddy 的真实首次登录和自动续跑。
3. 验证 Botmux 扫码、语音提示、`traex` 自动选择和默认目录自动确认。
4. 普通公网 macOS 版本、Developer ID 签名和公证仍未完成。

## 新话题恢复步骤

1. 先阅读本文件和 `.trae/skills/seele-botmux/SKILL.md`。
2. 运行 `git status --short --branch`，保护所有本地未提交修改。
3. 不以远端 Release 安装包覆盖当前工作区的未提交修改。
4. 按“后续待验收”在全新字节 Apple Silicon 电脑验证 `v2.1.0`，不要重复创建
   Tag 或发布安装包。
