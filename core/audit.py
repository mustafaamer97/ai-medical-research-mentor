from __future__ import annotations

from datetime import datetime
from typing import List

from pydantic import BaseModel, Field


class AuditEntry(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event: str
    detail: str = ""

    model_config = {"frozen": True}


class AuditLog(BaseModel):
    entries: List[AuditEntry] = Field(default_factory=list)

    model_config = {"frozen": False}

    def record(self, event: str, detail: str = "") -> None:
        self.entries.append(AuditEntry(event=event, detail=detail))

    def recent(self, n: int = 20) -> List[AuditEntry]:
        return self.entries[-n:]
