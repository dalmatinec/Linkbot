import sqlite3
import time

conn = sqlite3.connect(
    "users.db",
    check_same_thread=False
)

cursor = conn.cursor()


def init_db():

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        user_id INTEGER UNIQUE,
        username TEXT,
        first_name TEXT,

        joined_at INTEGER,
        last_activity INTEGER,

        banned INTEGER DEFAULT 0,

        links_total INTEGER DEFAULT 0,

        chat_links INTEGER DEFAULT 0,
        channel_links INTEGER DEFAULT 0,
        reserve_links INTEGER DEFAULT 0,

        last_chat_time INTEGER DEFAULT 0,
        last_channel_time INTEGER DEFAULT 0,
        last_reserve_time INTEGER DEFAULT 0
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS admins (

        user_id INTEGER PRIMARY KEY,

        username TEXT,
        role TEXT,

        created_at INTEGER
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (

        name TEXT PRIMARY KEY,
        value TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS link_logs (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        user_id INTEGER,
        category TEXT,

        created_at INTEGER
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS admin_logs (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        admin_id INTEGER,
        action TEXT,
        target TEXT,

        created_at INTEGER
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS broadcasts (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        admin_id INTEGER,

        success_count INTEGER,
        failed_count INTEGER,

        created_at INTEGER
    )
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_users_user_id
    ON users(user_id)
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_users_username
    ON users(username)
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_link_logs_user
    ON link_logs(user_id)
    """)

    conn.commit()


# =========================
# USERS
# =========================

def add_user(user_id, username, first_name):

    now = int(time.time())

    cursor.execute("""
    INSERT OR IGNORE INTO users (

        user_id,
        username,
        first_name,

        joined_at,
        last_activity

    )
    VALUES (?, ?, ?, ?, ?)
    """, (
        user_id,
        username,
        first_name,
        now,
        now
    ))

    cursor.execute("""
    UPDATE users
    SET
        username=?,
        first_name=?,
        last_activity=?
    WHERE user_id=?
    """, (
        username,
        first_name,
        now,
        user_id
    ))

    conn.commit()


def get_user(user_id):

    cursor.execute("""
    SELECT *
    FROM users
    WHERE user_id=?
    """, (user_id,))

    return cursor.fetchone()


def get_user_by_username(username):

    username = username.replace("@", "").lower()

    cursor.execute("""
    SELECT *
    FROM users
    WHERE LOWER(username)=?
    """, (username,))

    return cursor.fetchone()


def get_all_users():

    cursor.execute("""
    SELECT user_id
    FROM users
    WHERE banned=0
    """)

    return cursor.fetchall()


def update_activity(user_id):

    cursor.execute("""
    UPDATE users
    SET last_activity=?
    WHERE user_id=?
    """, (
        int(time.time()),
        user_id
    ))

    conn.commit()


# =========================
# BAN
# =========================

def ban_user(user_id):

    cursor.execute("""
    UPDATE users
    SET banned=1
    WHERE user_id=?
    """, (user_id,))

    conn.commit()


def unban_user(user_id):

    cursor.execute("""
    UPDATE users
    SET banned=0
    WHERE user_id=?
    """, (user_id,))

    conn.commit()


def is_banned(user_id):

    cursor.execute("""
    SELECT banned
    FROM users
    WHERE user_id=?
    """, (user_id,))

    result = cursor.fetchone()

    if not result:
        return False

    return bool(result[0])


# =========================
# ADMINS
# =========================

def add_admin(user_id, username, role="admin"):

    cursor.execute("""
    INSERT OR REPLACE INTO admins (

        user_id,
        username,
        role,
        created_at

    )
    VALUES (?, ?, ?, ?)
    """, (
        user_id,
        username,
        role,
        int(time.time())
    ))

    conn.commit()


def remove_admin(user_id):

    cursor.execute("""
    DELETE FROM admins
    WHERE user_id=?
    """, (user_id,))

    conn.commit()


def is_admin(user_id):

    cursor.execute("""
    SELECT *
    FROM admins
    WHERE user_id=?
    """, (user_id,))

    return cursor.fetchone() is not None


# =========================
# SETTINGS
# =========================

def set_setting(name, value):

    cursor.execute("""
    INSERT OR REPLACE INTO settings (
        name,
        value
    )
    VALUES (?, ?)
    """, (
        name,
        str(value)
    ))

    conn.commit()


def get_setting(name):

    cursor.execute("""
    SELECT value
    FROM settings
    WHERE name=?
    """, (name,))

    result = cursor.fetchone()

    if result:
        return result[0]

    return None


# =========================
# LINKS
# =========================

def add_link_log(user_id, category):

    now = int(time.time())

    cursor.execute("""
    INSERT INTO link_logs (
        user_id,
        category,
        created_at
    )
    VALUES (?, ?, ?)
    """, (
        user_id,
        category,
        now
    ))

    field = f"{category}_links"

    cursor.execute(f"""
    UPDATE users
    SET
        links_total = links_total + 1,
        {field} = {field} + 1
    WHERE user_id=?
    """, (user_id,))

    conn.commit()


# =========================
# COOLDOWN
# =========================

def update_category_time(user_id, category):

    field_map = {
        "chat": "last_chat_time",
        "channel": "last_channel_time",
        "reserve": "last_reserve_time"
    }

    field = field_map.get(category)

    if not field:
        return

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

    indexes = {
        "chat": 10,
        "channel": 11,
        "reserve": 12
    }

    return user[indexes[category]]


# =========================
# LOGS
# =========================

def add_admin_log(admin_id, action, target=""):

    cursor.execute("""
    INSERT INTO admin_logs (

        admin_id,
        action,
        target,
        created_at

    )
    VALUES (?, ?, ?, ?)
    """, (
        admin_id,
        action,
        target,
        int(time.time())
    ))

    conn.commit()


# =========================
# BROADCAST
# =========================

def add_broadcast(admin_id, success, failed):

    cursor.execute("""
    INSERT INTO broadcasts (

        admin_id,
        success_count,
        failed_count,
        created_at

    )
    VALUES (?, ?, ?, ?)
    """, (
        admin_id,
        success,
        failed,
        int(time.time())
    ))

    conn.commit()