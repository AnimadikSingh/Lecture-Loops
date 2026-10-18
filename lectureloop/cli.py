"""Command-line interface used locally and by GitHub Actions."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from .agent import dispatch_reminders, ingest, process_updates


def main() -> None:
    parser = argparse.ArgumentParser(description="LectureLoop automation agent")
    commands = parser.add_subparsers(dest="command", required=True)
    ingest_parser = commands.add_parser("ingest", help="create notes, flashcards, and quiz JSON")
    ingest_parser.add_argument("--course", required=True)
    ingest_parser.add_argument("--source", required=True, type=Path)
    ingest_parser.add_argument("--output", required=True, type=Path)
    ingest_parser.add_argument("--store", type=Path, help="student store to update with generated course topics")
    for name, help_text in [("dispatch", "send due Telegram revisions"), ("updates", "process Telegram commands")]:
        action = commands.add_parser(name, help=help_text)
        action.add_argument("--store", required=True, type=Path)
    args = parser.parse_args()
    if args.command == "ingest":
        materials = ingest(args.source, args.course, args.output, args.store)
        print(f"Generated {len(materials['topics'])} topics, {len(materials['flashcards'])} cards, and {len(materials['quiz'])} questions.")
        return
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    count = dispatch_reminders(args.store, token) if args.command == "dispatch" else process_updates(args.store, token)
    print(f"Processed {count} Telegram action(s).")


if __name__ == "__main__":
    main()

