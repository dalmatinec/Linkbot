"""Админка в боте: посты, конструктор кнопок, рассылки, группы, настройки, статус."""
import asyncio
import logging
from html import escape

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from . import config
from .db import DB, SETTINGS, now
from .posts import (
    KIND_NAMES, STYLE_NAMES, STYLES, PostError, capture, check_len, message_html, message_media,
    move_button, normalize_url, parse_buttons, parse_label, plain, send_post,
)
from .scheduler import Scheduler, fmt_time
from .userbot import Userbot

log = logging.getLogger(__name__)
router = Router()
router.message.filter(F.from_user.id.in_(config.OWNER_IDS))
router.callback_query.filter(F.from_user.id.in_(config.OWNER_IDS))

INTERVALS = [(15, "15 мин"), (30, "30 мин"), (60, "1 ч"), (120, "2 ч"), (180, "3 ч"), (360, "6 ч"),
             (720, "12 ч"), (1440, "24 ч")]


class S(StatesGroup):
    wait = State()


ICONS = {"text": "📄", "photo": "🖼", "video": "🎬", "animation": "🎞", "document": "📎"}


def is_forward(message: Message) -> bool:
    return message.forward_origin is not None


async def save_forward(ctx: "Ctx", draft: dict, orig_chat: int, orig_msg: int) -> int:
    """Бот пересылает пост юзерботу в личку, юзербот запоминает id и потом пересылает его в группы."""
    src = await ctx.sched.make_src(orig_chat, orig_msg)
    pid = ctx.db.add_post(**draft, mode="forward", src_id=src, orig_chat=orig_chat, orig_msg=orig_msg)
    ctx.db.update_post(pid, src_ub=ctx.ub.me.id)
    return pid


def kb(rows: list) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t, callback_data=d) for t, d in row] for row in rows if row
    ])


def short(text: str, n: int = 28) -> str:
    text = " ".join(text.split())
    return text if len(text) <= n else text[:n - 1] + "…"


class Ctx:
    def __init__(self, ev: Message | CallbackQuery, state: FSMContext, db: DB, sched: Scheduler, ub: Userbot,
                 bot: Bot) -> None:
        self.ev, self.state, self.db, self.sched, self.ub, self.bot = ev, state, db, sched, ub, bot
        self.answered = False

    @property
    def chat_id(self) -> int:
        return self.ev.from_user.id

    async def show(self, text: str, rows: list, new: bool = False) -> None:
        markup = kb(rows)
        if isinstance(self.ev, CallbackQuery) and not new:
            try:
                await self.ev.message.edit_text(text, reply_markup=markup)
                return
            except TelegramBadRequest as e:
                if "not modified" in str(e):
                    return
        await self.bot.send_message(self.chat_id, text, reply_markup=markup)

    async def alert(self, text: str) -> None:
        if isinstance(self.ev, CallbackQuery) and not self.answered:
            self.answered = True
            await self.ev.answer(text, show_alert=True)
        else:
            await self.bot.send_message(self.chat_id, text)

    async def ask(self, kind: str, prompt: str, back: str, **data) -> None:
        await self.state.set_state(S.wait)
        await self.state.set_data({"kind": kind, "back": back, **data})
        await self.show(prompt, [[("✖️ Отмена", "x:" + back)]])


# =================== экраны ===================
async def scr_main(ctx: Ctx) -> None:
    db = ctx.db
    active = sum(c["active"] for c in db.campaigns())
    ub = f"✅ {escape(ctx.ub.me.first_name or '')}" if ctx.ub.ready else "❌ не авторизован (python -m app login)"
    text = (f"<b>Linkbot</b>\n\nЮзербот: {ub}\nАктивных рассылок: {active}\n\n"
            "Новый пост можно просто переслать сюда.")
    await ctx.show(text, [
        [(f"📝 Посты ({len(db.posts())})", "posts"), (f"📣 Рассылки ({len(db.campaigns())})", "camps")],
        [(f"👥 Группы ({len(db.groups())})", "groups"), ("⚙️ Настройки", "set")],
        [("📊 Статус", "st")],
    ])


