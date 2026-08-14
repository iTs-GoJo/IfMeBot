# 🚀 IfMeBot (Reverse AI)

A friendly Persian (Farsi) Telegram group bot that injects fun, thought-provoking personal questions and group polls—powered by a lightweight LLM-backed AI. Ideal for communities that want to boost engagement with short personal prompts and automated polls.

---

✨ Highlights

- 🎯 Targets Persian-speaking Telegram groups (Farsi)
- 🗣️ Personal questions: privately asks active users short, casual prompts and uses AI to analyze replies
- 📊 Group polls: auto-creates 4-option polls after group activity thresholds are met
- 💾 Lightweight persistence using local SQLite (no external DB required)
- ⚙️ Easy configuration via environment variables / .env

---

## 📚 Table of contents

- [What this is](#what-this-is)
- [Features](#features)
- [Stack](#stack)
- [Project layout](#project-layout)
- [How it works](#how-it-works)
- [Requirements](#requirements)
- [Quick start](#quick-start)
- [Environment variables](#environment-variables)
- [Runtime & behavior](#runtime--behavior)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [Security & privacy](#security--privacy)
- [License](#license)
- [FAQ / Try asking](#faq--try-asking)

---

## What this is

IfMeBot (Reverse AI) is a small, opinionated Telegram bot that:

- Periodically asks an individual user a short, casual Persian question when they become active.
- Generates an AI-powered follow-up or summary based on the user's reply.
- Creates community polls automatically after group activity meets configured thresholds.

It aims to be lightweight, fun, and low-friction for admins to run on any host with Python.

---

## Features

- 🤖 LLM-powered question and poll generation
- 📨 Private personal question delivery to active users
- 📈 Group XP/levels and threshold-driven polls
- 🔁 Local SQLite persistence (reverse_ai.db)
- 🛠️ Configurable via .env and environment variables

---

## Stack

- Language: Python 3.10+
- Bot framework: python-telegram-bot (v22.x) with JobQueue
- HTTP client: httpx
- Config: python-dotenv

---

## Project layout

```
.ai.py        # AI integration (LLM calls for question/poll gen & analysis)
.bot.py       # Telegram handlers, main entrypoint, scheduling poll finish jobs
.config.py    # Env var loading and defaults
.database.py  # SQLite persistence (groups, users, polls)
.levels.py    # Group XP/level math and poll thresholds
.requirements.txt
.LICENSE
.env          # example: not committed
README.md
```

Bot flow summary: bot.py wires the Application and handlers. Incoming messages update per-user counters and group XP via database.py and levels.py. When a user or group hits configured thresholds, the bot generates personal questions or polls via ai.py and posts them.

---

## Requirements

- Python 3.10+
- Telegram bot token (see environment variables)
- Recommended: run in a single process (SQLite locking can appear under heavy concurrency)

---

## Quick start

1. Clone and install dependencies

```bash
git clone https://github.com/iTs-GoJo/IfMeBot.git
cd IfMeBot
python -m pip install -r requirements.txt
```

2. Create a `.env` file (see below)
3. Run the bot

```bash
python bot.py
```

The bot will create a local SQLite DB named `reverse_ai.db` in the repository directory.

---

## Environment variables

Create a `.env` file in the project root with these keys (example):

```env
# Required
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
AI_API_KEY=your-ai-api-key

# Optional overrides
AI_BASE_URL=https://api.groq.com/openai/v1
AI_MODEL=llama-3.3-70b-versatile

# Personal question tuning
PERSONAL_MIN_MESSAGES=10
PERSONAL_MAX_MESSAGES=20

# Group poll tuning
GROUP_POLL_MESSAGES=50
POLL_DURATION_SECONDS=180
```

Notes:
- TELEGRAM_BOT_TOKEN is required. The process will raise an error if missing.
- Install the job-queue extras for python-telegram-bot: `python -m pip install "python-telegram-bot[job-queue]==22.5"`

---

## Runtime & behavior

Personal questions
- After a user's message count reaches a random target between PERSONAL_MIN_MESSAGES and PERSONAL_MAX_MESSAGES, the bot creates a short, casual Persian question and sends it privately to the user.
- The user answer is optionally fed back to the AI for analysis and an AI-crafted reply is posted privately (or per code config).

Group polls
- Groups have XP and levels (see `levels.py`). When the group's message_count reaches the threshold for its level, the bot generates a 4-option poll and posts it in the group.
- Polls auto-close after POLL_DURATION_SECONDS and the bot may post a short summary or the AI's analysis.

Persistence
- groups, users, and polls are saved in a local SQLite DB (`reverse_ai.db`). The code applies lightweight ALTER TABLE additions for schema evolution—no heavy migration tool required.

---

## Configuration tips

- Change `POLL_DURATION_SECONDS` in `config.py` or via the env var to adjust poll length per deployment.
- To temporarily disable polls or personal questions, add simple guards in `bot.py` where the jobs are scheduled (e.g., return early based on env var).
- To change the language to English, update the system prompt in `ai.py` and adjust any Persian templates.

---

## Troubleshooting

- ❗ TELEGRAM_BOT_TOKEN is not set: add TELEGRAM_BOT_TOKEN to `.env`.
- 📦 Install job queue error: reinstall with extras: `python -m pip install "python-telegram-bot[job-queue]==22.5"`.
- 🔑 AI API errors: ensure AI_API_KEY, AI_BASE_URL and AI_MODEL are correct and reachable. `ai.py` uses `httpx` with a 60s timeout.
- 🔒 Database locked errors: SQLite can lock under concurrent writes. Run bot in one process or switch to an external DB if needed.

---

## Contributing

Thanks for considering contributions! Please:

1. Open an issue for bugs or feature requests
2. Fork the repo, create a focused branch, and open a PR

Guidelines:
- Keep changes small and focused
- Add tests where applicable

---

## Security & privacy

- The bot avoids asking sensitive personal data (see system prompts in `ai.py`).
- All data is stored locally in SQLite. If deploying publicly, secure the DB and environment variables.

---

## License

See the `LICENSE` file in the project root for license details.

---

## FAQ / Try asking

- Q: How can I change the language to English for messages and prompts?
  - A: Update the system prompt in `ai.py` and any Persian templates. You may also adjust translations stored in message templates.

- Q: Where does the bot store pending personal questions in the database?
  - A: See the `users` table in `database.py`: look for the `question` and `question_message_id` columns.

- Q: How do I adjust poll length per group?
  - A: See `POLL_DURATION_SECONDS` in `config.py` and where `context.job_queue.run_once` is used in `bot.py`.
