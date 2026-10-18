# LectureLoop Real-Time Telegram Setup

## Why this is separate from GitHub Actions

GitHub Actions is excellent for scheduled jobs, but it is not an always-running web server. The original revision workflow checks Telegram approximately every 15 minutes, so it cannot guarantee an instant reply.

For immediate replies, Telegram must deliver each message to a public HTTPS **webhook**. The new `lectureloop.webhook` service receives that delivery immediately, processes the same LectureLoop commands, and runs due-reminder checks on the same host.

Only use one mode at a time:

| Mode | Telegram response time | Where state is updated |
|---|---|---|
| GitHub Actions polling | Usually within 15 minutes | GitHub repository |
| Webhook server | Usually within a few seconds | Server's `data/students.json` file |

Do not enable the Telegram webhook while keeping the polling command step active. Telegram disables `getUpdates` when a webhook is registered. The updated GitHub revision workflow automatically skips its polling and reminder steps when the `TELEGRAM_WEBHOOK_URL` GitHub secret is present.

## Immediate local demo (your laptop)

This is the easiest way to demonstrate instant replies. It works only while your laptop, terminal, and internet connection remain on.

### 1. Install dependencies

```powershell
cd C:\Projects1211\lectureloops
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Set secrets for the current terminal session

Do not commit these values to a file.

```powershell
$env:TELEGRAM_BOT_TOKEN = "YOUR_NEW_TELEGRAM_TOKEN"
$env:GEMINI_API_KEY = "YOUR_GEMINI_KEY"
$env:TELEGRAM_WEBHOOK_SECRET = [guid]::NewGuid().ToString("N")
$env:LECTURELOOP_REMINDER_MINUTES = "15"
```

Keep this PowerShell window open. If it closes, set the same variables again. Store the generated webhook secret in a password manager; it must remain the same for the server process and webhook registration.

### 3. Start the LectureLoop webhook server

```powershell
uvicorn lectureloop.webhook:app --host 0.0.0.0 --port 8000
```

Leave this terminal running. Visit `http://localhost:8000/health` in a browser; it should display `{"status":"ok"}`.

### 4. Create a public HTTPS address

Telegram cannot send requests to `localhost`; it requires a public HTTPS URL. For a live deployment, use a hosted service. For a local demonstration, use a secure HTTPS tunnel such as Cloudflare Tunnel.

Install Cloudflare Tunnel (`cloudflared`) using its official instructions, then open a **second** PowerShell window and run:

```powershell
cloudflared tunnel --url http://localhost:8000
```

Copy the temporary URL that starts with `https://` and ends with `trycloudflare.com`.

### 5. Register the Telegram webhook

In the first PowerShell window, keep the server running. Open a **third** PowerShell window, set the same three secrets again, and run:

```powershell
$env:LECTURELOOP_URL = "https://YOUR-TUNNEL.trycloudflare.com"
python -m lectureloop.webhook configure --url $env:LECTURELOOP_URL
```

Telegram now sends `/start`, `/courses`, `/flashcards`, `/quiz`, `/status`, button clicks, and text answers directly to the server. Replies should arrive within a few seconds.

### 6. Switch GitHub Actions out of polling mode

In the repository, open **Settings -> Secrets and variables -> Actions** and add:

```text
Name: TELEGRAM_WEBHOOK_URL
Value: https://YOUR-TUNNEL.trycloudflare.com
```

This tells the scheduled GitHub workflow not to poll or send reminders while the webhook server owns Telegram state. The local webhook service itself sends due reminders every 15 minutes.

## Add new PDFs/material while using webhook mode

1. Add the new PDF or transcript in `lectures/`.
2. Commit and push only the changed file; Git sends only changes, not the entire project again.
3. Run the Material Agent in GitHub Actions.
4. After the GitHub workflow creates material, run `git pull --rebase origin main` locally.
5. Restart the local webhook server so it reads the updated `materials/` files.

The generated material normally appears in the dashboard after the Material Agent commits it and the dashboard deployment completes. This is commonly a few minutes, not a fixed exact time. Refresh the browser after the Pages deployment is successful.

## Switch back to GitHub Actions polling

In a terminal with `TELEGRAM_BOT_TOKEN` set, run:

```powershell
python -m lectureloop.webhook disable
```

Then delete the `TELEGRAM_WEBHOOK_URL` GitHub secret. The scheduled revision workflow can poll Telegram again.

## Production deployment

For a real always-on system, deploy the FastAPI service to a platform such as Render, Railway, Fly.io, or a cloud container service, and configure a persistent database. The server must have:

- a public HTTPS URL;
- `TELEGRAM_BOT_TOKEN`, `GEMINI_API_KEY`, and `TELEGRAM_WEBHOOK_SECRET` configured as host secrets;
- durable student storage (PostgreSQL/Firebase/Supabase recommended);
- a background scheduler or external cron for due reminders.

Do not rely on an ephemeral hosting filesystem for real student data. The local JSON implementation is ideal for the project demonstration, but a database is the production upgrade.