async def scr_posts(ctx: Ctx) -> None:
    rows = [[(("↪️" if p["mode"] == "forward" else ICONS[p["kind"]]) + f" {short(p['title'])}", f"p:{p['id']}")]
            for p in ctx.db.posts()]
    rows += [[("➕ Новый пост", "p:new")], [("◀️ Меню", "m")]]
    await ctx.show("📝 <b>Посты</b>\n\n↪️ пересылка: юзербот пересылает оригинал с плашкой «Переслано из».\n"
                   "📄🖼🎬 копия: созданный в боте пост, публикует бот через упоминание.", rows)


async def scr_post(ctx: Ctx, pid: int, new: bool = False) -> None:
    p = ctx.db.post(pid)
    if not p:
        return await scr_posts(ctx)
    used = [c["title"] for c in ctx.db.campaigns() if pid in c["posts"]]
    nbtn = sum(len(r) for r in p["buttons"])
    if p["mode"] == "forward":
        text = (f"↪️ <b>{escape(p['title'])}</b>\nТип: пересылка. Юзербот пересылает оригинал с плашкой "
                f"«Переслано из», кнопками и премиум-эмодзи. Редактировать пересылку нельзя: сделай копию.\n"
                f"В рассылках: {escape(', '.join(used)) if used else 'нет'}")
        return await ctx.show(text, [
            [("👁 Предпросмотр", f"p:{pid}:view")],
            [("📄 Сделать копию для правки", f"p:{pid}:copy")],
            [("🏷 Название", f"p:{pid}:title"), ("🗑 Удалить", f"p:{pid}:del")],
            [("◀️ Посты", "posts")],
        ], new=new)
    text = (f"📝 <b>{escape(p['title'])}</b>\nТип: {KIND_NAMES[p['kind']]} · кнопок: {nbtn}\n"
            f"В рассылках: {escape(', '.join(used)) if used else 'нет'}\n\n"
            f"<i>{escape(short(plain(p['html']), 300)) or '(без текста)'}</i>")
    await ctx.show(text, [
        [("👁 Предпросмотр", f"p:{pid}:view")],
        [("✏️ Текст", f"p:{pid}:text"), ("🖼 Медиа", f"p:{pid}:media")],
        [(f"🔘 Кнопки ({nbtn})", f"b:{pid}")],
        [("🏷 Название", f"p:{pid}:title"), ("📄 Копия", f"p:{pid}:copy")],
        [("🗑 Удалить", f"p:{pid}:del")],
        [("◀️ Посты", "posts")],
    ], new=new)


async def scr_buttons(ctx: Ctx, pid: int, new: bool = False) -> None:
    p = ctx.db.post(pid)
    if not p:
        return await scr_posts(ctx)
    rows = [[(("⭐ " if b[2] else "") + (b[0] or "·"), f"bb:{pid}:{r}:{c}") for c, b in enumerate(row)]
            for r, row in enumerate(p["buttons"])]
    rows += [[("➕ Добавить", f"b:{pid}:add")]]
    if p["buttons"]:
        rows += [[("🧹 Удалить все", f"b:{pid}:clear")]]
    rows += [[("◀️ К посту", f"p:{pid}")]]
    text = (f"🔘 <b>Кнопки поста «{escape(p['title'])}»</b>\n\nРаскладка как в посте. Нажми кнопку, чтобы "
            "изменить текст, ссылку, цвет или двигать её.") if p["buttons"] else \
        f"🔘 <b>Кнопки поста «{escape(p['title'])}»</b>\n\nКнопок пока нет."
    await ctx.show(text, rows, new=new)


