"""Validated JSON persistence for a small, self-hosted LectureLoop deployment."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import DueRevision, TopicPerformance


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"students": [], "telegram_offset": 0}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("students", []), list):
        raise ValueError("student store must be an object with a students list")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def due_revisions(data: dict[str, Any], now: datetime) -> list[DueRevision]:
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    due: list[DueRevision] = []
    for student in data["students"]:
        student_id = str(student["student_id"])
        for topic_id, raw_topic in student.get("topics", {}).items():
            raw_due = raw_topic.get("next_review_at")
            if not raw_due:
                continue
            due_at = datetime.fromisoformat(raw_due)
            if due_at.tzinfo is None:
                raise ValueError(f"next_review_at for {topic_id} must include a timezone")
            if due_at <= now:
                due.append(
                    DueRevision(student_id, str(topic_id), TopicPerformance.from_dict(raw_topic), due_at)
                )
    return due


def find_student(data: dict[str, Any], chat_id: str) -> dict[str, Any] | None:
    return next((s for s in data["students"] if str(s.get("telegram_chat_id")) == str(chat_id)), None)

