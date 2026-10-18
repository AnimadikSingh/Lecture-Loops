"""Small, dependency-free models used by the automation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class TopicPerformance:
    title: str
    attempts: int
    correct: int
    difficulty: str = "medium"

    @property
    def accuracy(self) -> float:
        return 0.0 if self.attempts <= 0 else self.correct / self.attempts

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "TopicPerformance":
        attempts = int(raw.get("attempts", 0))
        correct = int(raw.get("correct", 0))
        if attempts < 0 or correct < 0 or correct > attempts:
            raise ValueError("correct must be between 0 and attempts")
        return cls(
            title=str(raw["title"]).strip(),
            attempts=attempts,
            correct=correct,
            difficulty=str(raw.get("difficulty", "medium")).lower(),
        )


@dataclass(frozen=True)
class DueRevision:
    student_id: str
    topic_id: str
    topic: TopicPerformance
    due_at: datetime