async def scr_button(ctx: Ctx, pid: int, r: int, c: int, new: bool = False) -> None:
    p = ctx.db.post(pid)
    try:
        b = p["buttons"][r][c]
    except (TypeError, IndexError):
        return await scr_buttons(ctx, pid)
    text = (f"🔘 <b>{escape(b[0])}</b>\nСсылка: {escape(b[1])}\nЦвет: {STYLE_NAMES.get(b[3], 'обычная')}"
            f"\nПремиум-иконка: {'есть' if b[2] else 'нет'}\nМесто: ряд {r + 1}, позиция {c + 1}\n\n"
            "⬆️⬇️ выносят из ряда в отдельную строку или переносят в соседний ряд, ⬅️➡️ двигают внутри ряда.")
    k = f"{pid}:{r}:{c}"
    await ctx.show(text, [
        [("⬆️", f"bm:{k}:up"), ("⬇️", f"bm:{k}:down"), ("⬅️", f"bm:{k}:left"), ("➡️", f"bm:{k}:right")],
        [("✏️ Текст", f"bm:{k}:label"), ("🔗 Ссылка", f"bm:{k}:url")],
        [("🎨 Цвет", f"bm:{k}:style"), ("❌ Удалить", f"bm:{k}:del")],
        [("◀️ К кнопкам", f"b:{pid}")],
    ], new=new)


async def scr_camps(ctx: Ctx) -> None:
    rows = [[(("▶️ " if c["active"] else "⏸ ") + short(c["title"], 24) + f" · {c['interval_min']} мин",
              f"c:{c['id']}")] for c in ctx.db.campaigns()]
    rows += [[("➕ Новая рассылка", "c:new")], [("◀️ Меню", "m")]]
    await ctx.show("📣 <b>Рассылки</b>\n\nРассылка = посты (идут по кругу) + группы + интервал.", rows)


async def scr_camp(ctx: Ctx, cid: int, new: bool = False) -> None:
    c = ctx.db.campaign(cid)
    if not c:
        return await scr_camps(ctx)
    chats = ctx.db.camp_chat_ids(cid)
    running = cid in ctx.sched.running
    status = "🔄 идёт круг" if running else ("▶️ работает" if c["active"] else "⏸ на паузе")
    text = (f"📣 <b>{escape(c['title'])}</b>\n\nСтатус: {status}\nИнтервал: каждые {c['interval_min']} мин\n"
            f"Постов: {len(c['posts'])} (по кругу) · групп: {len(chats)}\n"
            f"Следующий круг: {fmt_time(c['next_run']) if c['active'] else '-'}\n"
            f"Последний: {escape(c['last_report'] or '-')}")
    await ctx.show(text, [
        [("⏸ Пауза" if c["active"] else "▶️ Запустить", f"c:{cid}:toggle")],
        [(f"📝 Посты ({len(c['posts'])})", f"cp:{cid}"), (f"👥 Группы ({len(chats)})", f"cg:{cid}")],
        [("⏱ Интервал", f"c:{cid}:int"), ("🚀 Круг сейчас", f"c:{cid}:now")],
        [("🏷 Название", f"c:{cid}:title"), ("🗑 Удалить", f"c:{cid}:del")],
        [("◀️ Рассылки", "camps")],
    ], new=new)


async def scr_camp_posts(ctx: Ctx, cid: int) -> None:
    c = ctx.db.campaign(cid)
    order = {pid: i + 1 for i, pid in enumerate(c["posts"])}
    rows = [[((f"✅ {order[p['id']]}. " if p["id"] in order else "⬜ ") + short(p["title"]), f"cp:{cid}:{p['id']}")]
            for p in ctx.db.posts()]
    rows += [[("◀️ К рассылке", f"c:{cid}")]]
    await ctx.show(f"📝 <b>Посты рассылки «{escape(c['title'])}»</b>\n\nОтметь посты. Номер = порядок, "
                   "в каждую группу они идут по кругу.", rows)


async def scr_camp_groups(ctx: Ctx, cid: int) -> None:
    c = ctx.db.campaign(cid)
    chats = ctx.db.camp_chat_ids(cid)
    groups = ctx.db.groups()
    rows = [[(("✅ " if g["chat_id"] in chats else "⬜ ") + ("" if g["enabled"] else "⏸ ") + short(g["title"]),
              f"cg:{cid}:{g['chat_id']}")] for g in groups[:90]]
    rows += [[("✅ Все", f"cg:{cid}:all"), ("⬜ Снять все", f"cg:{cid}:none")], [("◀️ К рассылке", f"c:{cid}")]]
    hint = "" if groups else "\n\nГрупп пока нет: открой 👥 Группы → 🔄 Обновить из юзербота."
    await ctx.show(f"👥 <b>Группы рассылки «{escape(c['title'])}»</b>\n⏸ = группа на паузе.{hint}", rows)


