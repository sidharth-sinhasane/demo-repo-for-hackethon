"""Thread-safe in-memory deployment state for the local release simulator."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from threading import Lock


STABLE_DEMO_REVISION = "1111111111111111111111111111111111111111"
REGRESSION_DEMO_REVISION = "2222222222222222222222222222222222222222"


@dataclass(frozen=True)
class Release:
    name: str
    version: str
    git_commit_sha: str
    deployed_at: str
    pull_request_number: int | None = None

    def as_dict(self) -> dict[str, str | int | None]:
        return asdict(self)


class ReleaseState:
    def __init__(self, default_release: str) -> None:
        self._lock = Lock()
        self._release = self._make_release(default_release)

    def current(self) -> Release:
        with self._lock:
            return self._release

    def deploy(
        self,
        *,
        name: str,
        git_commit_sha: str | None = None,
        pull_request_number: int | None = None,
    ) -> Release:
        with self._lock:
            self._release = self._make_release(
                name,
                git_commit_sha=git_commit_sha,
                pull_request_number=pull_request_number,
            )
            return self._release

    @staticmethod
    def _make_release(
        name: str,
        *,
        git_commit_sha: str | None = None,
        pull_request_number: int | None = None,
    ) -> Release:
        if name not in {"stable", "regression"}:
            raise ValueError("release must be stable or regression")

        default_revision = (
            STABLE_DEMO_REVISION if name == "stable" else REGRESSION_DEMO_REVISION
        )
        return Release(
            name=name,
            version=f"checkout-demo-{name}",
            git_commit_sha=git_commit_sha or default_revision,
            deployed_at=datetime.now(timezone.utc).isoformat(),
            pull_request_number=pull_request_number,
        )
