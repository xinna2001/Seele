# 更新记录

## 2.1.1

- 修复 macOS 冻结应用优先把 `Contents/Frameworks` 误判为资源根目录，导致
  `SeeleBotmuxCoach` 从不存在的 `Frameworks/bin` 启动后立即退出的问题。
- `.app` 布局现在优先使用标准 `Contents/Resources`，兼容 macOS App Translocation。
- 发布流程新增冻结主程序的 coach 路径与可执行权限 smoke test。

## 2.1.0

- 首次启动改为独立检测 Node.js、npm、Trae CLI、Lark CLI、AgentBuddy 和 Botmux，
  已安装组件不再重复安装。
- Lark CLI 应用初始化结束后增加本机配置独立复核，不再把网页成功误判为配置已落盘。
- Lark CLI 初始化每轮最多执行一次；未检测到本地配置时明确停止并提示重启 Seele
  续跑，避免自动重试造成重复创建应用。
- 安装完成后统一复核六个命令的解析路径，缺失任何一项都会在进入登录前失败退出。
- 安装 Terminal 标题改为从 `VERSION` 动态读取版本号。

## 2.0.3

- 修复仅适用于 macOS 的冻结 helper 路径测试在 Windows CI 上使用反斜杠解析而失败的问题。
- 产品实现与 `2.0.2` 相同；`2.0.2` Tag 未生成 Release，正式测试包使用 `2.0.3`。

## 2.0.2

- Trae CLI、Lark CLI 和 AgentBuddy 改用官方登录子命令与状态校验，授权完成后自动继续。
- Trae CLI 安装使用官方非交互环境变量，不再启动首次使用 TUI。
- npm 内部源改为单次安装参数，不再永久修改用户全局 registry。
- Botmux 原生 setup 接入 PTY 提示监听和 11 条动态语音，不记录用户输入或凭据。
- 固定自动选择 `TRAE (CoCo) -> traex`，并自动接受 Botmux 默认工作目录。
- 移除所有阶段间人工回车暂停，配置完成后自动安装插件、启动 Botmux 并开启自启动。
- 增加 17 个安装语音的格式、存在性和 PTY 自动衔接回归测试。

## 2.0.1

- 移除右键菜单中的“安装或配置 Botmux”，仅保留 `mac_byte` 首次启动自动检测。
- 接入 6 个真实的 16 kHz 安装提示音，并修正代码与实际文件名不一致的问题。
- 增加语音文件存在性回归测试和本地开发交接记录。
- 修复 macOS Retina 屏幕上角色 GIF 被低分辨率放大后发糊的问题。
- 精简 `mac_byte` 右键菜单，隐藏旧版语音与启动引导入口，并停止旧语音输入监听。
- 移除菜单的固定大字号和宽间距，恢复由系统 DPI 控制的紧凑尺寸。
- 缩小状态气泡字体、宽度和留白，并限制动态高度。
- 将气泡绑定为希儿的无焦点从属浮窗，稳定二者层级并保持 macOS 非激活状态可见。

## 2.0.0

- 增加字节内部 `mac_byte` 发行版。
- 首次启动自动检测 Botmux；未安装时打开 Terminal 执行最新版安装链路。
- Trae CLI、Lark CLI、AgentBuddy 和 Botmux 登录流程在 Terminal 中展示链接或二维码。
- 每个登录阶段提供语音文件占位，并在完成后等待用户确认再继续。
- 统一 PyInstaller 资源定位，并使用 PyQt5 替代 Tk 启动等待页。
- 增加 macOS arm64 `.dmg`、`.zip` 和打包后 smoke test。

## 1.0.0

- 保留原有桌面宠物、角色切换、语音输入和影刀 RPA 工作流能力。
- 支持 Botmux 会话状态、SSE 事件和未匹配输入转发。
- 提供带白名单、Token 与幂等保护的本地 RPA Bridge。
- 提供独立的 Seele Botmux Skill/MCP 插件。
- 增加 Windows x64 安装版、便携版和 GitHub Release 自动发布流程。
