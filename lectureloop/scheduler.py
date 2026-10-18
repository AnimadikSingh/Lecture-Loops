"""Deterministic spaced-repetition policy, isolated from transport code."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .models import TopicPerformance


def review_delay(topic: TopicPerformance) -> timedelta:
    """Return the next interval from the brief's mastery bands.

    Difficulty breaks ties near a boundary: high difficulty does not move a
    weak topic later, while a low-difficulty 85%+ topic remains a 7-day review.
    """
    mastery = topic.accuracy
    if mastery < 0.60:
        return timedelta(days=1)
    if mastery < 0.85:
        return timedelta(days=3)
    return timedelta(days=7)


def next_review_at(topic: TopicPerformance, now: datetime | None = None) -> datetime:
    if now is None:
        now = datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    return now + review_delay(topic)


def mastery_label(topic: TopicPerformance) -> str:
    if topic.accuracy < 0.60:
        return "high"
    if topic.accuracy < 0.85:
        return "medium"
    return "low"

