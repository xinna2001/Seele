"""Allowlisted ShadowBot/Yingdao workflow dispatch for UI and Botmux callers."""

from __future__ import annotations

import json
import os
import re
import sys
import threading
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from platform_utils import (
    app_path,
    get_tools_dir,
    open_external,
    platform_label,
    process_is_running,
)


SHADOWBOT_PROCESS_NAMES = ("shadowbotbrowser", "shadowbot", "yingdao")
TERMINAL_JOB_STATES = {"completed", "failed", "cancelled"}
_JOB_LOCK = threading.RLock()
_JOB_EVENT_LOCK = threading.Lock()
_JOB_EVENT_LISTENERS: set[Callable[[dict], None]] = set()


@dataclass(frozen=True)
class WorkflowDefinition:
    name: str
    workflow_id: str
    uid: str | None = None
    trigger_file: str | None = None


@dataclass
class WorkflowResult:
    ok: bool
    code: str
    message: str
    workflow: str
    workflow_id: str
    request_id: str
    state: str

    def to_dict(self) -> dict:
        return asdict(self)


def _read_json(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
            return data if isinstance(data, dict) else {}
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return {}


def list_workflows(base_dir: Path | None = None) -> list[WorkflowDefinition]:
    root = base_dir or app_path()
    uids = _read_json(root / "uid.json")
    trigger_files = _read_json(root / "file_name.json")
    names = sorted(set(uids) | set(trigger_files))
    workflows = []
    for name in names:
        trigger_file = str(trigger_files.get(name) or "").strip() or None
        uid = str(uids.get(name) or "").strip() or None
        workflows.append(
            WorkflowDefinition(
                name=name,
                workflow_id=trigger_file or name,
                uid=uid,
                trigger_file=trigger_file,
            )
        )
    return workflows


def resolve_workflow(name_or_id: str, base_dir: Path | None = None) -> WorkflowDefinition | None:
    key = str(name_or_id or "").strip()
    if not key:
        return None
    for workflow in list_workflows(base_dir):
        if key in {workflow.name, workflow.workflow_id}:
            return workflow
    return None


def is_shadowbot_running() -> bool:
    return process_is_running(SHADOWBOT_PROCESS_NAMES)


def _desktop_candidates() -> list[Path]:
    home = Path.home()
    candidates = [home / "Desktop"]
    public = os.environ.get("PUBLIC")
    if public:
        candidates.append(Path(public) / "Desktop")
    for key in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial"):
        root = os.environ.get(key)
        if root:
            candidates.append(Path(root) / "Desktop")
    return candidates


def open_shadowbot(uid: str) -> bool:
    target = f"shadowbot:Run?robot-uuid={uid}"
    if sys.platform == "win32" and not is_shadowbot_running():
        link = next(
            (desktop / "影刀.lnk" for desktop in _desktop_candidates() if (desktop / "影刀.lnk").exists()),
            None,
        )
        if link and hasattr(os, "startfile"):
            try:
                os.startfile(str(link), arguments=target)  # type: ignore[attr-defined]
                return True
            except OSError:
                pass
    return open_external(target)


def _job_dir(tools_dir: Path) -> Path:
    path = tools_dir / ".seele" / "jobs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _job_path(request_id: str, tools_dir: Path) -> Path:
    safe_id = str(request_id or "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,200}", safe_id):
        raise ValueError("request_id is invalid")
    return _job_dir(tools_dir) / f"{safe_id}.json"


def load_job(request_id: str, tools_dir: Path | None = None) -> dict | None:
    path = _job_path(request_id, tools_dir or get_tools_dir())
    data = _read_json(path)
    return data or None


def save_job(job: dict, tools_dir: Path | None = None) -> dict:
    root = tools_dir or get_tools_dir()
    request_id = str(job.get("request_id") or "")
    path = _job_path(request_id, root)
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as file:
        json.dump(job, file, ensure_ascii=False, indent=2)
    temporary.replace(path)
    return job


def subscribe_job_events(callback: Callable[[dict], None]) -> Callable[[], None]:
    with _JOB_EVENT_LOCK:
        _JOB_EVENT_LISTENERS.add(callback)

    def unsubscribe() -> None:
        with _JOB_EVENT_LOCK:
            _JOB_EVENT_LISTENERS.discard(callback)

    return unsubscribe


def _publish_job(job: dict) -> None:
    with _JOB_EVENT_LOCK:
        listeners = tuple(_JOB_EVENT_LISTENERS)
    event = {"type": "rpa.job", "job": dict(job)}
    for callback in listeners:
        try:
            callback(event)
        except Exception:
            pass


def update_job(
    request_id: str,
    state: str,
    message: str = "",
    *,
    tools_dir: Path | None = None,
) -> dict | None:
    normalized = str(state or "").strip().lower()
    if normalized not in {"accepted", "running", *TERMINAL_JOB_STATES}:
        raise ValueError("unsupported job state")
    root = tools_dir or get_tools_dir()
    with _JOB_LOCK:
        job = load_job(request_id, root)
        if not job:
            return None
        job["state"] = normalized
        job["updated_at"] = datetime.now(timezone.utc).isoformat()
        if message:
            job["message"] = str(message)
        saved = save_job(job, root)
    _publish_job(saved)
    return saved


def _trigger_workflow_unlocked(
    name_or_id: str,
    *,
    request_id: str | None = None,
    startup_mode: str | None = None,
    base_dir: Path | None = None,
    tools_dir: Path | None = None,
) -> WorkflowResult:
    root = base_dir or app_path()
    tools = tools_dir or get_tools_dir()
    workflow = resolve_workflow(name_or_id, root)
    request_id = str(request_id or uuid.uuid4())
    if not workflow:
        return WorkflowResult(
            False,
            "workflow_not_found",
            "未找到允许执行的影刀工作流。",
            str(name_or_id),
            "",
            request_id,
            "failed",
        )

    previous = load_job(request_id, tools)
    if previous:
        if str(previous.get("workflow_id") or "") != workflow.workflow_id:
            return WorkflowResult(
                False,
                "idempotency_conflict",
                "同一个 request_id 不能用于不同工作流。",
                workflow.name,
                workflow.workflow_id,
                request_id,
                "failed",
            )
        return WorkflowResult(
            bool(previous.get("ok")),
            str(previous.get("code") or "already_requested"),
            str(previous.get("message") or "请求已存在。"),
            str(previous.get("workflow") or workflow.name),
            str(previous.get("workflow_id") or workflow.workflow_id),
            request_id,
            str(previous.get("state") or "accepted"),
        )

    if startup_mode is None:
        startup_mode = str(_read_json(root / "state.json").get("startup_mode") or "slow")
    if startup_mode not in {"slow", "fast"}:
        return WorkflowResult(
            False,
            "invalid_startup_mode",
            "启动模式必须是 slow 或 fast。",
            workflow.name,
            workflow.workflow_id,
            request_id,
            "failed",
        )
    if startup_mode == "fast":
        if not workflow.trigger_file:
            result = WorkflowResult(
                False,
                "trigger_file_missing",
                "该工作流没有配置快启动文件。",
                workflow.name,
                workflow.workflow_id,
                request_id,
                "failed",
            )
        elif not is_shadowbot_running():
            result = WorkflowResult(
                False,
                "shadowbot_not_running",
                f"{platform_label()} 上未检测到影刀客户端。",
                workflow.name,
                workflow.workflow_id,
                request_id,
                "failed",
            )
        else:
            tools.mkdir(parents=True, exist_ok=True)
            (tools / f"{workflow.trigger_file}.txt").write_text(".\n", encoding="utf-8")
            result = WorkflowResult(
                True,
                "accepted",
                f"已提交影刀工作流：{workflow.name}",
                workflow.name,
                workflow.workflow_id,
                request_id,
                "accepted",
            )
    elif workflow.uid and open_shadowbot(workflow.uid):
        result = WorkflowResult(
            True,
            "accepted",
            f"已启动影刀工作流：{workflow.name}",
            workflow.name,
            workflow.workflow_id,
            request_id,
            "accepted",
        )
    else:
        result = WorkflowResult(
            False,
            "shadowbot_unavailable",
            f"无法在 {platform_label()} 上启动影刀工作流。",
            workflow.name,
            workflow.workflow_id,
            request_id,
            "failed",
        )

    job = result.to_dict()
    now = datetime.now(timezone.utc).isoformat()
    job["created_at"] = now
    job["updated_at"] = now
    save_job(job, tools)
    return result


def trigger_workflow(
    name_or_id: str,
    *,
    request_id: str | None = None,
    startup_mode: str | None = None,
    base_dir: Path | None = None,
    tools_dir: Path | None = None,
) -> WorkflowResult:
    with _JOB_LOCK:
        result = _trigger_workflow_unlocked(
            name_or_id,
            request_id=request_id,
            startup_mode=startup_mode,
            base_dir=base_dir,
            tools_dir=tools_dir,
        )
    _publish_job(result.to_dict())
    return result
