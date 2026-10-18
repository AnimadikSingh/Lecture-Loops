from datetime import datetime, timezone

from lectureloop.store import due_revisions
from lectureloop.materials import sync_student_topics


def test_due_revisions_returns_only_due_topics():
    data = {
        "students": [{"student_id": "a", "topics": {
            "due": {"title": "Due", "attempts": 5, "correct": 1, "next_review_at": "2026-10-18T08:00:00+00:00"},
            "later": {"title": "Later", "attempts": 5, "correct": 5, "next_review_at": "2026-10-19T08:00:00+00:00"},
        }}]
    }
    results = due_revisions(data, datetime(2026, 10, 18, 9, tzinfo=timezone.utc))
    assert [(item.student_id, item.topic_id) for item in results] == [("a", "due")]


def test_sync_materials_creates_course_topics(tmp_path):
    store = tmp_path / "students.json"
    store.write_text('{"students": [{"student_id":"a", "telegram_chat_id":"1", "topics": {}}]}')
    materials = {"topics": [{"id": "normalization", "title": "Normalization", "notes": "Organize relations."}], "quiz": [{"topic_id": "normalization", "question": "Why normalize?", "answer": "To reduce redundancy."}]}
    created = sync_student_topics(store, "dbms-unit-1", materials, datetime(2026, 10, 18, 9, tzinfo=timezone.utc))
    assert created == 1
    data = __import__("json").loads(store.read_text())
    assert data["students"][0]["courses"] == ["dbms-unit-1"]
    assert data["students"][0]["topics"]["dbms-unit-1:normalization"]["last_answer"] == "To reduce redundancy."

