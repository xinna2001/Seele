---
name: "seele-botmux"
description: "Integrates Seele desktop-pet status and allowlisted RPA workflows with Botmux. Invoke when changing Botmux monitoring, task routing, or Yingdao automation."
---

# Seele Botmux Integration

Use the repository's integration boundaries instead of coupling UI code directly to Botmux internals.

## Architecture

- Keep PyQt UI work in `Seele.py` on the Qt main thread.
- Use `botmux_client.py` for Dashboard REST, SSE, and task-trigger calls.
- Use `rpa_service.py` as the only workflow catalog and dispatch implementation.
- Use `rpa_bridge.py` for authenticated Botmux-to-Seele calls.
- Keep Botmux extension code under `botmux-skill/`; do not patch the vendored `botmux/` checkout.

## Safety Rules

- Dispatch only workflows present in `uid.json` or `file_name.json`.
- Never expose arbitrary shell commands, paths, or ShadowBot UUIDs as tool arguments.
- Require a bridge token outside loopback.
- Require Botmux trusted caller identity for remote workflow execution.
- Preserve request IDs so retries cannot execute a workflow twice.
- Treat `accepted` as submitted, not completed. Completion requires an explicit RPA callback.

## Verification

Run:

```bash
conda run -n Seele python -m compileall .
conda run -n Seele python -m unittest discover -s tests -v
```

When changing the Botmux plugin, also run `npm test` from `botmux-skill/` on a machine with Node.js 22+.
