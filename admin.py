from datetime import datetime
import shutil
import os

from config import (
    DATABASE_NAME,
    BACKUP_DIR,
    LOG_CHANNEL_ID
)

from db import (
    get_full_statistics,
    get_daily_report,
    get_admin_logs
)

def build_stats_text():

    stats = get_full_statistics()

    return f"""
📊 СТАТИСТИКА БОТА

👥 Пользователи:
• Всего: {stats['total_users']}
• Сегодня: {stats['new_today']}
• За неделю: {stats['new_week']}
• За месяц: {stats['new_month']}

📈 Активность:
• Активных сегодня: {stats['active_today']}

🔗 Ссылки:
• Всего: {stats['total_links']}
• Чат: {stats['chat_links']}
• Канал: {stats['channel_links']}
• Резерв: {stats['reserve_links']}

🚫 Ограничения:
• Забанено: {stats['banned']}
• Заблокировали бота: {stats['blocked']}

👨‍💼 Администраторы:
• Всего: {stats['admins']}
"""

def build_logs_text():

    logs = get_admin_logs()

    if not logs:
        return "Логи отсутствуют."

    text = "📋 ПОСЛЕДНИЕ ДЕЙСТВИЯ\n\n"

    for log in logs[:30]:

        text += (
            f"👤 {log[1]}\n"
            f"⚙️ {log[2]}\n"
            f"🎯 {log[3]}\n"
            f"🕒 {log[4]}\n\n"
        )

    return text[:4000]

def create_backup():

    os.makedirs(
        BACKUP_DIR,
        exist_ok=True
    )

    filename = (
        datetime.now().strftime(
            "database_%d-%m-%Y.db"
        )
    )

    backup_path = os.path.join(
        BACKUP_DIR,
        filename
    )

    shutil.copy(
        DATABASE_NAME,
        backup_path
    )

    return backup_path

def cleanup_backups():

    files = []

    for file in os.listdir(
        BACKUP_DIR
    ):

        if file.endswith(".db"):

            files.append(
                os.path.join(
                    BACKUP_DIR,
                    file
                )
            )

    files.sort(
        key=os.path.getmtime,
        reverse=True
    )

    for file in files[7:]:

        try:
            os.remove(file)
        except:
            pass

async def send_daily_report(
    bot
):

    report = get_daily_report()

    try:

        await bot.send_message(
            LOG_CHANNEL_ID,
            report
        )

    except:
        pass

async def send_backup_log(
    bot,
    backup_path
):

    try:

        await bot.send_message(
            LOG_CHANNEL_ID,
            f"""
💾 СОЗДАН БЭКАП

📁 Файл:
{backup_path}
"""
        )

    except:
        pass