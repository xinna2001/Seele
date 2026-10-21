"""Small, dependency-free Botmux Dashboard client used by the desktop pet."""

from __future__ import annotations

import json
import os
import sys
import threading
import time
import uuid
from copy import deepcopy
from pathlib import Path
from typing import Callable, Iterator
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from platform_utils import app_path, data_path


DEFAULT_CONFIG = {
    "enabled": False,
    "dashboard_url": "http://127.0.0.1:7891",
    "dashboard_token": "",
    "bot_id": "",
    "events_enabled": True,
    "route_unmatched_input": True,
    "request_timeout_seconds": 8,
    "bridge": {
        "enabled": False,
        "host": "127.0.0.1",
        "port": 8765,
        "token": "",
    },
}


class BotmuxError(RuntimeError):
    pass


def _merged_dict(base: dict, override: dict) -> dict:
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merged_dict(result[key], value)
        else:
            result[key] = value
    return result


def discover_local_dashboard(botmux_home: str | os.PathLike | None = None) -> dict:
    """
    Read the locally running Botmux Dashboard coordinates from ``~/.botmux``.

    Botmux writes the chosen port to ``.dashboard-port`` and the read token to
    ``.dashboard-token``. The port is dynamic, so a hardcoded default is wrong on
    any machine where Botmux did not pick 7891. Returns ``{}`` when nothing is
    found so callers can keep their existing configuration.
    """
    base = Path(botmux_home) if botmux_home else Path.home() / ".botmux"
    info: dict = {}
    try:
        port = (base / ".dashboard-port").read_text(encoding="utf-8").strip()
        if port.isdigit() and 1 <= int(port) <= 65535:
            info["port"] = int(port)
    except (OSError, ValueError):
        pass
    try:
        token = (base / ".dashboard-token").read_text(encoding="utf-8").strip()
        if token:
            info["token"] = token
    except OSError:
        pass
    if not info and botmux_home is None and sys.platform == "win32":
        info = discover_wsl_dashboard()
    return info


def discover_wsl_dashboard() -> dict:
    """Use the selected user's UNC files; never copy WSL credentials to Windows."""
    from windows_byte_bootstrap import read_status

    status = read_status()
    distro = status.get("distro")
    home = status.get("linux_home")
    if (not isinstance(distro, str) or not distro or any(c in distro for c in "\\/:")
            or not isinstance(home, str) or not home.startswith("/")
            or "\\" in home or ".." in home.split("/")):
        return {}
    for prefix in ("wsl.localhost", "wsl$"):
        base = Path(f"\\\\{prefix}\\{distro}" + home.replace("/", "\\") + "\\.botmux")
        found = discover_local_dashboard(base)
        if found:
            return found
    return {}


def load_config(
    path: str | os.PathLike | None = None,
    *,
    discover: bool = True,
) -> dict:
    config_path = Path(path) if path else data_path("botmux_config.json")
    raw = {}
    try:
        with config_path.open("r", encoding="utf-8") as file:
            loaded = json.load(file)
            if isinstance(loaded, dict):
                raw = loaded
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        pass

    config = _merged_dict(DEFAULT_CONFIG, raw)
    env_map = {
        "BOTMUX_DASHBOARD_URL": "dashboard_url",
        "BOTMUX_DASHBOARD_TOKEN": "dashboard_token",
        "BOTMUX_BOT_ID": "bot_id",
    }
    for env_name, key in env_map.items():
        value = os.environ.get(env_name)
        if value is not None:
            config[key] = value.strip()
    enabled = os.environ.get("SEELE_BOTMUX_ENABLED")
    if enabled is not None:
        config["enabled"] = enabled.strip().lower() in {"1", "true", "yes", "on"}

    # Auto-discover the local Botmux Dashboard so the pet works out of the box
    # without a bundled botmux_config.json. Explicit file/env values always win.
    if discover:
        explicit_url = "dashboard_url" in raw or "BOTMUX_DASHBOARD_URL" in os.environ
        explicit_token = "dashboard_token" in raw or "BOTMUX_DASHBOARD_TOKEN" in os.environ
        explicit_enabled = "enabled" in raw or "SEELE_BOTMUX_ENABLED" in os.environ
        if not (explicit_url and explicit_token and explicit_enabled):
            found = discover_local_dashboard()
            if found.get("port") and not explicit_url:
                config["dashboard_url"] = f"http://127.0.0.1:{found['port']}"
            if found.get("token") and not explicit_token:
                config["dashboard_token"] = found["token"]
            if found and not explicit_enabled:
                config["enabled"] = True
    return config


