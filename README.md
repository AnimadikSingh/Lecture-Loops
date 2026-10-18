# LectureLoop

LectureLoop is an agentic study companion that turns lecture transcripts and slide PDFs into clean, reviewable notes, flashcards, and quizzes. A separate revision agent watches each student's topic accuracy and sends the most useful next challenge to Telegram.

## The automation loop

```text
Lecture / slide PDF -> Gemini content agent -> materials/<course>.json
Student quiz results -> mastery policy -> due revision -> Telegram challenge
Telegram answer -> Gemini assessment -> updated mastery -> next scheduled run
```

The implementation follows the brief's review policy exactly:

- below 60% mastery: review in 1 day (high priority)
- 60-84% mastery: review in 3 days (medium priority)
- 85-100% mastery: review in 7 days (low priority)

## What is included

- `.github/workflows/lectureloop-ingest.yml`: manually run this Action with a committed transcript or text-based PDF. Gemini returns schema-constrained notes, flashcards, and short-answer quiz items in `materials/<course>.json`.
- `.github/workflows/lectureloop-revision.yml`: runs every 15 minutes, reads Telegram commands and answers, sends due revision prompts, then persists the Telegram cursor, outcome, and next review dates.
- `lectureloop/`: small testable agent modules for extraction, model output validation, scheduling, JSON state, and Telegram communication.

## Setup

1. Create a Telegram bot through [BotFather](https://t.me/BotFather) and copy its token.
2. Create a Gemini key in Google AI Studio.
3. Add repository Action secrets named `GEMINI_API_KEY` and `TELEGRAM_BOT_TOKEN`. Never place either in a committed file.
4. Copy `data/students.example.json` to `data/students.json`, replace the sample chat ID with the student’s chat ID, and commit it only in a private repository. For a production or multi-user system, replace `lectureloop.store` with a database rather than committing learner data.
5. Commit a transcript (`.txt`/`.md`) or a text-based slide PDF. In **Actions**, run **LectureLoop material agent**, enter the course id and source path. Review the generated JSON before sharing it with students.
6. The **LectureLoop revision agent** starts sending reminders when a topic's `next_review_at` becomes due. Students can send `/start`, `/status`, or reply to a delivered question. Gemini grades the reply against its stored reference answer, updates the topic's accuracy, and reschedules it.

## Local check

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest
```

## Important operating notes

- The scheduled workflow has a GitHub Actions `concurrency` lock, so a slow Telegram request cannot cause duplicate revision messages.
- Course source text is treated as untrusted content in the Gemini prompt. Generated material is schema-validated and should still be reviewed by the instructor.
- GitHub's scheduled triggers are not real-time; reminders are generally delivered within the workflow's 15-minute interval and may be delayed by GitHub under load. Use a hosted worker for minute-level delivery.
- This starter reads Telegram messages with `getUpdates`, which is suitable for a class demo but delivers answers on the next scheduled run. Use an authenticated Telegram webhook and database for a production, multi-user system.
