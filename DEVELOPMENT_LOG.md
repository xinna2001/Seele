# Seele 本地开发交接记录

本文件与 `Seele.py` 同级，是后续新话题继续开发时的统一交接入口。
每次修改代码、安装流程、音频、测试或发布配置后，都要同步更新本文件。

## 协作约束

- 当前采用“本地修改 -> 用户实际验收 -> 用户明确确认 -> 提交和发布”的顺序。
- 未经用户确认，不提交、不推送、不创建 Tag、不更新 GitHub Release。
- 不在本文记录 Token、Cookie、账号、内网凭据或其他秘密。
- 不删除远端 Release、Tag 或回退远端分支，除非用户明确批准。

## 2026-10-21 安装、自动更新与设置保留（2.5.0 发布准备）

用户授权实现启动联网检查、右键最后“检查更新”红点、点击下载安装重启、
设置移出应用包。本批次包含上一个未发布的 Windows 字节版改动；
用户已明确回复“OK啦，推吧”，授权本批次提交、合并和发布。
采用功能分支 -> PR -> CI 通过后合并 -> Tag/Release，保留分支和 PR 记录。

- `platform_utils.py`：区分只读资源与可写用户目录，按 edition 隔离设置；
  首次迁移 state/uid/file_name/config/botmux_config，原子写入与私有文件权限。
  macOS 新 ZIP 可优先迁移已安装同类型旧应用的设置。
- macOS 设置目录 `~/Library/Application Support/Seele/<edition>/`，
  Windows `%LOCALAPPDATA%/Seele/<edition>/`，Linux XDG data home。
  `SEELE_DATA_DIR` 用于测试隔离；配置窗口、语音、RPA、Botmux、日志均已接入。
- `UpdateUi.py`：启动 5 秒后检查、每小时检查、菜单末项红点，
  点击下载进度提示；离线后台静默、手动反馈，不与 Botmux 安装同时替换。
- `app_update.py`：官方 GitHub latest API，匿名限流时使用官方 latest/download
  manifest；严格版本/发行类型/平台选择，SHA256、发布清单、ZIP 路径与链接、
  包内版本/资源/签名和冻结主程序自检，拒绝降级。随包携带 certifi CA，
  不依赖构建机 Homebrew 证书；兼容 ditto 未标 UTF-8 的中文 ZIP 文件名。
- `app_update_entry.py`：独立 onefile helper，退出前准备与授权握手，
  等待旧进程退出后同目录原子替换，实际新版 PID/版本/nonce 健康回执；
  失败回滚，保留 Inno 卸载资源，安装目标文件锁，下一次启动清理已完成过程目录。
- macOS ZIP 首次启动可安装到 /Applications（不可写时 ~/Applications），
  已存在版本不降级、不跨发行类型覆盖；DMG 增加 Applications 拖放入口。
- 发布 workflow 与本地构建均打包独立更新 helper、增加冻结主程序 helper 自检；
  Windows VIP 从自身独立复制的 embeddable Python 执行更新程序，
  切换正式 EXE 后保留“启动希儿.vbs”入口；普通版启动刷新 RPA 的资源和设置路径。
- 验证：98 项 Python 测试通过（含设置保留、SHA、ZIP/symlink、
  平台选择、真实子进程健康回执、成功替换/失败回滚/父进程不退出、
  菜单最后项和红点、离线与点击下载、匿名限流回退）；插件测试通过，
  release YAML 解析与 diff 格式通过。
- 在线只读验证成功：官方 latest 显示 2.3.1，mac_byte/arm64 三个版本资产
  正确解析，真实 ZIP/清单下载 SHA256 与安全解压资源核验通过；临时副本已清理。
- 冻结 macOS 完整事务实跑：重新解压 ZIP 严格签名与 GUI/helper smoke，
  独立冻结 helper 准备、等待旧 PID 退出、原子替换、真实新版 GUI PID 健康回执、
  角色保留、替换后严格签名均通过。使用临时目标和隔离数据，未替换工作区或本机应用。
  冻结主程序在系统 CA 路径设为不存在时 HTTPS 检查通过，确认 certifi 随包可用。
  当前 2.5.0 不会降级；普通用户菜单安装与未来更高版本点击更新仍待真机验收。
- VIP 输出固定在 `vip-packages/Seele-2.5.0-vip-test-*.zip`，附 SHA256。
  Windows EXE/WSL 安装、重启和授权仍需 Windows 真机验收。
- 最终 mac_byte ZIP SHA256：
  `be801c99522ef1858849d25802d742eb091b0ed7e4f5c988b4d959c16a78508f`。
- 最终 windows_byte VIP ZIP SHA256：
  `4b166d22df7aaa877b3ede3762ffec5f7e354cf3a2cca5249cf37bee6af4f2cc`。
  两包 ZIP/摘要核验通过；Windows 包包含 certifi CA、独立 helper 源码与内置 Python。
- 菜单视觉证据：`vip-packages/Seele-2.5.0-update-menu.png`，
  模拟高版本红点，验证“检查更新”始终在底部；线上当前没有高于 2.5.0 的 Release。
- 发布 CI 修正：首次 Windows CI 在 CP1252 输出中文安装提示时抛
  `UnicodeEncodeError`，导致成功、重启和锁竞争分支异常退出。
  `run_install()` 开始时将可配置 stdout/stderr 设为 UTF-8，
  新增英文系统重定向输出与重启返回码回归，本地 99 项测试通过。
  该失败触发矩阵 fail-fast；PR/分支 CI 修正后重新运行。

## 2026-10-21 Windows 字节版 WSL 安装修复（2.4.0 本地待验收）

用户授权按其成功部署指南直接修复 Windows 字节版。本批次仅本地修改；
未提交、未推送、未发布。用户新增指南和 `.vscode/` 保留。

- `windows_byte_bootstrap.py`：当前用户 WSL2 探测、普通用户复用/初始化、
  窄范围 UAC 组件安装、原子进度、内核锁、重启续装任务及 HKCU Run 备用。
- `windows_byte_linux.py`：合并 WSL 配置、官方 Botmux 二进制安装、
  字节 CLI 安装与授权、插件、systemd/watchdog/linger、前台保活。
- `botmux_setup_coach.py`：WSL 内调用 Windows PowerShell 播放原语音，
  优先 Chrome 打开授权地址；文字参数用 UTF-16 编码脚本和单引号字面量传递。
- `Seele.py`/`botmux_client.py`：Windows 字节版避开旧影刀首次安装，
  菜单继续安装、后台 UNC Dashboard 发现、Qt 主线程更新连接。
- Windows 打包矩阵分普通版/字节版，冻结独立 console helper，
  主程序执行 helper 路径与 Linux 源资源自检；Inno 字节版独立目录与卸载任务。
- 本地版本升为 2.4.0；线上仍为 2.3.1。安装说明见 `WINDOWS_BYTE_INSTALL.md`。

验证：82 项 Python 测试通过，新增 16 项覆盖重启边界、续装、
Windows 身份、并发锁、systemd 合并、保活恢复、浏览器与 UNC 路由。
插件 build/validate/MCP smoke、Python 编译、diff 格式、离屏桌宠通过。
PowerShell 7.4.6 解析安装脚本和 workflow 的 PowerShell 部分通过；
release YAML 解析通过。仅语法校验，不代表 Windows 系统接口已实跑。

本地 VIP：

