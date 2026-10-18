"""Minimal Telegram Bot API client with deliberately narrow capabilities."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


class TelegramClient:
    def __init__(self, token: str) -> None:
        if not token.strip():
            raise ValueError("TELEGRAM_BOT_TOKEN is required")
        self.base_url = f"https://api.telegram.org/bot{token}"

    def _post(self, method: str, payload: dict[str, Any]) -> Any:
        request = urllib.request.Request(
            f"{self.base_url}/{method}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Telegram {method} failed: {exc.reason}") from exc
        if not body.get("ok"):
            raise RuntimeError(f"Telegram {method} rejected request: {body.get('description')}")
        return body["result"]

    def send_revision(self, chat_id: str, topic_title: str, question: str, urgency: str) -> None:
        text = (
            "LectureLoop revision\n"
            f"Your {urgency}-priority topic is {topic_title}.\n\n"
            f"⚡ Quick challenge: {question}\n\n"
            "Reply with your answer. I will update your revision schedule, or use /status to see your learning profile."
        )
        self.send_message(chat_id, text)

    def send_message(self, chat_id: str | int, text: str) -> None:
        for part in _message_chunks(text):
            self._post("sendMessage", {"chat_id": chat_id, "text": part})

    def send_flashcard(self, chat_id: str | int, course_id: str, index: int, card: dict[str, Any], total: int, answer: bool = False) -> None:
        text = f"Flashcard {index + 1}/{total}\n\nQ: {card['front']}"
        if answer:
            text += f"\n\nA: {card['back']}"
        buttons = [] if answer else [{"text": "Reveal answer", "callback_data": f"card|{course_id}|{index}|reveal"}]
        buttons.append({"text": "Next card", "callback_data": f"card|{course_id}|{(index + 1) % total}|show"})
        self._post("sendMessage", {"chat_id": chat_id, "text": text, "reply_markup": {"inline_keyboard": [buttons]}})

    def answer_callback(self, callback_id: str) -> None:
        self._post("answerCallbackQuery", {"callback_query_id": callback_id})

    def updates(self, offset: int) -> list[dict[str, Any]]:
        return self._post("getUpdates", {"offset": offset, "timeout": 0, "allowed_updates": ["message", "callback_query"]})


def _message_chunks(text: str, limit: int = 4000) -> list[str]:
    """Telegram caps messages at 4096 characters; preserve line boundaries where possible."""
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    remaining = text
    while remaining:
        cut = remaining.rfind("\n", 0, limit)
        cut = cut if cut > 0 else limit
        chunks.append(remaining[:cut])
        remaining = remaining[cut:].lstrip("\n")
    return chunks