async def scr_groups(ctx: Ctx) -> None:
    groups = ctx.db.groups()
    rows = [[(("✅ " if g["enabled"] else "⏸ ") + short(g["title"]), f"g:{g['chat_id']}")] for g in groups[:90]]
    rows += [[("🔄 Обновить из юзербота", "g:sync")], [("◀️ Меню", "m")]]
    paused = sum(not g["enabled"] for g in groups)
    await ctx.show(f"👥 <b>Группы юзербота</b>\n\nВсего: {len(groups)}, на паузе: {paused}.\n"
                   "Список берётся из чатов, где состоит юзербот.", rows)


async def scr_group(ctx: Ctx, chat_id: int) -> None:
    g = ctx.db.group(chat_id)
    if not g:
        return await scr_groups(ctx)
    text = (f"👥 <b>{escape(g['title'])}</b>\nID: <code>{chat_id}</code>\n"
            f"Статус: {'✅ включена' if g['enabled'] else '⏸ на паузе'}"
            + (f" ({escape(g['pause_reason'])})" if g["pause_reason"] and not g["enabled"] else "")
            + f"\nОшибок подряд: {g['errors']}\nПоследний пост: {fmt_time(ctx.db.last_ok(chat_id))}\n"
            f"Постов за сутки: {ctx.db.ok_since(chat_id, now() - 86400)}")
    await ctx.show(text, [
        [("⏸ Выключить" if g["enabled"] else "▶️ Включить", f"g:{chat_id}:tog")],
        [("♻️ Сбросить ошибки", f"g:{chat_id}:reset")],
        [("◀️ Группы", "groups")],
    ])


async def scr_settings(ctx: Ctx) -> None:
    rows = []
    for key, (_, desc, typ) in SETTINGS.items():
        v = ctx.db.setting(key)
        val = ("✅" if v else "❌") if typ == "bool" else str(v)
        rows.append([(f"{desc}: {val}", f"s:{key}")])
    rows.append([("◀️ Меню", "m")])
    await ctx.show("⚙️ <b>Настройки</b>\n\nНажми, чтобы изменить. Защита: задержка со случайной добавкой между "
                   "группами, антифлуд и суточный лимит на группу, автопауза группы после ошибок, тихие часы.", rows)


async def scr_status(ctx: Ctx) -> None:
    db = ctx.db
    good, bad = db.stats_since(now() - 86400)
    groups = db.groups()
    lines = [f"📊 <b>Статус</b>\n",
             f"Юзербот: {'✅ ' + escape(ctx.ub.me.first_name or '') if ctx.ub.ready else '❌ не авторизован'}",
             f"Тихие часы сейчас: {'да' if ctx.sched.quiet() else 'нет'}",
             f"За сутки: ✅ {good} постов, ❌ {bad} ошибок",
             f"Групп: {len(groups)}, на паузе: {sum(not g['enabled'] for g in groups)}", ""]
    for c in db.campaigns():
        if c["active"]:
            lines.append(f"▶️ {escape(c['title'])}: следующий {fmt_time(c['next_run'])}, "
                         f"последний {escape(c['last_report'] or '-')}")
    await ctx.show("\n".join(lines), [[("🔄 Обновить", "st")], [("◀️ Меню", "m")]])