- `vip-packages/Seele-2.4.0-vip-test-windows_byte-x64-portable.zip`：
  官方 Windows Python 3.11.9 embeddable + Windows Qt/wheels，
  完整解压后双击 `启动希儿.vbs`；没有另装 Python 的前置要求。
  ZIP CRC、资源清单、Python/Qt Windows DLL 校验通过。
- `vip-packages/Seele-2.4.0-vip-test-mac_byte-macos-arm64.zip`：
  本地 PyInstaller arm64，ad-hoc 严格签名、冻结主程序 smoke、
  coach 路径 smoke 与 ZIP 校验通过。
- 两包均带 `.zip.sha256`。构建脚本 `packaging/windows/build_vip.py` 和
  `packaging/build_mac_vip.py` 只做本地产物，不发布。

真实 Windows WSL 安装、重启/登录、账号授权、计划任务注册与
Windows PyInstaller EXE 构建未在当前 macOS 主机执行。

## 远端基线

- 仓库：`https://github.com/xinna2001/Seele`
- 当前分支：`main`
- `v2.2.3` 发布提交：`6169d28`
- `v2.2.2` 发布提交：`cf7c73e`
- `v2.2.1` 发布提交：`e9b5693`
- `v2.2.0` 发布提交：`6261e72`
- `v2.1.1` 发布提交：`860edf2`
- `v2.1.0` 发布提交：`1c64d7c`
- `v2.0.3` 正式测试发布提交：`ce59731`
- `v2.0.2` Tag 提交：`a82f064`；该版本因 Windows CI 中的 macOS 路径断言失败，
  未生成 GitHub Release，不作为测试包使用。
- `v2.0.1` 发布提交：`a552425`
- `v2.0.0` 发布基线提交：`8588a7d`
- `v1.0.0`：提交 `0619912`
- GitHub 已存在 `v1.0.0`、`v2.0.0`、`v2.0.1`、`v2.0.3`、`v2.1.0`、
  `v2.1.1`、`v2.2.0`、`v2.2.1`、`v2.2.2` 和 `v2.2.3` Release。
- `v2.2.3` Release：
  `https://github.com/xinna2001/Seele/releases/tag/v2.2.3`。
- `v2.2.2` Release：
  `https://github.com/xinna2001/Seele/releases/tag/v2.2.2`。
- `v2.2.1` Release：
  `https://github.com/xinna2001/Seele/releases/tag/v2.2.1`。
- `v2.2.0` Release：
  `https://github.com/xinna2001/Seele/releases/tag/v2.2.0`。
- `v2.1.1` Release：
  `https://github.com/xinna2001/Seele/releases/tag/v2.1.1`。
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

## 2026-10-09 v2.1.1 Botmux coach 路径修复

状态：已合并 `main` 并发布 `v2.1.1`，本地和线上包验证通过。
分支：`fix/mac-byte-coach-resource-path-v2.1.1`。
功能提交：`5e6d13f`。
合并提交：`17a1e2e`。
跨平台测试修复及 Tag 提交：`860edf2`。

### 问题证据

1. 用户首次安装截图中，前三项登录均已成功，进入 Botmux 配置前立即报错：
   `Contents/Frameworks/bin/SeeleBotmuxCoach: No such file or directory`，随后 Terminal
   显示“进程已完成”。
2. 在线 `v2.1.0` ZIP 确认 helper 实际位于
   `Contents/Resources/bin/SeeleBotmuxCoach`。
3. PyInstaller 同时在 `Contents/Frameworks` 创建了指向 `Resources` 数据文件的
   symlink。旧 `get_base_dir()` 先检查 `_MEIPASS=Frameworks`，因此被
   `Frameworks/state.json` symlink 提前命中并返回了错误的资源根目录。
4. 该错误是确定性的路径计算问题，重开 Terminal 后执行同一命令仍会复现，不采用
   自动重试或重复运行 `botmux setup`。

### 修复内容

1. 标准 macOS `.app` 布局固定优先解析 `Contents/Resources`，其他平台继续优先
   使用 PyInstaller `_MEIPASS`。
2. Botmux coach 命令统一通过包内 helper 路径函数生成。
3. 发布流程新增 `--botmux-coach-smoke-test`，由冻结后的主程序检查最终解析路径下
   helper 是否真实存在且可执行。
4. 回归测试同时在 `Frameworks` 和 `Resources` 放置可命中的 `state.json`，
   确认最终仍选择 `Resources/bin/SeeleBotmuxCoach`。
5. 按补丁更新规则将版本升级为 `2.1.1`。

### 本地验证

- Python `compileall`：通过。
- Python 单元测试：26 项通过。
- Botmux 插件 build、validate 和 MCP smoke：通过。
- 实际 arm64 `.app` 中 `Frameworks/state.json` 为指向 `Resources` 的 symlink；
  冻结主程序 `--botmux-coach-smoke-test` 通过。
- 包内 helper 位于 `Contents/Resources/bin` 且权限为 `0755`。
- ad-hoc 严格签名、主程序离屏 smoke、ZIP `unzip -t` 和 DMG `hdiutil verify`
  均通过；临时构建目录已物理删除。

### 线上发布验证

- 首次 `main` 跨平台工作流 `37878223733` 仅因 Windows 临时目录短路径
  `RUNNER~1` 与规范长路径的字符串断言不同而失败，产品测试均通过；修正测试后再发布。
- 修正后的 `main` 跨平台工作流 `37878452292`：Windows、macOS、Ubuntu 全部成功。
- `v2.1.1` 跨平台工作流 `37878559217`：Windows、macOS、Ubuntu 全部成功。
- `v2.1.1` 打包发布工作流 `37878559248`：Windows、macOS 打包及 Release 发布成功；
  macOS 作业包含新增的冻结主程序 coach 路径 smoke test。
- Release 包含 8 个预期资产，在线 macOS manifest 确认版本为 `2.1.1`、提交为
  `860edf210347ec3a64f1cba96fd2160d7672d3d2`、平台为 `macos-arm64`。
- 在线 SHA256：
  - ZIP：`4c4f4bcc74a274af64ec501ce715b47a012298ffd2d7781189f21c612d6ea67e`
  - DMG：`7fdeffe709455393a0548f354e70430aa33a2c68e338496682025ab48c8aadcc`
- 已下载线上 macOS ZIP 并通过发布 SHA256、`unzip -t`、ad-hoc 严格签名及
  `--botmux-coach-smoke-test`；包内 helper 存在且可执行，临时下载文件已物理删除。

## 2026-10-12 v2.2.0 登录注意力引导

状态：已合并 `main` 并发布 `v2.2.0`，本地和线上包验证通过。
分支：`feat/mac-byte-login-attention-v2.2.0`。
功能提交：`f04d832`。
合并提交：`ddea7d7`。
跨平台测试修复及 Tag 提交：`6261e72`。

### 产品决策

1. 不重开 Terminal。重开只会保留旧窗口或再次生成新的登录信息，增加用户误点旧链接
   的概率。
2. 每个实际需要扫码或授权的阶段开始前，把现有 Terminal 激活到前台，并同时清空
   当前屏幕和滚动历史，只展示当前阶段标题、链接或二维码。
3. 不实现永久“始终置顶”。持续置顶会遮挡浏览器授权页面，也可能需要额外辅助功能
   权限；阶段开始时重新激活即可满足提醒需求。
