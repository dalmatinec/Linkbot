import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from config import DB_PATH
from typing import Optional, List, Dict, Any, Union

DB_PATH = "bot.db"

def get_db():
    """Получить соединение с БД"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Инициализация всех таблиц"""
    conn = get_db()
    cur = conn.cursor()
    
    # Таблица users
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            joined_at TIMESTAMP,
            last_activity TIMESTAMP,
            banned INTEGER DEFAULT 0,
            links_total INTEGER DEFAULT 0,
            chat_links INTEGER DEFAULT 0,
            channel_links INTEGER DEFAULT 0,
            reserve_links INTEGER DEFAULT 0,
            last_chat_time TIMESTAMP,
            last_channel_time TIMESTAMP,
            last_reserve_time TIMESTAMP
        )
    ''')
    
    # Таблица admins
    cur.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            role TEXT,
            created_at TIMESTAMP
        )
    ''')
    
    # Таблица settings
    cur.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            name TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    # Таблица link_logs
    cur.execute('''
        CREATE TABLE IF NOT EXISTS link_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            category TEXT,
            created_at TIMESTAMP
        )
    ''')
    
    # Таблица admin_logs
    cur.execute('''
        CREATE TABLE IF NOT EXISTS admin_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER,
            action TEXT,
            target TEXT,
            created_at TIMESTAMP
        )
    ''')
    
    # Таблица broadcasts
    cur.execute('''
        CREATE TABLE IF NOT EXISTS broadcasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER,
            success_count INTEGER,
            failed_count INTEGER,
            created_at TIMESTAMP
        )
    ''')
    
    # Заполняем настройки по умолчанию (всё пустое, кроме обязательных)
    default_settings = {
        'chat_link': '',
        'channel_link': '',
        'operator1_name': 'Оператор SIS',
        'operator1_link': '',
        'operator2_name': 'Оператор BRO',
        'operator2_link': '',
        'reserve_link': '',
        'site_link': '',
        'info_text': 'ℹ️ Информация о боте\n\nЗдесь можно получить ссылки на ресурсы.'
    }
    
    for name, value in default_settings.items():
        cur.execute('INSERT OR IGNORE INTO settings (name, value) VALUES (?, ?)', (name, value))
    
    # Добавляем владельца в админы, если его там нет
    from config import OWNER_ID
    cur.execute('''
        INSERT OR IGNORE INTO admins (user_id, username, role, created_at)
        VALUES (?, ?, ?, ?)
    ''', (OWNER_ID, 'owner', 'owner', datetime.now()))
    
    conn.commit()
    conn.close()

# ============ РАБОТА С ПОЛЬЗОВАТЕЛЯМИ ============

def register_user(user_id: int, username: str, first_name: str):
    """Регистрация нового пользователя"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        INSERT OR IGNORE INTO users (user_id, username, first_name, joined_at, last_activity)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, username, first_name, datetime.now(), datetime.now()))
    # Если пользователь уже есть, обновляем username и first_name
    cur.execute('''
        UPDATE users SET username = ?, first_name = ? WHERE user_id = ?
    ''', (username, first_name, user_id))
    conn.commit()
    conn.close()

def update_activity(user_id: int):
    """Обновление последней активности"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute('UPDATE users SET last_activity = ? WHERE user_id = ?', (datetime.now(), user_id))
    conn.commit()
    conn.close()

def get_user(user_id: int) -> Optional[Dict]:
    """Получить данные пользователя"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def is_banned(user_id: int) -> bool:
    """Проверить забанен ли пользователь"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT banned FROM users WHERE user_id = ?', (user_id,))
    row = cur.fetchone()
    conn.close()
    return row['banned'] == 1 if row else False

def ban_user(user_id: int, admin_id: int):
    """Забанить пользователя"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute('UPDATE users SET banned = 1 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()
    add_admin_log(admin_id, 'ban', str(user_id))

def unban_user(user_id: int, admin_id: int):
    """Разбанить пользователя"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute('UPDATE users SET banned = 0 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()
    add_admin_log(admin_id, 'unban', str(user_id))

def update_link_usage(user_id: int, category: str):
    """Обновить статистику использования ссылок"""
    conn = get_db()
    cur = conn.cursor()
    now = datetime.now()
    
    # Обновляем счётчики
    cur.execute('UPDATE users SET links_total = links_total + 1 WHERE user_id = ?', (user_id,))
    
    if category == 'chat':
        cur.execute('UPDATE users SET chat_links = chat_links + 1, last_chat_time = ? WHERE user_id = ?', (now, user_id))
    elif category == 'channel':
        cur.execute('UPDATE users SET channel_links = channel_links + 1, last_channel_time = ? WHERE user_id = ?', (now, user_id))
    elif category == 'reserve':
        cur.execute('UPDATE users SET reserve_links = reserve_links + 1, last_reserve_time = ? WHERE user_id = ?', (now, user_id))
    
    # Добавляем лог перехода
    cur.execute('INSERT INTO link_logs (user_id, category, created_at) VALUES (?, ?, ?)', (user_id, category, now))
    
    conn.commit()
    conn.close()