# =================== кнопки меню ===================
async def route(ctx: Ctx, parts: list[str]) -> None:
    db, head = ctx.db, parts[0]
    arg = lambda i: parts[i] if len(parts) > i else None  # noqa: E731

    if head == "m":
        return await scr_main(ctx)
    if head == "posts":
        return await scr_posts(ctx)
    if head == "camps":
        return await scr_camps(ctx)
    if head == "groups":
        return await scr_groups(ctx)
    if head == "set":
        return await scr_settings(ctx)
    if head == "st":
        return await scr_status(ctx)

    if head == "pd":  # черновик из сообщения без режима ввода
        data = await ctx.state.get_data()
        await ctx.state.clear()
        which = arg(1) or "copy"
        draft = data.get(which)
        if not draft:
            return await ctx.alert("Черновик устарел, перешли пост ещё раз.")
        if which == "fwd":
            await ctx.show("⏳ Сохраняю пересылку…", [])
            pid = await save_forward(ctx, draft, data["orig_chat"], data["orig_msg"])
        else:
            pid = db.add_post(**draft)
        return await scr_post(ctx, pid)

    if head == "p":
        if arg(1) == "new":
            return await ctx.ask("newpost", "Перешли пост: он сохранится <b>пересылкой</b> (в группы уйдёт оригинал "
                                 "с плашкой «Переслано из»).\n\nИли отправь новый пост: текст, фото, видео, GIF или "
                                 "файл. Он сохранится <b>копией</b>, текст и кнопки можно править.", "posts")
        pid, act = int(parts[1]), arg(2)
        p = db.post(pid)
        if not p:
            return await scr_posts(ctx)
        if act is None:
            return await scr_post(ctx, pid)
        if p["mode"] == "forward" and act in ("text", "media", "nomedia"):
            return await scr_post(ctx, pid)
        if act == "view" and p["mode"] == "forward":
            try:
                await ctx.bot.forward_message(ctx.chat_id, p["orig_chat"], p["orig_msg"])
            except TelegramAPIError:
                return await ctx.alert("Оригинал в этом чате удалён, показать не могу. В группы пересылка "
                                       "всё равно уходит: юзербот хранит свою копию.")
            return await scr_post(ctx, pid, new=True)
        if act == "view":
            try:
                await send_post(ctx.bot, ctx.chat_id, p)
            except TelegramBadRequest as e:
                return await ctx.alert(f"Telegram не принял пост: {e.message}")
            return await scr_post(ctx, pid, new=True)
        if act == "text":
            return await ctx.ask("text", "Отправь новый текст поста. Форматирование и премиум-эмодзи сохранятся.",
                                 f"p:{pid}", pid=pid)
        if act == "media":
            rows_extra = [[("🚫 Убрать медиа", f"p:{pid}:nomedia")]] if p["kind"] != "text" else []
            await ctx.ask("media", "Отправь новое фото, видео, GIF или файл. Текст поста останется.", f"p:{pid}",
                          pid=pid)
            if rows_extra:
                await ctx.show("Или:", rows_extra, new=True)
            return
        if act == "nomedia":
            await ctx.state.clear()
            db.update_post(pid, kind="text", file_id=None)
            if not p["html"]:
                db.update_post(pid, html="…")
            return await scr_post(ctx, pid)
        if act == "title":
            return await ctx.ask("title", "Новое название поста (видно только в админке):", f"p:{pid}", pid=pid)
        if act == "copy":
            if p["kind"] == "text" and not p["html"]:
                return await ctx.alert("Из этой пересылки копию не сделать: тип сообщения не поддерживается.")
            try:
                check_len(p["kind"], p["html"])
            except PostError as e:
                return await ctx.alert(str(e))
            new_id = db.add_post(p["title"][:36] + " (копия)", p["kind"], p["file_id"], p["html"], p["buttons"])
            return await scr_post(ctx, new_id)
        if act == "del":
            return await ctx.show(f"Удалить пост «{escape(p['title'])}»? Он уберётся из всех рассылок.",
                                  [[("🗑 Да, удалить", f"p:{pid}:del2")], [("◀️ Нет", f"p:{pid}")]])
        if act == "del2":
            db.delete_post(pid)
            return await scr_posts(ctx)

    if head == "b":
        pid, act = int(parts[1]), arg(2)
        if (db.post(pid) or {}).get("mode") == "forward":
            return await scr_post(ctx, pid)
        if act == "add":
            return await ctx.ask(
                "btnadd",
                "Пришли кнопки. Каждая строка = ряд, формат <code>Текст - ссылка</code>, несколько в ряд через |\n\n"
                "<code>Сайт - https://site.kz | Чат - @chat\nНаписать нам - t.me/manager</code>\n\n"
                "Премиум-иконку и цвет можно задать потом у каждой кнопки.", f"b:{pid}", pid=pid)
        if act == "clear":
            db.update_post(pid, buttons=[])
        return await scr_buttons(ctx, pid)

    if head == "bb":
        return await scr_button(ctx, int(parts[1]), int(parts[2]), int(parts[3]))

    if head == "bm":
        pid, r, c, act = int(parts[1]), int(parts[2]), int(parts[3]), parts[4]
        p = db.post(pid)
        try:
            b = p["buttons"][r][c]
        except (TypeError, IndexError):
            return await scr_buttons(ctx, pid)
        if act in ("up", "down", "left", "right"):
            rows, r2, c2 = move_button(p["buttons"], r, c, act)
            if (r2, c2) == (r, c) and rows == p["buttons"]:
                return await ctx.alert("Дальше некуда.")
            db.update_post(pid, buttons=rows)
            return await scr_button(ctx, pid, r2, c2)
        if act == "style":
            nxt = STYLES[(STYLES.index(b[3]) + 1) % len(STYLES)] if b[3] in STYLES else None
            rows = p["buttons"]
            rows[r][c][3] = nxt
            db.update_post(pid, buttons=rows)
            return await scr_button(ctx, pid, r, c)
        if act == "del":
            rows = p["buttons"]
            rows[r].pop(c)
            rows = [row for row in rows if row]
            db.update_post(pid, buttons=rows)
            return await scr_buttons(ctx, pid)
        if act == "label":
            return await ctx.ask("btnlabel", "Новый текст кнопки. Первое премиум-эмодзи станет иконкой кнопки.",
                                 f"bb:{pid}:{r}:{c}", pid=pid, r=r, c=c)
        if act == "url":
            return await ctx.ask("btnurl", "Новая ссылка: https://…, t.me/… или @username", f"bb:{pid}:{r}:{c}",
                                 pid=pid, r=r, c=c)

    if head == "c":
        if arg(1) == "new":
            return await ctx.ask("camptitle", "Название новой рассылки:", "camps")
        cid, act = int(parts[1]), arg(2)
        c = db.campaign(cid)
        if not c:
            return await scr_camps(ctx)
        if act is None:
            return await scr_camp(ctx, cid)
        if act == "toggle":
            if not c["active"]:
                if not c["posts"] or not db.camp_chat_ids(cid):
                    return await ctx.alert("Сначала выбери посты и группы.")
                db.update_campaign(cid, active=1, next_run=now())
            else:
                db.update_campaign(cid, active=0)
            return await scr_camp(ctx, cid)
        if act == "now":
            if not ctx.ub.ready:
                return await ctx.alert("Юзербот не авторизован.")
            if not c["posts"] or not db.camp_chat_ids(cid):
                return await ctx.alert("Сначала выбери посты и группы.")
            if not ctx.sched.start_round(cid, force=True):
                return await ctx.alert("Круг уже идёт.")
            await ctx.alert("Проверочный круг запущен без антифлуда и лимитов, расписание не сдвигается. "
                            "Отчёт придёт по окончании.")
            return await scr_camp(ctx, cid)
        if act == "int":
            rows = [[(("✅ " if c["interval_min"] == m else "") + name, f"ci:{cid}:{m}") for m, name in INTERVALS[i:i + 4]]
                    for i in range(0, len(INTERVALS), 4)]
            rows += [[("✍️ Своё значение", f"c:{cid}:intc")], [("◀️ К рассылке", f"c:{cid}")]]
            return await ctx.show("⏱ Как часто проходить по всем группам рассылки?", rows)
        if act == "intc":
            return await ctx.ask("interval", "Интервал в минутах (от 5 до 10080):", f"c:{cid}", cid=cid)
        if act == "title":
            return await ctx.ask("camptitle", "Новое название рассылки:", f"c:{cid}", cid=cid)
        if act == "del":
            return await ctx.show(f"Удалить рассылку «{escape(c['title'])}»? Посты останутся.",
                                  [[("🗑 Да, удалить", f"c:{cid}:del2")], [("◀️ Нет", f"c:{cid}")]])
        if act == "del2":
            db.delete_campaign(cid)
            return await scr_camps(ctx)

    if head == "ci":
        cid, m = int(parts[1]), int(parts[2])
        c = db.campaign(cid)
        fields = {"interval_min": m}
        if c and c["active"]:
            fields["next_run"] = min(c["next_run"], now() + m * 60)
        db.update_campaign(cid, **fields)
        return await scr_camp(ctx, cid)

    if head == "cp":
        cid = int(parts[1])
        if arg(2):
            pid = int(parts[2])
            c = db.campaign(cid)
            posts = c["posts"]
            posts = [x for x in posts if x != pid] if pid in posts else posts + [pid]
            db.update_campaign(cid, posts=posts)
        return await scr_camp_posts(ctx, cid)

    if head == "cg":
        cid, a = int(parts[1]), arg(2)
        if a in ("all", "none"):
            for g in db.groups():
                db.set_camp_group(cid, g["chat_id"], a == "all")
        elif a:
            chat_id = int(a)
            db.set_camp_group(cid, chat_id, chat_id not in db.camp_chat_ids(cid))
        return await scr_camp_groups(ctx, cid)

    if head == "g":
        if arg(1) == "sync":
            if not ctx.ub.ready:
                return await ctx.alert("Юзербот не авторизован.")
            added, gone = db.sync_groups(await ctx.ub.groups())
            await ctx.alert(f"Новых групп: {added}, пропало: {gone}.")
            return await scr_groups(ctx)
        chat_id, act = int(parts[1]), arg(2)
        g = db.group(chat_id)
        if g and act == "tog":
            db.update_group(chat_id, enabled=0 if g["enabled"] else 1, errors=0, pause_reason=None)
        elif g and act == "reset":
            db.update_group(chat_id, errors=0)
        return await scr_group(ctx, chat_id)

    if head == "s":
        key = parts[1]
        default, desc, typ = SETTINGS[key]
        if typ == "bool":
            db.set_setting(key, 0 if db.setting(key) else 1)
            return await scr_settings(ctx)
        return await ctx.ask("setting", f"{desc}\nСейчас: {db.setting(key)}, по умолчанию: {default}.\n"
                                        "Пришли число:", "set", key=key)

    await scr_main(ctx)


