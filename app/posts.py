"""Пост: захват из сообщения (новое или пересланное), кнопки, отправка, ответ гостевого бота.

Кнопки хранятся как ряды: [[[текст, ссылка, премиум-иконка, цвет], ...], ...].
Текст хранится в HTML, премиум-эмодзи как <tg-emoji>.
"""
import re
from html import escape, unescape

from aiogram import Bot
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultArticle,
    InlineQueryResultCachedDocument,
    InlineQueryResultCachedMpeg4Gif,
    InlineQueryResultCachedPhoto,
    InlineQueryResultCachedVideo,
    InputTextMessageContent,
    Message,
)

CAPTION_LIMIT = 1024
TEXT_LIMIT = 4096
LABEL_LIMIT = 64
KIND_NAMES = {"text": "текст", "photo": "фото", "video": "видео", "animation": "GIF", "document": "файл"}
STYLES = [None, "primary", "success", "danger"]
STYLE_NAMES = {None: "обычная", "primary": "синяя", "success": "зелёная", "danger": "красная"}


class PostError(Exception):
    pass


def plain(html: str) -> str:
    return unescape(re.sub(r"<[^>]+>", "", html or ""))


def message_html(message: Message) -> str:
    return message.html_text if (message.text or message.caption) else ""


def message_media(message: Message) -> tuple[str, str | None]:
    """-> (вид, file_id). Порядок важен: у GIF заполнено и animation, и document."""
    if message.photo:
        return "photo", message.photo[-1].file_id
    if message.animation:
        return "animation", message.animation.file_id
    if message.video:
        return "video", message.video.file_id
    if message.document:
        return "document", message.document.file_id
    if message.text:
        return "text", None
    raise PostError("Такой тип не подходит. Нужен текст, фото, видео, GIF или файл.")


def check_len(kind: str, html: str) -> None:
    limit = TEXT_LIMIT if kind == "text" else CAPTION_LIMIT
    if len(plain(html)) > limit:
        raise PostError(f"Слишком длинный текст: {len(plain(html))} из {limit} символов"
                        + (" (у медиа подпись короче)." if kind != "text" else "."))


def capture(message: Message, strict: bool = True) -> dict:
    """Новое или пересланное сообщение -> поля поста. URL-кнопки пересланного поста сохраняются.
    strict=False для пересылок: юзербот перешлёт как есть, ограничения копии не важны."""
    try:
        if message.media_group_id:
            raise PostError("Альбомы гостевой бот отправить не может. Пришли одно фото или видео.")
        kind, file_id = message_media(message)
        html = message_html(message)
        if kind == "text" and not html:
            raise PostError("Пустой пост.")
        check_len(kind, html)
    except PostError:
        if strict:
            raise
        kind, file_id, html = "text", None, message_html(message)
    buttons = []
    kb = message.reply_markup
    for row in (kb.inline_keyboard if isinstance(kb, InlineKeyboardMarkup) else []):
        r = [[b.text, b.url, getattr(b, "icon_custom_emoji_id", None), getattr(b, "style", None)]
             for b in row if b.url]
        if r:
            buttons.append(r)
    title = " ".join(plain(html).split())[:30] or ("пересылка" if not strict else KIND_NAMES[kind])
    return {"title": title, "kind": kind, "file_id": file_id, "html": html, "buttons": buttons}


# ---------- кнопки ----------
def markup(buttons: list) -> InlineKeyboardMarkup | None:
    rows = []
    for row in buttons:
        rows.append([InlineKeyboardButton(text=b[0], url=b[1], icon_custom_emoji_id=b[2] or None,
                                          style=b[3] or None) for b in row])
    return InlineKeyboardMarkup(inline_keyboard=rows) if rows else None


def normalize_url(raw: str) -> str | None:
    raw = raw.strip()
    if re.fullmatch(r"@[A-Za-z0-9_]{4,32}", raw):
        return "https://t.me/" + raw[1:]
    if re.match(r"(t\.me|telegram\.me)/", raw):
        return "https://" + raw
    if re.match(r"(https?|tg)://\S+$", raw):
        return raw
    return None