class BotmuxClient:
    def __init__(self, config: dict | None = None):
        self.config = config or load_config()
        self.base_url = str(self.config.get("dashboard_url") or "").rstrip("/")
        self.token = str(self.config.get("dashboard_token") or "")
        self.timeout = max(1, int(self.config.get("request_timeout_seconds") or 8))

    def _headers(self, *, json_body: bool = False) -> dict[str, str]:
        headers = {"accept": "application/json"}
        if json_body:
            headers["content-type"] = "application/json"
        if self.token:
            headers["cookie"] = f"botmux_dashboard_token={self.token}"
        return headers

    def _request_json(self, method: str, path: str, body: dict | None = None) -> dict:
        if not self.base_url:
            raise BotmuxError("Botmux Dashboard URL is not configured")
        data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
        request = Request(
            f"{self.base_url}{path}",
            data=data,
            headers=self._headers(json_body=body is not None),
            method=method,
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise BotmuxError(f"Botmux returned HTTP {exc.code}: {detail}") from exc
        except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            raise BotmuxError(f"Cannot reach Botmux: {exc}") from exc
        if not isinstance(payload, dict):
            raise BotmuxError("Botmux returned an invalid JSON payload")
        return payload

    def get_sessions(self) -> list[dict]:
        payload = self._request_json("GET", "/api/sessions")
        sessions = payload.get("sessions", [])
        return [item for item in sessions if isinstance(item, dict)] if isinstance(sessions, list) else []

    def trigger(
        self,
        instruction: str,
        *,
        session_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict:
        bot_id = str(self.config.get("bot_id") or "").strip()
        if not bot_id:
            raise BotmuxError("bot_id is required before Seele can trigger Botmux")
        if not self.token:
            raise BotmuxError("dashboard_token is required before Seele can trigger Botmux")
        target = {"kind": "turn", "botId": bot_id}
        options = {"asyncReturnSessionId": True}
        if session_id:
            target["sessionId"] = session_id
            options["turnIdempotencyKey"] = idempotency_key or f"seele-turn-{uuid.uuid4()}"
        else:
            options["idempotencyKey"] = idempotency_key or f"seele-{uuid.uuid4()}"
        response = self._request_json(
            "POST",
            "/api/trigger",
            {
                "source": {"type": "webhook"},
                "target": target,
                "instruction": instruction,
                "envelope": {
                    "format": "text",
                    "sourceName": "seele-desktop",
                    "trusted": False,
                },
                "options": options,
            },
        )
        if response.get("ok") is not True:
            raise BotmuxError(str(response.get("error") or "Botmux rejected the task"))
        return response

    def get_trigger_result(self, session_id: str, trigger_id: str | None = None) -> dict:
        path = f"/api/sessions/{quote(session_id, safe='')}/trigger-result"
        if trigger_id:
            path += f"?triggerId={quote(trigger_id, safe='')}"
        return self._request_json("GET", path)

    def iter_events(self, stop_event: threading.Event) -> Iterator[tuple[str, dict]]:
        request = Request(
            f"{self.base_url}/events",
            headers={**self._headers(), "accept": "text/event-stream"},
            method="GET",
        )
        try:
            with urlopen(request, timeout=max(30, self.timeout)) as response:
                event_name = ""
                data_lines: list[str] = []
                while not stop_event.is_set():
                    raw = response.readline()
                    if not raw:
                        raise BotmuxError("Botmux event stream ended")
                    line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
                    if not line:
                        if event_name and data_lines:
                            try:
                                body = json.loads("\n".join(data_lines))
                            except json.JSONDecodeError:
                                body = None
                            if isinstance(body, dict):
                                yield event_name, body
                        event_name = ""
                        data_lines.clear()
                    elif line.startswith("event:"):
                        event_name = line[6:].strip()
                    elif line.startswith("data:"):
                        data_lines.append(line[5:].strip())
        except HTTPError as exc:
            raise BotmuxError(f"Botmux event stream returned HTTP {exc.code}") from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise BotmuxError(f"Botmux event stream failed: {exc}") from exc


FEISHU_APPLINK_PREFIX = "https://applink.feishu.cn/"

# Botmux raw session statuses grouped into three human-friendly buckets the
# task panel shows. Everything still open that is neither working nor awaiting a
# human counts as idle.
STATUS_WORKING = {"working", "analyzing", "starting"}
STATUS_ATTENTION = {"limited", "stalled"}
TASK_GROUP_LABELS = {
    "attention": "等你回复",
    "working": "进行中",
    "idle": "空闲",
}
# Sort order for the panel: attention first, then working, then idle.
TASK_GROUP_ORDER = {"attention": 0, "working": 1, "idle": 2}


def safe_feishu_link(session: dict) -> str:
    """
    Return a validated Feishu applink for a session, or "" when none is safe.

    Botmux already builds ``feishuThreadLink`` (precise thread) and
    ``feishuChatLink`` (whole chat). We never hand an arbitrary API string to the
    OS opener, so only ``https://applink.feishu.cn/`` URLs are accepted.
    """
    for key in ("feishuThreadLink", "feishuChatLink"):
        value = session.get(key)
        if isinstance(value, str):
            candidate = value.strip()
            if candidate.startswith(FEISHU_APPLINK_PREFIX):
                return candidate
    return ""


def classify_task_group(session: dict) -> str:
    """Map a raw Botmux session row to one of attention/working/idle."""
    if (
        session.get("agentAttention")
        or session.get("pendingRepo")
        or session.get("tuiPromptActive")
        or session.get("status") in STATUS_ATTENTION
    ):
        return "attention"
    if session.get("status") in STATUS_WORKING:
        return "working"
    return "idle"


def format_relative_time(timestamp_ms, now_ms: float | None = None) -> str:
    """Human-friendly '刚刚 / N 分钟前 / N 小时前 / N 天前' for a ms timestamp."""
    if not isinstance(timestamp_ms, (int, float)) or timestamp_ms <= 0:
        return "未知"
    now = now_ms if now_ms is not None else time.time() * 1000
    delta_seconds = (now - timestamp_ms) / 1000
    if delta_seconds < 0:
        delta_seconds = 0
    if delta_seconds < 60:
        return "刚刚"
    minutes = int(delta_seconds // 60)
    if minutes < 60:
        return f"{minutes} 分钟前"
    hours = int(delta_seconds // 3600)
    if hours < 24:
        return f"{hours} 小时前"
    days = int(delta_seconds // 86400)
    return f"{days} 天前"


def participant_name_index(rows: list[dict]) -> dict[str, str]:
    """Build a reusable Feishu open-id to display-name index from session rows."""
    names: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        reply_targets = row.get("replyTargets")
        if not isinstance(reply_targets, dict):
            continue
        for target in reply_targets.values():
            if not isinstance(target, dict):
                continue
            participants = target.get("participants")
            if not isinstance(participants, list):
                continue
            for participant in participants:
                if not isinstance(participant, dict) or participant.get("isBot"):
                    continue
                open_id = str(participant.get("openId") or "").strip()
                name = str(participant.get("name") or "").strip()
                if open_id and name:
                    names.setdefault(open_id, name)
    return names


def resolve_task_initiator(row: dict, names: dict[str, str]) -> tuple[str, str]:
    """
    Resolve the person who originally created the Botmux session.

    ``ownerOpenId`` is assigned from the sender when Botmux creates a Feishu
    session. It remains stable when other people later reply, unlike the latest
    message/quote sender fields.
    """
    if row.get("creationSource") == "schedule":
        return "系统定时", ""
    owner_open_id = str(row.get("ownerOpenId") or "").strip()
    if owner_open_id:
        return names.get(owner_open_id, "未知用户"), owner_open_id
    return "未知用户", ""


def build_active_tasks(
    rows: list[dict],
    *,
    now_ms: float | None = None,
    window_hours: float = 24,
    bot_id: str = "",
) -> list[dict]:
    """
    Turn raw Botmux session rows into normalized task-panel entries.

    - Drops closed sessions and anything with no activity in ``window_hours``.
    - Optionally filters to a single ``bot_id`` (larkAppId); empty keeps all bots.
    - Sorts attention first, then working, then idle, newest activity first.
    """
    now = now_ms if now_ms is not None else time.time() * 1000
    window_ms = window_hours * 3600 * 1000
    participant_names = participant_name_index(rows)
    tasks: list[dict] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if row.get("status") == "closed":
            continue
        if bot_id and row.get("larkAppId") != bot_id:
            continue
        last_active = row.get("lastMessageAt")
        if not isinstance(last_active, (int, float)) or last_active <= 0:
            # Fall back to spawn time so freshly created sessions still appear.
            spawned = row.get("spawnedAt")
            last_active = spawned if isinstance(spawned, (int, float)) else 0
        if window_ms and last_active and (now - last_active) > window_ms:
            continue
        group = classify_task_group(row)
        title = (
            row.get("title")
            or row.get("previewUserText")
            or row.get("previewBotText")
            or row.get("chatDisplayName")
            or "未命名任务"
        )
        preview = row.get("previewBotText") or row.get("previewUserText") or ""
        initiator_name, initiator_open_id = resolve_task_initiator(row, participant_names)
        tasks.append({
            "sessionId": str(row.get("sessionId") or ""),
            "botName": row.get("botName") or "机器人",
            "chat": row.get("chatDisplayName") or row.get("chatId") or "未知会话",
            "initiatorName": initiator_name,
            "initiatorOpenId": initiator_open_id,
            "title": str(title).strip(),
            "preview": str(preview).strip(),
            "group": group,
            "groupLabel": TASK_GROUP_LABELS.get(group, group),
            "status": row.get("status") or "",
            "lastActiveMs": float(last_active or 0),
            "lastActiveText": format_relative_time(last_active, now),
            "link": safe_feishu_link(row),
        })
    tasks.sort(
        key=lambda item: (TASK_GROUP_ORDER.get(item["group"], 9), -item["lastActiveMs"]),
    )
    return tasks


class BotmuxSessionState:
    def __init__(self, bot_id: str = ""):
        self.bot_id = bot_id
        self.sessions: dict[str, dict] = {}

    def _wanted(self, row: dict) -> bool:
        return not self.bot_id or row.get("larkAppId") == self.bot_id

    def replace(self, rows: list[dict]) -> None:
        self.sessions = {
            str(row["sessionId"]): dict(row)
            for row in rows
            if row.get("sessionId") and self._wanted(row)
        }

    def apply(self, event_name: str, body: dict) -> None:
        if event_name == "session.spawned":
            row = body.get("session")
            if isinstance(row, dict) and row.get("sessionId") and self._wanted(row):
                self.sessions[str(row["sessionId"])] = dict(row)
            return
        if event_name == "session.update":
            session_id = str(body.get("sessionId") or "")
            patch = body.get("patch")
            if session_id in self.sessions and isinstance(patch, dict):
                self.sessions[session_id].update(patch)
            return
        if event_name == "session.exited":
            session_id = str(body.get("sessionId") or "")
            if session_id in self.sessions:
                self.sessions[session_id]["status"] = "closed"

    def active_tasks(self, *, now_ms: float | None = None, window_hours: float = 24) -> list[dict]:
        """Normalized task-panel entries for the retained live sessions."""
        return build_active_tasks(
            list(self.sessions.values()),
            now_ms=now_ms,
            window_hours=window_hours,
            bot_id=self.bot_id,
        )

    def summary(self, *, connected: bool = True, error: str = "") -> dict:
        rows = [row for row in self.sessions.values() if row.get("status") != "closed"]
        attention = [
            row for row in rows
            if row.get("agentAttention")
            or row.get("pendingRepo")
            or row.get("tuiPromptActive")
            or row.get("status") in {"limited", "stalled"}
        ]
        working = [row for row in rows if row.get("status") in {"working", "analyzing", "starting"}]
        idle = [row for row in rows if row.get("status") == "idle"]
        focus = (attention or working or idle or rows or [None])[0]
        if not connected:
            kind = "offline"
        elif attention:
            kind = "attention"
        elif working:
            kind = "working"
        elif rows:
            kind = "idle"
        else:
            kind = "offline"
        return {
            "connected": connected,
            "kind": kind,
            "active": len(rows),
            "attention": len(attention),
            "session": focus,
            "error": error,
        }


class BotmuxMonitor:
    def __init__(self, callback: Callable[[dict], None], config: dict | None = None):
        self.config = config or load_config()
        self.callback = callback
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None

    @property
    def enabled(self) -> bool:
        return bool(self.config.get("enabled"))

    def start(self) -> bool:
        if not self.enabled or self.thread:
            return False
        self.thread = threading.Thread(target=self._run, name="seele-botmux-monitor", daemon=True)
        self.thread.start()
        return True

    def stop(self) -> None:
        self.stop_event.set()

    def _run(self) -> None:
        state = BotmuxSessionState(str(self.config.get("bot_id") or ""))
        backoff = 1
        while not self.stop_event.is_set():
            try:
                client = BotmuxClient(self.config)
                state.replace(client.get_sessions())
                if self.stop_event.is_set():
                    return
                self.callback(state.summary())
                backoff = 1
                if not self.config.get("events_enabled", True):
                    self.stop_event.wait(max(3, int(self.config.get("poll_interval_seconds") or 10)))
                    continue
                for event_name, body in client.iter_events(self.stop_event):
                    state.apply(event_name, body)
                    self.callback(state.summary())
                if self.stop_event.is_set():
                    return
            except (BotmuxError, TypeError, ValueError) as exc:
                if self.stop_event.is_set():
                    return
                self.callback(state.summary(connected=False, error=str(exc)))
                self.stop_event.wait(backoff)
                backoff = min(backoff * 2, 30)
