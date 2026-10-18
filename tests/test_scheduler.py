from datetime import datetime, timedelta, timezone

import pytest

from lectureloop.models import TopicPerformance
from lectureloop.scheduler import mastery_label, next_review_at, review_delay
from lectureloop.agent import update_topic_after_attempt


@pytest.mark.parametrize(
    ("attempts", "correct", "days", "label"),
    [(5, 2, 1, "high"), (8, 5, 3, "medium"), (10, 9, 7, "low")],
)
def test_spaced_repetition_bands(attempts, correct, days, label):
    topic = TopicPerformance("Topic", attempts, correct)
    assert review_delay(topic) == timedelta(days=days)
    assert mastery_label(topic) == label


def test_next_review_keeps_timezone():
    now = datetime(2026, 10, 18, 9, tzinfo=timezone.utc)
    assert next_review_at(TopicPerformance("Topic", 5, 2), now) == now + timedelta(days=1)


def test_invalid_performance_is_rejected():
    with pytest.raises(ValueError):
        TopicPerformance.from_dict({"title": "Topic", "attempts": 2, "correct": 3})


def test_answer_updates_mastery_and_reschedules_from_new_score():
    topic = {"title": "Topic", "attempts": 4, "correct": 2}
    now = datetime(2026, 10, 18, 9, tzinfo=timezone.utc)
    updated = update_topic_after_attempt(topic, True, now)
    assert (updated.attempts, updated.correct) == (5, 3)
    assert topic["next_review_at"] == (now + timedelta(days=3)).isoformat()

