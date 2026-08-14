# IfMeBot (Reverse AI)

Reverse AI (IfMeBot) is a Telegram group bot that injects fun, thought-provoking personal questions and group polls in Persian (Farsi). It uses an LLM-powered AI backend to generate questions, analyze personal answers, and create final opinions after polls.

Highlights
- Targets Persian-speaking Telegram groups.
- Two main features: short personal questions (sent to active users) and group polls (auto-created after group activity thresholds).
- Lightweight local SQLite database for persistence (no external DB required).
- Configurable via environment variables and .env.

Table of contents
- What this is
- Stack
- Project layout
- How it works
- Requirements
- Quick start
- Environment variables
- Runtime & behavior
- Troubleshooting
- Contributing
- License

## What this is
A small, opinionated Telegram bot (Persian) that: periodically asks an individual user a short, casual question and generates an AI-powered reply based on their answer; and creates group polls after configurable message activity, then posts the AI's final opinion when the poll ends.

### Stack
- Language(s): Python 3.10+ (code written in Python)
- Framework / runtime: python-telegram-bot (v22.x) with JobQueue
- Notable libraries: python-telegram-bot[job-queue], httpx, python-dotenv

## How it's organized
```
.ai.py        # AI integration (calls LLM for question/poll generation & analysis)
.bot.py       # Telegram handlers, main entrypoint, scheduling poll finish jobs
.config.py    # Env var loading and defaults
.database.py  # SQLite persistence (groups, users, polls)
.levels.py    # Group XP/level math and poll thresholds
.requirements.txt
.LICENSE
.env          # example: not committed
README.md
```
How it fits together: bot.py wires the Telegram Application and handlers. Incoming messages update per-user counters and group XP via database.py and levels.py. When a user hits their personal-question threshold, bot.py asks the AI (ai.py) for a question and waits for a reply; the reply is analyzed by ai.py. When the group reaches the poll-limit threshold, ai.py generates a 4-option poll, bot.py posts it, schedules a job to stop the poll, and then asks the AI for a final opinion.

## How to run it
1. Clone the repo and install dependencies

```bash
git clone https://github.com/iTs-GoJo/IfMeBot.git
cd IfMeBot
python -m pip install -r requirements.txt
```

2. Create a .env file (see Environment variables below)
3. Start the bot

```bash
python bot.py
```

The bot uses a local SQLite file named `reverse_ai.db` (created automatically in the repo directory).

## Environment variables
Create a .env file in the project root with the following keys:

```
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
AI_API_KEY=your-ai-api-key
# Optional: override the base URL & model if needed
AI_BASE_URL=https://api.groq.com/openai/v1
AI_MODEL=llama-3.3-70b-versatile

# Tuning: how many messages to wait before asking a personal question
PERSONAL_MIN_MESSAGES=10
PERSONAL_MAX_MESSAGES=20

# How many group messages before creating a poll (per-level defaults may override)
GROUP_POLL_MESSAGES=50
POLL_DURATION_SECONDS=180
```

Notes:
- TELEGRAM_BOT_TOKEN is required. The process will raise an error if missing.
- The code expects a job queue; install the `[job-queue]` extras for python-telegram-bot.

## Runtime & behavior
- Personal questions: After a user's message count reaches a random target between PERSONAL_MIN_MESSAGES and PERSONAL_MAX_MESSAGES, the bot creates a short, casual Persian question directed at that user (the bot uses reply messages). The bot then waits for that user's reply and sends an AI-generated, friendly reaction.

- Group polls: Groups have XP and levels. When the group's message_count reaches the threshold for that level (see levels.py), the bot generates a 4-option poll and posts it. After POLL_DURATION_SECONDS the poll is stopped and the AI produces a short final opinion.

- Persistence: groups, users, and polls are saved in a local SQLite DB (reverse_ai.db). No external DB or migrations are required; the code runs ALTER TABLE to add missing columns when needed.

## Troubleshooting
- Runtime error "TELEGRAM_BOT_TOKEN is not set": add TELEGRAM_BOT_TOKEN to .env.
- If you see "Install python-telegram-bot[job-queue]": reinstall with extras: python -m pip install "python-telegram-bot[job-queue]==22.5".
- AI API errors: ensure AI_API_KEY, AI_BASE_URL and AI_MODEL are correct and reachable. The ai.py function uses httpx with a 60s timeout.
- Database locked errors: SQLite can raise locking errors in some concurrent environments. Run the bot on a single process or use an external DB if needed.

## Contributing
- Bug reports and feature requests: open an issue.
- Small fixes: fork, create a branch, and open a PR. Keep changes focused.

## Security & privacy
- The bot intentionally avoids asking sensitive personal information (see ai.py system prompts).
- All data is stored locally in SQLite. If you deploy to a server, secure the DB and environment variables.

## License
This repository includes a LICENSE file in the root — see LICENSE for details.

## Try asking
- How can I change the language to English for messages and prompts?
- Where does the bot store pending personal questions in the database? (look in users table; see `question` and `question_message_id` columns)
- How do I adjust poll length per group? (see POLL_DURATION_SECONDS in config.py and context.job_queue.run_once in bot.py)
