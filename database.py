def get_posts_for_group(self, chat_id: int) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT p.* FROM posts p
                INNER JOIN post_groups pg ON p.id = pg.post_id
                WHERE pg.chat_id = ?
                ORDER BY p.id DESC
            ''', (chat_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    # ========== СТАТИСТИКА ==========
    
    def get_users_count(self, include_blocked: bool = False) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if include_blocked:
                cursor.execute('SELECT COUNT(*) FROM users')
            else:
                cursor.execute('SELECT COUNT(*) FROM users WHERE is_blocked = 0')
            return cursor.fetchone()[0]
    
    def get_groups_count(self) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM groups')
            return cursor.fetchone()[0]
    
    def get_posts_count(self) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM posts')
            return cursor.fetchone()[0]


_db_instance = None

def get_database(db_path: str = "bot_database.db") -> BotDatabase:
    global _db_instance
    if _db_instance is None:
        _db_instance = BotDatabase(db_path)
    return _db_instance