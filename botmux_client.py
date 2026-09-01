"""Small, dependency-free Botmux Dashboard client used by the desktop pet."""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from copy import deepcopy
from pathlib import Path
from typing import Callable, Iterator
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from platform_utils import app_path


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


def load_config(path: str | os.PathLike | None = None) -> dict:
    config_path = Path(path) if path else app_path("botmux_config.json")
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
                self.callback(state.summary(connected=False, error=str(exc)))
                self.stop_event.wait(backoff)
                backoff = min(backoff * 2, 30)
