"""Планировщик: круги рассылок, очередь вызовов, антифлуд, автопауза групп.

Как идёт один круг рассылки:
  1. По каждой группе рассылки (по очереди, с задержкой mention_delay + случайная добавка)
     проверяется антифлуд, выбирается следующий пост по кругу, ставится в очередь ожидания,
     юзербот пишет в группу «@бот».
  2. Гостевой бот получает вызов, берёт из очереди пост для этой группы и публикует его.
  3. После прохода по всем группам круг ждёт ответов (answer_timeout), считает итог,
     ошибки подряд копятся и при error_limit группа ставится на паузу.
Круги разных рассылок не перемешиваются: юзербот тегает только по одной рассылке за раз.
Посты-пересылки (mode=forward) юзербот пересылает сам, без бота: так сохраняется плашка «Переслано из».
"""
import asyncio
import logging
import random
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from html import escape

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from telethon import errors

from . import config
from .db import DB, now
from .posts import PostError
from .userbot import Userbot

log = logging.getLogger(__name__)


@dataclass
class Call:
    chat_id: int
    post: dict
    campaign_id: int | None
    fut: asyncio.Future = field(default_factory=lambda: asyncio.get_running_loop().create_future())
    trigger_id: int | None = None


def local_now() -> datetime:
    return datetime.now(timezone(timedelta(hours=config.TZ_OFFSET)))


def fmt_time(ts: int) -> str:
    if not ts:
        return "-"
    dt = datetime.fromtimestamp(ts, timezone(timedelta(hours=config.TZ_OFFSET)))
    return dt.strftime("%d.%m %H:%M")


