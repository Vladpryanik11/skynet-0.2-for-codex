"""Small local run store. It keeps execution history without a SaaS dependency."""

import json
import os
import uuid
from datetime import datetime, timezone

from institute.contracts import RunManifest
from institute.local_mode import skynet_mode


class RunStore:
    def __init__(self, directory: str | None = None):
        self.directory = directory or os.environ.get("RUNS_DIR", "./runs")

    def start(self, user_request: str, department: str) -> RunManifest:
        manifest = RunManifest(
            run_id=uuid.uuid4().hex[:12],
            user_request=user_request,
            department=department,
            mode=skynet_mode(),
            status="running",
            started_at=datetime.now(timezone.utc),
        )
        self._write(manifest)
        return manifest

    def complete(self, manifest: RunManifest, output: str) -> RunManifest:
        manifest.status = "completed"
        manifest.completed_at = datetime.now(timezone.utc)
        manifest.output_preview = output[:1000]
        self._write(manifest)
        return manifest

    def fail(self, manifest: RunManifest, error: Exception) -> RunManifest:
        manifest.status = "failed"
        manifest.completed_at = datetime.now(timezone.utc)
        manifest.error = f"{type(error).__name__}: {error}"[:1000]
        self._write(manifest)
        return manifest

    def _write(self, manifest: RunManifest) -> None:
        os.makedirs(self.directory, exist_ok=True)
        path = os.path.join(self.directory, f"{manifest.run_id}.json")
        with open(path, "w", encoding="utf-8") as file:
            json.dump(manifest.model_dump(mode="json"), file, ensure_ascii=False, indent=2)
