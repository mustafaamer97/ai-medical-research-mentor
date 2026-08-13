from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from config.settings import PERSISTENCE_FILE
from core.models import ResearchProject, ResearchState


def save_project(project: ResearchProject, path: Path = PERSISTENCE_FILE) -> None:
    state = ResearchState(project=project)
    path.write_text(state.model_dump_json(indent=2), encoding="utf-8")


def load_project(path: Path = PERSISTENCE_FILE) -> Optional[ResearchProject]:
    if not path.exists():
        return None
    try:
        raw = path.read_text(encoding="utf-8")
        state = ResearchState.model_validate_json(raw)
        return state.project
    except (json.JSONDecodeError, Exception):
        return None


def clear_project(path: Path = PERSISTENCE_FILE) -> None:
    if path.exists():
        path.unlink()