@router.callback_query()
async def on_callback(cq: CallbackQuery, state: FSMContext, db: DB, sched: Scheduler, ub: Userbot, bot: Bot):
    data = cq.data or "m"
    keep_draft = data.startswith("pd")
    if not keep_draft:
        await state.clear()
    if data.startswith("x:"):
        data = data[2:]
    ctx = Ctx(cq, state, db, sched, ub, bot)
    try:
        await route(ctx, data.split(":"))
    except PostError as e:
        await ctx.alert(str(e))
    except Exception:
        log.exception("Ошибка в админке: %s", data)
        await ctx.alert("Что-то пошло не так, подробности в логе.")
    if not ctx.answered:
        await cq.answer()


# =================== ввод ===================
@router.message(CommandStart())
@router.message(Command("admin"))
async def on_start(message: Message, state: FSMContext, db: DB, sched: Scheduler, ub: Userbot, bot: Bot):
    await state.clear()
    await scr_main(Ctx(message, state, db, sched, ub, bot))


@router.message(S.wait)
async def on_input(message: Message, state: FSMContext, db: DB, sched: Scheduler, ub: Userbot, bot: Bot):
    ctx = Ctx(message, state, db, sched, ub, bot)
    data = await state.get_data()
    kind = data.get("kind")
    try:
        await handle_input(ctx, kind, data, message)
    except PostError as e:
        await message.answer(f"⚠️ {e}\n\nПопробуй ещё раз или нажми Отмена.")


