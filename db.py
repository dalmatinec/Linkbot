import aiosqlite
import time
from datetime import datetime, timedelta, timezone

DB_PATH = "ladyshop.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS links (
                btn TEXT PRIMARY KEY, url TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS used_links (
                user_id BIGINT, btn TEXT, used_at TIMESTAMP,
                PRIMARY KEY(user_id, btn)
            );
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY, username TEXT, first_name TEXT,
                joined_at TIMESTAMP, is_banned INTEGER DEFAULT 0, is_admin INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS support_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id BIGINT,
                message_text TEXT, admin_msg_id BIGINT NULL,
                created_at TIMESTAMP, replied INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS daily_stats (
                date TEXT PRIMARY KEY, new_users INTEGER DEFAULT 0,
                links_chat INTEGER DEFAULT 0, links_channel INTEGER DEFAULT 0,
                links_reserve INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS flood_control (
                user_id BIGINT, message_ts REAL
            );
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY, value TEXT
            );
            INSERT OR IGNORE INTO settings VALUES ('link_lifetime', '15');
            INSERT OR IGNORE INTO links VALUES ('chat', '');
            INSERT OR IGNORE INTO links VALUES ('channel', '');
            INSERT OR IGNORE INTO links VALUES ('reserve', '');
        """)
        await db.commit()

async def get_link(btn: str) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT url FROM links WHERE btn = ?", (btn,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else ""

async def update_link(btn: str, new_url: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE links SET url = ? WHERE btn = ?", (new_url, btn))
        await db.commit()

async def record_link_usage(user_id: int, btn: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO used_links VALUES (?, ?, ?)",
            (user_id, btn, datetime.now(timezone.utc).isoformat())
        )
        await db.commit()

async def can_use_link(user_id: int, btn: str, minutes: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT used_at FROM used_links WHERE user_id = ? AND btn = ?",
            (user_id, btn)
        ) as cur:
            row = await cur.fetchone()
            if not row:
                return True
            used_at = datetime.fromisoformat(row[0])
            return datetime.now(timezone.utc) >= used_at + timedelta(minutes=minutes)

async def time_until_available(user_id: int, btn: str, minutes: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT used_at FROM used_links WHERE user_id = ? AND btn = ?",
            (user_id, btn)
        ) as cur:
            row = await cur.fetchone()
            if not row:
                return 0
            used_at = datetime.fromisoformat(row[0])
            available_at = used_at + timedelta(minutes=minutes)
            delta = (available_at - datetime.now(timezone.utc)).total_seconds()
            return max(0, int(delta))

async def add_user(user_id: int, username: str, first_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?, 0, 0)",
            (user_id, username, first_name, datetime.now(timezone.utc).isoformat())
        )
        await db.commit()

async def ban_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (user_id,))
        await db.commit()

async def unban_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_banned = 0 WHERE user_id = ?", (user_id,))
        await db.commit()

async def is_banned(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT is_banned FROM users WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
            return bool(row[0]) if row else False

async def add_admin(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_admin = 1 WHERE user_id = ?", (user_id,))
        await db.commit()

async def remove_admin(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_admin = 0 WHERE user_id = ?", (user_id,))
        await db.commit()

async def get_admins() -> list[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM users WHERE is_admin = 1") as cur:
            rows = await cur.fetchall()
            return [r[0] for r in rows]

async def get_all_user_ids() -> list[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM users WHERE is_banned = 0") as cur:
            rows = await cur.fetchall()
            return [r[0] for r in rows]

async def get_total_users() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cur:
            row = await cur.fetchone()
            return row[0]

async def get_banned_count() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users WHERE is_banned = 1") as cur:
            row = await cur.fetchone()
            return row[0]

async def add_support_message(user_id: int, text: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO support_messages (user_id, message_text, created_at) VALUES (?, ?, ?)",
            (user_id, text, datetime.now(timezone.utc).isoformat())
        )
        await db.commit()
        return cur.lastrowid

async def get_support_message(msg_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM support_messages WHERE id = ?", (msg_id,)) as cur:
            row = await cur.fetchone()
            if not row:
                return {}
            keys = ["id", "user_id", "message_text", "admin_msg_id", "created_at", "replied"]
            return dict(zip(keys, row))

async def mark_support_replied(msg_id: int, admin_msg_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE support_messages SET replied = 1, admin_msg_id = ? WHERE id = ?",
            (admin_msg_id, msg_id)
        )
        await db.commit()

async def increment_daily_stat(date: str, field: str):
    allowed_fields = {"new_users", "links_chat", "links_channel", "links_reserve"}
    if field not in allowed_fields:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            f"INSERT INTO daily_stats (date, {field}) VALUES (?, 1) "
            f"ON CONFLICT(date) DO UPDATE SET {field} = {field} + 1",
            (date,)
        )
        await db.commit()

async def get_daily_stats(date: str) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM daily_stats WHERE date = ?", (date,)) as cur:
            row = await cur.fetchone()
            if not row:
                return {"date": date, "new_users": 0, "links_chat": 0, "links_channel": 0, "links_reserve": 0}
            keys = ["date", "new_users", "links_chat", "links_channel", "links_reserve"]
            return dict(zip(keys, row))

async def check_flood(user_id: int) -> bool:
    from config import FLOOD_LIMIT, FLOOD_SECONDS
    now = time.time()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM flood_control WHERE user_id = ? AND message_ts < ?",
            (user_id, now - FLOOD_SECONDS)
        )
        await db.execute("INSERT INTO flood_control VALUES (?, ?)", (user_id, now))
        await db.commit()
        async with db.execute(
            "SELECT COUNT(*) FROM flood_control WHERE user_id = ? AND message_ts >= ?",
            (user_id, now - FLOOD_SECONDS)
        ) as cur:
            row = await cur.fetchone()
            return row[0] > FLOOD_LIMIT

async def set_link_lifetime(minutes: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE settings SET value = ? WHERE key = 'link_lifetime'", (str(minutes),))
        await db.commit()

async def get_link_lifetime() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM settings WHERE key = 'link_lifetime'") as cur:
            row = await cur.fetchone()
            return int(row[0]) if row else 15