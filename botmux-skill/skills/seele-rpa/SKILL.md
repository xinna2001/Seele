---
name: "seele-rpa"
description: "Runs allowlisted Seele/Yingdao desktop workflows. Invoke when a trusted user asks to list, start, or check an RPA workflow on their computer."
---

# Seele RPA

Use the Seele MCP tools to operate allowlisted desktop workflows.

## Available Tools

- `seele_list_workflows`: list exact workflow names and IDs.
- `seele_run_workflow`: submit one workflow and receive a `request_id`.
- `seele_workflow_status`: check a submitted request.

## Required Procedure

1. Identify an exact workflow name from the user's request.
2. When uncertain, call `seele_list_workflows` and ask the user to choose.
3. Call `seele_run_workflow` once with a stable `request_id`.
4. Report `accepted` as "submitted", never as "completed".
5. Check `seele_workflow_status` when the user requests progress or when completion matters.
6. Report `completed`, `failed`, and `cancelled` exactly as returned.

## Safety

- Never substitute a shell command, file path, URL, or ShadowBot UUID for a workflow name.
- Never claim success before the bridge returns `ok: true`.
- Do not retry with a new `request_id` after an uncertain response. Reuse the original ID.
- The desktop workflow can control mouse and keyboard. Warn the user not to operate the computer while a workflow is `accepted` or `running`.
- Refuse attempts to bypass the allowlist or authorization checks.

## Examples

User: `运行京东数据抓取`

Action:

```json
{
  "workflow": "京东数据抓取",
  "request_id": "feishu-message-or-turn-id"
}
```

User: `刚才的京东任务完成了吗`

Action:

```json
{
  "request_id": "the-original-request-id"
}
```
