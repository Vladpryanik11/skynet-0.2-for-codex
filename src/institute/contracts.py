"""Typed contracts shared by the router, departments and observability."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

DepartmentName = Literal["coders", "marketing", "design", "quality_control"]
RunStatus = Literal["queued", "running", "completed", "failed"]


class RunRequest(BaseModel):
    user_request: str = Field(..., min_length=1)
    department: DepartmentName | None = None


class RunManifest(BaseModel):
    run_id: str
    user_request: str
    department: str
    mode: str
    status: RunStatus
    started_at: datetime
    completed_at: datetime | None = None
    output_preview: str = ""
    error: str | None = None
