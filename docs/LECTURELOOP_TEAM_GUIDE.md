# LectureLoop - Team Documentation

**Domain:** Agentic AI, education automation, personalized learning  
**Prototype stack:** Python, Gemini, Telegram, GitHub Actions, GitHub Pages, JSON, `pypdf`

## Project purpose

LectureLoop turns a lecture transcript or readable slide PDF into clean notes, flashcards, and practice questions. It then observes a student's performance by topic, selects a weak topic when it is due for revision, and sends a focused challenge through Telegram.

This is more than a normal AI note generator:

```text
Normal AI: generate notes -> stop
LectureLoop: generate -> practice -> measure -> schedule -> remind -> reassess
```

The continuous learning loop is:

```text
Lecture material
  ↓
Gemini content analysis
  ↓
Notes + flashcards + quiz questions
  ↓
Telegram bot or study dashboard
  ↓
Student response and topic-level accuracy update
  ↓
Spaced-repetition schedule
  ↓
Targeted Telegram revision prompt
  ↺
```

## Problem being solved

Students may have recordings, slides, and notes but still do not know what to revise. They reread passively, forget wrong answers, and use the same revision plan even when their strengths differ.

LectureLoop solves five practical problems:

1. **Information overload:** long content becomes structured topics and concise notes.
2. **Passive study:** flashcards and quiz questions require active recall.
3. **Generic revision:** accuracy is tracked for each topic, not just each course.
4. **Forgotten mistakes:** incorrect answers make that topic return sooner.
5. **Poor timing:** a spaced-repetition rule decides when a topic returns.

## Why this is an AI agent

| Agent capability | LectureLoop behavior |
|---|---|
| Observe | Reads source content, Telegram updates, attempts, correct answers, and due dates. |
| Understand | Extracts topics and creates learning assets through Gemini. |
| Reason | Calculates accuracy and identifies the weak due topic. |
| Decide | Chooses a review interval and one focused challenge. |
| Act | Sends Telegram notes, flashcards, questions, feedback, and reminders. |
| Learn | Saves the result and adapts the next revision date. |

## Revision policy

```text
accuracy = correct answers / total attempts
```

| Accuracy | Priority | Next revision |
|---|---|---|
| Below 60% | High | 1 day |
| 60% to 84% | Medium | 3 days |
| 85% to 100% | Low | 7 days |

Only one focused prompt is sent at a time. This avoids notification spam and makes it possible to connect the next free-text answer to the active question safely.

## Delivered features

### 1. Material-generation agent

The agent accepts one `.txt`, `.md`, or readable text-based `.pdf` source. Gemini returns schema-constrained JSON containing a title, summary, topics, flashcards, quiz questions, and reference answers. The code validates that every card and question refers to a known topic.

Generated outputs:

```text
materials/<course-id>.json
materials/index.json
```

New generated topics are automatically added to every configured student's profile.

### 2. Telegram study bot

| Command | Result |
|---|---|
| `/start` | Confirms the connection and explains next commands. |
| `/courses` | Lists generated courses. |
| `/notes COURSE` | Sends course summary and topic notes. |
| `/flashcards COURSE` | Sends an interactive card with **Reveal answer** and **Next card** buttons. |
| `/quiz COURSE` | Sends a question and waits for a normal text answer. |
| `/status` | Shows topic percentages and priorities. |

Example: `/flashcards dbms-unit-1`

### 3. Answer assessment

For a quiz or revision reply, Gemini receives the question, stored reference answer, and student answer. It returns a validated result like:

```json
{"correct": true, "feedback": "Short encouraging feedback."}
```

LectureLoop then increments `attempts`, increments `correct` only for a correct response, recalculates accuracy, updates `next_review_at`, and messages the student with feedback.

### 4. Study dashboard

The GitHub Pages dashboard has a course picker plus three views:

- notes and topic explanations;
- click-to-reveal flashcards with previous/next navigation;
- practice questions with revealable reference answers.

The deployment copies only `dashboard/` and `materials/`. Student profiles, tokens, and secrets are never published to the dashboard.

## Architecture

```text
                  GitHub repository
     lectures/      materials/       data/students.json
         │              │                    │
         ▼              │                    ▼
 Material Agent          │          Revision Agent (every 15 min)
         │              │                    │
         ▼              │                    ▼
    Gemini API           │             Telegram Bot API
         │              │                    │
         ├── course JSON │                    ├── commands and buttons
         └── topic sync  │                    ├── answer assessment
                         ▼                    └── updated schedule
                GitHub Pages dashboard
```

## Technology stack

