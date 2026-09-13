"""Structured console logging and optional batched OpenObserve export."""

from __future__ import annotations

import atexit
import json
import logging
import os
import queue
import threading
import time
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        event = getattr(record, "structured_event", None)
        if not isinstance(event, dict):
            event = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": record.levelname,
                "event_name": "application.log",
                "message": record.getMessage(),
            }
        return json.dumps(event, default=str, separators=(",", ":"))


class OpenObserveSink:
    """Small best-effort batch exporter for OpenObserve's JSON ingestion API."""

    def __init__(self) -> None:
        self._url = os.getenv("O2_INGESTION_URL", "").strip()
        self._authorization = os.getenv("O2_AUTH_HEADER", "").strip()
        self._batch_size = _positive_int("O2_EXPORT_BATCH_SIZE", 10)
        self._interval = _positive_float("O2_EXPORT_INTERVAL_SECONDS", 0.5)
        self._queue: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=1000)
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._last_success_at: str | None = None
        self._last_error: str | None = None
        self._exported_events = 0
        self._dropped_events = 0
        self._thread: threading.Thread | None = None

        if self.configured:
            self._thread = threading.Thread(
                target=self._run, name="openobserve-exporter", daemon=True
            )
            self._thread.start()
            atexit.register(self.close)

    @property
    def configured(self) -> bool:
        return bool(self._url and self._authorization)

    def emit(self, event: dict[str, Any]) -> None:
        if not self.configured:
            return
        try:
            self._queue.put_nowait(event)
        except queue.Full:
            with self._lock:
                self._dropped_events += 1
                self._last_error = "export queue is full"

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "configured": self.configured,
                "queued_events": self._queue.qsize(),
                "exported_events": self._exported_events,
                "dropped_events": self._dropped_events,
                "last_success_at": self._last_success_at,
                "last_error": self._last_error,
            }

    def close(self) -> None:
        if not self._thread or self._stop.is_set():
            return
        self._stop.set()
        self._thread.join(timeout=2)

    def _run(self) -> None:
        while not self._stop.is_set() or not self._queue.empty():
            batch = self._next_batch()
            if not batch:
                continue
            self._send(batch)

    def _next_batch(self) -> list[dict[str, Any]]:
        batch: list[dict[str, Any]] = []
        try:
            batch.append(self._queue.get(timeout=self._interval))
        except queue.Empty:
            return batch

        deadline = time.monotonic() + self._interval
        while len(batch) < self._batch_size and time.monotonic() < deadline:
            try:
                batch.append(self._queue.get_nowait())
            except queue.Empty:
                break
        return batch

    def _send(self, batch: list[dict[str, Any]]) -> None:
        body = json.dumps(batch, default=str).encode("utf-8")
        request = Request(
            self._url,
            data=body,
            method="POST",
            headers={
                "Authorization": self._authorization,
                "Content-Type": "application/json",
                "User-Agent": "checkout-release-lab/1.0",
            },
        )

        try:
            with urlopen(request, timeout=8) as response:
                if response.status < 200 or response.status >= 300:
                    raise RuntimeError(f"OpenObserve returned HTTP {response.status}")
            with self._lock:
                self._exported_events += len(batch)
                self._last_success_at = datetime.now(timezone.utc).isoformat()
                self._last_error = None
        except HTTPError as error:
            self._record_error(f"OpenObserve returned HTTP {error.code}")
        except (URLError, TimeoutError, OSError) as error:
            self._record_error(f"OpenObserve export failed: {type(error).__name__}")
        finally:
            for _ in batch:
                self._queue.task_done()

    def _record_error(self, message: str) -> None:
        # Deliberately exclude URLs, headers, and response bodies because they can
        # contain tenant or credential information.
        with self._lock:
            self._last_error = message


class EventLogger:
    def __init__(self) -> None:
        self._logger = logging.getLogger("checkout_demo")
        self._logger.setLevel(logging.INFO)
        self._logger.propagate = False
        if not self._logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(JsonFormatter())
            self._logger.addHandler(handler)
        self.sink = OpenObserveSink()

    def emit(self, level: int, event_name: str, **fields: Any) -> dict[str, Any]:
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": logging.getLevelName(level),
            "event_name": event_name,
            **fields,
        }
        self._logger.log(
            level,
            fields.get("message", event_name),
            extra={"structured_event": event},
        )
        self.sink.emit(event)
        return event


def _positive_int(name: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(name, str(default))))
    except ValueError:
        return default


def _positive_float(name: str, default: float) -> float:
    try:
        return max(0.1, float(os.getenv(name, str(default))))
    except ValueError:
        return default