4. 提示音播放前读取 macOS 输出音量与静音状态。静音或低于 `20%` 时临时设为
   `20%` 并取消静音，脚本退出时恢复用户原设置。
5. 已完成并被状态命令跳过的登录阶段不激活窗口、不清屏、不调整音量。
6. Trae、Lark CLI、AgentBuddy 和 Botmux 的登录输出由 PTY helper 监听；检测到
   当前命令首个完整 HTTPS 登录地址后优先用 Google Chrome 打开，失败时回退默认浏览器。
7. 桌宠透明 GIF 不再依赖 QLabel 的增量合成；每帧先用
   `CompositionMode_Source` 清空整块 alpha 画布，再绘制当前帧，避免低配机器残留虚影。

### 实现范围

- Trae CLI 登录。
- Lark CLI 应用初始化。
- Lark CLI 用户 OAuth。
- AgentBuddy 登录。
- Botmux 原生 setup。
- 完整安装与仅 Botmux 配置两种路径。

### 本地验证

- Python `compileall`：通过。
- Python 单元测试：32 项通过。
- Botmux 插件 build、validate 和 MCP smoke：通过。
- AppleScript 音量、静音和 Terminal 激活语句通过 `osacompile` 编译检查。
- 使用假的系统音量接口验证：原始静音且音量为 0 时，登录前设为 20 并取消静音，
  Terminal 激活后，退出时恢复音量 0 和静音。
- 本地 Apple Silicon `.app` 构建、ad-hoc 严格签名、主程序离屏 smoke、coach
  路径 smoke 和 ZIP 完整性检查通过。
- 透明帧回归测试在同一画布连续绘制两个互斥区域，确认第二帧透明区域 alpha 为 0，
  第一帧像素不会残留。
- 登录 URL 回归覆盖分段 JSON 输出、每命令只打开一次、拒绝非 HTTPS/含凭据 URL、
  Google Chrome 优先和默认浏览器回退。
- VIP 测试包：
  `vip-packages/Seele-2.2.0-vip-test-mac_byte-macos-arm64.zip`。
- 包含本轮全部改动的最终本地 Apple Silicon ZIP 与 DMG 已重新构建；签名、主程序
  smoke、coach 路径、ZIP 和 DMG 验证全部通过。
- 最终 VIP ZIP SHA256：
  `b5c69e3f49e06e7425108576bbff86bc59aebb528ea05b5f78701e2feda8d34a`。

### 线上发布验证

- 首次 `main` 跨平台工作流 `38235322667` 仅因轻量测试环境未安装 PyQt5，新增
  渲染测试导入失败；产品代码和本地打包测试均通过。渲染测试改为 PyQt5 可用时运行。
- 修正后的 `main` 跨平台工作流 `38235671299`：Windows、macOS、Ubuntu 全部成功。
- `v2.2.0` 跨平台工作流 `38235832869`：Windows、macOS、Ubuntu 全部成功。
- `v2.2.0` 打包发布工作流 `38235833247`：Windows、macOS 打包及 Release 发布成功；
  macOS 作业安装完整 GUI 依赖并执行透明帧回归。
- Release 包含 8 个预期资产，在线 macOS manifest 确认版本为 `2.2.0`、提交为
  `6261e727e5fb98b81d380f66f24c888b084af297`、平台为 `macos-arm64`。
- 在线 SHA256：
  - ZIP：`3d1e78b4fb6d699b2c8932391cc47ec21e9277fd3ca7b10c59305fbe1bf39b07`
  - DMG：`1348bef99722c4c6350cbc30728cb16099890fba2424395583eed1c9ba87efb4`
- 已下载线上 macOS ZIP 并通过发布 SHA256、`unzip -t`、ad-hoc 严格签名、主程序
  smoke 和 coach 路径 smoke；包内版本为 `2.2.0`，helper 存在且可执行。

## 2026-10-13 v2.2.1 浏览器优先登录

状态：已合并 `main` 并发布 `v2.2.1`，本地和线上包验证通过。
分支：`fix/login-browser-first-v2.2.1`。
功能提交：`37c8ad5`。
合并及 Tag 提交：`e9b5693`。

### 产品决策

1. Trae、Lark CLI 和 AgentBuddy 登录不再主动前置 Terminal；旧记录在后台清理。
2. 登录提示音改为后台播放，官方登录命令立即启动；链接出现后 Chrome 自动到前台，
   用户可以边听语音边完成浏览器授权。
3. 链接 5 秒内未出现或命令失败时，PTY helper 才激活 Terminal；不在此时二次清屏，
   当前二维码、错误信息和手动恢复入口保持可见。
4. Botmux 继续在阶段开始时前置并清理 Terminal，初始语音完整播放后进入原生 setup；
   机器人名称、管理员邮箱和菜单交互仍需要终端可见。
5. 所有路径保留原始终端输出；浏览器优先不等于隐藏或关闭 Terminal。

### 实现内容

- `_shell_voice` 支持后台播放，普通登录阶段使用异步 `afplay`。
- 安装脚本拆分 `prepare_login_audio` 与 `prepare_login_attention`；前者处理音量并
  在后台清掉旧终端记录，后者仅供 Botmux 前置窗口和显示阶段标题。
- `LoginUrlCoach` 增加单调时钟超时、一次性 fallback 和失败完成回调。
- PTY 循环每 0.5 秒驱动 coach `tick()`，子进程结束后调用 `finish(exit_code)`。
- Botmux 的 URL 监听关闭超时 fallback，避免原生交互过程中二次清屏。

### 本地验证

- Python `compileall`：通过。
- Python 单元测试：36 项通过。
- Botmux 插件 build、validate 和 MCP smoke：通过。
- 生成脚本确认只有 Botmux 调用 `prepare_login_attention`；四个普通登录阶段均使用
  后台 `afplay`，并在语音启动后立即运行登录命令。
- 超时、命令失败、链接成功和 Terminal fallback 保留当前二维码均有回归覆盖。
- AppleScript Terminal 激活语句通过 `osacompile`。
- 本地 Apple Silicon `.app` 构建、ad-hoc 严格签名、主程序 smoke、coach 路径、
  ZIP `unzip -t` 和 DMG `hdiutil verify` 全部通过。
- VIP 测试包：
  `vip-packages/Seele-2.2.1-vip-test-mac_byte-macos-arm64.zip`。
- VIP ZIP SHA256：
  `1f544d803727cc1cf03c94e78e4ef21d9c4a2ce83c65ab9aafa01086f228d7b7`。

### 线上发布验证

- `main` 跨平台工作流 `38361430431`：Windows、macOS、Ubuntu 全部成功。
- `v2.2.1` 跨平台工作流 `38361605475`：Windows、macOS、Ubuntu 全部成功。
- `v2.2.1` 打包发布工作流 `38361605533`：Windows、macOS 打包及 Release 发布成功。
- Release 包含 8 个预期资产，在线 macOS manifest 确认版本为 `2.2.1`、提交为
  `e9b5693687761891157013c38fa0355df6c8f5a1`、平台为 `macos-arm64`。
- 在线 SHA256：
  - ZIP：`df8ef2eb09133fff7149afbde1fab853c89ccdffc21e0d604da71ed6d372f048`
  - DMG：`2cb432627dca932db1382977236ed41e4803053138b2ac477f57ddf8e9d40ff5`