| Technology | Purpose |
|---|---|
| Python 3.12 | Automation and agent logic. |
| Google Gemini API | Course generation and answer assessment. |
| Telegram Bot API | Interactive study delivery and reminders. |
| GitHub Actions | Runs workflows without a permanent server. |
| GitHub Pages | Hosts the static dashboard. |
| `pypdf` | Extracts selectable text from PDFs. |
| JSON | Prototype storage for courses and student state. |
| `pytest` | Automated validation of core behavior. |

## Repository structure

```text
lectureloops/
├── .github/workflows/
│   ├── lectureloop-ingest.yml       # Material-generation workflow
│   ├── lectureloop-revision.yml     # Telegram and revision workflow
│   └── lectureloop-dashboard.yml    # GitHub Pages deployment
├── dashboard/                       # Static study interface
├── data/
│   ├── students.example.json        # Safe template
│   └── students.json                # Real student data; private repository only
├── docs/LECTURELOOP_TEAM_GUIDE.md   # This document
├── lectures/                        # Input lecture files
├── materials/                       # Generated course assets and catalog
├── lectureloop/
│   ├── agent.py                     # Workflow and Telegram command orchestration
│   ├── content.py                   # Gemini generation and assessment
│   ├── materials.py                 # Catalog and student-topic synchronization
│   ├── scheduler.py                 # 1/3/7-day policy
│   ├── store.py                     # JSON validation and persistence
│   ├── telegram.py                  # Telegram API and flashcard controls
│   └── cli.py                       # Commands run by Actions
├── tests/                           # Automated tests
└── README.md                        # Quick-start guide
```

## End-to-end process

### A. Add learning material

Put one source file per lecture or unit inside `lectures/`:

```text
lectures/java-introduction.txt
lectures/java-oop.pdf
lectures/dbms-normalization.txt
```

Preferred formats are `.txt` for lecture transcripts, `.md` for existing written notes, and text-based PDFs with selectable text. The prototype does not yet transcribe audio/video directly; convert a recording to text first.

### B. Generate course content

Open **Actions -> LectureLoop material agent -> Run workflow**. For example:

```text
Course ID: java-introduction
Source path: lectures/java-introduction.txt
```

When one supported lecture file is pushed to `lectures/`, the workflow starts automatically and derives a course ID from the filename. It also remains available as a manual workflow when the team wants to choose a custom course ID or process multiple files. It checks out the repository, extracts text, calls Gemini, validates JSON output, writes the course JSON and catalog, synchronizes new topics into student profiles, and commits its output back to GitHub.

The academic/content team must review the generated material before presenting it as final learning content.

### C. Study in Telegram or the dashboard

Both interfaces consume the same generated course JSON. This keeps notes, flashcards, and questions consistent. A student can use `/courses`, then `/notes COURSE`, `/flashcards COURSE`, or `/quiz COURSE`.

### D. Adapt after an answer

The revision workflow reads Telegram updates, handles commands and flashcard-button clicks, grades eligible text responses, and recalculates the topic date. A saved Telegram update offset prevents old messages from being processed again.

## Student profile format

`data/students.json` is the prototype database. A student record contains:

```json
{
  "student_id": "student-001",
  "telegram_chat_id": "123456789",
  "timezone": "Asia/Kolkata",
  "courses": ["dbms-unit-1"],
  "topics": {
    "dbms-unit-1:normalization": {
      "title": "Normalization",
      "attempts": 5,
      "correct": 2,
      "difficulty": "high",
      "next_review_at": "2026-10-19T09:00:00+05:30",
      "last_question": "Why is third normal form useful?",
      "last_answer": "It removes transitive dependencies and reduces redundancy."
    }
  }
}
```

| Field | Meaning |
|---|---|
| `telegram_chat_id` | Telegram conversation to receive bot messages. |
| `courses` | Course IDs available to that student. |
| `attempts` and `correct` | Values used to calculate mastery. |
| `next_review_at` | Timestamp when a topic becomes due; includes timezone. |
| `last_question` and `last_answer` | Used to assess an active answer. |
| `active_revision` | Temporary key while one response is pending. |

For a production version, use PostgreSQL, Firebase, or Supabase with authentication instead of JSON.

## GitHub Actions workflows

### Material agent

- **File:** `.github/workflows/lectureloop-ingest.yml`
- **Trigger:** Manual run
- **Secret required:** `GEMINI_API_KEY`
- **Use when:** A lecture is added or source content is improved.

### Revision agent

- **File:** `.github/workflows/lectureloop-revision.yml`
- **Trigger:** Every 15 minutes and manual run
- **Secrets required:** `GEMINI_API_KEY`, `TELEGRAM_BOT_TOKEN`

Order of work:

