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
- `dashboard/`: a GitHub Pages study dashboard for generated notes, click-to-reveal flashcards, and quiz answers.
- `lectureloop/`: small testable agent modules for extraction, model output validation, scheduling, JSON state, and Telegram communication.

## Setup

1. Create a Telegram bot through [BotFather](https://t.me/BotFather) and copy its token.
2. Create a Gemini key in Google AI Studio.
3. Add repository Action secrets named `GEMINI_API_KEY` and `TELEGRAM_BOT_TOKEN`. Never place either in a committed file.
4. Copy `data/students.example.json` to `data/students.json`, replace the sample chat ID with the student’s chat ID, and commit it only in a private repository. For a production or multi-user system, replace `lectureloop.store` with a database rather than committing learner data.
5. Commit and push one transcript (`.txt`/`.md`) or text-based slide PDF in `lectures/`. The **LectureLoop material agent** starts automatically and derives the course ID from its filename. You can also run the workflow manually to choose the course ID or handle multiple lecture files. Review the generated JSON before sharing it with students.
6. The **LectureLoop revision agent** starts sending reminders when a topic's `next_review_at` becomes due. Students can use `/courses`, `/notes COURSE`, `/flashcards COURSE`, `/quiz COURSE`, `/start`, and `/status`; clicking a flashcard reveals its answer directly in Telegram. Gemini grades quiz or revision replies, updates topic accuracy, and reschedules the topic.

## Add more study material

Keep one lecture transcript or readable slide PDF per file in `lectures/`. For example:

```text
lectures/dbms-unit-1.txt
lectures/dbms-unit-2.pdf
lectures/os-processes.txt
```

Commit and push one new source file at a time. The **LectureLoop material agent** starts automatically, updates the course catalog, creates the material JSON, and adds those topics to every configured student automatically. The dashboard publisher then runs after a successful material workflow. It is safe to re-run a course when the lecture file is improved.

## Study in Telegram

After a scheduled or manually run revision workflow processes `/start`, use:

```text
/courses
/notes dbms-unit-1
/flashcards dbms-unit-1
/quiz dbms-unit-1
/status
```

Flashcards have Telegram buttons for revealing an answer and moving to the next card. `/quiz` sends one question; reply normally to have the answer assessed and the revision date updated.

## Publish the dashboard

The **Publish LectureLoop dashboard** workflow deploys notes, flashcards, and quiz answers to GitHub Pages. It deliberately publishes only `dashboard/` and `materials/`, never `data/students.json` or secrets.

In GitHub, open **Settings → Pages**, set **Source** to **GitHub Actions**, then run the dashboard workflow once. Its deployment result contains the dashboard URL. Keep the repository private, or only publish materials that are safe for public viewing.

## Instant Telegram replies

GitHub Actions polling answers Telegram messages on its next scheduled run, normally within 15 minutes. For immediate replies, run the optional FastAPI webhook service and point Telegram to its public HTTPS URL. The full local-demo and production guidance is in [Real-Time Telegram Setup](docs/INSTANT_TELEGRAM_SETUP.md).

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
