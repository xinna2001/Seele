### Seele

##### 谁不喜欢能帮你工作又听话的赛博妹妹呢\~

***

这是一个贩卖焦虑的时代。在 AI 时代来临的这个时刻，每一天听到最多的就是某某技术已过时，某某技术颠覆人们认知。

诚然，已有的 AI 大模型在很大的程度上方便了我们的程序员的工作。但是对于很多未曾接触过技术领域的同学来说。所谓 AI 提效，不过是空中楼阁罢了。

哪怕是对于我个人而言。有许许多多的新技术我都没有用过，就如skill，小龙虾。

但是这并不能影响什么，倘若智能手机是未来的主旋律，那没有抢到首批 iPhone 对我们有什么影响呢

影刀RPA 一个2019年设计出来的产品。在这个所谓 AI 的时代依旧能打。

有些东西永远弥足珍贵，就好像你和我\~

谢谢大家使用希儿！本项目使用语音识别+TTS+AI大模型+影刀RPA，实现的通过语音可以让电脑帮你执行工作流的功能！

只要将你的工作教给电脑一遍，它就能学会，并且100%复现，个人认为比有幻觉情况的大模型在执行复制任务时更有优势

另外，我也希望通过影刀RPA构建开源生态，打破技术壁垒，实现技术平权，让所有人都能体验技术带来的快乐！

## 当前架构

Seele 现在由三层组成：

- **桌面宠物**：PyQt5 界面、角色 GIF、气泡、托盘和输入窗口。
- **Botmux 连接**：订阅 Botmux Dashboard 的会话与 SSE 事件，展示机器人正在工作、等待确认或离线等状态；未匹配本地工作流的输入可以转给 Botmux Agent。
- **RPA 桥接**：仅允许调用 `uid.json` / `file_name.json` 中登记的影刀工作流，并通过带 token 的本地 HTTP 接口提供给 Botmux MCP。

Botmux 扩展位于 [`botmux-skill/`](botmux-skill/)，不需要修改 Botmux 的 daemon、worker 或 CLI adapter。

## 安装

推荐使用 Conda 和 Python 3.11：

```bash
conda create -n Seele python=3.11
conda activate Seele
pip install -r requirements.txt
python Seele.py
```

Linux 还需由系统包管理器安装 Qt/XCB、PortAudio 和 Tk。Wayland、macOS 和部分 Linux 桌面可能不允许 `keyboard` 注册全局热键，此时可在桌面宠物右键菜单选择“唤醒输入”。

## Botmux 配置

复制 `botmux_config.example.json` 为 `botmux_config.json`：

```json
{
  "enabled": true,
  "dashboard_url": "http://127.0.0.1:7891",
  "dashboard_token": "Botmux Dashboard token",
  "bot_id": "cli_xxx",
  "events_enabled": true,
  "route_unmatched_input": true,
  "bridge": {
    "enabled": true,
    "host": "127.0.0.1",
    "port": 8765,
    "token": "use-a-long-random-token"
  }
}
```

`botmux_config.json` 已加入 `.gitignore`，不要把 Dashboard token 或 Bridge token 提交到仓库。
Bridge token 可用 `python -c "import secrets; print(secrets.token_urlsafe(32))"` 生成。

Seele 使用以下 Botmux Dashboard 接口：

- `GET /api/sessions`：首次加载会话状态；
- `GET /events`：订阅实时状态；
- `POST /api/trigger`：把未匹配本地 RPA 的输入交给 Agent。

安装仓库内插件：

```bash
cd botmux-skill
npm test
botmux plugin install . --link
botmux plugin enable seele
```

具体环境变量和 WSL2 配置见 [`botmux-skill/README.md`](botmux-skill/README.md)。

## Windows、macOS 与 Linux

- **Windows**：支持现有影刀快捷方式、`shadowbot:` 协议、快启动触发文件和 Windows `Win+H` 听写。
- **macOS**：桌面宠物、Botmux 状态和协议 URL 启动可用；需要授予辅助功能、麦克风和输入监控权限。系统不支持 `Win+H`，输入框仍可直接使用。
- **Linux**：桌面宠物和 Botmux 状态可用；影刀是否可运行取决于本机是否有对应客户端或兼容的触发文件消费者。
- Botmux 官方更适合运行在 Linux/macOS；Windows 推荐 WSL2。Seele 保持运行在 Windows，通过本地 Bridge 与 WSL2 中的 Botmux 通信。

可以通过 `SEELE_TOOLS_DIR` 覆盖 RPA 触发目录。默认值是 Windows 的 `D:\SeeleTools`/`C:\SeeleTools`，macOS/Linux 的 `~/.seele/tools`。

## 安全边界

- Bridge 只接受配置中已有的工作流名称或 ID，不执行任意 shell 命令。
- 非 loopback 监听必须设置 bearer token。
- Botmux MCP 要求宿主注入可信飞书调用者身份。
- `request_id` 是幂等键，同一请求不会重复启动工作流。
- `accepted` 只表示已提交。需要影刀工作流回调 `/v1/jobs/:request_id/status` 后，才能显示真实的 `completed` 或 `failed`。
