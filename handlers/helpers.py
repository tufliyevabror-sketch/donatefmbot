"""Umumiy yordamchilar — bot.py dan ko'chirildi (faza 1).

Hech qanday handler yo'q, faqat sof funksiyalar. bot.py ularni
`from handlers.helpers import ...` orqali qayta import qiladi, shuning
uchun qolgan 3500 qator o'zgarishsiz ishlaydi.
"""
import asyncio
import re
import sqlite3 as _sqlite3

from aiogram.types import Message

import config
import database as db
import text as ls


def _lang(obj):
    """Message yoki CallbackQuery'dan user tilini oladi (sync, tez)."""
    try:
        uid = obj.from_user.id
        conn = _sqlite3.connect(config.DB_PATH)
        row = conn.execute("SELECT lang FROM users WHERE user_id=?", (uid,)).fetchone()
        conn.close()
        return (row[0] if row else "uz") or "uz"
    except Exception:
        return "uz"


async def _ensure_not_banned(message_or_call):
    """Check if user is banned; if so, send message and return False."""
    user_id = message_or_call.from_user.id
    user = await db.get_user(user_id)
    if user and user["is_banned"]:
        text = ls.banned_message(_lang(message_or_call))
        if isinstance(message_or_call, Message):
            await message_or_call.answer(text)
        else:
            await message_or_call.answer(text, show_alert=True)
        return False
    return True


async def safe_edit(message, *args, **kwargs):
    """edit_text'ning 'message is not modified' xatosidan himoya."""
    try:
        return await message.edit_text(*args, **kwargs)
    except Exception:
        return None


def format_price(value):
    return f"{(value or 0):,}".replace(",", " ")


async def _client_line(user_id, prefix="👤 Mijoz"):
    try:
        u = await db.get_user(user_id)
    except Exception:
        u = None
    ident = ""
    if u is not None:
        try:
            uname = u["username"] or ""
        except (KeyError, IndexError, TypeError):
            uname = ""
        try:
            name = u["full_name"] or ""
        except (KeyError, IndexError, TypeError):
            name = ""
        parts = []
        if uname:
            parts.append("@" + str(uname))
        if name:
            parts.append(str(name))
        ident = " — ".join(parts)
    return f"{prefix}: <code>{user_id}</code>" + (f"\n💠 {ident}" if ident else "")


def esc(s):
    return "" if s is None else str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def stars_to_som(stars):
    return stars * config.stars_rate_per_1000() // 1000


async def _all_admin_ids():
    """Adminlar ro'yxati (keshsiz, yangilangan): config + DB."""
    ids = set(config.ADMIN_IDS)
    try:
        for uid in await db.db_admins():
            ids.add(uid)
    except Exception:
        pass
    return ids


# Adminlar keshi. Muhim: `refresh_admin_cache` obyektni QAYTA BIND qilmaydi,
# faqat ichini tozalab to'ldiradi — shuning uchun `from helpers import
# _admin_ids_cache` qilgan barcha modullar bir xil obyektni ko'radi.
_admin_ids_cache = set()


def refresh_admin_cache(extra_ids=()):
    """Keshni yangilaydi (obyekt bir xil qoladi)."""
    _admin_ids_cache.clear()
    _admin_ids_cache.update(config.ADMIN_IDS)
    for uid in extra_ids or ():
        try:
            _admin_ids_cache.add(int(uid))
        except (TypeError, ValueError):
            continue
    return _admin_ids_cache


def admin_ids():
    """Adminlar ro'yxati (tez, sinxron)."""
    return _admin_ids_cache


def is_admin(user_id):
    if _admin_ids_cache:
        return user_id in _admin_ids_cache
    return user_id in config.ADMIN_IDS


async def _start_card_topup(msg, user_id, amount, lang="uz", card_label=None):
    """Karta topup: to'lov so'rovini yaratadi, adminga xabar beradi, foydalanuvchini eslatadi."""
    payment_id = await db.create_payment(user_id, "karta", amount, "")
    client = await _client_line(user_id)
    card_line = f"💳 Karta: <b>{card_label}</b>\n" if card_label else ""
    for admin_id in await _all_admin_ids():
        try:
            await msg.bot.send_message(
                admin_id,
                f"💰 <b>Hisobni to'ldirish</b>\n\n"
                f"{client}\n"
                f"💰 {format_price(amount)} so'm\n"
                f"💠 Usul: Karta\n"
                f"{card_line}"
                f"💳 To'lov: #{payment_id}",
            )
        except Exception:
            pass
    mins = max(1, config.pay_window_seconds() // 60)
    try:
        await msg.bot.send_message(
            user_id,
            f"📸 <b>Chek yuborishni unutmang!</b>\n\n"
            f"Pulni o'tkazgan bo'lsangiz — chek/screenshot RASMIni hoziroq shu yerga yuboring.\n"
            f"⏳ {mins} daqiqa ichida yuborsangiz, admin tez tasdiqlaydi.",
        )
    except Exception:
        pass
    return payment_id


async def _ocr_verdict(bot, file_id, amount, expected_card_last4=""):
    """Chek rasmini OCR bilan tekshiradi -> caption uchun qisqa maslahat (yoki '').
    Summa + karta oxirgi 4 raqam solishtiriladi (soxta chek himoyasi)."""
    try:
        if not config.bool_setting("ocr_enabled", True):
            return ""
        import cheq_ocr
        if not cheq_ocr.engine_ready() or not amount:
            return ""
        buf = await bot.download_file(file_id)
        raw = buf.read() if hasattr(buf, "read") else buf
        res = await asyncio.to_thread(
            cheq_ocr.check_receipt, raw, int(amount), expected_card_last4
        )
        return cheq_ocr.verdict_line(res, int(amount))
    except Exception:
        return ""


def _expected_card_last4(method):
    """Karta to'lovi bo'lsa aktiv karta oxirgi 4 raqam, aks holda ''."""
    try:
        if str(method or "").lower() not in ("card", "karta"):
            return ""
        digits = re.sub(r"[^\d]", "", config.get_active_card() or "")
        return digits[-4:] if len(digits) >= 4 else ""
    except Exception:
        return ""
