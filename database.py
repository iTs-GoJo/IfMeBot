import sqlite3
from contextlib import closing

DB_NAME = "reverse_ai.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with closing(get_connection()) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                chat_id INTEGER PRIMARY KEY,
                message_count INTEGER NOT NULL DEFAULT 0,
                poll_active INTEGER NOT NULL DEFAULT 0
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                message_count INTEGER NOT NULL DEFAULT 0,
                target_count INTEGER NOT NULL,
                waiting_answer INTEGER NOT NULL DEFAULT 0,
                question TEXT,
                question_message_id INTEGER,
                PRIMARY KEY (chat_id, user_id)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS polls (
                chat_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                question TEXT NOT NULL,
                options TEXT NOT NULL,
                ai_choice INTEGER NOT NULL,
                reason TEXT NOT NULL,
                PRIMARY KEY (chat_id, message_id)
            )
        """)

        # Migration for existing databases
        columns = conn.execute(
            "PRAGMA table_info(users)"
        ).fetchall()

        column_names = {
            column["name"]
            for column in columns
        }

        if "question_message_id" not in column_names:
            conn.execute("""
                ALTER TABLE users
                ADD COLUMN question_message_id INTEGER
            """)

        conn.commit()


def ensure_group(chat_id: int):
    with closing(get_connection()) as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO groups
            (chat_id, message_count, poll_active)
            VALUES (?, 0, 0)
            """,
            (chat_id,)
        )
        conn.commit()


def get_group(chat_id: int):
    ensure_group(chat_id)

    with closing(get_connection()) as conn:
        return conn.execute(
            """
            SELECT *
            FROM groups
            WHERE chat_id = ?
            """,
            (chat_id,)
        ).fetchone()


def increment_group_messages(chat_id: int) -> int:
    ensure_group(chat_id)

    with closing(get_connection()) as conn:
        conn.execute(
            """
            UPDATE groups
            SET message_count = message_count + 1
            WHERE chat_id = ?
            """,
            (chat_id,)
        )

        row = conn.execute(
            """
            SELECT message_count
            FROM groups
            WHERE chat_id = ?
            """,
            (chat_id,)
        ).fetchone()

        conn.commit()

        return row["message_count"]


def reset_group_messages(chat_id: int):
    with closing(get_connection()) as conn:
        conn.execute(
            """
            UPDATE groups
            SET message_count = 0
            WHERE chat_id = ?
            """,
            (chat_id,)
        )
        conn.commit()


def set_poll_active(chat_id: int, active: bool):
    with closing(get_connection()) as conn:
        conn.execute(
            """
            UPDATE groups
            SET poll_active = ?
            WHERE chat_id = ?
            """,
            (1 if active else 0, chat_id)
        )
        conn.commit()


def get_user(chat_id: int, user_id: int):
    with closing(get_connection()) as conn:
        return conn.execute(
            """
            SELECT *
            FROM users
            WHERE chat_id = ? AND user_id = ?
            """,
            (chat_id, user_id)
        ).fetchone()


def create_user(
    chat_id: int,
    user_id: int,
    target_count: int
):
    with closing(get_connection()) as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO users
            (
                chat_id,
                user_id,
                message_count,
                target_count,
                waiting_answer,
                question_message_id
            )
            VALUES (?, ?, 0, ?, 0, NULL)
            """,
            (chat_id, user_id, target_count)
        )

        conn.commit()


def increment_user_messages(
    chat_id: int,
    user_id: int
) -> int:
    with closing(get_connection()) as conn:
        conn.execute(
            """
            UPDATE users
            SET message_count = message_count + 1
            WHERE chat_id = ? AND user_id = ?
            """,
            (chat_id, user_id)
        )

        row = conn.execute(
            """
            SELECT message_count
            FROM users
            WHERE chat_id = ? AND user_id = ?
            """,
            (chat_id, user_id)
        ).fetchone()

        conn.commit()

        return row["message_count"]


def set_question(
    chat_id: int,
    user_id: int,
    question: str,
    question_message_id: int
):
    with closing(get_connection()) as conn:
        conn.execute(
            """
            UPDATE users
            SET question = ?,
                question_message_id = ?,
                waiting_answer = 1
            WHERE chat_id = ? AND user_id = ?
            """,
            (
                question,
                question_message_id,
                chat_id,
                user_id
            )
        )

        conn.commit()


def get_pending_question(
    chat_id: int,
    user_id: int
):
    with closing(get_connection()) as conn:
        return conn.execute(
            """
            SELECT question, question_message_id
            FROM users
            WHERE chat_id = ?
              AND user_id = ?
              AND waiting_answer = 1
            """,
            (chat_id, user_id)
        ).fetchone()


def finish_question(
    chat_id: int,
    user_id: int,
    new_target: int
):
    with closing(get_connection()) as conn:
        conn.execute(
            """
            UPDATE users
            SET message_count = 0,
                target_count = ?,
                waiting_answer = 0,
                question = NULL,
                question_message_id = NULL
            WHERE chat_id = ? AND user_id = ?
            """,
            (
                new_target,
                chat_id,
                user_id
            )
        )

        conn.commit()


def save_poll(
    chat_id: int,
    message_id: int,
    question: str,
    options: str,
    ai_choice: int,
    reason: str
):
    with closing(get_connection()) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO polls
            (
                chat_id,
                message_id,
                question,
                options,
                ai_choice,
                reason
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                chat_id,
                message_id,
                question,
                options,
                ai_choice,
                reason
            )
        )

        conn.commit()


def get_poll(chat_id: int, message_id: int):
    with closing(get_connection()) as conn:
        return conn.execute(
            """
            SELECT *
            FROM polls
            WHERE chat_id = ?
              AND message_id = ?
            """,
            (chat_id, message_id)
        ).fetchone()


def delete_poll(chat_id: int, message_id: int):
    with closing(get_connection()) as conn:
        conn.execute(
            """
            DELETE FROM polls
            WHERE chat_id = ? AND message_id = ?
            """,
            (chat_id, message_id)
        )
        conn.commit()