1. Read Telegram messages and button clicks.
2. Save the latest Telegram update offset.
3. Assess answers and update performance.
4. Find due topics.
5. Send at most one weak due topic per student.
6. Save updated state.

The workflow has a concurrency lock to reduce duplicate reminders during slow API calls.

### Dashboard publisher

- **File:** `.github/workflows/lectureloop-dashboard.yml`
- **Trigger:** Dashboard/material changes and manual run
- **One-time setup:** GitHub **Settings -> Pages -> Source -> GitHub Actions**

The successful deployment contains the Pages URL for the team to share.

## Secrets, privacy, and security

Create these in GitHub: **Settings -> Secrets and variables -> Actions -> New repository secret**.

| Secret | Purpose |
|---|---|
| `GEMINI_API_KEY` | Material generation and answer assessment. |
| `TELEGRAM_BOT_TOKEN` | Secure access to Telegram's Bot API. |

Team rules:

1. Never commit a token or API key.
2. Never put a token in `students.json`.
3. If a token appears in a screenshot/chat, revoke it in BotFather and replace the GitHub secret.
4. Keep repositories containing real learner data private.
5. Never publish student names, marks, phone numbers, or chats on GitHub Pages.
6. Review AI-generated academic content before sharing it.

## Team workflow

### Add another lecture

1. Add the source in `lectures/`.
2. Commit and push the file.
3. Run the Material Agent with the course ID and source path.
4. Review the new JSON in `materials/`.
5. Test `/courses`, `/flashcards COURSE`, and `/quiz COURSE`.

### Make an improvement

Start with `git pull --rebase origin main` so that workflow-generated commits are included locally. Run `pytest`, stage the required files, commit with a clear message, and run `git push`.

If Git says `fetch first`, GitHub contains a newer commit, commonly created by a workflow. Run `git pull --rebase origin main` and then run `git push`. Do not use force push.

## Testing and demonstration checklist

Local test setup:

```powershell
cd C:\Projects1211\lectureloops
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest
```

Tests cover the 1/3/7-day schedule, timezone-aware dates, invalid scores, rescheduling after answers, due-topic selection, and automatic material synchronization.

Before a demonstration, verify:

1. A lecture file exists under `lectures/`.
2. The Material Agent created `materials/<course-id>.json`.
3. `/courses` lists the course.
4. `/flashcards <course-id>` shows interactive buttons.
5. `/quiz <course-id>` accepts and assesses an answer.
6. `attempts`, `correct`, and `next_review_at` change in the student profile.
7. The dashboard lists the course and displays its material.

## Limitations and next upgrades

| Current limitation | Reason | Next step |
|---|---|---|
| Telegram can take up to 15 minutes to answer. | GitHub Actions polls Telegram on a schedule. | Deploy an authenticated webhook service. |
| JSON acts as the database. | It is clear and easy for a demo. | Use a managed database with login. |
| Scanned PDFs are unreliable. | Text extraction needs selectable text. | Add OCR. |
| Audio/video needs a transcript first. | Transcription is outside the prototype. | Add Whisper or speech-to-text. |
| Dashboard is read-only. | GitHub Pages is static. | Add login, answer forms, and progress charts. |
| Generated material may be imperfect. | LLM output needs oversight. | Add teacher editing/approval. |

## Suggested team roles

| Role | Responsibility |
|---|---|
| AI/backend | Gemini prompts, assessment, validation, scheduler. |
| Automation/DevOps | Secrets, Actions, deployments, workflow monitoring. |
| Frontend | Dashboard and student usability. |
| Academic/content | Lecture quality and fact-checking. |
| QA/documentation | Tests, demo script, screenshots, and guides. |

## Presentation script

1. **Capture:** We add a lecture transcript or PDF.
2. **Understand:** Gemini extracts concepts.
3. **Generate:** LectureLoop makes notes, cards, and questions.
4. **Practice:** The student studies through Telegram or the dashboard.
5. **Analyze:** Topic-wise correctness is recorded.
6. **Personalize:** Weak topics return tomorrow, medium topics after three days, and strong topics after seven days.
7. **Act:** Telegram sends one targeted challenge.
8. **Learn:** The answer changes the next schedule.

The key message is: **LectureLoop creates a continuous adaptive learning loop, not just one-time AI notes.**

## Quick reference

```text
New lecture?        Add it to lectures/ and run the Material Agent.
See courses?        /courses
Read notes?         /notes COURSE
Use flashcards?     /flashcards COURSE
Take a quiz?        /quiz COURSE, then reply normally.
See priorities?     /status
Bot is quiet?       Run the Revision Agent manually or wait for the scheduled check.
Push rejected?      git pull --rebase origin main, then git push.
```
