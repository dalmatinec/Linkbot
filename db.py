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

def add_admin_log(admin_id, action, target=""):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO admin_logs(
            admin_id,
            action,
            target,
            created_at
        )
        VALUES(?,?,?,?)
        """,
        (
            admin_id,
            action,
            target,
            datetime.now().isoformat()
        )
    )

    conn.commit()
    conn.close()


def get_admin_logs(limit=50):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM admin_logs
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,)
    )

    result = cursor.fetchall()

    conn.close()

    return result

def add_broadcast(admin_id, success_count, failed_count):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO broadcasts(
            admin_id,
            success_count,
            failed_count,
            created_at
        )
        VALUES(?,?,?,?)
        """,
        (
            admin_id,
            success_count,
            failed_count,
            datetime.now().isoformat()
        )
    )

    conn.commit()
    conn.close()


def get_broadcasts(limit=20):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM broadcasts
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,)
    )

    result = cursor.fetchall()

    conn.close()

    return result

def add_support_ticket(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO support_tickets(
            user_id,
            status,
            created_at
        )
        VALUES(?,?,?)
        """,
        (
            user_id,
            "open",
            datetime.now().isoformat()
        )
    )

    conn.commit()
    conn.close()


def close_support_ticket(ticket_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE support_tickets
        SET status='closed'
        WHERE id=?
        """,
        (ticket_id,)
    )

    conn.commit()
    conn.close()


def get_open_tickets():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM support_tickets
        WHERE status='open'
        ORDER BY id DESC
        """
    )

    result = cursor.fetchall()

    conn.close()

    return result

def add_user_block(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO user_blocks(
            user_id,
            created_at
        )
        VALUES(?,?)
        """,
        (
            user_id,
            datetime.now().isoformat()
        )
    )

    conn.commit()
    conn.close()


def get_blocks_count():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM user_blocks
        """
    )

    count = cursor.fetchone()[0]

    conn.close()

    return count

def get_all_users():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT user_id
        FROM users
        WHERE banned=0
        """
    )

    result = cursor.fetchall()

    conn.close()

    return result


def get_users_count():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM users
        """
    )

    count = cursor.fetchone()[0]

    conn.close()

    return count

def get_links_count():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM link_logs
        """
    )

    total = cursor.fetchone()[0]

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM link_logs
        WHERE category='chat'
        """
    )

    chat = cursor.fetchone()[0]

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM link_logs
        WHERE category='channel'
        """
    )

    channel = cursor.fetchone()[0]

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM link_logs
        WHERE category='reserve'
        """
    )

    reserve = cursor.fetchone()[0]

    conn.close()

    return total, chat, channel, reserve

def export_users():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
        user_id,
        username,
        first_name,
        joined_at
        FROM users
        """
    )

    result = cursor.fetchall()

    conn.close()

    return result

def user_exists(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT user_id
        FROM users
        WHERE user_id=?
        """,
        (user_id,)
    )

    result = cursor.fetchone()

    conn.close()

    return result is not None

def get_new_users_today():
    conn = get_connection()
    cursor = conn.cursor()

    today = datetime.now().date().isoformat()

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM users
        WHERE date(joined_at)=?
        """,
        (today,)
    )

    count = cursor.fetchone()[0]

    conn.close()

    return count


def get_new_users_week():
    conn = get_connection()
    cursor = conn.cursor()

    week_ago = (datetime.now() - timedelta(days=7)).isoformat()

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM users
        WHERE joined_at >= ?
        """,
        (week_ago,)
    )

    count = cursor.fetchone()[0]

    conn.close()

    return count


def get_new_users_month():
    conn = get_connection()
    cursor = conn.cursor()

    month_ago = (datetime.now() - timedelta(days=30)).isoformat()

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM users
        WHERE joined_at >= ?
        """,
        (month_ago,)
    )

    count = cursor.fetchone()[0]

    conn.close()

    return count

def get_active_today():
    conn = get_connection()
    cursor = conn.cursor()

    today = datetime.now().date().isoformat()

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM users
        WHERE date(last_activity)=?
        """,
        (today,)
    )

    count = cursor.fetchone()[0]

    conn.close()

    return count

def get_banned_count():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM users
        WHERE banned=1
        """
    )

    count = cursor.fetchone()[0]

    conn.close()

    return count

def get_admins_count():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM admins
        """
    )

    count = cursor.fetchone()[0]

    conn.close()

    return count

def get_last_ticket_time(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT created_at
        FROM support_tickets
        WHERE user_id=?
        ORDER BY id DESC
        LIMIT 1
        """,
        (user_id,)
    )

    result = cursor.fetchone()

    conn.close()

    if not result:
        return None

    return result[0]

def get_full_statistics():
    total_users = get_users_count()

    new_today = get_new_users_today()
    new_week = get_new_users_week()
    new_month = get_new_users_month()

    active_today = get_active_today()

    banned = get_banned_count()

    blocked = get_blocks_count()

    admins = get_admins_count()

    total_links, chat_links, channel_links, reserve_links = get_links_count()

    return {
        "total_users": total_users,

        "new_today": new_today,
        "new_week": new_week,
        "new_month": new_month,

        "active_today": active_today,

        "banned": banned,

        "blocked": blocked,

        "admins": admins,

        "total_links": total_links,
        "chat_links": chat_links,
        "channel_links": channel_links,
        "reserve_links": reserve_links
    }

def get_daily_report():
    stats = get_full_statistics()

    return f"""
📊 ЕЖЕДНЕВНЫЙ ОТЧЁТ

📅 Дата: {datetime.now().strftime('%d.%m.%Y')}

👥 Новые пользователи:
• Сегодня: {stats['new_today']}
• За неделю: {stats['new_week']}
• За месяц: {stats['new_month']}

🔗 Выдано ссылок:
• Всего: {stats['total_links']}
• Основной чат: {stats['chat_links']}
• Канал: {stats['channel_links']}
• Резервный доступ: {stats['reserve_links']}

👥 Активные пользователи сегодня: {stats['active_today']}

🚫 Забанено: {stats['banned']}

⛔ Заблокировали бота: {stats['blocked']}

👨‍💼 Администраторов: {stats['admins']}

📊 Всего пользователей: {stats['total_users']}
"""