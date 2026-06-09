# db.py

import sqlite3

from datetime import datetime

from config import DATABASE_NAME

from config import OWNER_ID

def get_connection():
    return sqlite3.connect(DATABASE_NAME)


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,

        joined_at TEXT,
        last_activity TEXT,

        banned INTEGER DEFAULT 0,

        links_total INTEGER DEFAULT 0,

        chat_links INTEGER DEFAULT 0,
        channel_links INTEGER DEFAULT 0,
        reserve_links INTEGER DEFAULT 0,

        last_chat_time TEXT,
        last_channel_time TEXT,
        last_reserve_time TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS admins(
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        role TEXT,
        created_at TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings(
        name TEXT PRIMARY KEY,
        value TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS link_logs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        category TEXT,
        created_at TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS admin_logs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admin_id INTEGER,
        action TEXT,
        target TEXT,
        created_at TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS broadcasts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admin_id INTEGER,
        success_count INTEGER,
        failed_count INTEGER,
        created_at TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS support_tickets(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        status TEXT,
        created_at TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_blocks(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        created_at TEXT
    )
    """)

    conn.commit()
    conn.close()

    create_default_settings()
    create_owner()


def create_default_settings():
    defaults = {
        "chat_id": "",
        "channel_id": "",
        "reserve_id": "",

        "chat_cooldown": "15",
        "channel_cooldown": "15",
        "reserve_cooldown": "15",

        "support_cooldown": "60",

        "broadcast_delay": "0.5",

        "start_text": "",
        "start_photo": "",

        "rules_text": ""
    }

    conn = get_connection()
    cursor = conn.cursor()

    for key, value in defaults.items():
        cursor.execute(
            """
            INSERT OR IGNORE INTO settings(name, value)
            VALUES(?, ?)
            """,
            (key, value)
        )

    conn.commit()
    conn.close()


def get_setting(name):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT value
        FROM settings
        WHERE name=?
        """,
        (name,)
    )

    result = cursor.fetchone()

    conn.close()

    return result[0] if result else None


def set_setting(name, value):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE settings
        SET value=?
        WHERE name=?
        """,
        (
            str(value),
            name
        )
    )

    conn.commit()
    conn.close()

def add_admin(user_id, username):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT OR REPLACE INTO admins(
            user_id,
            username,
            role,
            created_at
        )
        VALUES(?,?,?,?)
        """,
        (
            user_id,
            username,
            "admin",
            datetime.now().isoformat()
        )
    )

    conn.commit()
    conn.close()


def remove_admin(user_id):
    if int(user_id) == OWNER_ID:
        return

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        DELETE FROM admins
        WHERE user_id=?
        """,
        (user_id,)
    )

    conn.commit()
    conn.close()


def is_admin(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT role
        FROM admins
        WHERE user_id=?
        """,
        (user_id,)
    )

    result = cursor.fetchone()

    conn.close()

    return result is not None


def get_admins():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM admins
        """
    )

    result = cursor.fetchall()

    conn.close()

    return result

def add_link_log(user_id, category):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO link_logs(
            user_id,
            category,
            created_at
        )
        VALUES(?,?,?)
        """,
        (
            user_id,
            category,
            datetime.now().isoformat()
        )
    )

    conn.commit()
    conn.close()


def increase_link_counter(user_id, category):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE users
        SET links_total = links_total + 1
        WHERE user_id=?
        """,
        (user_id,)
    )

    if category == "chat":
        cursor.execute(
            """
            UPDATE users
            SET
                chat_links = chat_links + 1,
                last_chat_time = ?
            WHERE user_id=?
            """,
            (
                datetime.now().isoformat(),
                user_id
            )
        )

    elif category == "channel":
        cursor.execute(
            """
            UPDATE users
            SET
                channel_links = channel_links + 1,
                last_channel_time = ?
            WHERE user_id=?
            """,
            (
                datetime.now().isoformat(),
                user_id
            )
        )

    elif category == "reserve":
        cursor.execute(
            """
            UPDATE users
            SET
                reserve_links = reserve_links + 1,
                last_reserve_time = ?
            WHERE user_id=?
            """,
            (
                datetime.now().isoformat(),
                user_id
            )
        )

    conn.commit()
    conn.close()