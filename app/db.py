"""SQLite: посты, рассылки, группы, журнал отправок, настройки."""
import json
import os
import sqlite3
import time

SCHEMA = """
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY, title TEXT NOT NULL, kind TEXT NOT NULL, file_id TEXT,
    html TEXT NOT NULL DEFAULT '', buttons TEXT NOT NULL DEFAULT '[]', created INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS campaigns (
    id INTEGER PRIMARY KEY, title TEXT NOT NULL, interval_min INTEGER NOT NULL DEFAULT 60,
    active INTEGER NOT NULL DEFAULT 0, next_run INTEGER NOT NULL DEFAULT 0,
    posts TEXT NOT NULL DEFAULT '[]', last_report TEXT, created INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS camp_groups (
    campaign_id INTEGER NOT NULL, chat_id INTEGER NOT NULL, PRIMARY KEY (campaign_id, chat_id)
);
CREATE TABLE IF NOT EXISTS groups (
    chat_id INTEGER PRIMARY KEY, title TEXT NOT NULL, enabled INTEGER NOT NULL DEFAULT 1,
    errors INTEGER NOT NULL DEFAULT 0, pause_reason TEXT
);
CREATE TABLE IF NOT EXISTS sent (
    id INTEGER PRIMARY KEY, chat_id INTEGER NOT NULL, campaign_id INTEGER, post_id INTEGER,
    ts INTEGER NOT NULL, ok INTEGER NOT NULL, err TEXT
);
CREATE INDEX IF NOT EXISTS sent_chat_ts ON sent (chat_id, ts);
CREATE TABLE IF NOT EXISTS cursors (
    campaign_id INTEGER NOT NULL, chat_id INTEGER NOT NULL, idx INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (campaign_id, chat_id)
);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, val TEXT NOT NULL);
"""

# key: (по умолчанию, описание, тип)
SETTINGS = {
    "mention_delay": (2, "Задержка между группами, сек", "int"),
    "jitter": (3, "Случайная добавка к задержке, сек", "int"),
    "min_gap": (30, "Антифлуд: пауза между постами в одной группе, мин", "int"),
    "max_per_day": (24, "Лимит постов в одну группу за сутки", "int"),
    "error_limit": (3, "Ошибок подряд до автопаузы группы", "int"),
    "answer_timeout": (30, "Ждать ответа бота, сек", "int"),
    "delete_trigger": (0, "Удалять сообщение-вызов после поста", "bool"),
    "delete_after": (10, "Через сколько удалять вызов, сек", "int"),
    "quiet_from": (-1, "Тихие часы: с (час, -1 выкл)", "int"),
    "quiet_to": (-1, "Тихие часы: до (час)", "int"),
    "reports": (1, "Отчёт после каждого круга рассылки", "bool"),
}


def now() -> int:
    return int(time.time())