- 已下载线上 macOS ZIP 并通过发布 SHA256、`unzip -t`、ad-hoc 严格签名、主程序
  smoke 和 coach 路径 smoke；包内版本为 `2.2.1`，helper 存在且可执行。

## 2026-10-14 tmux 与 Homebrew 前置修复

状态：已通过 PR
[#1](https://github.com/xinna2001/Seele/pull/1) 合并 `main` 并发布 `v2.2.2`；
本地、PR、`main`、Tag 和线上安装资产均验证通过。
分支：`fix/mac-byte-homebrew-tmux-bootstrap`。
首个实现提交：`69dca28`。
合并提交：`b476900`。
共同作者：Cary Cao（GitHub `Carycmj`）。

### 问题结论

1. 用户截图中的缺失项不是 Trae，而是 `tmux`。Botmux daemon 默认使用 tmux 后端，
   tmux 缺失时无法启动。
2. Trae CLI 已有独立检测：`command -v traex` 失败时执行字节内部官方安装脚本。
3. Botmux 尝试自动安装 tmux，但本机没有 Homebrew 时只能输出推荐命令并失败。
4. 截图中的 Homebrew 命令来自官方安装器，当前脚本通过 `bash -n`。虽然安装器支持
   `NONINTERACTIVE=1`，但全新 Mac 无缓存 sudo 权限时可能因 `sudo -n` 直接失败，
   因此实现采用截图中的官方交互命令，保留管理员密码和确认步骤。
5. Homebrew 的 tmux formula 可用；本机 `brew install --dry-run tmux` 成功解析
   稳定版和依赖。

### 实现内容

1. 将 `tmux` 加入 mac_byte 独立命令检测，缺失时进入完整修复路径。
2. tmux 缺失但 Homebrew 已存在：直接执行 `brew install tmux`。
3. Homebrew 也缺失：下载并运行官方交互安装脚本，用户完成必要的管理员权限确认后，
   加载 Apple Silicon 或 Intel 的 `brew shellenv`，再自动安装 tmux。
4. 安装完成后执行 `tmux -V`，并在最终七命令校验中再次检查 tmux。
5. 仅补装依赖且 `~/.botmux/bots.json` 已有效时，保留现有机器人配置并跳过重复
   `botmux setup`。

### 本地验证

- Homebrew 官方安装脚本下载成功，本次 SHA256 为
  `5f333bbe53bc490e51e7ccb1df8779b3dd6ee73a1a7379efda216edb08ccb148`；
  `bash -n` 和 `--help` 均通过，测试后临时文件已删除。
- `brew install --dry-run tmux` 成功解析稳定版及依赖，不修改本机已安装版本。
- 生成的“需要 setup”和“已有配置跳过 setup”两种脚本均通过 `/bin/zsh -n`。
- Python `compileall`：通过。
- Python 单元测试：38 项通过。
- Botmux 插件 build、validate 和 MCP smoke：通过。
- 本地 Apple Silicon `.app` 与 console helper 构建、ad-hoc 严格签名、主程序 smoke
  和 coach 路径 smoke：通过；临时构建目录已物理删除。

### v2.2.2 发布准备

- `VERSION` 和 `CHANGELOG.md` 已更新为 `2.2.2`。
- Python 单元测试：38 项通过，包含 macOS 透明渲染回归测试。
- Botmux 插件 build、validate 和 MCP smoke：通过。
- Apple Silicon `.app` 与 console helper 均确认为 arm64；包内版本、plist
  short version 和 build version 均为 `2.2.2`。
- ad-hoc 严格签名、主程序 smoke、coach 路径 smoke、ZIP 完整性和 DMG 校验均通过。
- VIP 测试包：
  `vip-packages/Seele-2.2.2-vip-test-mac_byte-macos-arm64.zip`。
- VIP ZIP SHA256：
  `877c8f7b62aa5c721ddf9a735b360d7e1ecf267fe511385f9afd0a343eba239e`。
- 最终 ZIP 重新解压后再次通过严格签名、主程序、coach 和 helper smoke；构建与验证
  临时目录均已物理删除。

### v2.2.2 线上发布验证

- 发布提交与 Tag 目标：`cf7c73e98fbfada28563bf4489260b081b0019b5`。
- `main` 跨平台工作流 `38537489923`：Windows、macOS、Ubuntu 全部成功。
- `v2.2.2` 跨平台工作流 `38537656527`：Windows、macOS、Ubuntu 全部成功。
- `v2.2.2` 打包发布工作流 `38537656591`：Windows、macOS 打包及 Release 发布成功。
- Release 包含 8 个预期资产，在线 macOS manifest 确认版本为 `2.2.2`、提交为
  `cf7c73e98fbfada28563bf4489260b081b0019b5`、平台为 `macos-arm64`。
- 在线 SHA256：
  - ZIP：`247705921074f731f943d0afc47e9fb9dcca1b463566d0e80f2b6ae7336c5386`
  - DMG：`abf669a43d59d986a2b98c33dd07d9073023e65a296049e020d9884327067e7e`
- 已下载线上 macOS ZIP 和 DMG，并通过发布 SHA256、`unzip -t`、`hdiutil verify`、
  ad-hoc 严格签名、主程序 smoke、coach 路径 smoke 和独立 helper smoke；包内版本
  与 plist 版本均为 `2.2.2`。

## 2026-10-14 Botmux tmux 半完成安装恢复

状态：已完成本地验证，待 PR 审核。
分支：`fix/mac-byte-botmux-tmux-recovery`。

### 问题结论

1. `v2.2.2` 已能发现并补装 tmux，也会在脚本末尾执行 Botmux 启动与开机自启。
2. 但“已有 Botmux 配置、只缺 tmux”仍被归入 `full`，会额外检查所有工具和登录，
   不符合只恢复运行环境的预期。
3. tmux 补好后如果 Botmux 仍离线，原检测只看命令和配置，会误判为 `ready`，后续
   双击 Seele 不再触发恢复。
4. `botmux status` 在 daemon 离线时仍返回 0，必须检查明确的 supervisor 在线文本，
   不能只依赖退出码。

### 实现内容

1. 新增 `repair` 模式：已有有效 `bots.json` 且只缺 tmux 时进入运行恢复。
2. 命令完整、配置有效但 supervisor 离线时同样进入 `repair`。
3. `repair` 只补装或校验 tmux，然后安装/启用 Seele 插件，执行 `botmux start`、
   `botmux autostart enable` 及两项状态读回。
4. 恢复过程保留现有机器人配置，跳过 Node.js、Trae CLI、Lark CLI、AgentBuddy、
   Botmux 安装、全部登录和 `botmux setup`。

### 本地验证

- 新增 supervisor 在线/离线识别和三种模式路由测试。
- 新增隔离 shell 集成测试：模拟 tmux 缺失，验证只执行 `brew install tmux`，随后
  依次执行插件安装、启动、开机自启和状态读回，并验证状态文件为 `completed`。
- `full` 与 `repair` 生成脚本均通过 `/bin/zsh -n`。
- Python 单元测试：41 项通过。
- Botmux 插件 build、validate 和 MCP smoke：通过。

## 2026-10-14 Trae CLI 旧版本能力修复

状态：已通过 PR
[#3](https://github.com/xinna2001/Seele/pull/3) 合并 `main`，纳入 `v2.2.3`；
PR 的 Windows、macOS、Ubuntu 跨平台 CI 均已通过。
分支：`fix/mac-byte-stale-traex-backend`。
修复提交：`43e849f`。
合并提交：`f53a81b`。

### 问题结论

1. 截图在“安装完成，开始逐项登录”后执行 `traex backend cn`，随后由根命令报
   `unexpected argument 'cn' found`。
2. 可用的 `0.207.1` 及后续版本将 `backend` 识别为子命令；本机留存的 `0.200.19`
   可稳定复现截图：它把 `backend` 当作可选 prompt，再把第二个位置参数 `cn` 判为多余。
3. 原安装逻辑只检查 `command -v traex`。旧二进制只要存在就会跳过官方安装脚本，
   但后续无条件调用新版本才支持的 `backend cn`，因此在首次登录前退出。

### 实现内容

1. 启动依赖检测和安装脚本都增加无副作用能力探测：
   `traex backend cn --help`；旧版 `traex` 会重新进入 `full`，不会误走只配置流程。
2. 命令不存在或能力探测失败时调用官方安装脚本升级；升级后清理 shell 命令缓存。
3. 登录前再次验证命令与 `backend cn` 能力，仍不满足时输出明确校验错误并停止。

### 本地验证

- `0.200.19` 二进制执行探测返回退出码 `2`，错误与截图一致；`0.207.1`、`0.208.1`
  和 `0.209.1` 返回退出码 `0`。
- 新增隔离 shell 测试：模拟已有旧版 `traex`，验证先探测失败、调用官方安装管线、
  传递三项非交互环境变量，再次探测成功。
- Python `compileall`：通过；Python 单元测试：43 项通过。
- `full`、`setup` 和 `repair` 三种生成脚本均通过 `/bin/zsh -n`。

### v2.2.3 发布准备

- `VERSION`、`CHANGELOG.md` 和 mac_byte 安装命令文档已更新为 `2.2.3`。
- GitHub Release 说明已补充 Trae CLI `backend cn` 能力探测与旧版本自动升级行为。
- Python 单元测试 43 项、Botmux 插件 build/validate/MCP smoke、Python `compileall`
  和 `full`/`setup`/`repair` 三种生成脚本语法检查已重新执行并通过。

### v2.2.3 线上发布验证

- 发布分支提交：`ca86e82`；`main` 合并与 Tag 目标提交：`6169d28`。
- 发布分支跨平台工作流 `38556522449` 和 `main` 跨平台工作流 `38556675686`：
  Windows、macOS、Ubuntu 全部成功。
- `v2.2.3` 打包发布工作流 `38556850903`：Windows、mac_byte 打包、smoke、
  资产上传及 GitHub Release 发布全部成功。
- Release 包含 8 个预期资产，两个 manifest 均确认版本 `2.2.3`、提交
  `6169d28f1769556f7f891007256ebb59c3be3d85`，平台分别为 `windows-x64` 和
  `macos-arm64`。
- 已下载全部线上资产；mac_byte 和 Windows 的 SHA256 清单全部匹配，两个 ZIP
  完整性、DMG `hdiutil verify`、macOS app ad-hoc 严格签名、主程序 smoke、Coach
  smoke、包内 `VERSION` 与 plist 版本均通过；主程序和 Coach 均为 arm64。
- 在线 SHA256：
  - mac_byte ZIP：`c8f419ce38899e27d82b62d33c560636c54b8004c953dc19f244f574976decae`
  - mac_byte DMG：`d0076f7302c7c6bb938a2e3ae413bfeca44c04246c8b60d3da7aee8f8822716d`
  - Windows 便携 ZIP：`60f213f33d0051110bffa2660d1666db93b78014dc207db9c408b13ae5aa3628`
  - Windows 安装包：`6a98a6a5929d1fa0519819c29f904c5093842de693ae4e35841e47634daf8ab5`

## 2026-10-19 v2.2.4 Trae CLI PATH、提前结束续跑与二维码转发修复

状态：已提交并推送 `main`，已创建 `v2.2.4` Tag 和 GitHub Release；
本地、跨平台 CI、线上构建及下载复核均通过。
发布提交：`eff3701`。

### 问题结论

1. 用户截图显示 Trae CLI 登录二维码只输出了一部分，随后 `SeeleBotmuxCoach` 抛出
   `BlockingIOError: [Errno 35] Resource temporarily unavailable` 并退出。
2. 根因不是二维码内容错误，而是冻结 console helper 处在 PTY 转发链路中；它先把
   子进程的大块二维码输出写回 Terminal，再喂给登录链接解析器。macOS Terminal
   短暂返回不可写时，原代码没有重试，导致 helper 直接崩溃，也让后续 URL 解析没有
   机会继续执行。
3. 用户手动打开新终端输入 `traex` 报找不到，更像是官方安装器完成后未能把
   `$HOME/.local/bin` 持久写入 zsh 启动文件；桌宠安装脚本自身会临时导入该目录，
   所以重新打开 Seele 后通常能续跑成功。
4. “进程已完成”是 `.command` 脚本提前退出后的 Terminal 文案。此前桌宠只负责打开
   Terminal，没有继续监控外部脚本结果，因此失败后需要用户手动重新打开应用续跑。

### 本地修改

1. `botmux_setup_coach.py` 新增有界 `_write_all`：遇到 `EAGAIN` /
   `BlockingIOError` 时等待 fd 可写并续写，单次最多等待 5 秒，避免无限卡住。
2. PTY 输出处理顺序调整为先 `feed` 给 coach，再写回 Terminal；这样 HTTPS 登录链接
   一出现就会优先打开 Chrome，不再被二维码输出背压阻塞。
3. `mac_byte_bootstrap.py` 在 Trae CLI 安装/升级后尽量把 `$HOME/.local/bin` 写入
   `.zprofile` 和 `.zshrc`，并附带创建 `$HOME/.local/bin/trae-code` shim 转发到
   `traex` 以兼容旧命令名。
4. `Seele.py` 在启动安装终端后继续监控 `bootstrap-status.json`；发现状态为
   `failed` 时自动关闭带本轮 UUID 的 Terminal 窗口，并重新启动一次安装状态机。
5. 版本号升级为 `2.2.4`，并更新 `CHANGELOG.md` 与
   `MAC_BYTE_AUTO_INSTALL_COMMANDS.md`。

### 本地验证

- 针对性单元测试：`tests.test_botmux_setup_coach` 与
  `tests.test_integrations.MacByteBootstrapTests` 共 36 项通过。
- Python 全量单元测试：48 项通过。
- Python `py_compile`：`botmux_setup_coach.py`、`mac_byte_bootstrap.py`、
  `tests/test_botmux_setup_coach.py`、`tests/test_integrations.py` 通过。
- Python `compileall`、Botmux 插件 `npm test`、`git diff --check` 均通过。
- Apple Silicon `.app`、console helper、ad-hoc 签名、主程序 smoke、coach 路径
  smoke 和 VIP ZIP 完整性校验均通过。
- 本地打包时将 `PYINSTALLER_CONFIG_DIR` 指向工作区内
  `build/pyinstaller-config`，避免 PyInstaller 清理默认工作区外缓存触发沙箱限制。
- VIP 测试包：
  `vip-packages/Seele-2.2.4-vip-test-mac_byte-macos-arm64.zip`。
- VIP ZIP SHA256：
  `c52015d4e5c632b5fcdd2dad1edfc45d41cf3c6c3482218bdfb19eb29a11c304`。

### 线上发布验证

- `main` 跨平台测试工作流 `39239202439`：Windows、macOS、Ubuntu 全部成功。
- `v2.2.4` 跨平台测试工作流 `39239205955`：Windows、macOS、Ubuntu 全部成功。
- `v2.2.4` 打包发布工作流 `39239205939`：Windows、mac_byte 打包、smoke、
  资产上传及 GitHub Release 发布全部成功。
- Release：
  `https://github.com/xinna2001/Seele/releases/tag/v2.2.4`。
- Release 包含 10 个预期资产；两个 manifest 均确认版本为 `2.2.4`、提交为
  `eff3701b3b6f57552637396fb5ad1cd2cd2340c5`，平台分别为 `windows-x64` 和
  `macos-arm64`。
- 在线 macOS ZIP 与 DMG 已重新下载，并通过发布 SHA256、ZIP 完整性、
  `hdiutil verify`、ad-hoc 严格签名、主程序 smoke 和 coach 路径 smoke；包内
  `VERSION`、plist short/build version 均为 `2.2.4`，主程序和 Coach 均为 arm64。
- 在线 SHA256：
  - mac_byte ZIP：`3d21b0fe20e1621aca6b61195c9bd31262554675f35c5340a84ec02050375243`
  - mac_byte DMG：`17e4d4cdc7ba8562d12e09f94377c125ada5ac1cb0489ec2cf2b1e4e3c632789`
  - Windows 便携 ZIP：`5796cac39ddd791496ade0c5261cabc9b7be390d9fe8baa42a0038aebd925734`
  - Windows 安装包：`d1f95a1984c2149ecb7f93213b1d15bbcbe77966f8227745b50596ae4bf0837c`

## 2026-10-19 v2.2.5 Homebrew 密码语音与确定性选项自动化

状态：已提交并推送 `main`，已创建 `v2.2.5` Tag 和 GitHub Release；本地、
跨平台 CI、线上构建及下载复核均通过。

### 问题结论

1. 全新 Mac 安装 tmux 时会先进入 Homebrew 官方安装器。`sudo` 输出 `Password:`
   后原流程没有语音，用户不知道需要输入电脑开机密码，且密码输入时终端不会回显。
2. Homebrew 当前官方确认提示是
   `Press RETURN/ENTER to continue or any other key to abort:`。该提示必须发送回车；
   输入 `Y` 会被视为“任意其他键”并中止。实现仅在真正的 `[Y/n]` 或 `[y/N]`
   提示中发送 `y`。
3. Botmux `3.43.0` 的应用来源、失效登录态重新扫码、失败返回和中国飞书租户都有
   确定默认项；账号确认、机器人名称、管理员邮箱和 App 凭证仍需要用户判断或输入。

### 实现内容

1. console helper 新增 `--homebrew-install` 模式，在 PTY 中运行 Homebrew 官方脚本；
   检测到 `Password:` 时播放独立语音，但密码始终由用户直接输入且不记录。
2. Homebrew helper 对官方 `RETURN/ENTER` 文案自动按回车，对明确的 `[Y/n]` /
   `[y/N]` 自动输入 `y`，未知问题不自动回答。
3. Botmux coach 按提示文字自动选择“一次扫码创建新应用”、唯一的“重新扫码”、
   默认的“返回应用来源”和“飞书（中国版）”，不依赖菜单序号。
4. 自动项不再播放要求用户手动选择的旧语音；身份、名称、邮箱和密钥提示仍保留。
5. 新增 `mac_byte_homebrew_password_16k.wav`，格式为 16 kHz、Int16、双声道 WAV；
   版本号升级为 `2.2.5`，同步更新更新记录、语音说明和安装命令文档。

### 本地验证

- Homebrew 官方脚本 SHA256：
  `5f333bbe53bc490e51e7ccb1df8779b3dd6ee73a1a7379efda216edb08ccb148`；
  已复核 `wait_for_user` 只接受 CR/LF。
- Homebrew 和 Botmux 自动输入均有真实 PTY 子进程测试；敏感输入不自动回答测试通过。
- 定向测试 `tests.test_botmux_setup_coach` 与
  `tests.test_integrations.MacByteBootstrapTests`：41 项通过。
- 实际构建 `.venv` 的 Python 全量单元测试：53 项通过；定向 `compileall` 通过。
- Conda `Seele` 环境的全量 `compileall` 通过；单元测试仅透明渲染用例因该环境缺少
  `PyQt5.QtCore` 无法导入，实际构建 `.venv` 中同一用例已单独通过。
- Botmux 插件 build、validate 和 MCP smoke 通过；`git diff --check` 通过。
- `full`、`setup` 和 `repair` 三种生成脚本均通过 `/bin/zsh -n`。
- 新语音经 `afinfo` 确认为 2 声道、16000 Hz、Int16，时长 10.6195 秒。
- Apple Silicon `.app` 和 console helper 均为 arm64；包内版本、plist short/build
  version 均为 `2.2.5`；ad-hoc 严格签名、主程序 smoke、coach 路径 smoke 和
  Homebrew helper 模式 smoke 全部通过。
- VIP ZIP 已通过完整性检查，并从全新解压目录重复通过签名、版本、架构、语音资源
  和全部 smoke：
  `vip-packages/Seele-2.2.5-vip-test-mac_byte-macos-arm64.zip`。
- VIP ZIP SHA256：
  `da2a562286d62cad3796e1b633a3f079ad05aeb40338eb0801f8cc6d747ed742`。

### 线上发布验证

- 发布提交：`6a62ffd`。
- `main` 跨平台测试工作流 `39256399189`：Windows、macOS、Ubuntu 全部成功。
- `v2.2.5` 跨平台测试工作流 `39256639215`：Windows、macOS、Ubuntu 全部成功。
- `v2.2.5` 打包发布工作流 `39256639374`：Windows、mac_byte 打包、smoke、
  资产上传及 GitHub Release 发布全部成功。
- Release：`https://github.com/xinna2001/Seele/releases/tag/v2.2.5`，包含 10 个预期资产。
- 在线 manifest 确认版本为 `2.2.5`、提交为
  `6a62ffdb7db6fafc5674d84cbec85c8441aa926c`、平台为 `macos-arm64`。
- 已重新下载在线 macOS ZIP 与 DMG；两个文件的发布 SHA256、ZIP 完整性、
  `hdiutil verify`、ad-hoc 严格签名、主程序 smoke 和包内 `VERSION=2.2.5` 均通过。
- 在线 SHA256：
  - mac_byte ZIP：`fe4dbab931e3f3410e391b271a1ed060260056dd8efbe95cba312a5e4d6557ca`
  - mac_byte DMG：`7e83d0ba72fd99b4ddbc0c1dd45fdb40ea561628d6c8cfe30906a5fcbb286acf`
  - Windows 便携 ZIP：`56334cc9babc6516f0c868a724e71ac70b1e2a52b3c35baab81d4558fc4d7df7`
  - Windows 安装包：`30ccd0ed600a87913ac14f3fb32e9a4361dd566486c47bc7410ad73978937d40`

## 2026-10-19 v2.2.6 角色窗口响应式布局与关闭入口

状态：已提交并推送 `main`，已创建 `v2.2.6` Tag 和 GitHub Release；本地、
跨平台 CI、线上构建、latest 别名及下载复核均通过。

### 问题结论

1. `RoleSwitchWindow.main` 固定窗口 `800×750`、最小尺寸同样为 `800×750`，内部角色
   卡片固定 `720×320`；macOS Retina 按逻辑像素渲染后会占据大部分屏幕。
2. 角色窗口和后续音色说明弹窗都使用 `FramelessWindowHint`，系统标题栏和关闭按钮
   被移除。代码虽然支持 `Esc`，但界面没有可见关闭入口，用户只能选择角色触发关闭。
3. 三个角色按钮固定横排且高度为 82，在小屏窗口中没有重排规则。

### 实现内容

1. 新增屏幕可用区域计算：按当前角色窗口所属显示器或鼠标所在显示器选择尺寸并居中，
   上限为 `640×460`，同时保留 32 像素安全边距。
2. 角色窗口和音色说明弹窗新增右上角系统关闭图标；点击关闭或按 `Esc` 都不修改角色。
3. 窗口宽度小于 480 时，三个角色按钮自动从横排切换为纵排，并同步重新计算卡片高度。
4. 角色按钮改为明确的白底、蓝色边框和 18 像素文字，不再依赖 macOS 当前主题隐式
   提供按钮边框。
5. 音色说明弹窗同步改为响应式尺寸、紧凑字号与按钮高度，保留“知道了”操作。
6. 版本号升级为 `2.2.6`，更新 `CHANGELOG.md` 和 mac_byte 命令文档版本。

### 当前验证

- 新增响应式尺寸纯函数测试，以及窗口不超出屏幕、横竖布局重排、关闭不写状态测试。
- macOS/PyQt 定向渲染测试：3 项通过。
- 已生成并检查默认 `496×408`、小屏 `420×360` 和音色说明三张像素截图：
  关闭按钮均可见，角色名称完整，无按钮或文字重叠。
- 实际构建 `.venv` 的 Python 全量单元测试：55 项通过；定向 `compileall` 通过。
- Botmux 插件 build、validate 和 MCP smoke 通过；`git diff --check` 通过。
- Apple Silicon `.app` 和 console helper 均为 arm64；包内版本、plist short/build
  version 均为 `2.2.6`；ad-hoc 严格签名、主程序 smoke、coach 路径 smoke 和
  Homebrew helper 模式 smoke 全部通过。
- VIP ZIP 已通过完整性检查，并从全新解压目录重复通过签名、版本、架构和全部 smoke：
  `vip-packages/Seele-2.2.6-vip-test-mac_byte-macos-arm64.zip`。
- VIP ZIP SHA256：
  `0b6d5698b31ccd0f769993a1e0114f659243d071164fc2c2016fa6f58621daea`。

### 线上发布验证

- 发布提交：`04a00f7`。
- `main` 跨平台测试工作流 `39257471075`：Windows、macOS、Ubuntu 全部成功。
- `v2.2.6` 跨平台测试工作流 `39257656513`：Windows、macOS、Ubuntu 全部成功。
- `v2.2.6` 打包发布工作流 `39257656618`：Windows、mac_byte 打包、smoke、
  资产上传及 GitHub Release 发布全部成功。
- Release：`https://github.com/xinna2001/Seele/releases/tag/v2.2.6`，包含 10 个预期资产；
  GitHub latest 已指向 `v2.2.6`。
- 在线 manifest 确认版本为 `2.2.6`、提交为
  `04a00f7ef08280abf6cd1c9b0d3feb0fe697d205`、平台为 `macos-arm64`。
- `releases/latest/download/Seele-mac_byte-macos-arm64.zip` 已重定向到 `v2.2.6`
  的稳定别名资产，版本化与稳定别名的 GitHub digest 一致。
- 已重新下载在线 macOS ZIP 与 DMG；两个文件的发布 SHA256、ZIP 完整性、
  `hdiutil verify`、ad-hoc 严格签名、主程序 smoke、包内 `VERSION`、plist short/build
  version 均为 `2.2.6`；主程序和 Coach 均为 arm64。
- 在线 SHA256：
  - mac_byte ZIP：`aeec9164d670fd99cbdcda2d29180eed95029b9fe0c4d2ab801dc9593c1c4678`
  - mac_byte DMG：`d5f0b1c9d1f770245cba04550229d3ff2a88ebc5bed504c8dd096f1d006cb4f1`
  - Windows 便携 ZIP：`eeeaef5205aa5eb1d866368f61ac4ec542c68aa8cee4427ac89bfb53263581eb`
  - Windows 安装包：`1e1843d933c72148e9aabcfa1ae8af4a2c176f8150f63b252490595dae8540f7`

## 2026-10-20 v2.3.0 Botmux 任务面板

状态：已完成本地修改与验证，准备提交推送 `main`、创建 `v2.3.0` Tag 和 GitHub Release。
按用户明确授权直接发布；真机验收在发布后进行，VIP 包同时产出供实跑。

### 需求与决策

1. 用户设想：一个能看到“谁在哪个群发起了什么任务、现在什么状态”的面板，24 小时无
   反馈的任务自动从面板隐藏，点一下直接跳转到对应飞书话题以找回上下文。
2. 结论：在桌宠（Seele）里做，不改 Botmux 本体。依据——Botmux `/api/sessions`
   已返回全部所需字段（`botName`、`chatDisplayName`、`status`、`lastMessageAt`、
   以及已拼好的 `feishuThreadLink`/`feishuChatLink` 深链）；需求主要是个人化的视图层
   和“有主见的默认”（如 24h 过滤），不适合作为上游所有用户的默认行为；桌宠已内置
   `botmux_client` 的 REST/SSE 管道，净新增视图即可，且与 Botmux 频繁升级解耦。
3. 入口定为右键菜单「任务面板」→ 独立窗口；状态归并为口语化「进行中 / 等你回复 /
   空闲」，底层仍映射 Botmux 原始字段。

### 实现内容

1. `botmux_client.py`：
   - 新增 `discover_local_dashboard()`：读取 `~/.botmux/.dashboard-port` 与
     `.dashboard-token`。`load_config()` 增加 `discover=True`，在未显式配置时自动
     连通本机 Dashboard（显式文件/环境变量优先）。修复“未随包附带
     `botmux_config.json` 导致默认 `enabled=false`、端口硬编码 `7891`”的连通缺口。
   - 新增纯函数 `safe_feishu_link()`（仅接受 `https://applink.feishu.cn/` 深链）、
     `classify_task_group()`（attention/working/idle）、`format_relative_time()`
     和 `build_active_tasks()`（丢弃 closed 与超 24h、可按 bot 过滤、三组排序）。
   - `BotmuxSessionState` 增加 `active_tasks()` 复用上述视图；`summary()` 行为不变。
2. 新增 `TaskPanelWindow.py`：无边框圆角半透明窗口，沿用角色窗口的美学与
   `_fit_to_screen` 自适应；后台线程 `_SessionFetcher` 拉取会话不阻塞 UI；15 秒自动
   刷新；空列表、离线和无链接任务均有降级显示；点击行用 `open_external` 打开深链。
3. `Seele.py`：右键菜单新增「任务面板」入口与 `OpenTaskPanel()`；右键菜单改为圆角、
   品牌蓝悬停的统一样式。
4. 版本号升级为 `2.3.0`（新增功能，MINOR 递增、PATCH 归零）。

### 本地验证

- Python `compileall`：通过。
- Python 单元测试：64 项通过（新增任务面板数据层 8 项、面板 UI 渲染/跳转 1 项）。
- Botmux 插件 build、validate 和 MCP smoke：通过。
- 对运行中的本机 Botmux 实测：自动发现 Dashboard，拉取 1384 行会话，过滤出 24h 内
  29 条活跃任务，分组、深链与相对时间均正确。
- 离屏渲染任务面板与右键菜单截图，确认样式与现有风格一致、新入口可见。

### 线上发布验证

- 发布提交：`046ec22`；`main` 推送 `dab1b1d..046ec22`，Tag `v2.3.0`。
- `v2.3.0` 打包发布工作流 `39432992027`：Windows、mac_byte 打包、smoke、资产上传及
  GitHub Release 发布全部成功。
- Release：`https://github.com/xinna2001/Seele/releases/tag/v2.3.0`，包含 10 个预期资产；
  GitHub latest 指向 `v2.3.0`。
- 在线 manifest 确认版本 `2.3.0`、提交 `046ec225e435ce4c59e7018b900ee7f02e972b13`、
  平台 `macos-arm64`、签名 `ad-hoc`。
- 已重新下载在线 macOS ZIP，发布 SHA256 与 `unzip -t` 均通过；临时文件已删除。
- 在线 SHA256：
  - mac_byte ZIP：`28e14859a5618fd3b1b7b427801bf80b446a0a1d41a08296dc9bc9d4757ed292`
  - mac_byte DMG：`81414ec56cb1b648f5d0c24ab65fc9efd9f17fc81367cb4e2bc76e0a845130d9`
- 本地 VIP 测试包：
  `vip-packages/Seele-2.3.0-vip-test-mac_byte-macos-arm64.zip`
  （SHA256 `fdfff100fca1c8314fd3973586703a42a8405f0cf88a875e901d95ee51009d98`）。

## 2026-10-21 v2.3.1 任务发起者补全

状态：用户已确认提交；已提交并推送 `main`，创建 `v2.3.1` Tag 和 GitHub Release；
本地、跨平台 CI、线上构建与下载复核均通过。

### 问题证据

1. 用户实际验收 `v2.3.0` 后确认状态、群名和飞书话题跳转均正常，但任务卡片没有显示
   “最开始是谁艾特 Agent 发起任务”。
2. Dashboard `/api/sessions` 已返回 `ownerOpenId`。Botmux 创建普通飞书会话时会把
   当时的消息发送者写入该字段，后续其他人追问不会改变它；不能使用
   `quoteTargetSenderOpenId` 或最后一条消息发送者代替。
3. 同一会话的 `replyTargets[].participants[]` 保存参与者的 `openId` 和 `name`；
   汇总全部会话后可建立稳定的 `open_id → 姓名` 索引。
4. 本机真实数据共 1396 条会话、16 条 24 小时活跃任务；16 条的 `ownerOpenId`
   均成功解析为姓名，当前覆盖率 100%。

### 实现内容

1. `botmux_client.py` 新增 `participant_name_index()` 和
   `resolve_task_initiator()`；`build_active_tasks()` 输出
   `initiatorName`/`initiatorOpenId`。
2. 普通飞书任务严格使用 `ownerOpenId` 识别最初发起者，并允许从其他历史会话跨行
   补全姓名；定时任务显示“系统定时”，无姓名时显示“未知用户”。
3. `TaskPanelWindow.py` 卡片首行改为“发起者：姓名 · 群名”，悬停提示分别显示完整
   发起者和会话名称。
4. 版本升级为 `2.3.1`（补丁修复，PATCH 递增）。

### 本地验证

- Python `compileall`：通过。
- Python 单元测试：66 项通过；新增跨会话发起者补名与定时任务回退测试。
- Botmux 插件 build、validate 和 MCP smoke：通过。
- 真实 Dashboard 构建 16 条活跃任务耗时约 140ms（包含 Dashboard 请求），发起者
  姓名解析覆盖率 100%。
- 使用真实数据离屏渲染 `560×620` 面板截图，确认“发起者 + 群名 + 状态 + 时间”
  无重叠。
- Apple Silicon `.app` 和 Coach 均为 arm64；包内版本与 plist short/build version
  均为 `2.3.1`；ad-hoc 严格签名、主程序 smoke、Coach 路径 smoke 和 ZIP 完整性
  均通过。
- VIP 测试包：
  `vip-packages/Seele-2.3.1-vip-test-mac_byte-macos-arm64.zip`
  （SHA256 `b3197edf8062e32bd7b815e20b6fbca0dee6a81e55ce27af151a1fa933a497ff`）。

### 线上发布验证

- 功能提交与 Tag 目标：`16d2a6220e0725b4bfd93e2632e35c66915670af`。
- `main` 跨平台测试工作流 `39551162562`、`v2.3.1` 跨平台测试工作流
  `39551165705`：Windows、macOS、Ubuntu 全部成功。
- `v2.3.1` 打包发布工作流 `39551165593`：Windows、mac_byte 打包、smoke、
  资产上传及 GitHub Release 发布全部成功。
- Release：`https://github.com/xinna2001/Seele/releases/tag/v2.3.1`，包含 10 个
  预期资产；GitHub latest 已指向 `v2.3.1`。
- 在线 manifest 确认版本 `2.3.1`、提交
  `16d2a6220e0725b4bfd93e2632e35c66915670af`、平台 `macos-arm64`、签名 `ad-hoc`。
- 已重新下载在线 macOS ZIP；发布 SHA256 与 `unzip -t` 均通过，验证临时文件已删除。
- 在线 SHA256：
  - mac_byte ZIP：`f85012eaa533e3590cec8ff4f9eb63890a985eafe903cdbce2e13d242ef4fb56`
  - mac_byte DMG：`da3c03bc3a9d9cab83ef8ed4804ac4ee3465f266dca88a3123250b384095c08d`

## 已实现的 2.0 架构

- `Seele.py`：PyQt 桌宠、托盘菜单、气泡和 Botmux 状态展示。
- `mac_byte_bootstrap.py`：字节内部 macOS 首次启动检测、安装和登录引导。
- `botmux_client.py`：Botmux Dashboard REST、SSE、任务触发、本机 Dashboard 自动发现
  和任务面板数据视图（`build_active_tasks` 等）。
- `TaskPanelWindow.py`：Botmux 任务面板窗口；展示 24h 内活跃任务并跳转飞书话题。
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

1. 在全新字节 Apple Silicon 电脑验证 `v2.3.1` 完整安装和失败续跑。
2. 验证 Trae、Lark CLI、AgentBuddy 的真实首次登录和自动续跑。
3. 验证 Homebrew 密码语音、自动确认、Botmux 扫码及全部确定性默认项。
4. 验证角色窗口在实际 Retina 屏幕上的尺寸、关闭按钮和小屏重排。
5. 在真机验证任务面板：自动发现本机 Dashboard、24h 过滤、状态分组、点击跳转飞书话题。
6. 普通公网 macOS 版本、Developer ID 签名和公证仍未完成。

## 新话题恢复步骤

1. 先阅读本文件和 `.trae/skills/seele-botmux/SKILL.md`。
2. 运行 `git status --short --branch`，保护所有本地未提交修改。
3. 不以远端 Release 安装包覆盖当前工作区的未提交修改。
4. 按“后续待验收”在全新字节 Apple Silicon 电脑继续验证当前正式版本；再次发布前
   先确认工作区、Tag 和线上 Release 状态，避免覆盖未提交修改或重复创建版本。
