# Windows 字节版安装与续装

本地开发版本：2.4.0，尚未发布。适用 Windows 11 x64，Windows 10 22H2 x64 可参考。
安装 CLI 需要字节网络；WSL 中也必须能够访问安装源和授权网站。

## 运行方式

便携 VIP 测试包：完整解压到一个固定目录，双击 `启动希儿.vbs`。
包内包含 Windows Python 与 Qt，Windows 主机无需另装 Python。
如无窗口，双击 `查看启动问题.cmd`，保留终端错误。
路径中有空格或中文也支持。因为重启续装任务引用这个目录，安装完成前不要移动它。

源码：安装依赖后，将 `SEELE_EDITION=windows_byte` 再运行 `python run_exe.py`。
正式 EXE 构建流程已接入 GitHub Actions，但本次本地测试没有运行远程发布。

## 自动处理的流程

1. 根据当前 Windows 用户注册的发行版，选择已保存的发行版、`Ubuntu-24.04`
   或已有 Ubuntu。可用 `SEELE_WSL_DISTRO` 指定准确名称，名称不存在会停止。
2. 检查 WSL 版本并实际执行 Linux 探针。已有 WSL2 继续使用；WSL1 保留数据转换。
3. 缺系统组件时，仅对启用组件与安装 WSL 系统部分请求 UAC。
   若 Windows 要求重启，先保存进度；用户自行重启，同一用户登录后自动继续。
   同一次开机重复打开不会再次安装。不能绕过 Windows 首次启用虚拟化的重启。
4. 缺发行版则安装 `Ubuntu-24.04`；默认普通 Linux 用户保留。
   默认 root 时，请输入已有用户名，或创建新用户并设置 Linux 密码。
5. 合并 `/etc/wsl.conf` 的 systemd 与默认用户设置，保留网络与挂载设置。
   配置变化时只重启目标发行版；请先保存该发行版中的工作。
6. 安装 Linux 依赖、官方自包含 Botmux、Node 22、Trae CLI、Lark CLI 与 AgentBuddy。
   已有兼容组件跳过。按终端提示完成本人登录、扫码、名称和邮箱输入；
   Windows Chrome 优先打开授权网页，固定 Botmux 菜单项自动填写。
7. 保留已有 `.botmux/bots.json`，安装 Seele 插件并启用 systemd 用户服务、
   watchdog 和 linger。CLI 及 Botmux 数据放在 Linux 用户目录。
8. 注册当前 Windows 用户登录任务和每 5 分钟恢复触发器。
   前台 Linux 保活进程让 WSL 持续存活；服务由 systemd/watchdog 恢复。
   任务不保存 Windows 密码，只在该用户登录后运行。
9. 桌宠从选定用户的 WSL UNC 文件读取 Dashboard 动态端口与令牌，
   通过 Windows localhost 连接。显式 `botmux_config.json` 或环境变量优先。

## 失败续装与运维

安装状态：`%LOCALAPPDATA%\Seele\windows_byte\status.json`。
桌宠右键选择“继续 Botmux 安装”。失败保留组件、数据和配置。
续装计划任务被企业策略拒绝时，退回当前用户 HKCU Run 启动项；
长期保活计划任务注册失败会显示失败，需要修复企业策略后重试。

安装成功删除临时续装任务，保留 `Seele-Botmux-WSL` 长期任务。
Windows 睡眠或关机会中断服务，下一次同一用户登录后恢复。
便携包停止自动唤醒可在任务计划程序中禁用 `Seele-Botmux-WSL`；
EXE 安装版卸载时移除 Windows 任务，保留 WSL 和 Linux 数据。

如果 Dashboard 无法连接，检查 WSL localhost 转发与企业网络配置。
本安装器不改防火墙、全局 `.wslconfig`、电源设置或其他发行版。
RPA Bridge 默认关闭；Windows 与 WSL 之间的影刀网络配置仍需单独设置。

## 真机验收

本地模拟测试无法代替以下 Windows 行为：

- 新机器首次启用 WSL → 显示重启提示 → 重启并用同一用户登录 → 自动续装。
- 已部署 Botmux 的机器复用原 Ubuntu、普通用户与机器人，避免重复 setup。
- 首次用户名/密码设置、Trae/Lark/AgentBuddy 授权、飞书扫码后真实回复。
- 关闭安装窗口、退出桌宠后，Botmux 服务仍在线；Windows 重启登录后自动恢复。
- `wsl --terminate <发行版>` 后，计划任务重试/恢复触发器重新唤醒。
- 桌宠任务面板连接 WSL Dashboard，点击任务能打开飞书对应话题。

参考用户实机成功指南 `BotMux-WSL-Windows-部署与长期运行指南.md`，
以及 Microsoft 的 WSL 安装、systemd 与 Task Scheduler 文档。
微软说明 systemd 服务本身不会让 WSL 保持运行，因此增加了前台保活进程。