def parse_buttons(text: str) -> list:
    """Каждая строка - ряд. «Текст - ссылка», несколько в ряд через |."""
    rows = []
    for n, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        row = []
        for seg in line.split("|"):
            m = re.match(r"^\s*(.+?)\s+-\s+(\S+)\s*$", seg)
            url = normalize_url(m.group(2)) if m else None
            if not m or not url:
                raise PostError(f"Строка {n}: не понял «{escape(seg.strip())}». Формат: Текст - https://ссылка")
            row.append([m.group(1)[:LABEL_LIMIT], url, None, None])
        if len(row) > 8:
            raise PostError(f"Строка {n}: больше 8 кнопок в ряд нельзя.")
        rows.append(row)
    if not rows:
        raise PostError("Не нашёл ни одной кнопки.")
    return rows


def parse_label(message: Message) -> tuple[str, str | None]:
    """Первое премиум-эмодзи в тексте становится иконкой кнопки, остальное - подписью."""
    text = message.text or ""
    raw = text.encode("utf-16-le")
    for e in message.entities or []:
        if e.type == "custom_emoji":
            rest = (raw[:e.offset * 2] + raw[(e.offset + e.length) * 2:]).decode("utf-16-le")
            label = " ".join(rest.split()) or text.strip()
            return label[:LABEL_LIMIT], e.custom_emoji_id
    return " ".join(text.split())[:LABEL_LIMIT], None


def move_button(rows: list, r: int, c: int, d: str) -> tuple[list, int, int]:
    """Сдвиг кнопки. ⬅️➡️ внутри ряда; ⬆️⬇️: из ряда в отдельную строку, из отдельной строки в соседний ряд."""
    rows = [list(x) for x in rows]
    b = rows[r][c]
    if d == "left" and c > 0:
        rows[r][c - 1], rows[r][c] = rows[r][c], rows[r][c - 1]
        return rows, r, c - 1
    if d == "right" and c < len(rows[r]) - 1:
        rows[r][c + 1], rows[r][c] = rows[r][c], rows[r][c + 1]
        return rows, r, c + 1
    if d == "up":
        if len(rows[r]) > 1:
            rows[r].pop(c)
            rows.insert(r, [b])
            return rows, r, 0
        if r > 0 and len(rows[r - 1]) < 8:
            rows.pop(r)
            rows[r - 1].append(b)
            return rows, r - 1, len(rows[r - 1]) - 1
    if d == "down":
        if len(rows[r]) > 1:
            rows[r].pop(c)
            rows.insert(r + 1, [b])
            return rows, r + 1, 0
        if r < len(rows) - 1 and len(rows[r + 1]) < 8:
            rows.pop(r)
            rows[r].insert(0, b)
            return rows, r, 0
    return rows, r, c


# ---------- отправка ----------
async def send_post(bot: Bot, chat_id: int, post: dict) -> Message:
    kb = markup(post["buttons"])
    html = post["html"] or None
    kind, fid = post["kind"], post["file_id"]
    common = {"caption": html, "parse_mode": "HTML", "reply_markup": kb}
    if kind == "photo":
        return await bot.send_photo(chat_id, fid, **common)
    if kind == "video":
        return await bot.send_video(chat_id, fid, **common)
    if kind == "animation":
        return await bot.send_animation(chat_id, fid, **common)
    if kind == "document":
        return await bot.send_document(chat_id, fid, **common)
    return await bot.send_message(chat_id, post["html"], parse_mode="HTML", reply_markup=kb)


def guest_result(post: dict):
    """Пост в виде результата для answerGuestQuery (формат тот же, что у инлайн-режима)."""
    rid = f"p{post['id']}"
    kb = markup(post["buttons"])
    html = post["html"] or None
    kind, fid = post["kind"], post["file_id"]
    common = {"id": rid, "caption": html, "parse_mode": "HTML", "reply_markup": kb}
    if kind == "photo":
        return InlineQueryResultCachedPhoto(photo_file_id=fid, **common)
    if kind == "video":
        return InlineQueryResultCachedVideo(video_file_id=fid, title=post["title"], **common)
    if kind == "animation":
        return InlineQueryResultCachedMpeg4Gif(mpeg4_file_id=fid, **common)
    if kind == "document":
        return InlineQueryResultCachedDocument(document_file_id=fid, title=post["title"], **common)
    return InlineQueryResultArticle(
        id=rid, title=post["title"], reply_markup=kb,
        input_message_content=InputTextMessageContent(message_text=post["html"], parse_mode="HTML"),
    )
