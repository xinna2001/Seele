# Seele Botmux Skill

This directory is a self-contained Botmux plugin. It contributes:

- the `seele-rpa` Skill;
- an MCP server exposing allowlisted workflow tools;
- no daemon, worker, or CLI adapter patches.

## Build and install

Node.js 22+ and Botmux 3.8+ are required.

```bash
cd botmux-skill
npm test
botmux plugin install . --link
botmux plugin enable seele
```

Start a new Botmux session after enabling the plugin so its Skill/MCP snapshot is refreshed.

## Private configuration

After installing the plugin, create `~/.botmux/plugins/seele/config.json`:

```json
{
  "bridgeUrl": "http://127.0.0.1:8765",
  "bridgeToken": "same-token-as-botmux_config.json",
  "allowedOpenIds": ["ou_your_feishu_open_id"]
}
```

This file stays in Botmux's private plugin directory and is not part of the npm package or this repository. `allowedOpenIds` may be an array or comma-separated string. An empty value still requires a Botmux-authenticated Lark caller, but accepts any such caller already admitted by the bot.

```bash
chmod 600 ~/.botmux/plugins/seele/config.json
```

`SEELE_BRIDGE_URL`, `SEELE_BRIDGE_TOKEN`, and `SEELE_ALLOWED_OPEN_IDS` environment variables can override the file when the MCP process is launched manually. Botmux intentionally starts plugin MCP processes with a restricted environment, so the private config file is the reliable production path.

For WSL2, `127.0.0.1` works with mirrored networking. With NAT networking, set `SEELE_BRIDGE_URL` to the Windows host address and configure Seele's bridge host as `0.0.0.0`. Keep the bearer token enabled and restrict the port with Windows Firewall.

## Bridge contract

Seele exposes:

- `GET /healthz`
- `GET /v1/workflows`
- `POST /v1/workflows/run`
- `GET /v1/jobs/:request_id`
- `POST /v1/jobs/:request_id/status`

All routes except `/healthz` use `Authorization: Bearer <token>` when a token is configured.

The bridge reports `accepted` after dispatch. To report true completion, make the Yingdao workflow call the status endpoint with:

```json
{
  "state": "completed",
  "message": "optional result summary"
}
```

Supported states are `accepted`, `running`, `completed`, `failed`, and `cancelled`.
