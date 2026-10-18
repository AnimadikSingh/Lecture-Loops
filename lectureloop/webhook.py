"""Optional real-time Telegram webhook server for LectureLoop."""

from __future__ import annotations

import argparse
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, Header, HTTPException

from .agent import dispatch_reminders, process_update
from .store import read_json, write_json
from .telegram import TelegramClient

def _required(name: str) -> str:
    value = os.getenv(name, "")
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def _store_path() -> Path:
    return Path(os.getenv("LECTURELOOP_STORE", "data/students.json"))


def _materials_dir() -> Path:
    return Path(os.getenv("LECTURELOOP_MATERIALS", "materials"))


def dispatch_due_reminders() -> None:
    """Run in the webhook host so it owns state in real-time mode."""
    dispatch_reminders(_store_path(), _required("TELEGRAM_BOT_TOKEN"))


@asynccontextmanager
async def lifespan(_: FastAPI):
    scheduler = BackgroundScheduler(timezone="UTC")
    if os.getenv("LECTURELOOP_REMINDERS", "true").lower() == "true" and os.getenv("TELEGRAM_BOT_TOKEN"):
        interval = max(1, int(os.getenv("LECTURELOOP_REMINDER_MINUTES", "15")))
        scheduler.add_job(dispatch_due_reminders, "interval", minutes=interval, id="lectureloop-reminders", replace_existing=True)
        scheduler.start()
    yield
    if scheduler.running:
        scheduler.shutdown(wait=False)


app = FastAPI(title="LectureLoop Telegram webhook", docs_url=None, redoc_url=None, lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/telegram/webhook")
def telegram_webhook(
    update: dict[str, Any],
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict[str, int | bool]:
    expected_secret = _required("TELEGRAM_WEBHOOK_SECRET")
    if x_telegram_bot_api_secret_token != expected_secret:
        raise HTTPException(status_code=401, detail="invalid Telegram webhook secret")
    data = read_json(_store_path())
    handled = process_update(data, TelegramClient(_required("TELEGRAM_BOT_TOKEN")), update, _materials_dir(), datetime.now(timezone.utc))
    if "update_id" in update:
        data["telegram_offset"] = max(int(data.get("telegram_offset", 0)), int(update["update_id"]) + 1)
    write_json(_store_path(), data)
    return {"ok": True, "handled": handled}


def configure_webhook(url: str, secret: str) -> None:
    TelegramClient(_required("TELEGRAM_BOT_TOKEN")).set_webhook(url.rstrip("/") + "/telegram/webhook", secret)
    print("Telegram webhook configured.")


def main() -> None:
    parser = argparse.ArgumentParser(description="LectureLoop real-time webhook utility")
    subcommands = parser.add_subparsers(dest="command", required=True)
    configure = subcommands.add_parser("configure", help="register a public HTTPS webhook URL with Telegram")
    configure.add_argument("--url", required=True)
    subcommands.add_parser("disable", help="switch Telegram back to scheduled polling")
    args = parser.parse_args()
    if args.command == "configure":
        configure_webhook(args.url, _required("TELEGRAM_WEBHOOK_SECRET"))
    else:
        TelegramClient(_required("TELEGRAM_BOT_TOKEN")).delete_webhook()
        print("Telegram webhook disabled; polling can be used again.")


if __name__ == "__main__":
    main()
