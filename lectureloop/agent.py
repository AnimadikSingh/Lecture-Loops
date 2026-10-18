"""Agent entry points for content ingestion, reminders, and Telegram feedback."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .content import assess_answer, extract_source, generate_materials
from .materials import read_catalog, read_material, sync_student_topics, update_catalog
from .models import TopicPerformance
from .scheduler import mastery_label, next_review_at
from .store import due_revisions, find_student, read_json, write_json
from .telegram import TelegramClient


def ingest(source_path: Path, course_id: str, output_path: Path, store_path: Path | None = None) -> dict[str, Any]:
    if not course_id.replace("-", "").replace("_", "").isalnum():
        raise ValueError("course_id may contain only letters, numbers, hyphens, and underscores")
    materials = generate_materials(extract_source(source_path), course_id)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    import json
    output_path.write_text(json.dumps(materials, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    update_catalog(output_path.parent, course_id, materials)
    if store_path:
        sync_student_topics(store_path, course_id, materials, datetime.now(timezone.utc))
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


def _course_id(argument: str, student: dict[str, Any], materials_dir: Path) -> str:
    available = [item["id"] for item in read_catalog(materials_dir)]
    allowed = [course for course in student.get("courses", available) if course in available]
    if argument and argument in allowed:
        return argument
    if len(allowed) == 1:
        return allowed[0]
    raise ValueError("Choose a course: " + ", ".join(allowed or available))


def _send_course_list(telegram: TelegramClient, chat_id: int, student: dict[str, Any], materials_dir: Path) -> None:
    catalog = read_catalog(materials_dir)
    courses = [item for item in catalog if item["id"] in student.get("courses", [entry["id"] for entry in catalog])]
    if not courses:
        telegram.send_message(chat_id, "No course material is available yet. Generate a lecture from GitHub Actions first.")
        return
    lines = ["Your courses:"]
    lines.extend(f"- {item['title']} (`{item['id']}`): {item['flashcard_count']} cards, {item['quiz_count']} questions" for item in courses)
    lines.append("\nUse /notes COURSE, /flashcards COURSE, or /quiz COURSE.")
    telegram.send_message(chat_id, "\n".join(lines))


def _handle_flashcard_callback(telegram: TelegramClient, callback: dict[str, Any], student: dict[str, Any], materials_dir: Path) -> bool:
    parts = str(callback.get("data", "")).split("|")
    if len(parts) != 4 or parts[0] != "card":
        return False
    _, course_id, raw_index, action = parts
    if course_id not in student.get("courses", [course_id]):
        return False
    material = read_material(materials_dir, course_id)
    cards = material.get("flashcards", [])
    index = int(raw_index)
    if not 0 <= index < len(cards):
        return False
    telegram.answer_callback(str(callback["id"]))
    telegram.send_flashcard(callback["message"]["chat"]["id"], course_id, index, cards[index], len(cards), answer=action == "reveal")
    return True


def process_update(data: dict[str, Any], telegram: TelegramClient, update: dict[str, Any], materials_dir: Path, now: datetime) -> int:
    """Process one Telegram update; shared by scheduled polling and real-time webhooks."""
    callback = update.get("callback_query")
    if callback:
        chat_id = str(callback.get("message", {}).get("chat", {}).get("id", ""))
        student = find_student(data, chat_id)
        try:
            return int(bool(student and _handle_flashcard_callback(telegram, callback, student, materials_dir)))
        except (ValueError, KeyError):
            return 0
    message = update.get("message", {})
    chat = message.get("chat", {})
    command = str(message.get("text", "")).strip().split(maxsplit=1)[0].lower()
    student = find_student(data, str(chat.get("id", "")))
    if not student:
        return 0
    argument = str(message.get("text", "")).strip().partition(" ")[2].strip()
    if command == "/start":
        telegram.send_message(chat["id"], "LectureLoop is connected. Use /courses to open notes, flashcards, and quizzes; /status shows revision priorities.")
    elif command in {"/help", "/courses"}:
        _send_course_list(telegram, chat["id"], student, materials_dir)
    elif command == "/notes":
        try:
            material = read_material(materials_dir, _course_id(argument, student, materials_dir))
            text = f"{material['title']} - Notes\n\n{material['summary']}\n\n" + "\n\n".join(f"{topic['title']}\n{topic['notes']}" for topic in material["topics"])
            telegram.send_message(chat["id"], text)
        except ValueError as exc:
            telegram.send_message(chat["id"], str(exc))
    elif command == "/flashcards":
        try:
            course_id = _course_id(argument, student, materials_dir)
            material = read_material(materials_dir, course_id)
            cards = material.get("flashcards", [])
            if not cards:
                raise ValueError("This course has no flashcards yet.")
            telegram.send_flashcard(chat["id"], course_id, 0, cards[0], len(cards))
        except ValueError as exc:
            telegram.send_message(chat["id"], str(exc))
    elif command == "/quiz":
        try:
            course_id = _course_id(argument, student, materials_dir)
            material = read_material(materials_dir, course_id)
            questions = material.get("quiz", [])
            if not questions:
                raise ValueError("This course has no quiz questions yet.")
            item = questions[0]
            topic_key = f"{course_id}:{item['topic_id']}"
            raw_topic = student["topics"].get(topic_key)
            if not raw_topic:
                raise ValueError("Run the material-generation workflow again to prepare this student's quiz topics.")
            raw_topic["last_question"], raw_topic["last_answer"] = item["question"], item["answer"]
            student["active_revision"] = topic_key
            telegram.send_message(chat["id"], f"Quiz: {item['question']}\n\nReply with your answer and I will grade it.")
        except ValueError as exc:
            telegram.send_message(chat["id"], str(exc))
    elif command == "/status":
        lines = ["Your LectureLoop priorities"]
        for topic in student.get("topics", {}).values():
            correct, attempts = int(topic.get("correct", 0)), int(topic.get("attempts", 0))
            score = 0 if attempts == 0 else round(correct * 100 / attempts)
            lines.append(f"- {topic['title']}: {score}% ({mastery_label(TopicPerformance.from_dict(topic))} priority)")
        telegram.send_message(chat["id"], "\n".join(lines))
    elif command and not command.startswith("/"):
        topic_id = student.get("active_revision")
        topic = student.get("topics", {}).get(topic_id)
        if not topic or not topic.get("last_question") or not topic.get("last_answer"):
            telegram.send_message(chat["id"], "I do not have an active question yet. Use /status or wait for the next revision prompt.")
            return 1
        assessment = assess_answer(str(topic["last_question"]), str(topic["last_answer"]), str(message["text"]))
        updated = update_topic_after_attempt(topic, bool(assessment["correct"]), now)
        student.pop("active_revision", None)
        result = "Correct" if assessment["correct"] else "Not quite"
        telegram.send_message(chat["id"], f"{result}. {assessment['feedback']}\nNext {updated.title} revision: {topic['next_review_at']}.")
    else:
        return 0
    return 1


def process_updates(store_path: Path, token: str, materials_dir: Path = Path("materials"), now: datetime | None = None) -> int:
    """Poll and process pending Telegram updates for the GitHub Actions fallback."""
    now = now or datetime.now(timezone.utc)
    data = read_json(store_path)
    telegram = TelegramClient(token)
    handled = 0
    next_offset = int(data.get("telegram_offset", 0))
    for update in telegram.updates(next_offset):
        next_offset = max(next_offset, int(update["update_id"]) + 1)
        handled += process_update(data, telegram, update, materials_dir, now)
    data["telegram_offset"] = next_offset
    write_json(store_path, data)
    return handled

