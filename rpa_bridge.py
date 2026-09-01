"""Token-protected local HTTP bridge for Botmux-to-Seele RPA calls."""

from __future__ import annotations

import hmac
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable
from urllib.parse import unquote, urlparse

import rpa_service


MAX_BODY_BYTES = 64 * 1024


class RpaBridge:
    def __init__(self, config: dict, on_event: Callable[[dict], None] | None = None):
        self.config = config
        self.on_event = on_event
        self.server: ThreadingHTTPServer | None = None
        self.thread: threading.Thread | None = None

    @property
    def enabled(self) -> bool:
        return bool(self.config.get("enabled"))

    def start(self) -> bool:
        if not self.enabled or self.server:
            return False
        host = str(self.config.get("host") or "127.0.0.1").strip()
        configured_port = self.config.get("port", 8765)
        port = int(8765 if configured_port is None else configured_port)
        token = str(self.config.get("token") or "")
        if host not in {"127.0.0.1", "::1", "localhost"} and not token:
            raise RuntimeError("RPA bridge requires a token when binding beyond loopback")

        bridge = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "SeeleBridge/1.0"

            def log_message(self, _format: str, *_args) -> None:
                return

            def _json(self, status: int, body: dict) -> None:
                payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("content-type", "application/json; charset=utf-8")
                self.send_header("content-length", str(len(payload)))
                self.send_header("cache-control", "no-store")
                self.end_headers()
                self.wfile.write(payload)

            def _authorized(self) -> bool:
                if not token:
                    return True
                supplied = self.headers.get("authorization", "")
                expected = f"Bearer {token}"
                return hmac.compare_digest(supplied, expected)

            def _require_auth(self) -> bool:
                if self._authorized():
                    return True
                self._json(401, {"ok": False, "error": "unauthorized"})
                return False

            def _body(self) -> dict:
                raw_length = self.headers.get("content-length", "0")
                try:
                    length = int(raw_length)
                except ValueError as exc:
                    raise ValueError("invalid content-length") from exc
                if length < 0 or length > MAX_BODY_BYTES:
                    raise ValueError("request body is too large")
                raw = self.rfile.read(length)
                body = json.loads(raw.decode("utf-8")) if raw else {}
                if not isinstance(body, dict):
                    raise ValueError("request body must be an object")
                return body

            def do_GET(self) -> None:
                path = urlparse(self.path).path
                if path == "/healthz":
                    self._json(200, {"ok": True, "service": "seele-rpa-bridge"})
                    return
                if not self._require_auth():
                    return
                if path == "/v1/workflows":
                    rows = [
                        {
                            "name": workflow.name,
                            "workflow_id": workflow.workflow_id,
                            "modes": [
                                mode
                                for mode, available in (
                                    ("slow", bool(workflow.uid)),
                                    ("fast", bool(workflow.trigger_file)),
                                )
                                if available
                            ],
                        }
                        for workflow in rpa_service.list_workflows()
                    ]
                    self._json(200, {"ok": True, "workflows": rows})
                    return
                prefix = "/v1/jobs/"
                if path.startswith(prefix):
                    request_id = unquote(path[len(prefix):])
                    try:
                        job = rpa_service.load_job(request_id)
                    except ValueError:
                        job = None
                    if job:
                        self._json(200, {"ok": True, "job": job})
                    else:
                        self._json(404, {"ok": False, "error": "job_not_found"})
                    return
                self._json(404, {"ok": False, "error": "not_found"})

            def do_POST(self) -> None:
                path = urlparse(self.path).path
                if not self._require_auth():
                    return
                try:
                    body = self._body()
                except (ValueError, json.JSONDecodeError) as exc:
                    self._json(400, {"ok": False, "error": "bad_request", "detail": str(exc)})
                    return
                if path == "/v1/workflows/run":
                    workflow = str(body.get("workflow") or "")
                    request_id = str(body.get("request_id") or "") or None
                    mode = str(body.get("startup_mode") or "") or None
                    try:
                        result = rpa_service.trigger_workflow(
                            workflow,
                            request_id=request_id,
                            startup_mode=mode,
                        )
                    except ValueError as exc:
                        self._json(400, {"ok": False, "error": "bad_request_id", "detail": str(exc)})
                        return
                    self._json(202 if result.ok else 400, result.to_dict())
                    return
                prefix = "/v1/jobs/"
                if path.startswith(prefix) and path.endswith("/status"):
                    request_id = unquote(path[len(prefix):-len("/status")]).rstrip("/")
                    try:
                        job = rpa_service.update_job(
                            request_id,
                            str(body.get("state") or ""),
                            str(body.get("message") or ""),
                        )
                    except ValueError as exc:
                        self._json(400, {"ok": False, "error": "bad_state", "detail": str(exc)})
                        return
                    if not job:
                        self._json(404, {"ok": False, "error": "job_not_found"})
                        return
                    self._json(200, {"ok": True, "job": job})
                    return
                self._json(404, {"ok": False, "error": "not_found"})

        self.server = ThreadingHTTPServer((host, port), Handler)
        self.server.daemon_threads = True
        self.thread = threading.Thread(
            target=self.server.serve_forever,
            name="seele-rpa-bridge",
            daemon=True,
        )
        self.thread.start()
        self._emit({
            "type": "rpa.bridge",
            "state": "online",
            "host": host,
            "port": self.server.server_port,
        })
        return True

    def stop(self) -> None:
        server = self.server
        self.server = None
        self.thread = None
        if server:
            server.shutdown()
            server.server_close()
        self._emit({"type": "rpa.bridge", "state": "offline"})

    def _emit(self, event: dict) -> None:
        if not self.on_event:
            return
        try:
            self.on_event(event)
        except Exception:
            pass