def can_get_link(user_id: int, category: str) -> tuple[bool, int]:
    """Проверить, может ли пользователь получить ссылку. Возвращает (можно, секунды_ожидания)"""
    user = get_user(user_id)
    if not user:
        return True, 0
    
    now = datetime.now()
    
    if category == 'chat':
        last_time = user.get('last_chat_time')
        if last_time:
            last_time = datetime.fromisoformat(last_time) if isinstance(last_time, str) else last_time
            elapsed = (now - last_time).total_seconds()
            if elapsed < CHAT_COOLDOWN:
                return False, int(CHAT_COOLDOWN - elapsed)
    elif category == 'channel':
        last_time = user.get('last_channel_time')
        if last_time:
            last_time = datetime.fromisoformat(last_time) if isinstance(last_time, str) else last_time
            elapsed = (now - last_time).total_seconds()
            if elapsed < CHANNEL_COOLDOWN:
                return False, int(CHANNEL_COOLDOWN - elapsed)
    elif category == 'reserve':
        last_time = user.get('last_reserve_time')
        if last_time:
            last_time = datetime.fromisoformat(last_time) if isinstance(last_time, str) else last_time
            elapsed = (now - last_time).total_seconds()
            if elapsed < RESERVE_COOLDOWN:
                return False, int(RESERVE_COOLDOWN - elapsed)
    
    return True, 0

# ============ РАБОТА С АДМИНАМИ ============

def is_admin(user_id: int) -> bool:
    """Проверить, является ли пользователь админом"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT 1 FROM admins WHERE user_id = ?', (user_id,))
    row = cur.fetchone()
    conn.close()
    return row is not None

def add_admin(user_id: int, username: str, role: str = 'admin', admin_id: int = None):
    """Добавить админа"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        INSERT OR REPLACE INTO admins (user_id, username, role, created_at)
        VALUES (?, ?, ?, ?)
    ''', (user_id, username, role, datetime.now()))
    conn.commit()
    conn.close()
    if admin_id:
        add_admin_log(admin_id, 'add_admin', str(user_id))

def remove_admin(user_id: int, admin_id: int = None):
    """Удалить админа"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute('DELETE FROM admins WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()
    if admin_id:
        add_admin_log(admin_id, 'remove_admin', str(user_id))

def get_all_admins() -> List[Dict]:
    """Получить всех админов"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT * FROM admins ORDER BY created_at')
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# ============ РАБОТА С НАСТРОЙКАМИ ============

def get_setting(name: str) -> str:
    """Получить настройку"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT value FROM settings WHERE name = ?', (name,))
    row = cur.fetchone()
    conn.close()
    return row['value'] if row else ''

def set_setting(name: str, value: str, admin_id: int = None):
    """Установить настройку"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute('INSERT OR REPLACE INTO settings (name, value) VALUES (?, ?)', (name, value))
    conn.commit()
    conn.close()
    if admin_id:
        add_admin_log(admin_id, 'set_setting', f'{name}={value}')

def get_all_settings() -> Dict[str, str]:
    """Получить все настройки"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT name, value FROM settings')
    rows = cur.fetchall()
    conn.close()
    return {row['name']: row['value'] for row in rows}

# ============ ЛОГИ ============

def add_admin_log(admin_id: int, action: str, target: str = ''):
    """Добавить лог действия админа"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO admin_logs (admin_id, action, target, created_at)
        VALUES (?, ?, ?, ?)
    ''', (admin_id, action, target, datetime.now()))
    conn.commit()
    conn.close()

def add_broadcast_log(admin_id: int, success_count: int, failed_count: int) -> int:
    """Добавить лог рассылки, вернуть ID"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO broadcasts (admin_id, success_count, failed_count, created_at)
        VALUES (?, ?, ?, ?)
    ''', (admin_id, success_count, failed_count, datetime.now()))
    broadcast_id = cur.lastrowid
    conn.commit()
    conn.close()
    return broadcast_id

# ============ СТАТИСТИКА ============

def get_user_stats() -> Dict:
    """Получить статистику по пользователям"""
    conn = get_db()
    cur = conn.cursor()
    now = datetime.now()
    today_start = datetime(now.year, now.month, now.day)
    week_start = today_start - timedelta(days=7)
    month_start = today_start - timedelta(days=30)
    
    # Всего пользователей
    cur.execute('SELECT COUNT(*) as count FROM users')
    total = cur.fetchone()['count']
    
    # За сегодня
    cur.execute('SELECT COUNT(*) as count FROM users WHERE joined_at >= ?', (today_start,))
    today = cur.fetchone()['count']
    
    # За неделю
    cur.execute('SELECT COUNT(*) as count FROM users WHERE joined_at >= ?', (week_start,))
    week = cur.fetchone()['count']
    
    # За месяц
    cur.execute('SELECT COUNT(*) as count FROM users WHERE joined_at >= ?', (month_start,))
    month = cur.fetchone()['count']
    
    # Активные за день (last_activity >= сегодня)
    cur.execute('SELECT COUNT(*) as count FROM users WHERE last_activity >= ?', (today_start,))
    active_today = cur.fetchone()['count']
    
    # Баны
    cur.execute('SELECT COUNT(*) as count FROM users WHERE banned = 1')
    banned = cur.fetchone()['count']
    
    # Статистика по ссылкам
    cur.execute('SELECT SUM(chat_links) as chat, SUM(channel_links) as channel, SUM(reserve_links) as reserve FROM users')
    links = cur.fetchone()
    
    conn.close()
    
    return {
        'total': total,
        'today': today,
        'week': week,
        'month': month,
        'active_today': active_today,
        'banned': banned,
        'chat_links': links['chat'] or 0,
        'channel_links': links['channel'] or 0,
        'reserve_links': links['reserve'] or 0,
        'total_links': (links['chat'] or 0) + (links['channel'] or 0) + (links['reserve'] or 0)
    }

# ============ КОЛДЖАУНЫ ============
from config import CHAT_COOLDOWN, CHANNEL_COOLDOWN, RESERVE_COOLDOWN