"""Course catalog and per-student topic synchronization."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .store import read_json, write_json


def material_path(materials_dir: Path, course_id: str) -> Path:
    if not course_id.replace("-", "").replace("_", "").isalnum():
        raise ValueError("course_id may contain only letters, numbers, hyphens, and underscores")
    return materials_dir / f"{course_id}.json"


def read_material(materials_dir: Path, course_id: str) -> dict[str, Any]:
    path = material_path(materials_dir, course_id)
    if not path.exists():
        raise ValueError(f"No generated material exists for '{course_id}'")
    return json.loads(path.read_text(encoding="utf-8"))


def read_catalog(materials_dir: Path) -> list[dict[str, Any]]:
    index_path = materials_dir / "index.json"
    if not index_path.exists():
        return []
    courses = json.loads(index_path.read_text(encoding="utf-8")).get("courses", [])
    return courses if isinstance(courses, list) else []


def update_catalog(materials_dir: Path, course_id: str, materials: dict[str, Any]) -> None:
    index_path = materials_dir / "index.json"
    catalog = {item["id"]: item for item in read_catalog(materials_dir) if isinstance(item, dict) and "id" in item}
    catalog[course_id] = {
        "id": course_id,
        "title": str(materials["title"]),
        "file": f"{course_id}.json",
        "topic_count": len(materials.get("topics", [])),
        "flashcard_count": len(materials.get("flashcards", [])),
        "quiz_count": len(materials.get("quiz", [])),
    }
    index_path.write_text(json.dumps({"courses": sorted(catalog.values(), key=lambda item: item["title"].lower())}, indent=2) + "\n", encoding="utf-8")


def sync_student_topics(store_path: Path, course_id: str, materials: dict[str, Any], now: datetime) -> int:
    """Make every generated topic immediately available to every configured student."""
    data = read_json(store_path)
    quiz_by_topic = {item["topic_id"]: item for item in materials.get("quiz", [])}
    created = 0
    for student in data["students"]:
        student.setdefault("courses", [])
        if course_id not in student["courses"]:
            student["courses"].append(course_id)
        topics = student.setdefault("topics", {})
        for item in materials.get("topics", []):
            topic_key = f"{course_id}:{item['id']}"
            quiz = quiz_by_topic.get(item["id"], {})
            if topic_key not in topics:
                topics[topic_key] = {
                    "title": item["title"],
                    "attempts": 0,
                    "correct": 0,
                    "difficulty": "medium",
                    "next_review_at": now.isoformat(),
                    "last_question": quiz.get("question", f"Explain {item['title']} in your own words."),
                    "last_answer": quiz.get("answer", item["notes"]),
                }
                created += 1
    write_json(store_path, data)
    return created
