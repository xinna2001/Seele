# 更新记录

## 未发布

- 移除右键菜单中的“安装或配置 Botmux”，仅保留 `mac_byte` 首次启动自动检测。
- 接入 6 个真实的 16 kHz 安装提示音，并修正代码与实际文件名不一致的问题。
- 增加语音文件存在性回归测试和本地开发交接记录。

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
