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
- 远端基线提交：`8588a7d`，对应 `v2.0.0`
- `v1.0.0`：提交 `0619912`
- GitHub 已存在 `v1.0.0` 和 `v2.0.0` Release。
- `v2.0.0` 在“所有后续修改先本地验收”的约束提出前已经发布。不要擅自删除或改写。

## 2026-09-29 修复批次

状态：用户已明确批准上推独立分支并合并 `main`。
目标分支：`fix/mac-byte-bootstrap-audio`。

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

## 已实现的 2.0 架构

- `Seele.py`：PyQt 桌宠、托盘菜单、气泡和 Botmux 状态展示。
- `mac_byte_bootstrap.py`：字节内部 macOS 首次启动检测、安装和登录引导。
- `botmux_client.py`：Botmux Dashboard REST、SSE 和任务触发。
- `rpa_service.py`：影刀工作流白名单、幂等和状态管理。
- `rpa_bridge.py`：Botmux 到本地 RPA 的受限 HTTP Bridge。
- `botmux-skill/`：Seele 的 Botmux 插件；不修改 Botmux 内核。

`mac_byte` 完整安装流程使用内网命令安装 Node.js、Trae CLI、Lark CLI 和
AgentBuddy，并从 npm 官方源安装 `botmux@latest`。登录链接或二维码保留在
Terminal 中展示，每个登录步骤结束后暂停，等待用户按回车继续。

## 验证记录

2026-09-29 本地验证：

- `python -m compileall`：通过。
- Python 单元测试：17 项通过。
- 6 个语音文件存在性测试：通过。
- `git diff --check`：通过。
- 本轮尚未重新构建包含真实音频的 `.app`，`dist/Seele.app` 可能是修改前的本地构建产物。

常用验证命令：

```bash
.venv/bin/python -m compileall -q Seele.py mac_byte_bootstrap.py tests
.venv/bin/python -m unittest discover -s tests -v
git diff --check
```

## 后续待验收

1. 在隔离环境验证“未安装 Botmux”时自动打开完整安装 Terminal。
2. 验证每个登录阶段播放的语音内容与实际步骤一致。
3. 验证登录链接、二维码和每步按回车暂停的交互。
4. 验收通过后再重新构建 `mac_byte` `.app`、DMG 和 ZIP。
5. 由用户决定是否更新现有 `v2.0.0`，或发布新的修订版本。
6. 普通公网 macOS 版本、Developer ID 签名和公证仍未完成。

## 新话题恢复步骤

1. 先阅读本文件和 `.trae/skills/seele-botmux/SKILL.md`。
2. 运行 `git status --short --branch`，保护所有本地未提交修改。
3. 不以远端 `v2.0.0` 覆盖当前工作区。
4. 按“待用户验收”继续，不提前推送或发布。