def need_text(message: Message) -> str:
    if not message.text:
        raise PostError("Нужен текст.")
    return message.text.strip()


async def handle_input(ctx: Ctx, kind: str, data: dict, message: Message) -> None:
    db = ctx.db
    if kind == "newpost":
        if is_forward(message):  # пересланное сохраняем пересылкой
            pid = await save_forward(ctx, capture(message, strict=False), message.chat.id, message.message_id)
        else:
            pid = db.add_post(**capture(message))
        await ctx.state.clear()
        return await scr_post(ctx, pid)

    if kind == "setting":
        try:
            v = int(need_text(message))
        except ValueError:
            raise PostError("Нужно целое число.")
        if v < -1 or v > 100000:
            raise PostError("Странное значение.")
        db.set_setting(data["key"], v)
        await ctx.state.clear()
        return await scr_settings(ctx)

    if kind == "camptitle":
        title = need_text(message)[:40]
        await ctx.state.clear()
        if data.get("cid"):
            db.update_campaign(data["cid"], title=title)
            return await scr_camp(ctx, data["cid"])
        return await scr_camp(ctx, db.add_campaign(title))

    if kind == "interval":
        try:
            m = int(need_text(message))
        except ValueError:
            raise PostError("Нужно число минут.")
        if not 5 <= m <= 10080:
            raise PostError("От 5 до 10080 минут.")
        db.update_campaign(data["cid"], interval_min=m)
        await ctx.state.clear()
        return await scr_camp(ctx, data["cid"])

    pid = data.get("pid")
    p = db.post(pid) if pid else None
    if not p:
        await ctx.state.clear()
        return await scr_posts(ctx)

    if kind == "text":
        html = message_html(message)
        if not html:
            raise PostError("Нужен текст.")
        check_len(p["kind"], html)
        db.update_post(pid, html=html)
    elif kind == "media":
        mkind, fid = message_media(message)
        if mkind == "text":
            raise PostError("Нужно фото, видео, GIF или файл.")
        check_len(mkind, p["html"])
        db.update_post(pid, kind=mkind, file_id=fid)
    elif kind == "title":
        db.update_post(pid, title=need_text(message)[:40])
    elif kind == "btnadd":
        rows = parse_buttons(need_text(message))
        db.update_post(pid, buttons=p["buttons"] + rows)
        await ctx.state.clear()
        return await scr_buttons(ctx, pid)
    elif kind in ("btnlabel", "btnurl"):
        r, c = data["r"], data["c"]
        rows = p["buttons"]
        if kind == "btnlabel":
            label, icon = parse_label(message)
            if not label:
                raise PostError("Нужен текст.")
            rows[r][c][0], rows[r][c][2] = label, icon
        else:
            url = normalize_url(need_text(message))
            if not url:
                raise PostError("Не похоже на ссылку. Нужно https://…, t.me/… или @username")
            rows[r][c][1] = url
        db.update_post(pid, buttons=rows)
        await ctx.state.clear()
        return await scr_button(ctx, pid, r, c)
    await ctx.state.clear()
    await scr_post(ctx, pid)


