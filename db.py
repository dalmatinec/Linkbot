import sqlite3
import time

conn = sqlite3.connect(
    "users.db"
)

cursor = conn.cursor()


def init_db():

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (

        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,

        is_banned INTEGER DEFAULT 0,

        last_link_time INTEGER DEFAULT 0,
        last_message_time INTEGER DEFAULT 0,

        last_chat_time INTEGER DEFAULT 0,
        last_channel_time INTEGER DEFAULT 0,
        last_reserve_time INTEGER DEFAULT 0
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS admins (

        user_id INTEGER PRIMARY KEY,
        username TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (

        name TEXT PRIMARY KEY,
        value TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stats (

        total_links INTEGER DEFAULT 0
    )
    """)

    cursor.execute("""
    SELECT * FROM stats
    """)

    if not cursor.fetchone():

        cursor.execute("""
        INSERT INTO stats (
            total_links
        )
        VALUES (0)
        """)

    conn.commit()


def add_user(user_id, username, first_name):

    cursor.execute("""
    INSERT OR IGNORE INTO users (
        user_id,
        username,
        first_name
    )
    VALUES (?, ?, ?)
    """, (
        user_id,
        username,
        first_name
    ))

    conn.commit()


def get_user(user_id):

    cursor.execute("""
    SELECT * FROM users
    WHERE user_id=?
    """, (user_id,))

    return cursor.fetchone()


def ban_user(user_id):

    cursor.execute("""
    UPDATE users
    SET is_banned=1
    WHERE user_id=?
    """, (user_id,))

    conn.commit()


def unban_user(user_id):

    cursor.execute("""
    UPDATE users
    SET is_banned=0
    WHERE user_id=?
    """, (user_id,))

    conn.commit()


def is_banned(user_id):

    cursor.execute("""
    SELECT is_banned FROM users
    WHERE user_id=?
    """, (user_id,))

    user = cursor.fetchone()

    if not user:
        return False

    return bool(user[0])


def add_admin(user_id, username):

    cursor.execute("""
    INSERT OR IGNORE INTO admins (
        user_id,
        username
    )
    VALUES (?, ?)
    """, (
        user_id,
        username
    ))

    conn.commit()


def remove_admin_by_username(username):

    cursor.execute("""
    DELETE FROM admins
    WHERE username=?
    """, (username,))

    conn.commit()


def remove_admin_by_id(user_id):

    cursor.execute("""
    DELETE FROM admins
    WHERE user_id=?
    """, (user_id,))

    conn.commit()


def is_admin(user_id):

    cursor.execute("""
    SELECT * FROM admins
    WHERE user_id=?
    """, (user_id,))

    return cursor.fetchone() is not None


def update_link_time(user_id, timestamp):

    cursor.execute("""
    UPDATE users
    SET last_link_time=?
    WHERE user_id=?
    """, (
        timestamp,
        user_id
    ))

    conn.commit()


def update_message_time(user_id, timestamp):

    cursor.execute("""
    UPDATE users
    SET last_message_time=?
    WHERE user_id=?
    """, (
        timestamp,
        user_id
    ))

    conn.commit()


def update_category_time(user_id, category):

    field = f"last_{category}_time"

    cursor.execute(f"""
    UPDATE users
    SET {field}=?
    WHERE user_id=?
    """, (
        int(time.time()),
        user_id
    ))

    conn.commit()


def get_category_time(user, category):

    fields = {
        "chat": 7,
        "channel": 8,
        "reserve": 9
    }

    return user[fields[category]]


def set_setting(name, value):

    cursor.execute("""
    INSERT OR REPLACE INTO settings (
        name,
        value
    )
    VALUES (?, ?)
    """, (
        name,
        value
    ))

    conn.commit()


def get_setting(name):

    cursor.execute("""
    SELECT value FROM settings
    WHERE name=?
    """, (name,))

    result = cursor.fetchone()

    if result:
        return result[0]

    return None


def increment_links():

    cursor.execute("""
    UPDATE stats
    SET total_links = total_links + 1
    """)

    conn.commit()


def get_stats():

    cursor.execute("""
    SELECT COUNT(*)
    FROM users
    """)

    users = cursor.fetchone()[0]

    cursor.execute("""
    SELECT COUNT(*)
    FROM users
    WHERE is_banned=1
    """)

    banned = cursor.fetchone()[0]

    cursor.execute("""
    SELECT total_links
    FROM stats
    """)

    links = cursor.fetchone()[0]

    return users, banned, links

def remove_admin(value):

    if str(value).isdigit():

        cursor.execute("""
        DELETE FROM admins
        WHERE user_id=?
        """, (int(value),))

    else:

        username = str(value).replace("@", "")

        cursor.execute("""
        DELETE FROM admins
        WHERE username=?
        """, (username,))

    conn.commit()

def get_user_by_username(username):

    username = username.replace("@", "")

    cursor.execute("""
    SELECT * FROM users
    WHERE username=?
    """, (username,))

    return cursor.fetchone()

def get_all_users():

    cursor.execute("""
    SELECT user_id
    FROM users
    """)

    return cursor.fetchall()