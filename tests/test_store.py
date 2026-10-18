from datetime import datetime, timezone

from lectureloop.store import due_revisions


def test_due_revisions_returns_only_due_topics():
    data = {
        "students": [{"student_id": "a", "topics": {
            "due": {"title": "Due", "attempts": 5, "correct": 1, "next_review_at": "2026-10-18T08:00:00+00:00"},
            "later": {"title": "Later", "attempts": 5, "correct": 5, "next_review_at": "2026-10-19T08:00:00+00:00"},
        }}]
    }
    results = due_revisions(data, datetime(2026, 10, 18, 9, tzinfo=timezone.utc))
    assert [(item.student_id, item.topic_id) for item in results] == [("a", "due")]