@router.message()
async def on_free(message: Message, state: FSMContext, db: DB, sched: Scheduler, ub: Userbot, bot: Bot):
    """Пересланный или новый пост без режима ввода: предложить сохранить."""
    if (message.text or "").startswith("/"):
        return await scr_main(Ctx(message, state, db, sched, ub, bot))
    fwd = is_forward(message)
    try:
        copy_draft = capture(message)
    except PostError:
        copy_draft = None
    if not fwd and copy_draft is None:
        return await scr_main(Ctx(message, state, db, sched, ub, bot))
    fwd_draft = capture(message, strict=False) if fwd else None
    await state.set_data({"copy": copy_draft, "fwd": fwd_draft, "orig_chat": message.chat.id,
                          "orig_msg": message.message_id})
    rows = []
    if fwd:
        rows.append([("↪️ Сохранить пересылкой", "pd:fwd")])
    if copy_draft:
        rows.append([("📄 Сохранить копией" if fwd else "💾 Сохранить", "pd:copy")])
    rows.append([("✖️ Нет", "m")])
    title = (fwd_draft or copy_draft)["title"]
    hint = ("\n\nПересылкой: в группы уйдёт оригинал с плашкой «Переслано из», править нельзя.\n"
            "Копией: бот опубликует копию, можно править текст и кнопки.") if fwd else ""
    await message.answer(f"Сохранить пост «{escape(title)}»?{hint}", reply_markup=kb(rows))
