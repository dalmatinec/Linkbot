import sqlite3
from datetime import datetime

db = sqlite3.connect("users.db")
cursor = db.cursor()


def init_db():
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE,
        username TEXT,
        first_name TEXT,
        joined_at TEXT,
        last_link_time INTEGER DEFAULT 0,
        last_message_time INTEGER DEFAULT 0,
        banned INTEGER DEFAULT 0
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE,
        username TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT UNIQUE,
        value TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stats (
        total_links INTEGER DEFAULT 0
    )
    """)

    cursor.execute("""
    INSERT OR IGNORE INTO stats (rowid, total_links)
    VALUES (1, 0)
    """)

    db.commit()


def add_user(user_id, username, first_name):
    cursor.execute(
        "SELECT * FROM users WHERE user_id=?",
        (user_id,)
    )

    user = cursor.fetchone()

    if not user:
        cursor.execute("""
        INSERT INTO users
        (user_id, username, first_name, joined_at)
        VALUES (?, ?, ?, ?)
        """, (
            user_id,
            username,
            first_name,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))

        db.commit()


def get_user(user_id):
    cursor.execute(
        "SELECT * FROM users WHERE user_id=?",
        (user_id,)
    )

    return cursor.fetchone()


def update_link_time(user_id, timestamp):
    cursor.execute("""
    UPDATE users
    SET last_link_time=?
    WHERE user_id=?
    """, (
        timestamp,
        user_id
    ))

    db.commit()


def update_message_time(user_id, timestamp):
    cursor.execute("""
    UPDATE users
    SET last_message_time=?
    WHERE user_id=?
    """, (
        timestamp,
        user_id
    ))

    db.commit()


def is_banned(user_id):
    cursor.execute("""
    SELECT banned FROM users
    WHERE user_id=?
    """, (user_id,))

    result = cursor.fetchone()

    if result:
        return result[0] == 1

    return False


def ban_user(user_id):
    cursor.execute("""
    UPDATE users
    SET banned=1
    WHERE user_id=?
    """, (user_id,))

    db.commit()


def unban_user(user_id):
    cursor.execute("""
    UPDATE users
    SET banned=0
    WHERE user_id=?
    """, (user_id,))

    db.commit()


def add_admin(user_id, username):
    cursor.execute("""
    INSERT OR IGNORE INTO admins
    (user_id, username)
    VALUES (?, ?)
    """, (
        user_id,
        username
    ))

    db.commit()


def remove_admin(user_id):
    cursor.execute("""
    DELETE FROM admins
    WHERE user_id=?
    """, (user_id,))

    db.commit()


def is_admin(user_id):

    cursor.execute("""
    SELECT * FROM admins
    WHERE user_id=?
    """, (user_id,))

    return cursor.fetchone() is not None


def get_user_by_username(username):
    username = username.replace("@", "")

    cursor.execute("""
    SELECT * FROM users
    WHERE username=?
    """, (username,))

    return cursor.fetchone()


def set_setting(key, value):
    cursor.execute("""
    INSERT OR REPLACE INTO settings
    (key, value)
    VALUES (?, ?)
    """, (
        key,
        str(value)
    ))

    db.commit()


def get_setting(key):
    cursor.execute("""
    SELECT value FROM settings
    WHERE key=?
    """, (key,))

    result = cursor.fetchone()

    if result:
        return result[0]

    return None


def get_all_users():
    cursor.execute("""
    SELECT user_id FROM users
    WHERE banned=0
    """)

    return cursor.fetchall()


def increment_links():
    cursor.execute("""
    UPDATE stats
    SET total_links = total_links + 1
    WHERE rowid=1
    """)

    db.commit()


def get_stats():
    cursor.execute("""
    SELECT COUNT(*) FROM users
    """)

    users = cursor.fetchone()[0]

    cursor.execute("""
    SELECT COUNT(*) FROM users
    WHERE banned=1
    """)

    banned = cursor.fetchone()[0]

    cursor.execute("""
    SELECT total_links FROM stats
    WHERE rowid=1
    """)

    links = cursor.fetchone()[0]

    return users, banned, links