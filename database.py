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


        # migration
        tables = {
            "groups": [
                ("xp", "INTEGER DEFAULT 0"),
                ("level", "INTEGER DEFAULT 1"),
                ("total_messages", "INTEGER DEFAULT 0")
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
                question_message_id = ?,
                waiting_answer = 1
            WHERE chat_id = ?
            AND user_id = ?
            """,
            (
                question,
                message_id,
                chat_id,
                user_id
            )
        )

        conn.commit()



def get_pending_question(
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
            AND waiting_answer = 1
            """,
            (
                chat_id,
                user_id
            )
        ).fetchone()



def finish_question(
    chat_id,
    user_id,
    target
):

    with closing(get_connection()) as conn:

        conn.execute(
            """
            UPDATE users
            SET
                message_count = 0,
                target_count = ?,
                waiting_answer = 0,
                question = NULL,
                question_message_id = NULL
            WHERE chat_id = ?
            AND user_id = ?
            """,
            (
                target,
                chat_id,
                user_id
            )
        )

        conn.commit()



# ---------------- POLLS ----------------


def save_poll(
    chat_id,
    message_id,
    question,
    options,
    ai_choice,
    reason,
    challenge_mode
):

    with closing(get_connection()) as conn:

        conn.execute(
            """
            INSERT OR REPLACE INTO polls
            VALUES
            (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                chat_id,
                message_id,
                question,
                options,
                ai_choice,
                reason,
                challenge_mode
            )
        )

        conn.commit()



def get_poll(
    chat_id,
    message_id
):

    with closing(get_connection()) as conn:

        return conn.execute(
            """
            SELECT *
            FROM polls
            WHERE chat_id = ?
            AND message_id = ?
            """,
            (
                chat_id,
                message_id
            )
        ).fetchone()



def delete_poll(
    chat_id,
    message_id
):

    with closing(get_connection()) as conn:

        conn.execute(
            """
            DELETE FROM polls
            WHERE chat_id = ?
            AND message_id = ?
            """,
            (
                chat_id,
                message_id
            )
        )

        conn.commit()
