"""Agent entry points for content ingestion, reminders, and Telegram feedback."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .content import assess_answer, extract_source, generate_materials
from .models import TopicPerformance
from .scheduler import mastery_label, next_review_at
from .store import due_revisions, find_student, read_json, write_json
from .telegram import TelegramClient


def ingest(source_path: Path, course_id: str, output_path: Path) -> dict[str, Any]:
    if not course_id.replace("-", "").replace("_", "").isalnum():
        raise ValueError("course_id may contain only letters, numbers, hyphens, and underscores")
    materials = generate_materials(extract_source(source_path), course_id)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    import json
    output_path.write_text(json.dumps(materials, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return materials


def dispatch_reminders(store_path: Path, token: str, now: datetime | None = None) -> int:
    now = now or datetime.now(timezone.utc)
    data = read_json(store_path)
    telegram = TelegramClient(token)
    student_index = {str(s["student_id"]): s for s in data["students"]}
    delivered = 0
    # One focused prompt at a time is less noisy and guarantees that a free-text
    # response can be associated with a single topic.
    candidates: dict[str, Any] = {}
    for revision in due_revisions(data, now):
        current = candidates.get(revision.student_id)
        if current is None or revision.topic.accuracy < current.topic.accuracy or (
            revision.topic.accuracy == current.topic.accuracy and revision.due_at < current.due_at
        ):
            candidates[revision.student_id] = revision
    for revision in candidates.values():
        student = student_index[revision.student_id]
        if student.get("active_revision"):
            continue
        raw_topic = student["topics"][revision.topic_id]
        telegram.send_revision(
            str(student["telegram_chat_id"]),
            revision.topic.title,
            str(raw_topic.get("last_question", f"Explain {revision.topic.title} in your own words.")),
            mastery_label(revision.topic),
        )
        student["active_revision"] = revision.topic_id
        # Reserve the next review before this state is persisted so this topic is not resent next run.
        raw_topic["next_review_at"] = next_review_at(revision.topic, now).isoformat()
        delivered += 1
    if delivered:
        write_json(store_path, data)
    return delivered


def update_topic_after_attempt(raw_topic: dict[str, Any], correct: bool, now: datetime) -> TopicPerformance:
    """Record one answer and immediately calculate a revision date from the new mastery."""
    raw_topic["attempts"] = int(raw_topic.get("attempts", 0)) + 1
    raw_topic["correct"] = int(raw_topic.get("correct", 0)) + int(correct)
    topic = TopicPerformance.from_dict(raw_topic)
    raw_topic["next_review_at"] = next_review_at(topic, now).isoformat()
    return topic


def process_updates(store_path: Path, token: str, now: datetime | None = None) -> int:
    """Handle only /start and /status. Grading can be added behind an authenticated webhook later."""
    now = now or datetime.now(timezone.utc)
    data = read_json(store_path)
    telegram = TelegramClient(token)
    handled = 0
    next_offset = int(data.get("telegram_offset", 0))
    for update in telegram.updates(next_offset):
        next_offset = max(next_offset, int(update["update_id"]) + 1)
        message = update.get("message", {})
        chat = message.get("chat", {})
        command = str(message.get("text", "")).strip().split(maxsplit=1)[0].lower()
        student = find_student(data, str(chat.get("id", "")))
        if not student:
            continue
        if command == "/start":
            telegram.send_message(chat["id"], "LectureLoop is connected. Use /status to see your current revision priorities.")
            handled += 1
        elif command == "/status":
            lines = ["Your LectureLoop priorities"]
            for topic in student.get("topics", {}).values():
                correct, attempts = int(topic.get("correct", 0)), int(topic.get("attempts", 0))
                score = 0 if attempts == 0 else round(correct * 100 / attempts)
                lines.append(f"- {topic['title']}: {score}% ({mastery_label(TopicPerformance.from_dict(topic))} priority)")
            telegram.send_message(chat["id"], "\n".join(lines))
            handled += 1
        elif command and not command.startswith("/"):
            topic_id = student.get("active_revision")
            topic = student.get("topics", {}).get(topic_id)
            if not topic or not topic.get("last_question") or not topic.get("last_answer"):
                telegram.send_message(chat["id"], "I do not have an active question yet. Use /status or wait for the next revision prompt.")
                continue
            assessment = assess_answer(str(topic["last_question"]), str(topic["last_answer"]), str(message["text"]))
            updated = update_topic_after_attempt(topic, bool(assessment["correct"]), now)
            student.pop("active_revision", None)
            result = "Correct" if assessment["correct"] else "Not quite"
            telegram.send_message(
                chat["id"],
                f"{result}. {assessment['feedback']}\nNext {updated.title} revision: {topic['next_review_at']}.",
            )
            handled += 1
    data["telegram_offset"] = next_offset
    write_json(store_path, data)
    return handled

