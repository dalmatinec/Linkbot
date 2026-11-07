"""Юзербот на Telethon: список групп и упоминание бота."""
import logging

from telethon import TelegramClient, utils

from . import config

log = logging.getLogger(__name__)


class Userbot:
    def __init__(self) -> None:
        self.client = TelegramClient(config.SESSION, config.API_ID, config.API_HASH)
        self.me = None
        self.last_dialogs = 0  # сколько диалогов вернул последний запрос групп

    @property
    def ready(self) -> bool:
        return self.me is not None

    async def start(self) -> bool:
        await self.client.connect()
        if not await self.client.is_user_authorized():
            log.warning("Юзербот не авторизован: запустите python -m app login")
            return False
        self.me = await self.client.get_me()
        await self.client.get_dialogs()  # прогрев кэша, чтобы слать по числовому id
        log.info("Юзербот: %s (id %s)", self.me.username or self.me.first_name, self.me.id)
        return True

    async def groups(self) -> list[tuple[int, str]]:
        found, total, kinds = [], 0, {}
        async for d in self.client.iter_dialogs():
            total += 1
            e = d.entity
            kind = type(e).__name__ + (":mega" if getattr(e, "megagroup", False) else "") \
                + (":giga" if getattr(e, "gigagroup", False) else "")
            kinds[kind] = kinds.get(kind, 0) + 1
            if d.is_group or getattr(e, "gigagroup", False):
                found.append((utils.get_peer_id(e), d.name or str(d.id)))
        log.info("Диалогов юзербота: %s %s, из них групп: %s", total, kinds, len(found))
        self.last_dialogs = total
        return found

    async def mention(self, chat_id: int, bot_username: str):
        return await self.client.send_message(chat_id, f"@{bot_username}")

    # ---------- пересылки ----------
    # Бот пересылает пост юзерботу в личку, юзербот потом пересылает это сообщение в группы.
    # Пересылка пересланного сохраняет исходную плашку «Переслано из ...», кнопки и премиум-эмодзи.
    async def start_bot(self, bot_username: str) -> None:
        await self.client.send_message(bot_username, "/start")

    async def find_forward(self, bot_username: str, since: int) -> int | None:
        """id самого свежего пересланного сообщения от бота не старше since (unix)."""
        for m in await self.client.get_messages(bot_username, limit=5):
            if not m.out and m.fwd_from and m.date.timestamp() >= since - 5:
                return m.id
        return None

    async def forward(self, chat_id: int, msg_id: int, bot_username: str) -> None:
        res = await self.client.forward_messages(chat_id, msg_id, from_peer=bot_username)
        if not res:
            raise RuntimeError("сообщение для пересылки не найдено")

    async def delete(self, chat_id: int, msg_id: int) -> None:
        try:
            await self.client.delete_messages(chat_id, [msg_id])
        except Exception as e:
            log.info("Не удалил вызов в %s: %s", chat_id, e)


async def login() -> None:
    """Интерактивный вход: номер, код, пароль 2FA. Сессия сохраняется в data/userbot.session."""
    import os
    os.makedirs(config.DATA_DIR, exist_ok=True)
    client = TelegramClient(config.SESSION, config.API_ID, config.API_HASH)
    await client.start()
    me = await client.get_me()
    print(f"Готово: вошли как {me.first_name} (@{me.username}), id {me.id}")
    await client.disconnect()
