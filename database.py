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
                poll_active INTEGER NOT NULL DEFAULT 0,
                xp INTEGER NOT NULL DEFAULT 0,
                level INTEGER NOT NULL DEFAULT 1,
                total_messages INTEGER NOT NULL DEFAULT 0
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
                PRIMARY KEY(chat_id, user_id)
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
                challenge_mode INTEGER DEFAULT 0,
                PRIMARY KEY(chat_id, message_id)
            )
        """)


        # migration: additive ALTER TABLE for new columns
        tables = {
            "groups": [
                ("xp", "INTEGER DEFAULT 0"),
                ("level", "INTEGER DEFAULT 1"),
                ("total_messages", "INTEGER DEFAULT 0"),
                ("bot_active", "INTEGER DEFAULT 1"),
                ("personal_questions_enabled", "INTEGER DEFAULT 1"),
                ("polls_enabled", "INTEGER DEFAULT 1"),
            ],
            "users": [
                ("question_message_id", "INTEGER")
            ],
            "polls": [
                ("challenge_mode", "INTEGER DEFAULT 0")
            ]
        }


        for table, columns in tables.items():

            existing = conn.execute(
                f"PRAGMA table_info({table})"
            ).fetchall()

            names = {
                col["name"]
                for col in existing
            }


            for name, sql_type in columns:

                if name not in names:

                    conn.execute(
                        f"""
                        ALTER TABLE {table}
                        ADD COLUMN {name} {sql_type}
                        """
                    )


        conn.commit()



# ---------------- GROUP ----------------


def ensure_group(chat_id):

    with closing(get_connection()) as conn:

        conn.execute(
            """
            INSERT OR IGNORE INTO groups
            (
                chat_id
            )
            VALUES (?)
            """,
            (chat_id,)
        )

        conn.commit()



def get_group(chat_id):

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



def add_group_message(chat_id):

    ensure_group(chat_id)

    with closing(get_connection()) as conn:

        conn.execute(
            """
            UPDATE groups
            SET
                message_count = message_count + 1,
                xp = xp + 1,
                total_messages = total_messages + 1
            WHERE chat_id = ?
            """,
            (chat_id,)
        )


        row = conn.execute(
            """
            SELECT *
            FROM groups
            WHERE chat_id = ?
            """,
            (chat_id,)
        ).fetchone()


        conn.commit()

        return row



def update_level(
    chat_id,
    level
):

    with closing(get_connection()) as conn:

        conn.execute(
            """
            UPDATE groups
            SET level = ?
            WHERE chat_id = ?
            """,
            (
                level,
                chat_id
            )
        )

        conn.commit()



def reset_group_messages(chat_id):

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



def set_poll_active(
    chat_id,
    active
):

    with closing(get_connection()) as conn:

        conn.execute(
            """
            UPDATE groups
            SET poll_active = ?
            WHERE chat_id = ?
            """,
            (
                1 if active else 0,
                chat_id
            )
        )

        conn.commit()



# ---------------- GROUP SETTINGS HELPERS ----------------


def set_bot_active(chat_id, active):
    """Enable or disable the bot for a specific group."""
    with closing(get_connection()) as conn:
        conn.execute(
            """
            UPDATE groups
            SET bot_active = ?
            WHERE chat_id = ?
            """,
            (
                1 if active else 0,
                chat_id,
            ),
        )
        conn.commit()


def set_personal_questions_enabled(chat_id, enabled):
    """Enable or disable personal questions for a group."""
    with closing(get_connection()) as conn:
        conn.execute(
            """
            UPDATE groups
            SET personal_questions_enabled = ?
            WHERE chat_id = ?
            """,
            (
                1 if enabled else 0,
                chat_id,
            ),
        )
        conn.commit()


def set_polls_enabled(chat_id, enabled):
    """Enable or disable group polls for a group."""
    with closing(get_connection()) as conn:
        conn.execute(
            """
            UPDATE groups
            SET polls_enabled = ?
            WHERE chat_id = ?
            """,
            (
                1 if enabled else 0,
                chat_id,
            ),
        )
        conn.commit()


def get_group_settings(chat_id):
    """Return a dict with current group settings and stats."""
    row = get_group(chat_id)
    return {
        "bot_active": bool(row["bot_active"]),
        "personal_questions_enabled": bool(row["personal_questions_enabled"]),
        "polls_enabled": bool(row["polls_enabled"]),
        "level": row["level"],
        "xp": row.get("xp", 0) if isinstance(row, dict) else row["xp"],
    }



# ---------------- USERS ----------------


def get_user(
    chat_id,
    user_id
):

    with closing(get_connection()) as conn:

        return conn.execute(
            """
            SELECT *
            FROM users
            WHERE chat_id = ?
            AND user_id = ?
            """,
            (
                chat_id,
                user_id
            )
        ).fetchone()



def create_user(
    chat_id,
    user_id,
    target
):

    with closing(get_connection()) as conn:

        conn.execute(
            """
            INSERT OR IGNORE INTO users
            (
                chat_id,
                user_id,
                target_count
            )
            VALUES
            (?, ?, ?)
            """,
            (
                chat_id,
                user_id,
                target
            )
        )

        conn.commit()



def increment_user_messages(
    chat_id,
    user_id
):

    with closing(get_connection()) as conn:

        conn.execute(
            """
            UPDATE users
            SET message_count = message_count + 1
            WHERE chat_id = ?
            AND user_id = ?
            """,
            (
                chat_id,
                user_id
            )
        )


        row = conn.execute(
            """
            SELECT message_count
            FROM users
            WHERE chat_id = ?
            AND user_id = ?
            """,
            (
                chat_id,
                user_id
            )
        ).fetchone()


        conn.commit()

        return row["message_count"]



def set_question(
    chat_id,
    user_id,
    question,
    message_id
):

    with closing(get_connection()) as conn:

        conn.execute(
            """
            UPDATE users
            SET
                question = ?,
                waiting_answer = 1,
                question_message_id = ?
            WHERE chat_id = ?
            AND user_id = ?
            """,
            (
                question,
                message_id,
                chat_id,
                user_id,
            )
        )

        conn.commit()