class DB:
    def __init__(self, path: str) -> None:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self.c = sqlite3.connect(path, isolation_level=None, check_same_thread=False)
        self.c.row_factory = sqlite3.Row
        self.c.execute("PRAGMA journal_mode=WAL")
        self.c.executescript(SCHEMA)
        self._migrate()

    def _migrate(self) -> None:
        """Пересылки: mode = copy | forward; src_id - id сообщения в чате юзербота с ботом;
        orig_chat/orig_msg - где лежит оригинал у админа (для предпросмотра)."""
        cols = {r["name"] for r in self.q("PRAGMA table_info(posts)")}
        for name, ddl in [("mode", "TEXT NOT NULL DEFAULT 'copy'"), ("src_id", "INTEGER"),
                          ("orig_chat", "INTEGER"), ("orig_msg", "INTEGER")]:
            if name not in cols:
                self.x(f"ALTER TABLE posts ADD COLUMN {name} {ddl}")

    def q(self, sql: str, *a) -> list[sqlite3.Row]:
        return self.c.execute(sql, a).fetchall()

    def one(self, sql: str, *a) -> sqlite3.Row | None:
        return self.c.execute(sql, a).fetchone()

    def x(self, sql: str, *a) -> sqlite3.Cursor:
        return self.c.execute(sql, a)

    # ---------- настройки ----------
    def setting(self, key: str) -> int:
        row = self.one("SELECT val FROM settings WHERE key=?", key)
        return int(row["val"]) if row else int(SETTINGS[key][0])

    def set_setting(self, key: str, val: int) -> None:
        self.x("INSERT INTO settings (key, val) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET val=excluded.val",
               key, str(int(val)))

    # ---------- посты ----------
    @staticmethod
    def _post(row: sqlite3.Row | None) -> dict | None:
        if row is None:
            return None
        d = dict(row)
        d["buttons"] = json.loads(d["buttons"])
        return d

    def posts(self) -> list[dict]:
        return [self._post(r) for r in self.q("SELECT * FROM posts ORDER BY id")]

    def post(self, pid: int) -> dict | None:
        return self._post(self.one("SELECT * FROM posts WHERE id=?", pid))

    def add_post(self, title: str, kind: str, file_id: str | None, html: str, buttons: list, mode: str = "copy",
                 src_id: int | None = None, orig_chat: int | None = None, orig_msg: int | None = None) -> int:
        return self.x("INSERT INTO posts (title, kind, file_id, html, buttons, created, mode, src_id, orig_chat, orig_msg)"
                      " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                      title, kind, file_id, html, json.dumps(buttons, ensure_ascii=False), now(), mode, src_id,
                      orig_chat, orig_msg).lastrowid

    def update_post(self, pid: int, **fields) -> None:
        if "buttons" in fields:
            fields["buttons"] = json.dumps(fields["buttons"], ensure_ascii=False)
        sets = ", ".join(f"{k}=?" for k in fields)
        self.x(f"UPDATE posts SET {sets} WHERE id=?", *fields.values(), pid)

    def delete_post(self, pid: int) -> None:
        self.x("DELETE FROM posts WHERE id=?", pid)
        for c in self.campaigns():
            if pid in c["posts"]:
                self.update_campaign(c["id"], posts=[p for p in c["posts"] if p != pid])

    # ---------- рассылки ----------
    @staticmethod
    def _camp(row: sqlite3.Row | None) -> dict | None:
        if row is None:
            return None
        d = dict(row)
        d["posts"] = json.loads(d["posts"])
        return d

    def campaigns(self) -> list[dict]:
        return [self._camp(r) for r in self.q("SELECT * FROM campaigns ORDER BY id")]

    def campaign(self, cid: int) -> dict | None:
        return self._camp(self.one("SELECT * FROM campaigns WHERE id=?", cid))

    def add_campaign(self, title: str) -> int:
        return self.x("INSERT INTO campaigns (title, created) VALUES (?, ?)", title, now()).lastrowid

    def update_campaign(self, cid: int, **fields) -> None:
        if "posts" in fields:
            fields["posts"] = json.dumps(fields["posts"])
        sets = ", ".join(f"{k}=?" for k in fields)
        self.x(f"UPDATE campaigns SET {sets} WHERE id=?", *fields.values(), cid)

    def delete_campaign(self, cid: int) -> None:
        self.x("DELETE FROM campaigns WHERE id=?", cid)
        self.x("DELETE FROM camp_groups WHERE campaign_id=?", cid)
        self.x("DELETE FROM cursors WHERE campaign_id=?", cid)

    def camp_chat_ids(self, cid: int) -> set[int]:
        return {r["chat_id"] for r in self.q("SELECT chat_id FROM camp_groups WHERE campaign_id=?", cid)}

    def set_camp_group(self, cid: int, chat_id: int, on: bool) -> None:
        if on:
            self.x("INSERT OR IGNORE INTO camp_groups VALUES (?, ?)", cid, chat_id)
        else:
            self.x("DELETE FROM camp_groups WHERE campaign_id=? AND chat_id=?", cid, chat_id)

    def cursor(self, cid: int, chat_id: int) -> int:
        row = self.one("SELECT idx FROM cursors WHERE campaign_id=? AND chat_id=?", cid, chat_id)
        return row["idx"] if row else 0

    def set_cursor(self, cid: int, chat_id: int, idx: int) -> None:
        self.x("INSERT INTO cursors VALUES (?, ?, ?) ON CONFLICT(campaign_id, chat_id) DO UPDATE SET idx=excluded.idx",
               cid, chat_id, idx)

    # ---------- группы ----------
    def groups(self) -> list[dict]:
        return [dict(r) for r in self.q("SELECT * FROM groups ORDER BY title COLLATE NOCASE")]

    def group(self, chat_id: int) -> dict | None:
        row = self.one("SELECT * FROM groups WHERE chat_id=?", chat_id)
        return dict(row) if row else None

    def sync_groups(self, found: list[tuple[int, str]]) -> tuple[int, int]:
        """Список из юзербота: новые добавляет, названия обновляет, пропавшие удаляет. -> (новых, удалено)."""
        have = {g["chat_id"] for g in self.groups()}
        ids = {cid for cid, _ in found}
        for cid, title in found:
            self.x("INSERT INTO groups (chat_id, title) VALUES (?, ?) ON CONFLICT(chat_id) DO UPDATE SET title=excluded.title",
                   cid, title)
        gone = have - ids
        for cid in gone:
            self.x("DELETE FROM groups WHERE chat_id=?", cid)
            self.x("DELETE FROM camp_groups WHERE chat_id=?", cid)
        return len(ids - have), len(gone)

    def update_group(self, chat_id: int, **fields) -> None:
        sets = ", ".join(f"{k}=?" for k in fields)
        self.x(f"UPDATE groups SET {sets} WHERE chat_id=?", *fields.values(), chat_id)

    # ---------- журнал ----------
    def log_sent(self, chat_id: int, cid: int | None, pid: int | None, ok: bool, err: str | None = None) -> None:
        self.x("INSERT INTO sent (chat_id, campaign_id, post_id, ts, ok, err) VALUES (?, ?, ?, ?, ?, ?)",
               chat_id, cid, pid, now(), int(ok), err)

    def last_ok(self, chat_id: int) -> int:
        row = self.one("SELECT MAX(ts) AS t FROM sent WHERE chat_id=? AND ok=1", chat_id)
        return row["t"] or 0

    def ok_since(self, chat_id: int, since: int) -> int:
        return self.one("SELECT COUNT(*) AS n FROM sent WHERE chat_id=? AND ok=1 AND ts>=?", chat_id, since)["n"]

    def stats_since(self, since: int) -> tuple[int, int]:
        row = self.one("SELECT SUM(ok) AS good, SUM(1-ok) AS bad FROM sent WHERE ts>=?", since)
        return row["good"] or 0, row["bad"] or 0