class Scheduler:
    def __init__(self, db: DB, bot: Bot, ub: Userbot, bot_username: str) -> None:
        self.db, self.bot, self.ub, self.bot_username = db, bot, ub, bot_username
        self.pending: dict[int, deque[Call]] = {}
        self.running: set[int] = set()
        self.lock = asyncio.Lock()
        self.manual_ts: dict[int, int] = {}  # время последнего ручного вызова по группе

    # ---------- общие ----------
    async def notify(self, text: str) -> None:
        for uid in config.OWNER_IDS:
            try:
                await self.bot.send_message(uid, text)
            except Exception as e:
                log.info("Не отправил уведомление %s: %s", uid, e)

    def quiet(self) -> bool:
        a, b = self.db.setting("quiet_from"), self.db.setting("quiet_to")
        if a < 0 or b < 0 or a == b:
            return False
        h = local_now().hour
        return a <= h < b if a < b else (h >= a or h < b)

    def flood_reason(self, chat_id: int) -> str | None:
        gap = self.db.setting("min_gap") * 60
        last = self.db.last_ok(chat_id)
        if gap and last and now() - last < gap:
            return f"антифлуд, прошло {(now() - last) // 60} мин"
        return self.limit_reason(chat_id)

    def limit_reason(self, chat_id: int) -> str | None:
        """Лимиты на группу: в час и в сутки (и для рассылок, и для ручных вызовов)."""
        per_hour = self.db.setting("max_per_hour")
        if per_hour and self.db.ok_since(chat_id, now() - 3600) >= per_hour:
            return f"лимит {per_hour} в час"
        per_day = self.db.setting("max_per_day")
        if per_day and self.db.ok_since(chat_id, now() - 86400) >= per_day:
            return "лимит за сутки"
        return None

    def take(self, chat_id: int) -> Call | None:
        """Гостевой бот забирает вызов для группы."""
        q = self.pending.get(chat_id)
        while q:
            call = q.popleft()
            if not call.fut.done():
                return call
        return None

    # ---------- проверка медиа ----------
    async def check_media(self) -> None:
        """Медиа в постах-копиях привязано к боту. После смены бота старые file_id не работают:
        находим такие посты и говорим владельцу, какие пересоздать."""
        bad = []
        for p in self.db.posts():
            if p.get("mode") == "forward" or not p.get("file_id"):
                continue
            try:
                await self.bot.get_file(p["file_id"])
            except TelegramAPIError as e:
                msg = str(getattr(e, "message", e)).lower()
                if "too big" not in msg:  # большой файл getFile не отдаёт, но он рабочий
                    bad.append(p)
        if bad:
            log.warning("Медиа не от этого бота в постах: %s", [p["id"] for p in bad])
            await self.notify("⚠️ В этих постах фото/видео от другого бота, они не отправятся:\n"
                              + "\n".join(f"• {escape(p['title'])}" for p in bad)
                              + "\n\nОткрой 📝 Посты → пост → 🖼 Медиа и пришли файл заново.")

    # ---------- пересылки ----------
    async def make_src(self, orig_chat: int, orig_msg: int) -> int:
        """Бот пересылает оригинал поста юзерботу в личку. -> id этого сообщения у юзербота."""
        if not self.ub.ready:
            raise PostError("Юзербот не авторизован, пересылку сохранить нельзя. Сохрани копией.")
        since = now()
        try:
            await self.bot.forward_message(self.ub.me.id, orig_chat, orig_msg)
        except TelegramAPIError:
            await self.ub.start_bot(self.bot_username)  # юзербот ещё не запускал бота - бот не может ему писать
            await asyncio.sleep(2)
            try:
                await self.bot.forward_message(self.ub.me.id, orig_chat, orig_msg)
            except TelegramAPIError as e:
                raise PostError(f"Пост не пересылается ({getattr(e, 'message', e)}). Видимо, оригинал удалён "
                                "или в источнике запрет пересылки. Перешли пост боту заново.")
        for _ in range(5):
            await asyncio.sleep(1)
            src = await self.ub.find_forward(self.bot_username, since)
            if src:
                return src
        raise PostError("Юзербот не увидел пересланный пост у себя. Попробуй ещё раз.")

    async def forward_post(self, chat_id: int, post: dict) -> None:
        """Пересылка поста юзерботом. Если пост сохранён другим аккаунтом юзербота, сначала пересоздаёт его у текущего."""
        if not self.ub.ready:
            raise RuntimeError("юзербот не авторизован")
        if post.get("src_ub") != self.ub.me.id:
            if not post.get("orig_chat") or not post.get("orig_msg"):
                raise PostError("пересылка от старого юзербота, перешли пост боту заново")
            src = await self.make_src(post["orig_chat"], post["orig_msg"])
            self.db.update_post(post["id"], src_id=src, src_ub=self.ub.me.id)
            post["src_id"], post["src_ub"] = src, self.ub.me.id
            log.info("Пересылка %s пересохранена для юзербота %s", post["id"], self.ub.me.id)
        await self.ub.forward(chat_id, post["src_id"], self.bot_username)

    def manual_block(self, chat_id: int) -> str | None:
        """Можно ли сейчас ручной вызов в этой группе. -> причина отказа или None.
        Если можно, сразу занимает слот, чтобы пачка упоминаний подряд не прошла."""
        gap = self.db.setting("manual_gap") * 60
        last = max(self.db.last_ok(chat_id), self.manual_ts.get(chat_id, 0))
        if gap and last and now() - last < gap:
            return f"пауза, прошло {(now() - last) // 60} из {gap // 60} мин"
        reason = self.limit_reason(chat_id)
        if reason:
            return reason
        self.manual_ts[chat_id] = now()
        return None

    def manual_post(self, chat_id: int) -> tuple[dict, int | None] | None:
        """Пост для ручного вызова: следующий по кругу из рассылки этой группы (сначала активные),
        если группа ни в одной рассылке - следующий из всех постов. -> (пост, id рассылки) или None."""
        camps = [c for c in self.db.campaigns() if chat_id in self.db.camp_chat_ids(c["id"])]
        camps.sort(key=lambda c: not c["active"])
        for c in camps:
            posts = [p for p in (self.db.post(pid) for pid in c["posts"]) if p]
            if posts:
                idx = self.db.cursor(c["id"], chat_id)
                self.db.set_cursor(c["id"], chat_id, idx + 1)
                return posts[idx % len(posts)], c["id"]
        posts = self.db.posts()
        if not posts:
            return None
        idx = self.db.cursor(0, chat_id)  # 0 - свой круг для групп без рассылки
        self.db.set_cursor(0, chat_id, idx + 1)
        return posts[idx % len(posts)], None

    def _drop(self, call: Call) -> None:
        q = self.pending.get(call.chat_id)
        if q and call in q:
            q.remove(call)

    def _fail(self, chat_id: int, title: str, reason: str, call: Call | None = None) -> str | None:
        """Учёт ошибки. -> текст, если группа ушла на автопаузу."""
        self.db.log_sent(chat_id, call.campaign_id if call else None, call.post["id"] if call else None, False, reason)
        g = self.db.group(chat_id)
        if not g:
            return None
        errs = g["errors"] + 1
        self.db.update_group(chat_id, errors=errs)
        if errs >= self.db.setting("error_limit") and g["enabled"]:
            self.db.update_group(chat_id, enabled=0, pause_reason=reason)
            return f"⏸ {escape(title)}: на паузе после {errs} ошибок подряд ({escape(reason)})"
        return None

    # ---------- группы ----------
    async def sync_groups(self, announce: bool = True) -> None:
        """Подтянуть группы юзербота: новые добавить, пропавшие убрать, владельцу сообщить о новых."""
        if not self.ub.ready:
            return
        found = await self.ub.groups()
        have = {g["chat_id"] for g in self.db.groups()}
        # сменился аккаунт юзербота - старый список групп больше не нужен
        row = self.db.one("SELECT val FROM settings WHERE key='ub_id'")
        switched = row is None or int(row["val"]) != self.ub.me.id
        # совсем пустой ответ (ни одного диалога) - сбой, ничего не удаляем; есть чаты, но нет групп - честно чистим
        if not found and have and not switched and not self.ub.last_dialogs:
            return
        added, gone = self.db.sync_groups(found)
        if switched:
            self.db.x("INSERT INTO settings (key, val) VALUES ('ub_id', ?) "
                      "ON CONFLICT(key) DO UPDATE SET val=excluded.val", str(self.ub.me.id))
            if row is not None:
                log.info("Юзербот сменился: групп %s, убрано старых %s", len(found), gone)
                await self.notify(f"🔁 Юзербот сменился. Групп у нового аккаунта: {len(found)}, "
                                  f"старых убрано: {gone}.\n\nПроверь 📣 Рассылки → группы.")
                return
        new = [title for cid, title in found if cid not in have]
        if new:
            log.info("Новые группы: %s", ", ".join(new))
            if announce and have:
                await self.notify("➕ Юзербот в новых группах:\n" + "\n".join(f"• {escape(t)}" for t in new)
                                  + "\n\nДобавь их в рассылку: 📣 Рассылки → группы.")

    async def groups_loop(self) -> None:
        while True:
            try:
                await self.sync_groups()
            except Exception:
                log.exception("Ошибка обновления групп")
            await asyncio.sleep(120)

    # ---------- цикл ----------
    async def loop(self) -> None:
        asyncio.create_task(self.groups_loop())
        while True:
            try:
                await self.tick()
            except Exception:
                log.exception("Ошибка планировщика")
            await asyncio.sleep(15)

    async def tick(self) -> None:
        if not self.ub.ready or self.quiet():
            return
        t = now()
        for c in self.db.campaigns():
            if c["active"] and c["next_run"] <= t and c["id"] not in self.running:
                self.start_round(c["id"])

    def start_round(self, cid: int, force: bool = False) -> bool:
        """force=True: круг вне расписания (кнопка Круг сейчас) - без антифлуда и лимитов,
        расписание следующего круга не сдвигается."""
        if cid in self.running:
            return False
        self.running.add(cid)
        asyncio.create_task(self._round_safe(cid, force))
        return True

    async def _round_safe(self, cid: int, force: bool = False) -> None:
        try:
            await self.round(cid, force)
        except Exception:
            log.exception("Ошибка круга рассылки %s", cid)
        finally:
            self.running.discard(cid)

    # ---------- круг ----------
    async def round(self, cid: int, force: bool = False) -> None:
        camp = self.db.campaign(cid)
        if not camp:
            return
        if not force:
            spread = camp["interval_min"] * 60 * 0.05  # ±5%, чтобы не было идеально ровного шага
            self.db.update_campaign(cid, next_run=now() + camp["interval_min"] * 60 + int(random.uniform(-spread, spread)))

        posts = [p for p in (self.db.post(pid) for pid in camp["posts"]) if p]
        chats = self.db.camp_chat_ids(cid)
        groups = [g for g in self.db.groups() if g["chat_id"] in chats and g["enabled"]]
        if not posts or not groups:
            await self.notify(f"📣 {escape(camp['title'])}: пропуск, нет {'постов' if not posts else 'активных групп'}.")
            return

        calls: list[tuple[Call, str]] = []
        direct_ok = 0
        skipped: list[str] = []
        paused: list[str] = []
        async with self.lock:
            for i, g in enumerate(groups):
                chat_id, title = g["chat_id"], g["title"]
                reason = None if force else self.flood_reason(chat_id)
                if reason:
                    skipped.append(f"{escape(title)}: {reason}")
                    continue
                idx = self.db.cursor(cid, chat_id)
                post = posts[idx % len(posts)]
                call = Call(chat_id, post, cid)
                forward = post.get("mode") == "forward"
                try:
                    if forward:  # настоящая пересылка от юзербота, бот не нужен
                        await self.forward_post(chat_id, post)
                        self.db.set_cursor(cid, chat_id, idx + 1)
                        self.db.log_sent(chat_id, cid, post["id"], True)
                        self.db.update_group(chat_id, errors=0)
                        direct_ok += 1
                    else:  # копия через гостевой режим: упоминание, бот отвечает постом
                        self.pending.setdefault(chat_id, deque()).append(call)
                        msg = await self.ub.mention(chat_id, self.bot_username)
                        call.trigger_id = msg.id
                        log.info("Круг %s: юзербот упомянул бота в %s (%s)", cid, chat_id, title)
                        self.db.set_cursor(cid, chat_id, idx + 1)
                        calls.append((call, title))
                except errors.FloodWaitError as e:
                    self._drop(call)
                    skipped.append(f"{escape(title)}: FloodWait {e.seconds} сек")
                    log.warning("FloodWait %s сек, жду", e.seconds)
                    await asyncio.sleep(e.seconds + 5)
                    continue
                except errors.SlowModeWaitError as e:
                    self._drop(call)
                    skipped.append(f"{escape(title)}: медленный режим, {e.seconds} сек")
                except Exception as e:
                    self._drop(call)
                    name = type(e).__name__
                    p = self._fail(chat_id, title, f"юзербот ({'пересылка' if forward else 'вызов'}): {name}", call)
                    skipped.append(f"{escape(title)}: {name}")
                    if p:
                        paused.append(p)
                if i < len(groups) - 1:
                    await asyncio.sleep(self.db.setting("mention_delay") + random.uniform(0, self.db.setting("jitter")))

        # ждём ответов бота
        if calls:
            await asyncio.wait([c.fut for c, _ in calls], timeout=self.db.setting("answer_timeout"))
        ok = direct_ok
        for call, title in calls:
            result = call.fut.result() if call.fut.done() else "бот не ответил вовремя"
            if result is True:
                ok += 1
                self.db.log_sent(call.chat_id, cid, call.post["id"], True)
                self.db.update_group(call.chat_id, errors=0)
                if self.db.setting("delete_trigger") and call.trigger_id:
                    asyncio.create_task(self._delete_later(call.chat_id, call.trigger_id))
            else:
                self._drop(call)
                if not call.fut.done():
                    call.fut.cancel()
                if call.trigger_id:  # голый «@бот» без поста не оставляем
                    await self.ub.delete(call.chat_id, call.trigger_id)
                p = self._fail(call.chat_id, title, str(result), call)
                skipped.append(f"{escape(title)}: {escape(str(result))}")
                if p:
                    paused.append(p)

        report = f"📣 <b>{escape(camp['title'])}</b>: {ok} из {len(groups)}"
        if skipped:
            report += "\n" + "\n".join(f"• {s}" for s in skipped[:15])
        self.db.update_campaign(cid, last_report=f"{fmt_time(now())}: {ok} из {len(groups)}")
        log.info("Итог круга %s: %s из %s. %s", cid, ok, len(groups), "; ".join(skipped) or "без ошибок")
        if paused:
            await self.notify("\n".join(paused))
        if self.db.setting("reports"):
            await self.notify(report)

    async def _delete_later(self, chat_id: int, msg_id: int) -> None:
        await asyncio.sleep(self.db.setting("delete_after"))
        await self.ub.delete(chat_id, msg_id)
