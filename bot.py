import asyncio
import base64
import logging
import os
import re
import time
from datetime import datetime

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    ErrorEvent,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    MenuButtonWebApp,
    Message,
    Update,
    WebAppInfo,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

import animations
import catalog
import config
import database as db
import i18n
import keyboards as kb
import order_notify
import services
import text as ls
from handlers.helpers import (
    _admin_ids_cache,
    _client_line,
    _ensure_not_banned,
    _lang,
    esc,
    format_price,
    is_admin,
    refresh_admin_cache,
    safe_edit,
)
from states import (
    AdminStates,
    BalanceBuyStates,
    StarsBuyStates,
    SupportStates,
    TopUpStates,
)

logging.basicConfig(level=logging.INFO)


class _TransientNetworkFilter(logging.Filter):
    """Vaqtinchalik tarmoq uzilishlari (timeout/reset) — ERROR emas, ogohlantirish.

    Polling o'zi qayta ulanadi, user hech narsa sezmaydi. Log toza turadi.
    Conflict (ikki instansiya) kabi jiddiy signallar ERRORligicha qoladi.
    """

    _NOISE = (
        "request timeout", "timed out", "connection reset",
        "server disconnected", "temporary failure", "try again",
    )

    def filter(self, record):
        try:
            if record.levelno >= logging.ERROR and "aiogram" in record.name:
                msg = str(record.getMessage()).lower()
                if any(n in msg for n in self._NOISE):
                    record.levelno = logging.WARNING
                    record.levelname = "WARNING"
        except Exception:
            pass
        return True


def _install_transient_filter():
    """Filtr HANDLER'ga qo'yiladi, logger'ga emas.

    Muhim: logging.Filter faqat o'sha logger orqali yozilgan recordlarni
    tekshiradi. `aiogram.dispatcher` kabi child logger'lar esa o'z record'ini
    yaratadi — parent logger filtri ularga TEGMAYDI. Faqat handler filtri
    propagation paytida ishlaydi. Shu sabab filtr root handler'lariga qo'yiladi.
    """
    filt = _TransientNetworkFilter()
    root = logging.getLogger()
    if not root.handlers:
        root.addHandler(logging.StreamHandler())
    for h in root.handlers:
        h.addFilter(filt)
    for name in ("aiogram", "aiogram.dispatcher", "uvicorn", "uvicorn.error"):
        for h in logging.getLogger(name).handlers:
            h.addFilter(filt)


_install_transient_filter()

router = Router()


# ================== FLOOD FILTRI ==================
# 10 soniyada 8+ xabar -> 5 soniya sabotaj + ogohlantirish (adminlar chetlab o'tadi)
_flood_hits: dict = {}
_flood_warn: dict = {}
_FLOOD_WINDOW = 10.0
_FLOOD_LIMIT = 8
_FLOOD_MUTE = 5.0


class FloodMiddleware(BaseMiddleware):
    """Tez-tez yuborishni vaqtincha cheklaydi."""

    async def __call__(self, handler, event, data):
        user = getattr(event, "from_user", None)
        if user is None or is_admin(user.id):
            return await handler(event, data)
        now = time.monotonic()
        hits = _flood_hits.setdefault(user.id, [])
        hits[:] = [t for t in hits if now - t < _FLOOD_WINDOW]
        if len(hits) >= _FLOOD_LIMIT:
            last_warn = _flood_warn.get(user.id, 0.0)
            if now - last_warn > _FLOOD_MUTE:
                _flood_warn[user.id] = now
                try:
                    if event.__class__.__name__ == "CallbackQuery":
                        await event.answer(
                            "⏳ Juda tez yuboryapsiz! Biroz kuting…",
                            show_alert=True,
                        )
                    else:
                        await event.answer("⏳ Juda tez yuboryapsiz! Biroz kuting…")
                except Exception:
                    pass
            return  # handlerni chaqirmaymiz
        hits.append(now)
        if len(_flood_hits) > 50000:
            _flood_hits.clear()
            _flood_warn.clear()
        return await handler(event, data)





@router.error()
async def _global_error(event: ErrorEvent, bot=None):
    """Barcha handler xatolari: logga yozadi va tugma spinnerini yopadi."""
    exc = event.exception
    benign = ("chat not found", "query is too old", "message is not modified",
              "message to edit not found", "message to delete not found",
              "button is too old", "user is deactivated", "PEER_ID_INVALID",
              "can't parse entities", "wrong message identifier")
    msg = str(exc)
    if type(exc).__name__ == "TelegramBadRequest" and any(b in msg for b in benign):
        logging.getLogger("bot").warning("Handler xatosi (kutilgan): %r", exc)
    else:
        logging.getLogger("bot").error(
            "Handler xatosi: %r", exc, exc_info=exc
        )
    cb = event.update.callback_query if event.update else None
    if cb and bot:
        try:
            await cb.answer(
                "⚠️ Kutilmagandik xatolik. Qayta urinib ko'ring.",
                show_alert=True,
            )
        except Exception:
            pass
    return True


async def refresh_admins():
    refresh_admin_cache(await db.db_admins())


# ================== START / MENU ==================
# (faza 2: handlers/start.py ga ko'chirildi)
from handlers.start import router as start_router


@router.message(Command("orders"))
async def cmd_orders(message: Message):
    if not await _ensure_not_banned(message): return
    user_id = message.from_user.id
    orders = await db.get_user_orders(user_id, 10)
    weburl = config.get_settings().get("webapp_url") or config.WEBAPP_URL
    text = "📦 <b>Oxirgi buyurtmalar</b>\n\n"
    if not orders:
        text += "Hozircha buyurtmalar yo'q."
    else:
        STAT = {
            "kutilmoqda": "⏳ Kutilmoqda",
            "bajarildi": "✅ Bajarildi",
            "rad_etildi": "❌ Bekor qilingan",
            "to'lov_kutilmoqda": "💳 To'lov kutilmoqda",
        }
        for o in orders:
            st = STAT.get(o["status"], o["status"])
            pname = str(o["package_name"]).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            text += f"• <b>#{o['id']}</b> {pname} — {o['price']:,} so'm\n  {st} · {o['created_at']}\n"
    kb = None
    if weburl:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🛍 Mini App'da ochish", web_app=WebAppInfo(url=weburl))],
                [InlineKeyboardButton(text="🔄 Yangilash", callback_data="noop")],
            ]
        )
    await message.answer(text, reply_markup=kb)


@router.message(Command("track"))
async def cmd_track(message: Message):
    if not await _ensure_not_banned(message): return
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip().lstrip("#").isdigit():
        await message.answer("🔎 Buyurtma raqamini kiriting: <code>/track 123</code>")
        return
    order_id = int(parts[1].strip().lstrip("#"))
    o = await db.get_order(order_id)
    if not o:
        await message.answer(f"❌ #{order_id} raqamli buyurtma topilmadi.")
        return
    if o["user_id"] != message.from_user.id and message.from_user.id not in _admin_ids_cache:
        await message.answer("⛔ Bu buyurtma sizga tegishli emas.")
        return
    STAT = {
        "kutilmoqda": "⏳ Kutilmoqda",
        "bajarildi": "✅ Bajarildi",
        "rad_etildi": "❌ Bekor qilingan",
        "to'lov_kutilmoqda": "💳 To'lov kutilmoqda",
    }
    st = STAT.get(o["status"], o["status"])
    pname = str(o["package_name"]).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    cfg = config.get_delivery_config()
    pending = await db.get_pending_orders()
    text = (
        f"🔎 <b>Buyurtma #{o['id']}</b>\n\n"
        f"📦 {pname}\n"
        f"🎮 Platforma: <b>{esc(str(o['platform']))}</b>\n"
        f"🆔 O'yin ID: <code>{esc(str(o['game_id']))}</code>\n"
        f"💰 Narxi: <b>{o['price']:,} so'm</b>\n"
        f"📌 Holat: {st}\n"
        f"⏰ Yaratilgan: {o['created_at']}\n\n"
        f"{ls.delivery_status_text(cfg, len(pending), _lang(message))}"
    )
    await message.answer(text)


@router.message(F.text == "⚙️ Sozlamalar")
async def show_settings(message: Message):
    if not await _ensure_not_banned(message): return
    user = await db.get_user(message.from_user.id)
    lang = user["lang"] if user else "uz"
    await message.answer(ls.settings_text(user), reply_markup=kb.user_settings_kb(lang))


@router.callback_query(F.data == "lang:menu")
async def lang_menu(call: CallbackQuery):
    await call.answer()
    user = await db.get_user(call.from_user.id)
    lang = user["lang"] if user else "uz"
    from i18n import t
    await safe_edit(call.message, t(lang, "language_label") + ":", reply_markup=kb.lang_kb(lang))


@router.callback_query(F.data.startswith("lang:"))
async def set_lang(call: CallbackQuery):
    new_lang = call.data.split(":")[1]
    if new_lang not in ("uz", "ru", "en"):
        await call.answer("Invalid language", show_alert=True)
        return
    await db.save_lang(call.from_user.id, new_lang)
    await call.answer("Til o'zgartirildi / Язык изменён / Language changed ✅", show_alert=True)
    user = await db.get_user(call.from_user.id)
    await safe_edit(call.message, ls.settings_text(user), reply_markup=kb.user_settings_kb(new_lang))


@router.message(Command("bonus"))
@router.message(F.text == "🎁 Kunlik bonus")
async def daily_bonus_cmd(message: Message):
    if not await _ensure_not_banned(message):
        return
    uid = message.from_user.id
    user = await db.get_user(uid)
    if not user:
        await db.register_user(uid, message.from_user.username, message.from_user.first_name or "")
    claimed, amount, balance, next_ts = await db.claim_daily_bonus(uid)
    if claimed:
        await message.answer(
            f"🎉 Kunlik bonus olindi: +{amount:,} so'm!\n"
            f"💰 Balans: {balance:,} so'm".replace(",", " "),
            reply_markup=kb.main_menu_kb(),
        )
        return
    left = max(0, int(next_ts) - int(time.time()))
    h, rem = divmod(left, 3600)
    m, s = divmod(rem, 60)
    await message.answer(
        f"⏳ Bugungi bonus olindi.\n"
        f"Keyingi bonus: {h:02}:{m:02}:{s:02} so'ndan keyin.",
        reply_markup=kb.main_menu_kb(),
    )


@router.message(F.text == "🤝 Taklif")
async def show_taklif(message: Message):
    if not await _ensure_not_banned(message): return
    await invite_cmd(message)


@router.message(F.text == "❌ Bekor qilish")
async def cancel_flow(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Bekor qilindi.", reply_markup=kb.main_menu_kb())


# ================== PROMO / INVITE ==================

@router.callback_query(F.data == "noop")
async def noop(call: CallbackQuery):
    await call.answer()


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Bekor qilindi.")


@router.message(Command("set"))
async def cmd_set(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Ruxsat yo'q.")
        return
    parts = (message.text or "").split(maxsplit=2)
    if len(parts) < 3:
        await message.answer(
            "📝 Format: <code>/set kalit qiymat</code>\n"
            "Misol: <code>/set delivery_api_url https://... </code>\n"
            "<code>/set delivery_provider custom</code>"
        )
        return
    key, value = parts[1], parts[2].strip()
    config.update_settings({key: value})
    await message.answer(f"✅ <b>{key}</b> = <code>{value}</code>")

@router.message(Command("addadmin"))
async def cmd_addadmin(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Sizda admin huquqi yo'q.")
        return
    parts = (message.text or "").split()
    if len(parts) < 2:
        await message.answer("📝 Format: <code>/addadmin user_id</code>")
        return
    try:
        target = int(parts[1])
    except ValueError:
        await message.answer("❌ Noto'g'ri ID.")
        return
    await db.add_admin_db(target, added_by=message.from_user.id)
    await refresh_admins()
    await message.answer(f"✅ <code>{target}</code> admin qilindi.")

@router.message(Command("deladmin"))
async def cmd_deladmin(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Sizda admin huquqi yo'q.")
        return
    parts = (message.text or "").split()
    if len(parts) < 2:
        await message.answer("📝 Format: <code>/deladmin user_id</code>")
        return
    try:
        target = int(parts[1])
    except ValueError:
        await message.answer("❌ Noto'g'ri ID.")
        return
    if target in config.ADMIN_IDS:
        await message.answer("❌ Bu asosiy admin. Uni o'chirib bo'lmaydi.")
        return
    await db.remove_admin_db(target)
    await refresh_admins()
    await message.answer(f"✅ <code>{target}</code> adminlikdan olindi.")

@router.message(Command("listadmins"))
async def cmd_listadmins(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Sizda admin huquqi yo'q.")
        return
    ids = await db.all_admin_ids()
    lines = [f"👑 <b>Adminlar</b> ({len(ids)} ta):\n"]
    for uid in ids:
        tag = " (asosiy)" if uid in config.ADMIN_IDS else ""
        lines.append(f"• <code>{uid}</code>{tag}")
    await message.answer("\n".join(lines))

async def _send_user_stats(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user:
        await message.answer("❌ Ma'lumot topilmadi. /start bosing.")
        return
    if user["is_banned"]:
        await message.answer(ls.banned_message(_lang(message)))
        return
    s = await db.user_stats(message.from_user.id)
    role = "🏪 Sotuvchi" if s["is_reseller"] else "👤 Mijoz"
    await message.answer(
        "📊 <b>Mening statistikam</b>\n\n"
        f"{role}\n"
        f"💰 Balans: <b>{format_price(s['balance'])} so'm</b>\n"
        f"💳 Jami to'lav: <b>{format_price(s['total_topup'])} so'm</b> ({s['payments']} ta)\n"
        f"💎 Keshbek: <b>{format_price(s['keshbek'])} so'm</b>\n"
        f"📦 Buyurtmalar: <b>{s['orders']}</b> ta (kutilmoqda: {s['orders_pending']})\n"
        f"🛍 Sarflagan: <b>{format_price(s['spent'])} so'm</b>\n"
        f"🤝 Taklif qilgan: <b>{s['referrals']}</b> kishi (olgan: {format_price(s['referral_earned'])} so'm)\n"
        f"⭐️ Sevimlilar: <b>{s['favorites']}</b> ta\n"
        f"📅 Ro'yxatdan o'tgan: <b>{s['reg_date']}</b>\n"
        f"🆔 ID: <code>{message.from_user.id}</code>"
    )


@router.message(F.text == "📊 Statistika")
async def user_stats_btn(message: Message):
    await _send_user_stats(message)


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    if not is_admin(message.from_user.id):
        await _send_user_stats(message)
        return
    s = await db.get_stats()
    text = (
        "📊 <b>To'liq statistika</b>\n\n"
        f"👥 <b>Foydalanuvchilar</b>\n"
        f"  Jami: <b>{s['users']}</b>\n"
        f"  Oylik faol (MAU): <b>{s['month_users']}</b>\n"
        f"  Yangi (bu oy): <b>{s['month_new_users']}</b>\n\n"
        f"📦 <b>Buyurtmalar</b>\n"
        f"  Bajarilgan (jami): <b>{s['orders']}</b>\n"
        f"  Kutilayotgan: <b>{s['pending']}</b>\n\n"
        f"💰 <b>Tushumlar</b>\n"
        f"  Umumiy: <b>{ls.money(s['revenue'])} so'm</b>\n"
        f"  Oylik: <b>{ls.money(s['month_revenue'])} so'm</b>\n"
        f"  Bugun buyurtmalar: <b>{s['today_orders']}</b> ta\n\n"
        f"💳 <b>To'lovlar</b>\n"
        f"  To'ldirilgan (jami): <b>{ls.money(s['topups'])} so'm</b>\n"
        f"  Oylik: <b>{ls.money(s['month_topups'])} so'm</b>\n"
        f"  Kutilayotgan: <b>{s['pending_pay']}</b> ta\n"
    )
    await message.answer(text)


@router.message(Command("trend"))
async def cmd_trend(message: Message):
    """Oxirgi 7 kun: buyurtmalar va tushum grafigi (faqat admin)."""
    if not is_admin(message.from_user.id):
        return
    rows = await db.daily_stats(7)
    lines = ["📈 <b>Oxirgi 7 kun</b>", ""]
    mx_o = max((r["orders"] for r in rows), default=0) or 1
    mx_r = max((r["revenue"] for r in rows), default=0) or 1
    lines.append("📦 Buyurtmalar:")
    for r in rows:
        bar = "█" * max(1, round(r["orders"] * 18 / mx_o)) if r["orders"] else "░"
        lines.append(f"• {r['d']}: <b>{r['orders']}</b> {bar}")
    lines.append("\n💰 Tushum (so'm):")
    for r in rows:
        bar = "█" * max(1, round(r["revenue"] * 18 / mx_r)) if r["revenue"] else "░"
        lines.append(f"• {r['d']}: <b>{ls.money(r['revenue'])}</b> {bar}")
    tot_o = sum(r["orders"] for r in rows)
    tot_r = sum(r["revenue"] for r in rows)
    tot_u = sum(r["new_users"] for r in rows)
    lines.append(
        f"\n📊 Jami: <b>{tot_o}</b> buyurtma · <b>{ls.money(tot_r)}</b> so'm"
        f" · <b>{tot_u}</b> yangi user"
    )
    await message.answer("\n".join(lines))

@router.message(Command("promo"))
async def promo_cmd(message: Message):
    user = await db.get_user(message.from_user.id)
    if user and user["is_banned"]:
        await message.answer(ls.banned_message(_lang(message)))
        return
    parts = (message.text or "").split(maxsplit=1)
    code = (parts[1] if len(parts) > 1 else "").strip()
    if not code:
        await message.answer(
            "🎁 <b>Promokod</b>\n\n"
            "Promokodingizni yuboring:\n<code>/promo KOD</code>\n\n"
            "Yoki Mini App → Sozlamalar → Chegirma kodlar."
        )
        return
    ok, msg = await db.redeem_promo(message.from_user.id, code)
    if ok:
        bal = (await db.get_user(message.from_user.id))["balance"]
        await message.answer(
            f"🎉 <b>Promokod qabul qilindi!</b>\n\n"
            f"💰 Balansingizga <b>{format_price(int(msg))} so'm</b> qo'shildi.\n"
            f"💠 Yangi balans: <b>{format_price(bal)} so'm</b>"
        )
    else:
        await message.answer(ls.promo_result_text(False, msg, _lang(message)))


@router.message(Command("invite"))
async def invite_cmd(message: Message):
    await db.get_or_create_user(
        message.from_user.id, message.from_user.username, message.from_user.full_name
    )
    percent = int(str(config.get_settings().get("referral_reward_topup_percent", 5)).replace(" ", "").replace(",", ""))
    username = config.get_settings().get("bot_username") or "game_shop_bot"
    link = f"https://t.me/{username}?start=ref_{message.from_user.id}"
    stats = await db.get_referral_stats(message.from_user.id)
    await message.answer(
        ls.referral_text(link, stats, percent, _lang(message)),
        reply_markup=kb.invite_kb(username, message.from_user.id),
    )


# ================== GAMES CATALOG ==================
# (faza 3a: handlers/catalog.py ga ko'chirildi)
from handlers.catalog import router as catalog_router

# ================== BALANCE / TOPUP ==================
# (faza 3b: handlers/payments.py ga ko'chirildi)
from handlers.payments import router as payments_router

# Flood filtri barcha sibling routerlarga (har bir hodisa bittasiga kiradi)
for _mw_router in (start_router, catalog_router, payments_router, router):
    _mw_router.message.middleware(FloodMiddleware())
    _mw_router.callback_query.middleware(FloodMiddleware())
del _mw_router


async def _verify_player_nickname(game_id, player_id):
    """O'yinchi ID -> o'yindagi nom (Free Fire/Roblox/Standoff). Topilmasa ''."""
    if not config.bool_setting("nickname_check_enabled", True):
        return ""
    try:
        import delivery
        res = await asyncio.wait_for(
            delivery.verify_player(game_id, str(player_id or "")), timeout=12
        )
        if res and res.get("ok") and res.get("name"):
            return esc(str(res["name"])[:40])
    except Exception:
        pass
    return ""


# ================== CARD CHECK / INVOICE ==================
# (faza 3b: handlers/payments.py ga ko'chirildi)

# ================== YORDAM / FAQ / MUROJAAT / ID ==================

def _help_text() -> str:
    s = config.get_settings()
    cb = s.get("keshbek_percent", 10)
    ref = s.get("referral_reward_topup_percent", 5)
    res = s.get("reseller_percent", 10)
    win = max(1, config.pay_window_seconds() // 60)
    return (
        "❓ <b>Yordam</b>\n\n"
        "💳 <b>To'lov:</b> «💰 Balans» → usul → summa → kartaga o'tkazing va "
        f"<b>chek rasmini yuboring</b> ({win} daqiqa ichida).\n"
        "📦 <b>Xarid:</b> «🛒 O'yinlar» → o'yin → paket → «Balans bilan» → o'yin ID.\n"
        f"💎 <b>Keshbek:</b> har bir to'lovda {cb}% bonus balansga qo'shiladi.\n"
        f"🤝 <b>Taklif:</b> do'stingiz birinchi to'lov qilsa, sizga {ref}% keladi "
        f"(sotuvchilar uchun {res}%).\n"
        "📧 <b>Murojaat:</b> «📧 Murojaat» — savol yozing, admin javob beradi.\n\n"
        "Batafsil quyidagilarni bosing 👇"
    )


def _faq_texts() -> dict:
    s = config.get_settings()
    cb = s.get("keshbek_percent", 10)
    ref = s.get("referral_reward_topup_percent", 5)
    res = s.get("reseller_percent", 10)
    win = max(1, config.pay_window_seconds() // 60)
    return {
        "pay": (
            "💳 <b>To'lov qanday?</b>\n\n"
            "1) «💰 Balans» → «💳 Karta»\n"
            "2) Summani tanlang yoki «✍️ Boshqa summa»\n"
            "3) Ko'rsatilgan kartaga pul o'tkazing\n"
            "4) <b>Chek / screenshot rasmini shu yerga yuboring</b>\n"
            "5) Admin tasdiqlaydi → balans avtomatik qo'shiladi\n\n"
            f"⏳ Muddat: <b>{win} daqiqa</b> (eslatma yuboriladi).\n"
            "⭐️ Tez variant: Telegram Stars orqali."
        ),
        "order": (
            "📦 <b>Buyurtma qanday?</b>\n\n"
            "1) «🛒 O'yinlar» → o'yinni tanlang\n"
            "2) Paketni tanlang\n"
            "3) «💰 Balans bilan»\n"
            "4) <b>O'yin ID</b>ni kiriting\n"
            "5) Avtomatik yuboriladi yoki admin bajaradi\n\n"
            "📜 «📜 Tarix» bo'limidan holatini kuzatishingiz mumkin."
        ),
        "cashback": (
            "💎 <b>Keshbek (bonus)</b>\n\n"
            f"Har bir <b>to'lov</b> (balansni to'ldirish)da <b>{cb}%</b> avtomatik bonus "
            "balansingizga qo'shiladi.\n\n"
            f"Misol: 100 000 so'm to'lov qilsangiz → <b>+{100000 * int(str(cb).replace(' ', '')) // 100:,} so'm</b> bonus.\n\n"
            "⚠️ Xarid qilganda keshbek qaytmaydi — faqat to'lovda beriladi."
        ).replace(",", " "),
        "referral": (
            "🤝 <b>Taklif (Referral)</b>\n\n"
            "«🤝 Taklif» → «📩 Do'stlarga ulashish».\n\n"
            f"Do'stingiz shu havola bilan ro'yxatdan o'tsa va <b>birinchi marta to'lov</b> qilsa, "
            f"sizga <b>{ref}%</b> avtomatik keladi.\n\n"
            f"🏪 <b>Sotuvchi</b> bo'lsangiz — sizga <b>{res}%</b> keladi."
        ),
        "support": (
            "📧 <b>Murojaat</b>\n\n"
            "1) «📧 Murojaat» tugmasini bosing\n"
            "2) Savolingizni yozing\n"
            "3) Admin javobni shu yerga yozadi\n\n"
            "💡 <code>/id</code> — o'z ID raqamingizni ko'rsatadi."
        ),
    }


@router.message(Command("id"))
async def cmd_id(message: Message):
    await message.answer(
        f"🆔 <b>Sizning ID:</b> <code>{message.from_user.id}</code>\n\n"
        "Admin yordamida ko'rsatish uchun shu IDni yuboring."
    )


_PROCESS_START = time.monotonic()


def _uptime_human(seconds: int) -> str:
    d, rem = divmod(int(seconds), 86400)
    h, rem = divmod(rem, 3600)
    m, s = divmod(rem, 60)
    parts = []
    if d:
        parts.append(f"{d} kun")
    if h:
        parts.append(f"{h} soat")
    if m:
        parts.append(f"{m} daqiqa")
    if not parts:
        parts.append(f"{s} soniya")
    return ", ".join(parts)


def _rss_mb():
    try:
        with open("/proc/self/status", encoding="utf-8") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) / 1024.0
    except Exception:
        return None
    return None


def _http_status(url, timeout=5):
    import urllib.request

    try:
        req = urllib.request.Request(url, method="GET", headers={"User-Agent": "bot-monitor"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return f"HTTP {resp.status}"
    except Exception as e:
        return f"Xato: {str(e)[:60]}"


async def build_status_text(bot) -> str:
    s = config.get_settings()
    cfg = config.get_delivery_config()
    stats = await db.get_stats()
    rss = _rss_mb()
    weburl = (s.get("webapp_url") or config.WEBAPP_URL or "").rstrip("/")

    webhook_url = ""
    pending_updates = "—"
    last_webhook_err = "yo'q"
    try:
        info = await bot.get_webhook_info()
        webhook_url = info.url or ""
        pending_updates = info.pending_update_count
        if info.last_error_message:
            last_webhook_err = f"{info.last_error_message[:80]} ({datetime.fromtimestamp(info.last_error_date)})" if info.last_error_date else info.last_error_message[:80]
    except Exception as e:
        last_webhook_err = f"API xatosi: {str(e)[:60]}"

    webapp_http = await asyncio.to_thread(_http_status, weburl) if weburl else "URL yo'q"
    notif_queue = await db.count_notifications()
    admins = await db.all_admin_ids()
    import sys

    return (
        "🖥 <b>Bot holati</b>\n\n"
        f"⏱ Ishlash: <b>{_uptime_human(time.monotonic() - _PROCESS_START)}</b>\n"
        f"🆔 PID: <code>{os.getpid()}</code> · 🧠 RSS: <b>{f'{rss:.0f} MB' if rss else '—'}</b>\n"
        f"🐍 Python: <code>{sys.version.split()[0]}</code> · aiogram: <code>{__import__('aiogram').__version__}</code>\n\n"
        f"🌐 Rejim: <b>{'Webhook' if USE_WEBHOOK else 'Polling'}</b>\n"
        f"🔗 Webhook: <code>{esc(webhook_url or 'o\'rnatilmagan')}</code>\n"
        f"📨 Kutilayotgan update: <b>{pending_updates}</b>\n"
        f"🛒 Webapp: <code>{esc(weburl or 'yo\'q')}</code> — {webapp_http}\n"
        f"🐛 Webhook oxirgi xato: {esc(last_webhook_err)}\n\n"
        f"📊 Foydalanuvchi: <b>{stats['users']}</b>\n"
        f"📦 Buyurtma: <b>{stats['orders']}</b> (kutilayotgan <b>{stats['pending']}</b>)\n"
        f"💳 To'lov: <b>{stats['topups']}</b> so'm (kutilayotgan <b>{stats['pending_pay']}</b>)\n"
        f"🔔 Navbatdagi bildirishnoma: <b>{notif_queue}</b>\n"
        f"🚚 Delivery: <code>{cfg['provider']}</code> ({cfg['interval']} sek)\n"
        f"🔑 Adminlar: <b>{len(admins)}</b>\n"
        f"🔧 maintenance: {'yoqilgan' if s.get('maintenance') else 'o\'chiq'}"
    )


@router.message(Command("status"))
async def cmd_status(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Sizda admin huquqi yo'q.")
        return
    await message.answer(await build_status_text(message.bot))


@router.callback_query(F.data == "admin:status")
async def admin_status(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    await safe_edit(call.message, await build_status_text(call.bot), reply_markup=kb.admin_menu_kb())
    await call.answer()


@router.message(Command("help"))
@router.message(F.text == "❓ Yordam")
async def cmd_help(message: Message):
    await message.answer(_help_text(), reply_markup=kb.help_kb())


@router.message(Command("webapp"))
async def cmd_webapp(message: Message):
    weburl = config.get_settings().get("webapp_url") or config.WEBAPP_URL
    if not weburl:
        await message.answer("⚠️ Webapp hozir mavjud emas.")
        return
    await message.answer(
        "🌐 <b>DonateFM Mini App</b>",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🛍 Mini App'ni ochish", web_app=WebAppInfo(url=weburl))]
            ]
        ),
    )


@router.callback_query(F.data == "faq:main")
async def faq_main(call: CallbackQuery):
    await safe_edit(call.message, _help_text(), reply_markup=kb.help_kb())
    await call.answer()


@router.callback_query(F.data.startswith("faq:"))
async def faq_item(call: CallbackQuery):
    key = call.data.split(":", 1)[1]
    text = _faq_texts().get(key)
    if not text:
        await call.answer()
        return
    await safe_edit(call.message, text, reply_markup=kb.help_back_kb())
    await call.answer()


@router.message(F.text == "📧 Murojaat")
async def support_start(message: Message, state: FSMContext):
    if not await _ensure_not_banned(message): return
    await state.set_state(SupportStates.awaiting_message)
    await message.answer(
        "📧 <b>Murojaat</b>\n\nSavolingizni yozing — admin sizga javob beradi.\n\n"
        "<i>(/cancel — bekor qilish)</i>",
        reply_markup=kb.cancel_kb(),
    )


@router.callback_query(F.data == "support:start")
async def support_start_cb(call: CallbackQuery, state: FSMContext):
    if not await _ensure_not_banned(call): return
    await state.set_state(SupportStates.awaiting_message)
    await safe_edit(call.message,
        "📧 <b>Murojaat</b>\n\nSavolingizni yozing — admin sizga javob beradi.\n\n"
        "<i>(/cancel — bekor qilish)</i>")
    await call.answer()


@router.callback_query(F.data.startswith("admin_reply:"))
async def admin_reply_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    try:
        uid = int(call.data.split(":")[1])
    except (ValueError, IndexError):
        return
    await state.set_state(AdminStates.replying_user)
    await state.update_data(reply_target=uid)
    await safe_edit(call.message,
        f"✉️ Foydalanuvchi <code>{uid}</code> ga javobni yozing.\n"
        "<i>(yuborish uchun pastga yozing, bekor qilish: /cancel)</i>",
        reply_markup=kb.back_admin_menu_kb())
    await call.answer()


@router.callback_query(F.data.startswith("admin_reseller:"))
async def admin_reseller_toggle(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    parts = call.data.split(":")
    try:
        uid, val = int(parts[1]), int(parts[2])
    except (ValueError, IndexError):
        return
    await db.set_user_reseller(uid, val)
    user = await db.get_user(uid)
    if not user:
        await call.answer("Topilmadi", show_alert=True)
        return
    is_res = bool(user["reseller"]) if "reseller" in user else False
    await safe_edit(call.message,
        ls.user_profile_text(user),
        reply_markup=kb.user_view_kb(uid, bool(user["is_banned"]), is_res))
    await call.answer("✅ Sotuvchi" if val else "✅ Oddiy foydalanuvchi", show_alert=True)


# ================== ADMIN PANEL ==================

@router.message(Command("admin"))
async def admin_panel(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Sizda admin huquqi yo'q.")
        return
    await state.set_state(AdminStates.search_query)
    await message.answer(ls.admin_menu_text(_lang(message)), reply_markup=kb.admin_menu_kb())


@router.callback_query(F.data == "admin:menu")
async def admin_menu_cb(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    await state.clear()
    await safe_edit(call.message, ls.admin_menu_text(_lang(call)), reply_markup=kb.admin_menu_kb())
    await call.answer()


@router.callback_query(F.data == "admin:stats")
async def admin_stats(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    s = await db.get_stats()
    await safe_edit(call.message, ls.admin_stats_text(s, _lang(call)), reply_markup=kb.back_home_kb())
    await call.answer()


@router.callback_query(F.data == "admin:orders")
async def admin_orders(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    orders = await db.get_pending_orders()
    if not orders:
        await safe_edit(call.message, "📦 Buyurtmalar yo'q ✅", reply_markup=kb.admin_menu_kb())
        await call.answer()
        return
    await safe_edit(call.message, "📦 <b>Kutilayotgan buyurtmalar</b>:", reply_markup=kb.orders_list_kb(orders))
    await call.answer()


@router.callback_query(F.data.startswith("admin_order_view:"))
async def admin_order_view(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    order_id = int(call.data.split(":")[1])
    o = await db.get_order(order_id)
    if not o:
        await call.answer("Topilmadi", show_alert=True)
        return
    await safe_edit(call.message, ls.admin_order_text(o, _lang(call)), reply_markup=kb.order_admin_kb(order_id, o["game_id"]))
    await call.answer()


@router.callback_query(F.data.startswith("admin_order_ok:"))
async def admin_order_ok(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    order_id = int(call.data.split(":")[1])
    o = await db.get_order(order_id)
    if not o:
        await call.answer("Topilmadi", show_alert=True)
        return
    if o["status"] != "kutilmoqda":
        await call.answer(f"Holat: {o['status']}", show_alert=True)
        return
    await db.set_order_status(order_id, "bajarildi")
    await order_notify.notify_user(call.bot, o, "bajarildi", lang=_lang(call))
    await safe_edit(call.message, 
        "✅ Buyurtma bajarildi deb belgilandi.",
        reply_markup=kb.admin_menu_kb(),
    )
    await call.answer("Bajarildi ✅")


@router.callback_query(F.data.startswith("admin_order_refund:"))
async def admin_order_refund(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    order_id = int(call.data.split(":")[1])
    o = await db.get_order(order_id)
    if not o:
        await call.answer("Topilmadi", show_alert=True)
        return
    if o["status"] == "rad_etildi":
        await call.answer("Bu buyurtma allaqachon rad etilgan", show_alert=True)
        return
    if o["status"] == "to'lov_kutilmoqda":
        await call.answer("To'lov hali tasdiqlanmagan", show_alert=True)
        return
    await db.set_order_status(order_id, "rad_etildi")
    await db.refund_balance(o["user_id"], o["price"], ref=str(order_id))
    await order_notify.notify_user(
        call.bot, o, "rad_etildi", detail=ls.order_reason_admin(_lang(call)), lang=_lang(call)
    )
    await safe_edit(call.message, 
        "↩️ Buyurtma rad etildi, pul qaytarildi.",
        reply_markup=kb.admin_menu_kb(),
    )
    await call.answer("Rad etildi")


@router.callback_query(F.data == "admin:payments")
async def admin_payments(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    payments = await db.get_confirmable_payments()
    if not payments:
        await safe_edit(call.message, 
            "💳 Kutilayotgan to'lovlar yo'q ✅",
            reply_markup=kb.admin_menu_kb(),
        )
        await call.answer()
        return
    MARK = {"kutilmoqda": "⏳", "rad_etildi": "❌", "tasdiqlandi": "✅", "qaytarildi": "↩️"}
    lines = ["💳 <b>To'lovlar jadvali</b>\n"]
    for p in payments[:12]:
        mark = MARK.get(p["status"], "•")
        when = str(p["created_at"] or "")[-5:]
        lines.append(
            f"{mark} <code>#{p['id']}</code> · {format_price(p['amount'] or 0)} so'm · "
            f"{p['method']} · <code>{p['user_id']}</code> · {when}"
        )
    lines.append(f"\n📊 Jami: <b>{len(payments)}</b> ta")
    await safe_edit(call.message, 
        "\n".join(lines),
        reply_markup=kb.payments_list_kb(payments),
    )
    await call.answer()


@router.callback_query(F.data.startswith("admin_pay_view:"))
async def admin_pay_view(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    payment_id = int(call.data.split(":")[1])
    p = await db.get_payment(payment_id)
    if not p:
        await call.answer("To'lov topilmadi (o'chirilgan yoki mavjud emas)", show_alert=True)
        try:
            await call.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        return
    await safe_edit(call.message, ls.admin_payment_text(p, _lang(call)), reply_markup=kb.payment_view_kb(payment_id))
    await call.answer()


@router.callback_query(F.data.startswith("admin_pay_ok:"))
async def admin_pay_ok(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    payment_id = int(call.data.split(":")[1])
    p = await db.get_payment(payment_id)
    if not p:
        await call.answer("To'lov topilmadi (o'chirilgan yoki mavjud emas)", show_alert=True)
        try:
            await call.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        return
    if p["status"] not in ("kutilmoqda", "rad_etildi"):
        await call.answer("Bu to'lov allqachon hal qilingan", show_alert=True)
        return
    if p["method"] == "refund":
        await call.answer("Bu qaytaruv to'lovi — tasdiqlab bo'lmaydi", show_alert=True)
        return
    late = p["status"] == "rad_etildi"
    late_note = "\n<i>(Muddati o'tgan edi — kech tasdiqlandi)</i>" if late else ""
    
    # Loading animation
    await call.message.edit_text("⏳ <b>To'lov tasdiqlanmoqda...</b> ", reply_markup=None)
    await asyncio.sleep(0.3)
    
    # Buyurtma bilan bog'liq to'lov (ref = ord:{order_id})
    if p["ref"] and p["ref"].startswith("ord:"):
        order_id = int(p["ref"].split(":")[1])
        o = await db.get_order(order_id)
        if not o or o["user_id"] != p["user_id"]:
            await call.answer("Buyurtma topilmadi", show_alert=True)
            return
        if o["status"] not in ("to'lov_kutilmoqda", "rad_etildi"):
            await call.answer("Buyurtma holati o'zgargan", show_alert=True)
            return
        await db.set_payment_status(payment_id, "tasdiqlandi")
        await db.set_order_status(order_id, "kutilmoqda")
        game = kb.find_game(o["platform"]) or {"name": o["platform"]}
        await order_notify.notify_user(call.bot, o, "kutilmoqda", lang=_lang(call))
        for admin_id in _admin_ids_cache:
            try:
                await call.bot.send_message(
                    admin_id,
                    f"🎉 <b>To'lov keldi, buyurtma tayyor!</b>\n\n"
                    f"📦 Buyurtma: <code>#{order_id}</code>\n"
                    f"🎮 {game['name']} — {o['package_name']}\n"
                    f"🆔 O'yin ID: <code>{o['game_id']}</code>\n"
                    f"👤 Mijoz: <code>{p['user_id']}</code>\n"
                    f"💰 {format_price(p['amount'])} so'm\n\n"
                    f"Endi mahsulotni yuboring:",
                    reply_markup=kb.order_admin_kb(order_id),
                )
            except Exception:
                pass
        await animations.animate_success(call.message, 
            f"✅ To'lov #{payment_id} tasdiqlandi. Buyurtma #{order_id} kutilmoqda." + late_note
        )
        await call.answer("Tasdiqlandi ✅")
        return

    # Oddiy hisob to'ldirish (manual topup)
    ok = await db.confirm_payment(payment_id, p["user_id"], p["amount"])
    if not ok:
        await call.answer("Tasdiqlab bo'lmadi — holat o'zgargan", show_alert=True)
        return
    try:
        await call.bot.send_message(
            p["user_id"],
            f"✅ <b>To'lovingiz tasdiqlandi!</b>\n\n"
            f"Summa: <b>{format_price(p['amount'])} so'm</b> "
            f"balansingizga qo'shildi.",
        )
    except Exception:
        pass
    await animations.animate_success(call.message, 
        f"✅ To'lov #{payment_id} tasdiqlandi. Foydalanuvchi balansiga <b>{format_price(p['amount'])} so'm</b> qo'shildi." + late_note
    )
    await call.answer("Tasdiqlandi ✅")


@router.callback_query(F.data.startswith("admin_pay_no:"))
async def admin_pay_no(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    payment_id = int(call.data.split(":")[1])
    p = await db.get_payment(payment_id)
    if not p:
        await call.answer("To'lov topilmadi (o'chirilgan yoki mavjud emas)", show_alert=True)
        try:
            await call.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        return
    if p["status"] != "kutilmoqda":
        await call.answer("Bu to'lov allaqachon hal qilingan", show_alert=True)
        return
    await db.set_payment_status(payment_id, "rad_etildi")
    try:
        await call.bot.send_message(
            p["user_id"],
            f"❌ To'lov rad etildi.\nTo'lov: #{payment_id}\n"
            f"Agar xato bo'lsa, admin bilan bog'laning.",
        )
    except Exception:
        pass
    await safe_edit(call.message, 
        f"❌ To'lov #{payment_id} rad etildi.",
        reply_markup=kb.admin_menu_kb(),
    )
    await call.answer("Rad etildi")


@router.callback_query(F.data == "admin:users")
async def admin_users(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    users = await db.get_all_users()
    if not users:
        await safe_edit(call.message, 
            "👥 Foydalanuvchilar yo'q.", reply_markup=kb.admin_menu_kb()
        )
        await call.answer()
        return
    await safe_edit(call.message, 
        "👥 <b>Foydalanuvchilar</b>:",
        reply_markup=kb.users_list_kb(users),
    )
    await call.answer()


@router.callback_query(F.data.startswith("admin_ub_"))
async def admin_ub_change(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        await call.answer()
        return
    parts = call.data.split(":")
    action = parts[0].replace("admin_ub_", "")  # plus or minus
    target = int(parts[1])
    await state.set_state(AdminStates.entering_balance)
    await state.update_data(target_user=target, action=action)
    verb = "qo'shish" if action == "plus" else "kamaytirish"
    await call.message.answer(f"💠 {verb} uchun summa kiriting (so'm):")
    await call.answer()


# ================== ADMIN EXTENDED ==================

@router.callback_query(F.data == "admin:add_balance")
async def admin_add_balance_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.set_state(AdminStates.choosing_user)
    await safe_edit(call.message, 
        "💠 Balans qo'shish.\n\nFoydalanuvchi ID yoki @username kiriting:",
        reply_markup=kb.back_admin_menu_kb(),
    )
    await call.answer()


@router.message(AdminStates.choosing_user)
async def admin_choose_user(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    q = (message.text or "").strip().lstrip("@")
    users = await db.search_users(q)
    if not users:
        await message.answer("❌ Foydalanuvchi topilmadi. /admin orqali qaytib urinib ko'ring.")
        await state.clear()
        return
    u = users[0]
    await state.set_state(AdminStates.entering_balance)
    await state.update_data(target_user=u["user_id"], action="plus")
    await message.answer(
        f"👤 <b>{u['full_name'] or u['user_id']}</b> (@{u['username'] or '-'})\n"
        f"💰 Hozirgi balans: <b>{format_price(u['balance'])} so'm</b>\n\n"
        f"Qo'shish uchun summa kiriting:"
    )


@router.callback_query(F.data == "admin:search")
async def admin_search_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.set_state(AdminStates.search_query)
    await safe_edit(call.message, 
        ls.admin_search_prompt(_lang(call)), reply_markup=kb.back_admin_menu_kb()
    )
    await call.answer()


@router.message(AdminStates.search_query)
async def admin_search_do(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    q = (message.text or "").strip()
    if "t.me/" in q:
        q = q.split("t.me/", 1)[1].split("/", 1)[0].split("?", 1)[0]
    q = q.lstrip("@").strip()
    users = await db.search_users(q)
    if not users:
        await message.answer("🔎 Hech narsa topilmadi. Boshqa so'rov yozing yoki /admin.", reply_markup=kb.back_admin_menu_kb())
        return
    await message.answer(
        f"🔎 <b>{len(users)} ta natija</b> \"{q}\":",
        reply_markup=kb.users_list_kb(users),
    )


@router.callback_query(F.data.startswith("admin_user_view:"))
async def admin_user_view(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer()
        return
    user_id = int(call.data.split(":")[1])
    user = await db.get_user(user_id)
    if not user:
        await call.answer("Topilmadi", show_alert=True)
        return
    await safe_edit(call.message, 
        ls.user_profile_text(user),
        reply_markup=kb.user_view_kb(user_id, bool(user["is_banned"]),
                                   bool(user["reseller"]) if "reseller" in user else False),
    )
    await call.answer()


@router.callback_query(F.data.startswith("admin_ban:"))
async def admin_ban(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    _, user_id, ban = call.data.split(":")
    user_id, ban = int(user_id), int(ban)
    await db.set_user_ban(user_id, ban)
    user = await db.get_user(user_id)
    if not user:
        await call.answer("Foydalanuvchi topilmadi", show_alert=True)
        return
    await safe_edit(call.message,
        ls.user_profile_text(user),
        reply_markup=kb.user_view_kb(user_id, bool(user["is_banned"]),
                                   bool(user["reseller"]) if "reseller" in user else False),
    )
    await call.answer("✅" if ban else "✅ Ban o'chirildi")


# ---------------- BROADCAST ----------------

@router.callback_query(F.data == "admin:broadcast")
async def admin_broadcast_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.set_state(AdminStates.broadcast_text)
    await safe_edit(call.message,
        ls.broadcast_start_text(_lang(call)), reply_markup=kb.back_admin_menu_kb()
    )
    await call.answer()


@router.message(AdminStates.broadcast_text)
async def admin_broadcast_capture(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    text = message.text or message.caption or ""
    if not text.strip():
        await message.answer("⚠️ Matn kiriting yoki /cancel.")
        return
    users = await db.get_all_user_ids()
    await state.update_data(broadcast_msg=text)
    await state.set_state(AdminStates.entering_notice)
    preview_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Yuborish", callback_data="broadcast_go")],
            [InlineKeyboardButton(text="❌ Bekor", callback_data="broadcast_cancel")],
        ]
    )
    await message.answer(
        f"{ls.broadcast_preview_text(len(users), _lang(message))}\n\n<i>{text[:200]}</i>",
        reply_markup=preview_kb,
    )


@router.callback_query(F.data == "broadcast_go")
async def broadcast_go(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    data = await state.get_data()
    text = data.get("broadcast_msg", "")
    photo_id = data.get("broadcast_photo")
    await state.clear()
    await safe_edit(call.message, "📤 <b>Yuborilmoqda...</b>")
    users = await db.get_all_user_ids()
    ok = 0
    for uid in users:
        try:
            if photo_id:
                await call.bot.send_photo(uid, photo=photo_id, caption=text)
            else:
                await call.bot.send_message(uid, text)
            ok += 1
            await asyncio.sleep(0.05)
        except Exception:
            pass
    await safe_edit(call.message, 
        f"📢 Reklama yuborildi: <b>{ok}/{len(users)}</b>",
        reply_markup=kb.back_admin_menu_kb(),
    )
    await call.answer("Tayyor ✅")


@router.callback_query(F.data == "broadcast_cancel")
async def broadcast_cancel(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        await call.answer()
        return
    await state.clear()
    await safe_edit(call.message, "❌ Bekor qilindi.", reply_markup=kb.admin_menu_kb())
    await call.answer()


# ---------------- PROMOCODES ----------------

@router.callback_query(F.data == "admin:promos")
async def admin_promos(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    promos = await db.list_promos()
    await safe_edit(call.message, 
        "🎁 <b>Promokodlar</b>",
        reply_markup=kb.promo_list_kb(promos),
    )
    await call.answer()


@router.callback_query(F.data == "admin_promo_new")
async def admin_promo_new(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.set_state(AdminStates.promo_code)
    await safe_edit(call.message, 
        "🎁 <b>Yangi promokod</b>\n\nKod kiriting (masalan: DONATE2026):",
        reply_markup=kb.back_admin_menu_kb(),
    )
    await call.answer()


@router.callback_query(F.data == "admin:features")
async def admin_features(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    await safe_edit(call.message,
        "⚙️ <b>Funksiyalar</b>\n\n"
        "✅ = yoqiq · ❌ = o'chirilgan\n\n"
        "O'zgartirish uchun tugmani bosing.",
        reply_markup=kb.features_kb())
    await call.answer()


_FEATURE_LABELS = {
    "auto_delivery_enabled": "🚚 Avtomatik yetkazish",
    "ocr_enabled": "🔍 Chek OCR tekshiruv",
    "nickname_check_enabled": "👤 O'yinchi nomini ko'rsatish",
    "id_validation_enabled": "🔢 ID format tekshiruv",
    "chek_reminder_enabled": "⏰ Chek eslatmasi",
    "maintenance": "🔧 Texnik ishlar rejimi",
}


@router.callback_query(F.data.startswith("admin:toggle:"))
async def admin_toggle_feature(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    key = call.data.split(":", 2)[2]
    if key not in _FEATURE_LABELS:
        await call.answer("Noma'lum funksiya", show_alert=True)
        return
    new_val = config.toggle_setting(key)
    label = _FEATURE_LABELS[key]
    state_txt = "yoqildi ✅" if new_val else "o'chirildi ❌"
    if key == "maintenance":
        state_txt = "yoqildi ✅ (foydalanuvchilar texnik ishlar rejimida)" if new_val else "o'chirildi ❌ (do'kon ochiq)"
    await call.answer(f"{label}: {state_txt}", show_alert=True)
    await safe_edit(call.message,
        "⚙️ <b>Funksiyalar</b>\n\n"
        "✅ = yoqiq · ❌ = o'chirilgan\n\n"
        "O'zgartirish uchun tugmani bosing.",
        reply_markup=kb.features_kb())


@router.callback_query(F.data == "admin:provider_link")
async def admin_provider_link(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.set_state(AdminStates.provider_url)
    await safe_edit(call.message,
        "🔌 <b>Provider API ulash</b>\n\n"
        "<b>1-qadam:</b> provayder API manzilini yuboring.\n"
        "<code>https://api.example.com</code>\n\n"
        "Shartnoma: shu manzilga <code>POST /verify</code> va <code>POST /fulfill</code>.\n\n"
        "Bekor qilish: /cancel",
        reply_markup=kb.back_admin_menu_kb())
    await call.answer()


@router.message(AdminStates.provider_url)
async def admin_provider_url(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    url = (message.text or "").strip().rstrip("/")
    if not (url.startswith(("http://", "https://"))):
        await message.answer("❌ Manzil <code>http</code> yoki <code>https</code> bilan boshlanishi kerak.\nQayta yuboring yoki /cancel.")
        return
    config.update_settings({"delivery_api_url": url})
    await state.set_state(AdminStates.provider_key)
    await message.answer(
        "🔑 <b>2-qadam: API kalitini yuboring</b>\n\n"
        "Kalitni shu yerga yozing. U faqat shu serverda saqlanadi.\n"
        "Bekor qilish: /cancel"
    )


@router.message(AdminStates.provider_key)
async def admin_provider_key(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    key = (message.text or "").strip()
    await state.clear()
    if not key:
        await message.answer("❌ Kalit bo'sh — provider ulanmadi.")
        return
    config.update_settings({"delivery_api_key": key, "delivery_provider": "custom"})
    import delivery as dlv
    result = await dlv.test_provider()
    await message.answer(
        "✅ <b>Provider saqlandi!</b>\n\n"
        f"🔌 URL: <code>{config.get_settings().get('delivery_api_url', '')}</code>\n"
        f"🧪 Tekshiruv: {result}\n\n"
        "Buyurtmalar endi avtomatik yuboriladi (har 30 soniyada).\n"
        "Xato bo'lsa — avval «🧪 Provider test» ni bosing."
    )


@router.callback_query(F.data == "admin:provider_test")
async def admin_provider_test(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    import delivery as dlv
    await call.answer("⏳ Tekshirilyapti...", show_alert=False)
    result = await dlv.test_provider()
    await call.message.answer(f"🧪 <b>Provider test</b>\n\n{result}")


@router.message(AdminStates.promo_code)
async def admin_promo_code(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    code = (message.text or "").strip()
    if not code:
        return
    await state.update_data(promo_code=code)
    await state.set_state(AdminStates.promo_reward)
    await message.answer("💠 Foydalanuvchi balansiga qo'shiladigan <b>so'm</b> miqdori:")


@router.message(AdminStates.promo_reward)
async def admin_promo_reward(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    try:
        reward = int((message.text or "").strip().replace(" ", "").replace(",", ""))
    except ValueError:
        await message.answer("❌ To'g'ri raqam kiriting.")
        return
    await state.update_data(promo_reward=reward)
    await state.set_state(AdminStates.promo_max)
    await message.answer("🔢 Foydalanish limiti (son):")


@router.message(AdminStates.promo_max)
async def admin_promo_max(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    try:
        max_uses = int((message.text or "").strip())
    except ValueError:
        await message.answer("❌ To'g'ri raqam kiriting.")
        return
    await state.update_data(promo_max=max_uses)
    await state.set_state(AdminStates.promo_expiry)
    await message.answer(
        "📅 Amal qilish muddati (YYYY-MM-DD) yoki 'yo'q':"
    )


@router.message(AdminStates.promo_expiry)
async def admin_promo_expiry(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    data = await state.get_data()
    expiry = (message.text or "").strip()
    if expiry.lower() in ("yo'q", "no", "0", "-"):
        expiry = ""
    await db.create_promo(
        data["promo_code"], data["promo_reward"], data["promo_max"], expiry
    )
    await state.clear()
    await message.answer(
        f"✅ Promokod yaratildi!\n\n"
        f"Kod: <b>{data['promo_code']}</b>\n"
        f"Bonus: <b>{format_price(data['promo_reward'])} so'm</b>\n"
        f"Limit: {data['promo_max']} ta"
    )


@router.callback_query(F.data.startswith("admin_promo_view:"))
async def admin_promo_view(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    code = call.data.split(":", 2)[1]
    p = await db.get_promo(code)
    if not p:
        await call.answer("Topilmadi", show_alert=True)
        return
    await safe_edit(call.message, 
        f"🎁 <b>{code}</b>\n\n"
        f"Bonus: <b>{format_price(p['reward_amount'])} so'm</b>\n"
        f"Ishlatilgan: <b>{p['used_count']}/{p['max_uses']}</b>\n"
        f"Muddati: {p['expires_at'] or 'cheksiz'}\n"
        f"Yaratilgan: {p['created_at']}",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"admin_promo_del:{code}")],
                [InlineKeyboardButton(text="🔙 Ro'yxat", callback_data="admin:promos")],
            ]
        ),
    )
    await call.answer()


@router.callback_query(F.data.startswith("admin_promo_del:"))
async def admin_promo_del(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    code = call.data.split(":", 2)[1]
    conn = await db.get_connection()
    await conn.execute("DELETE FROM promocodes WHERE code = ?", (code,))
    await conn.commit()
    await conn.close()
    promos = await db.list_promos()
    await safe_edit(call.message, "🎁 <b>Promokodlar</b>", reply_markup=kb.promo_list_kb(promos))
    await call.answer("O'chirildi ✅")


# ---------------- DELIVERY ----------------

@router.callback_query(F.data == "admin:delivery")
async def admin_delivery(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    cfg = config.get_delivery_config()
    pending = await db.get_pending_orders()
    await safe_edit(call.message, 
        ls.delivery_status_text(cfg, len(pending), _lang(call)),
        reply_markup=kb.delivery_kb(len(pending), cfg["provider"]),
    )
    await call.answer()


@router.callback_query(F.data == "admin_delivery_retry")
async def admin_delivery_retry(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer()
        return
    import delivery

    res = await delivery.process_pending_orders(call.bot)
    pending = await db.get_pending_orders()
    if res:
        await call.answer(f"{res} ta ishlandi")
    else:
        await call.answer("Provider sozlanmagan yoki hammasi yuborildi")
    cfg = config.get_delivery_config()
    await safe_edit(call.message, 
        ls.delivery_status_text(cfg, len(pending), _lang(call)),
        reply_markup=kb.delivery_kb(len(pending), cfg["provider"]),
    )


@router.callback_query(F.data.startswith("admin_send_delivery:"))
async def admin_send_delivery(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    import delivery

    order_id = int(call.data.split(":")[1])
    order = await db.get_order(order_id)
    if not order:
        await call.answer("Topilmadi", show_alert=True)
        return
    await safe_edit(call.message, f"🚚 Buyurtma #{order_id} yuborilmoqda...", reply_markup=None)
    res = await delivery.deliver_order(order)
    p = delivery.order_parts(order)
    msgs = {
        "done": f"✅ #{order_id} avtomatik yuborildi! ({p['package']} → {p['player']})",
        "fail": f"❌ #{order_id}: {res['msg']}",
        "error": f"⚠️ #{order_id} xato: {res['msg'][:120]}",
        "manual": f"ℹ️ #{order_id}: provider sozlanmagan. 'Bajarildi' tugmasini bosing.",
        "skip": f"ℹ️ #{order_id}: holat yangi emas.",
    }
    await safe_edit(call.message, 
        msgs.get(res["status"], str(res)), reply_markup=kb.back_admin_menu_kb()
    )
    await call.answer()


@router.callback_query(F.data == "admin_set_provider")
async def admin_set_provider(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    await safe_edit(call.message, 
        "🚚 <b>Provider tanlang</b>",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="ℹ️ Qo'lda (manual)", callback_data="set_provider:manual")],
                [InlineKeyboardButton(text="🔌 O'z HTTP API", callback_data="set_provider:custom")],
                [InlineKeyboardButton(text="🇺🇿 Baulu API", callback_data="set_provider:baulu")],
                [InlineKeyboardButton(text="🌐 LiveOP API", callback_data="set_provider:liveop")],
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin:delivery")],
            ]
        ),
    )
    await call.answer()


@router.callback_query(F.data.startswith("set_provider:"))
async def set_provider_do(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer()
        return
    provider = call.data.split(":", 1)[1]
    config.update_settings({"delivery_provider": provider})
    cfg = config.get_delivery_config()
    pending = await db.get_pending_orders()
    await safe_edit(call.message, 
        f"✅ Provider: <b>{provider}</b> sozlandi.\n\n"
        + ls.delivery_status_text(cfg, len(pending), _lang(call)),
        reply_markup=kb.delivery_kb(len(pending), cfg["provider"]),
    )
    await call.answer()


# ---------------- SETTINGS (ADMIN) ----------------

@router.callback_query(F.data == "admin:settings")
async def admin_settings(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    await safe_edit(call.message, 
        ls.admin_settings_text(config.get_settings(), _lang(call)),
        reply_markup=kb.settings_kb(),
    )
    await call.answer()


@router.callback_query(F.data.startswith("admin:set:"))
async def admin_set_key(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    key = call.data.split(":", 2)[2]
    if key == "webapp_url":
        config.update_settings(
            {"webapp_url": config.get_settings().get("webapp_url", "")}
        )
        await safe_edit(call.message, 
            "🌐 Joriy webapp URL avtomatik tunnel orqali o'rnatiladi.\n"
            "Qo'lda o'zgartirish: <code>/set webapp_url &lt;url&gt;</code>",
            reply_markup=kb.back_admin_menu_kb(),
        )
        await call.answer()
        return
    await state.set_state(AdminStates.settings_value)
    await state.update_data(settings_key=key)
    labels = {
        "card_active": "💳 Faol karta: <code>uzcard</code>, <code>humo</code>, <code>tbc</code> yoki <code>uzum</code>",
        "star_rate_1000": "⭐️ 1000 Stars uchun so'm:",
        "keshbek_percent": "💰 Keshbek % (masalan 10):",
        "referral_reward_topup_percent": "🤝 Referral % (masalan 5):",
        "reseller_percent": "🏪 Sotuvchi % (masalan 10):",
        "announcement": "📢 E'lon matni (/start da ko'rinadi):",
        "delivery_provider": "🚚 Provider: manual/custom/baulu/liveop",
    }
    await safe_edit(call.message, 
        f"✏️ {labels.get(key, key)} qiymatini yuboring:",
        reply_markup=kb.back_admin_menu_kb(),
    )
    await call.answer()


@router.callback_query(F.data == "admin:set_other")
async def admin_set_other(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.set_state(AdminStates.settings_key)
    await safe_edit(call.message, 
        "✏️ Kalit nomini yuboring (masalan: min_topup_card, delivery_api_url, delivery_api_key):",
        reply_markup=kb.back_admin_menu_kb(),
    )
    await call.answer()


@router.message(AdminStates.settings_key)
async def admin_settings_key(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    key = (message.text or "").strip()
    await state.update_data(settings_key=key)
    await state.set_state(AdminStates.settings_value)
    await message.answer(f"<code>{key}</code> uchun qiymat kiriting:")


@router.message(AdminStates.settings_value)
async def admin_settings_value(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    data = await state.get_data()
    key = data.get("settings_key", "")
    value = (message.text or "").strip()
    await state.clear()
    config.update_settings({key: value})
    await message.answer(
        f"✅ <b>{key}</b> = <code>{value}</code>\n\n"
        f"Joriy sozlamalar:",
        reply_markup=kb.settings_kb(),
    )


# ================== KATALOG (ADMIN) ==================

def _cat_money(v):
    try:
        return f"{int(v or 0):,}".replace(",", " ")
    except (TypeError, ValueError):
        return str(v)


def _cat_list_text():
    games = catalog.load_games()
    total = sum(len(g.get("packages") or []) for g in games)
    return (
        "📚 <b>Katalog boshqaruvi</b>\n\n"
        f"🎮 O'yinlar: <b>{len(games)}</b>\n"
        f"📦 Paketlar: <b>{total}</b>\n\n"
        "O'yinni tanlang 👇"
    )


def _cat_game_text(g):
    pkgs = g.get("packages") or []
    cats = ", ".join((g.get("categories") or {}).values()) or "—"
    lines = [
        f"🎮 <b>{g.get('emoji', '')} {g.get('name', '')}</b>",
        f"🆔 ID: <code>{g['id']}</code>",
        f"📝 {g.get('desc') or '—'}",
        f"🧩 {cats}",
        f"📦 Paketlar: <b>{len(pkgs)}</b>",
        "",
    ]
    for p in pkgs:
        lines.append(
            f"• <code>{p.get('id')}</code> {p.get('name')} — {_cat_money(p.get('price'))} so'm"
        )
    return "\n".join(lines)


def _cat_pkg_text(g, p):
    return (
        f"📦 <b>{p.get('name')}</b>\n\n"
        f"🆔 Paket ID: <code>{p.get('id')}</code>\n"
        f"🎮 O'yin: <code>{g['id']}</code> — {g.get('name')}\n"
        f"🔢 Miqdor: <b>{p.get('amount')}</b>\n"
        f"💰 Narx: <b>{_cat_money(p.get('price'))} so'm</b>\n"
        f"🧩 Kategoriya: <code>{p.get('category') or 'all'}</code>"
    )


async def _cat_open(call, game_id=None):
    g = catalog.find_game(game_id) if game_id else None
    if not g:
        await safe_edit(call.message, _cat_list_text(), reply_markup=kb.catalog_kb())
        return
    await safe_edit(
        call.message,
        _cat_game_text(g),
        reply_markup=kb.catalog_game_kb(g["id"], g.get("packages") or []),
    )


@router.callback_query(F.data == "admin:catalog")
async def admin_catalog(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    await _cat_open(call)
    await call.answer()


@router.callback_query(F.data.startswith("admin:cat_game_add"))
async def admin_cat_game_add(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.set_state(AdminStates.catalog_game)
    await safe_edit(
        call.message,
        "➕ <b>Yangi o'yin</b>\n\n"
        "Quyidagi formatda yuboring:\n"
        "<code>ID | Nomi | Emoji | Tavsif</code>\n\n"
        "Misol: <code>ml | Mobile Legends | 🎮 | Molchilar va Skinlar</code>",
        reply_markup=kb.back_admin_menu_kb(),
    )
    await call.answer()


@router.callback_query(F.data.startswith("admin:catg_edit:"))
async def admin_cat_game_edit(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    game_id = call.data.split(":", 3)[2]
    g = catalog.find_game(game_id)
    if not g:
        await call.answer("O'yin topilmadi", show_alert=True)
        await _cat_open(call)
        return
    await state.set_state(AdminStates.catalog_game_edit)
    await state.update_data(game_id=game_id)
    await safe_edit(
        call.message,
        f"✏️ <b>O'yinni tahrirlash: {g.get('name')}</b>\n\n"
        "Quyidagi formatda yuboring:\n"
        "<code>Nomi | Tavsif</code>\n\n"
        f"Joriy: <code>{g.get('name')} | {g.get('desc') or ''}</code>",
        reply_markup=kb.back_admin_menu_kb(),
    )
    await call.answer()


@router.callback_query(F.data.startswith("admin:catg_del:"))
async def admin_cat_game_del(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    game_id = call.data.split(":", 3)[2]
    if not catalog.delete_game(game_id):
        await call.answer("O'yin topilmadi", show_alert=True)
    else:
        await call.answer(f"{game_id} o'chirildi", show_alert=True)
    await _cat_open(call)


@router.callback_query(F.data.startswith("admin:catp_add:"))
async def admin_cat_pkg_add(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    game_id = call.data.split(":", 3)[2]
    if not catalog.find_game(game_id):
        await call.answer("O'yin topilmadi", show_alert=True)
        await _cat_open(call)
        return
    await state.set_state(AdminStates.catalog_pkg)
    await state.update_data(game_id=game_id)
    await safe_edit(
        call.message,
        f"➕ <b>Yangi paket: {game_id}</b>\n\n"
        "Quyidagi formatda yuboring:\n"
        "<code>Nomi | Miqdor | Narx | Kategoriya</code>\n\n"
        "Kategoriya ixtiyoriy (bo'sh qoldirsa <code>all</code>).\n"
        "Misol: <code>720 Diamonds | 720 | 74990 | diamond</code>",
        reply_markup=kb.back_admin_menu_kb(),
    )
    await call.answer()


@router.callback_query(F.data.startswith("admin:catp_price:"))
async def admin_cat_pkg_price(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    _, _, game_id, pkg_id = call.data.split(":", 3)
    g = catalog.find_game(game_id)
    p = next((x for x in (g.get("packages") or []) if x.get("id") == pkg_id), None) if g else None
    if not p:
        await call.answer("Paket topilmadi", show_alert=True)
        await _cat_open(call, game_id)
        return
    await state.set_state(AdminStates.catalog_pkg_price)
    await state.update_data(game_id=game_id, pkg_id=pkg_id)
    await safe_edit(
        call.message,
        f"💰 <b>{p.get('name')}</b> — joriy narx: <b>{_cat_money(p.get('price'))} so'm</b>\n\n"
        "Yangi narxni raqamda yuboring:",
        reply_markup=kb.back_admin_menu_kb(),
    )
    await call.answer()


@router.callback_query(F.data.startswith("admin:catp_name:"))
async def admin_cat_pkg_name(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    _, _, game_id, pkg_id = call.data.split(":", 3)
    g = catalog.find_game(game_id)
    p = next((x for x in (g.get("packages") or []) if x.get("id") == pkg_id), None) if g else None
    if not p:
        await call.answer("Paket topilmadi", show_alert=True)
        await _cat_open(call, game_id)
        return
    await state.set_state(AdminStates.catalog_pkg_name)
    await state.update_data(game_id=game_id, pkg_id=pkg_id)
    await safe_edit(
        call.message,
        f"✏️ <b>{p.get('name')}</b> — yangi nomni yuboring:",
        reply_markup=kb.back_admin_menu_kb(),
    )
    await call.answer()


@router.callback_query(F.data.startswith("admin:catp_del:"))
async def admin_cat_pkg_del(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    _, _, game_id, pkg_id = call.data.split(":", 3)
    if not catalog.delete_package(game_id, pkg_id):
        await call.answer("Paket topilmadi", show_alert=True)
    else:
        await call.answer("Paket o'chirildi", show_alert=True)
    await _cat_open(call, game_id)


@router.callback_query(F.data.startswith("admin:catp:"))
async def admin_cat_pkg_view(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    _, _, game_id, pkg_id = call.data.split(":", 3)
    g = catalog.find_game(game_id)
    p = next((x for x in (g.get("packages") or []) if x.get("id") == pkg_id), None) if g else None
    if not p:
        await call.answer("Paket topilmadi", show_alert=True)
        await _cat_open(call, game_id)
        return
    await safe_edit(
        call.message,
        _cat_pkg_text(g, p),
        reply_markup=kb.catalog_pkg_kb(game_id, pkg_id),
    )
    await call.answer()


@router.callback_query(F.data.startswith("admin:cat:"))
async def admin_cat_game_view(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    game_id = call.data.split(":", 2)[2]
    if not catalog.find_game(game_id):
        await call.answer("O'yin topilmadi", show_alert=True)
        await _cat_open(call)
        return
    await _cat_open(call, game_id)
    await call.answer()


# ---------------- Katalog: matn kiritish ----------------

@router.message(AdminStates.catalog_game)
async def admin_cat_game_input(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    parts = [x.strip() for x in (message.text or "").split("|")]
    if len(parts) < 2 or not parts[0] or not parts[1]:
        await message.answer(
            "❌ Format noto'g'ri.\n<code>ID | Nomi | Emoji | Tavsif</code> shaklida yuboring."
        )
        return
    g, err = catalog.add_game(
        parts[0],
        parts[1],
        parts[2] if len(parts) > 2 else "",
        parts[3] if len(parts) > 3 else "",
    )
    if err:
        await message.answer(f"❌ {err}")
        return
    await state.clear()
    await message.answer(
        f"✅ <b>{g['name']}</b> qo'shildi.\n\n" + _cat_game_text(g),
        reply_markup=kb.catalog_game_kb(g["id"], g.get("packages") or []),
    )


@router.message(AdminStates.catalog_game_edit)
async def admin_cat_game_edit_input(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    data = await state.get_data()
    parts = [x.strip() for x in (message.text or "").split("|")]
    if not parts or not parts[0]:
        await message.answer("❌ Format: <code>Nomi | Tavsif</code>")
        return
    fields = {"name": parts[0]}
    if len(parts) > 1:
        fields["desc"] = parts[1]
    g = catalog.update_game(data.get("game_id", ""), fields)
    await state.clear()
    if not g:
        await message.answer("❌ O'yin topilmadi.")
        return
    await message.answer(
        "✅ Yangilandi.\n\n" + _cat_game_text(g),
        reply_markup=kb.catalog_game_kb(g["id"], g.get("packages") or []),
    )


@router.message(AdminStates.catalog_pkg)
async def admin_cat_pkg_input(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    data = await state.get_data()
    game_id = data.get("game_id", "")
    parts = [x.strip() for x in (message.text or "").split("|")]
    if len(parts) < 3:
        await message.answer(
            "❌ Format: <code>Nomi | Miqdor | Narx | Kategoriya</code>"
        )
        return
    try:
        price = int(parts[2].replace(" ", "").replace(",", ""))
    except ValueError:
        await message.answer("❌ Narxni raqam bilan yozing (masalan: 10990).")
        return
    if price < 0:
        await message.answer("❌ Narx manfiy bo'lishi mumkin emas.")
        return
    category = parts[3] if len(parts) > 3 and parts[3] else "all"
    pkg = {
        "id": catalog.unique_package_id(game_id, "pkg"),
        "name": parts[0],
        "amount": parts[1],
        "price": price,
        "category": category,
    }
    if not catalog.add_package(game_id, pkg):
        await state.clear()
        await message.answer("❌ O'yin topilmadi.")
        return
    await state.clear()
    g = catalog.find_game(game_id)
    await message.answer(
        f"✅ Paket qo'shildi.\n\n{_cat_pkg_text(g, pkg)}",
        reply_markup=kb.catalog_game_kb(game_id, g.get("packages") or []),
    )


@router.message(AdminStates.catalog_pkg_price)
async def admin_cat_pkg_price_input(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    data = await state.get_data()
    try:
        price = int((message.text or "").replace(" ", "").replace(",", ""))
    except ValueError:
        await message.answer("❌ Raqam kiriting (masalan: 10990).")
        return
    if price < 0:
        await message.answer("❌ Narx manfiy bo'lishi mumkin emas.")
        return
    p = catalog.update_package(data.get("game_id", ""), data.get("pkg_id", ""), {"price": price})
    await state.clear()
    if not p:
        await message.answer("❌ Paket topilmadi.")
        return
    g = catalog.find_game(data.get("game_id", ""))
    await message.answer(
        f"✅ Narx yangilandi.\n\n{_cat_pkg_text(g, p)}",
        reply_markup=kb.catalog_pkg_kb(data.get("game_id", ""), data.get("pkg_id", "")),
    )


@router.message(AdminStates.catalog_pkg_name)
async def admin_cat_pkg_name_input(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    data = await state.get_data()
    name = (message.text or "").strip()
    if not name:
        await message.answer("❌ Nom bo'sh bo'lishi mumkin emas.")
        return
    p = catalog.update_package(data.get("game_id", ""), data.get("pkg_id", ""), {"name": name})
    await state.clear()
    if not p:
        await message.answer("❌ Paket topilmadi.")
        return
    g = catalog.find_game(data.get("game_id", ""))
    await message.answer(
        f"✅ Nom yangilandi.\n\n{_cat_pkg_text(g, p)}",
        reply_markup=kb.catalog_pkg_kb(data.get("game_id", ""), data.get("pkg_id", "")),
    )


# ================== PRO OBUNA ==================

def _pro_money(v):
    try:
        return f"{int(v or 0):,}".replace(",", " ")
    except (TypeError, ValueError):
        return str(v)


def _pro_prices():
    base = config._int_setting("pro_price_month", 50000)
    disc = max(0, min(100, config._int_setting("pro_discount_percent", 5)))
    now = max(0, base - base * disc // 100)
    return base, disc, now


def _pro_keshbek_percents():
    base = config._int_setting("keshbek_percent", 10)
    return base, base + config._int_setting("pro_keshbek_bonus_percent", 5)


async def pro_card_text(user, lang="uz"):
    base, disc, price = _pro_prices()
    kb_base, kb_full = _pro_keshbek_percents()
    active = db.pro_active((user or {}).get("pro_until"))
    lines = [i18n.t(lang, "pro_title"), ""]
    if active:
        lines.append(i18n.t(lang, "pro_active", date=user.get("pro_until")))
    else:
        lines.append(i18n.t(lang, "pro_inactive"))
    lines += [
        "",
        i18n.t(lang, "pro_price_now", price=_pro_money(price)),
        "",
        i18n.t(lang, "pro_perks", base=kb_base, full=kb_full),
    ]
    if disc > 0:
        lines += [
            "",
            i18n.t(lang, "pro_price", price=_pro_money(base), percent=disc, saved=_pro_money(base * disc // 100)),
        ]
    if not config.bool_setting("pro_enabled", True):
        lines += ["", i18n.t(lang, "pro_disabled")]
    return "\n".join(lines)


@router.message(F.text == "💎 PRO")
async def pro_menu_button(message: Message):
    if not await _ensure_not_banned(message):
        return
    user = await db.get_user(message.from_user.id)
    await message.answer(await pro_card_text(user, _lang(message)), reply_markup=kb.pro_kb())


@router.message(Command("pro"))
async def cmd_pro(message: Message):
    if not await _ensure_not_banned(message):
        return
    user = await db.get_user(message.from_user.id)
    await message.answer(await pro_card_text(user, _lang(message)), reply_markup=kb.pro_kb())


@router.callback_query(F.data == "pro:info")
async def pro_info(call: CallbackQuery):
    user = await db.get_user(call.from_user.id)
    await safe_edit(call.message, await pro_card_text(user, _lang(call)), reply_markup=kb.pro_kb())
    await call.answer()


@router.callback_query(F.data == "pro:buy")
async def pro_buy(call: CallbackQuery):
    lang = _lang(call)
    user = await db.get_user(call.from_user.id)
    if not user:
        await call.answer("Foydalanuvchi topilmadi", show_alert=True)
        return
    if not config.bool_setting("pro_enabled", True):
        await call.answer(i18n.t(lang, "pro_disabled"), show_alert=True)
        return
    _base, _disc, price = _pro_prices()
    if price > 0 and not await db.deduct_balance(user["user_id"], price):
        await call.answer(
            i18n.t(
                lang,
                "pro_no_balance",
                price=_pro_money(price),
                balance=_pro_money(user.get("balance", 0)),
            ),
            show_alert=True,
        )
        return
    until = await db.extend_pro(user["user_id"], 30)
    _, kb_full = _pro_keshbek_percents()
    await safe_edit(
        call.message,
        i18n.t(lang, "pro_buy_ok", date=until, price=_pro_money(price), full=kb_full),
        reply_markup=kb.pro_kb(),
    )
    await call.answer("✅ PRO yoqildi")
    for admin_id in _admin_ids_cache:
        try:
            await call.bot.send_message(
                admin_id,
                f"⭐ <b>Yangi PRO obuna</b>\n\n"
                f"👤 {user.get('full_name') or ''} (<code>{user['user_id']}</code>)\n"
                f"💳 {_pro_money(price)} so'm yechildi\n"
                f"📅 {until} gacha",
            )
        except Exception:
            pass


# ---------------- PRO: admin ----------------

def _admin_pro_text():
    base, disc, price = _pro_prices()
    return (
        "⭐ <b>PRO obunani boshqarish</b>\n\n"
        f"🎛 Holat: {'yoqilgan ✅' if config.bool_setting('pro_enabled', True) else 'o\'chirilgan ❌'}\n"
        f"💰 Narx: <b>{_pro_money(price)} so'm</b> / 30 kun\n"
        f"🏷 Chegirma: <b>{disc}%</b> (asosiy {_pro_money(base)})\n"
        f"💎 Keshbek bonusi: <b>{_pro_keshbek_percents()[1]}%</b>\n"
        f"🔢 Joriy sozlamalar: <code>pro_price_month</code>, <code>pro_discount_percent</code>, "
        f"<code>pro_keshbek_bonus_percent</code>"
    )


@router.callback_query(F.data == "admin:pro")
async def admin_pro(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    active = await db.list_pro_users(True, 20)
    text = _admin_pro_text() + f"\n\n👥 <b>Faol PRO:</b> <b>{len(active)}</b>\n"
    if active:
        for u in active[:15]:
            text += f"• <code>{u['user_id']}</code> — {u['full_name'] or ''} → {u['pro_until']}\n"
    else:
        text += "— hozircha yo'q —\n"
    builder = InlineKeyboardBuilder()
    builder.button(
        text=("❌ PRO ni o'chirish" if config.bool_setting("pro_enabled", True) else "✅ PRO ni yoqish"),
        callback_data="admin:pro_toggle",
    )
    builder.button(text="✏️ Narxni o'zgartirish", callback_data="admin:set:pro_price_month")
    builder.button(text="🏷 Chegirmani o'zgartirish", callback_data="admin:set:pro_discount_percent")
    builder.button(text="💎 Keshbek bonusi", callback_data="admin:set:pro_keshbek_bonus_percent")
    builder.button(text="➕ Foydalanuvchiga PRO berish", callback_data="admin:pro_grant")
    builder.button(text="⚙️ Funksiyalar", callback_data="admin:features")
    builder.button(text="🔙 Admin panel", callback_data="admin:menu")
    builder.adjust(1)
    await safe_edit(call.message, text, reply_markup=builder.as_markup())
    await call.answer()


@router.callback_query(F.data == "admin:pro_toggle")
async def admin_pro_toggle(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    new_val = config.toggle_setting("pro_enabled")
    await call.answer("PRO yoqildi ✅" if new_val else "PRO o'chirildi ❌", show_alert=True)
    await admin_pro(call)


@router.callback_query(F.data == "admin:pro_grant")
async def admin_pro_grant(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await state.set_state(AdminStates.pro_target)
    await safe_edit(
        call.message,
        "➕ <b>PRO berish</b>\n\nFoydalanuvchi ID sini yuboring (30 kun beriladi):",
        reply_markup=kb.back_admin_menu_kb(),
    )
    await call.answer()


@router.message(AdminStates.pro_target)
async def admin_pro_grant_input(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    raw = (message.text or "").strip().lstrip("@")
    target = None
    if raw.isdigit():
        target = int(raw)
    if not target:
        u = await db.get_user_by_username(raw)
        target = u["user_id"] if u else None
    if not target:
        await state.clear()
        await message.answer("❌ Foydalanuvchi topilmadi.")
        return
    until = await db.extend_pro(target, 30)
    await state.clear()
    await message.answer(f"✅ <code>{target}</code> uchun PRO {until} gacha yoqildi.")
    try:
        await message.bot.send_message(
            target,
            "⭐ <b>Sizga PRO obuna berildi!</b>\n\n"
            f"📅 Muddat: <b>{until}</b> gacha\n\nBatafsil: /pro",
        )
    except Exception:
        pass


# ---------------- PRO: muddat nazorati ----------------

async def _pro_expire_loop():
    """PRO muddati tugaganlarni xabardor qiladi va keshbekni qayta hisoblaydi."""
    while True:
        try:
            await asyncio.sleep(3600)
            expired = await db.expired_pro_users(100)
            for u in expired:
                await db.mark_pro_notified(u["user_id"])
                await db.set_keshbek(u["user_id"])
                lang = u.get("lang") or "uz"
                kb_base, _ = _pro_keshbek_percents()
                try:
                    await services.get_bot().send_message(
                        u["user_id"],
                        i18n.t(lang, "pro_expired", date=u["pro_until"], base=kb_base),
                    )
                except Exception:
                    pass
            # Faol PRO foydalanuvchilarning keshbeki muddat bilan mos bo'lsin
            active = await db.list_pro_users(True, 200)
            for u in active:
                await db.set_keshbek(u["user_id"])
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logging.getLogger("bot").warning("pro_expire_loop xatosi: %s", e)
            await asyncio.sleep(60)


# ================== TEXT INPUT HANDLER (unified) ==================

# Bot ishlaydigan buyruqlar. Ro'yxatga qo'shilmagan buyruq — "noma'lum" degani.
_KNOWN_COMMANDS = frozenset({
    "start", "orders", "track", "cancel", "set", "addadmin", "deladmin",
    "listadmins", "stats", "promo", "invite", "id", "status", "help",
    "webapp", "admin", "pro",
})


def _command_name(txt: str):
    """'/start@bot arg' -> 'start'; buyruq emas bo'lsa None."""
    t = (txt or "").strip()
    if not t.startswith("/") or len(t) < 2:
        return None
    return t[1:].split()[0].split("@")[0].lower()


@router.message(F.text)
async def text_handler(message: Message, state: FSMContext):
    cmd = _command_name(message.text)
    if cmd:
        if cmd in _KNOWN_COMMANDS:
            from aiogram.dispatcher.event.bases import SkipHandler
            raise SkipHandler()
        # Noma'lum buyruq: FSM holatiga (topup summa/qidiruv) aralashmasin.
        await message.answer(f"⚠️ Noma'lum buyruq: <code>/{cmd}</code>")
        try:
            await state.clear()
        except Exception:
            pass
        return
    if not await _ensure_not_banned(message): return
    st = await state.get_state()

    # --- Card topup: custom amount input ---
    if st == TopUpStates.waiting_custom_amount:
        try:
            amount = int(message.text.strip().replace(" ", "").replace(",", ""))
        except ValueError:
            await message.answer("❌ To'g'ri raqam kiriting.")
            return
        min_a = config.get_settings().get("min_topup_card", 10000)
        max_a = config.get_settings().get("max_topup_card", 1000000)
        if amount < min_a:
            await message.answer(f"❌ Minimal summa: {format_price(min_a)} so'm.")
            return
        if amount > max_a:
            await message.answer(f"❌ Maksimal summa: {format_price(max_a)} so'm.")
            return
        await state.set_state(TopUpStates.waiting_card_choice)
        await state.update_data(card_amount=amount)
        await message.answer(
            f"💳 <b>Qaysi kartaga to'lov qilasiz?</b>\n\n"
            f"💰 Summa: <b>{format_price(amount)} so'm</b>\n\n"
            "Kartani tanlang — so'ngra karta raqami ko'rsatiladi:",
            reply_markup=kb.topup_cards_kb(amount),
        )
        return

    # --- Admin: enter balance amount ---
    if st == AdminStates.entering_balance:
        if not is_admin(message.from_user.id):
            await state.clear()
            return
        data = await state.get_data()
        target = data.get("target_user")
        action = data.get("action")
        await state.clear()
        if not target:
            await message.answer("❌ Xatolik yuz berdi.")
            return
        try:
            amount = int(message.text.strip().replace(" ", "").replace(",", ""))
        except ValueError:
            await message.answer("❌ To'g'ri raqam kiriting.")
            return
        if amount <= 0:
            await message.answer("❌ Summa musbat bo'lishi kerak.")
            return
        if action == "plus":
            await db.add_balance(target, amount, method="admin")
            new_bal = (await db.get_user(target))["balance"]
            await message.answer(
                f"✅ Foydalanuvchiga <b>{format_price(amount)} so'm</b> qo'shildi."
                f"\nYangilangan balans: <b>{format_price(new_bal)} so'm</b>"
            )
            try:
                await message.bot.send_message(
                    target,
                    f"💰 Balansingizga <b>{format_price(amount)} so'm</b> qo'shildi.",
                )
            except Exception:
                pass
        else:
            user = await db.get_user(target)
            if user:
                new_bal = max(0, user["balance"] - amount)
                await db.set_user_balance(target, new_bal)
                await message.answer(
                    f"✅ Balans yangilandi: <b>{format_price(new_bal)} so'm</b>"
                )
        return

    # --- Shop: buy via Stars — waiting for game id ---
    if st == StarsBuyStates.waiting_player_id:
        data = await state.get_data()
        game_id = data.get("pending_stars_game_id")
        package_id = data.get("pending_stars_package_id")
        await state.clear()
        game = kb.find_game(game_id)
        pkg = kb.find_package(game_id, package_id)
        input_val = (message.text or "").strip()
        if not game or not pkg:
            await message.answer("❌ Xatolik yuz berdi.")
            return
        if not input_val:
            await message.answer("❌ O'yin ID kiriting.")
            return
        if len(input_val) > 100:
            await message.answer("❌ Juda uzun ma'lumot. Qisqaroq ID kiriting.")
            return

        player_b64 = base64.urlsafe_b64encode(input_val.encode()).decode()
        stars = config.stars_count_for_price(pkg["price"])
        nick = await _verify_player_nickname(game_id, input_val)
        try:
            import delivery as _dlv2
            ok_id, id_hint = _dlv2.validate_player_id(game_id, input_val)
        except Exception:
            ok_id, id_hint = True, ""
        if not ok_id:
            await message.answer(
                "⚠️ <b>ID formatida xato bor!</b>\n\n"
                f"Kutilgan format: <code>{id_hint}</code>\n\n"
                "Qayta kiriting (yoki /cancel)."
            )
            return
        await message.answer_invoice(
            title=f"{game['name']} — {pkg['name']}",
            description=(
                f"{pkg['name']} uchun to'lov\n"
                f"🆔 O'yin ID: <code>{input_val}</code>"
                + (f"\n👤 O'yinchi: <b>{nick}</b>" if nick else "")
                + f"\n{format_price(pkg['price'])} so'm ≈ {stars} ⭐️"
            ),
            payload=f"buy:{game_id}:{package_id}:{player_b64}",
            currency="XTR",
            prices=[LabeledPrice(label="XTR", amount=stars)],
            provider_token="",
        )
        return

    # --- Shop: waiting for game id (balance payment) ---
    if st == BalanceBuyStates.waiting_player_id:
        data = await state.get_data()
        user_id = message.from_user.id
        user = await db.get_user(user_id)
        game_id = data.get("pending_game_id")
        package_id = data.get("pending_package_id")
        price = data.get("pending_price")
        game = kb.find_game(game_id)
        pkg = kb.find_package(game_id, package_id)
        await state.clear()
        if not game or not pkg or not user:
            await message.answer("❌ Xatolik yuz berdi.")
            return
        if user["balance"] < price:
            await message.answer(ls.too_low_balance_text(_lang(message)))
            return
        input_val = message.text.strip()
        if len(input_val) > 100:
            await message.answer("❌ Juda uzun ma'lumot. Qisqaroq ID kiriting.")
            return
        try:
            import delivery as _dlv
            ok_id, id_hint = _dlv.validate_player_id(game_id, input_val)
        except Exception:
            ok_id, id_hint = True, ""
        if not ok_id:
            await message.answer(
                "⚠️ <b>ID formatida xato bor!</b>\n\n"
                f"Kutilgan format: <code>{id_hint}</code>\n\n"
                "Qayta kiriting (yoki /cancel)."
            )
            return
        nick = await _verify_player_nickname(game_id, input_val)
        nick_user = f"\n👤 O'yinchi: <b>{nick}</b>" if nick else ""
        nick_admin = f"\n👤 O'yinchi nomi: <b>{nick}</b>" if nick else ""
        order_id, _err = await db.purchase(
            user_id,
            game["id"],
            pkg["name"],
            str(pkg["amount"]),
            price,
            input_val,
        )
        if not order_id:
            await message.answer("❌ Balans yetarli emas yoki xatolik.")
            return
        await message.answer(ls.order_created_text(order_id, _lang(message)) + nick_user)
        client = await _client_line(user_id)
        for admin_id in _admin_ids_cache:
            try:
                await message.bot.send_message(
                    admin_id,
                    f"📦 <b>Yangi buyurtma!</b>\n\n"
                    f"🎮 {game['name']}\n"
                    f"📦 {pkg['name']}\n"
                    f"🆔 O'yin ID: <code>{input_val}</code>{nick_admin}\n"
                    f"{client}\n"
                    f"💰 {format_price(price)} so'm\n"
                    f"💠 To'lov: Balans",
                    reply_markup=kb.order_admin_kb(order_id),
                )
            except Exception:
                pass
        return

    # --- Murojaat (support) ---
    if st == SupportStates.awaiting_message:
        await state.clear()
        text = (message.text or "").strip()
        if not text:
            return
        client = await _client_line(message.from_user.id, "👤 Mijoz")
        delivered = 0
        for admin_id in _admin_ids_cache:
            try:
                await message.bot.send_message(
                    admin_id,
                    f"📣 <b>Yangi murojaat</b>\n\n{client}\n\n<b>Xabar:</b>\n{esc(text)[:1500]}\n\n"
                    f"🆔 <code>{message.from_user.id}</code>",
                    reply_markup=kb.support_admin_kb(message.from_user.id),
                )
                delivered += 1
            except Exception:
                pass
        await message.answer(
            "✅ Murojaatingiz adminga yuborildi. Javob shu yerga keladi."
            if delivered
            else "❌ Xatolik yuz berdi. Iltimos keyinroq urinib ko'ring."
        )
        return

    # --- Admin: murojaatga javob ---
    if st == AdminStates.replying_user:
        if not is_admin(message.from_user.id):
            await state.clear()
            return
        data = await state.get_data()
        target = data.get("reply_target")
        await state.clear()
        if not target:
            await message.answer("❌ Xatolik yuz berdi.")
            return
        try:
            await message.bot.send_message(int(target), f"📬 <b>Admin javobi:</b>\n\n{message.text}")
            await message.answer("✅ Javob foydalanuvchiga yuborildi.")
        except Exception:
            await message.answer("❌ Yuborilmadi (foydalanuvchi botni bloklagan bo'lishi mumkin).")
        return

    # --- Fallback: holat yo'q yoki tushunilmagan matn ---
    if is_admin(message.from_user.id):
        if message.reply_to_message and message.reply_to_message.text:
            m = re.search(r"🆔\s*<code>(\d+)</code>", message.reply_to_message.text)
            if m:
                try:
                    await message.bot.send_message(
                        int(m.group(1)), f"📬 <b>Admin javobi:</b>\n\n{message.text}"
                    )
                    await message.answer("✅ Javob foydalanuvchiga yuborildi (reply).")
                except Exception:
                    await message.answer("❌ Yuborilmadi.")
                return
        await state.set_state(AdminStates.search_query)
        await message.answer(ls.admin_search_prompt(_lang(message)), reply_markup=kb.back_admin_menu_kb())
        return
    if st:
        await state.clear()
    await message.answer(ls.menu_text(_lang(message)), reply_markup=kb.main_menu_kb())



# ================== MAIN ==================

async def _poll_with_retry(dp, bot):
    delay = 1
    while True:
        try:
            await dp.start_polling(bot)
            return
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logging.getLogger("bot").error(
                "Polling to'xtadi, %ss dan keyin qayta boshlanadi: %s", delay, e
            )
            await asyncio.sleep(delay)
            delay = min(delay * 2, 60)


async def _expire_payments_loop(bot):
    """Har 60s da eski kutilmoqda to'lovlarni rad_etildi qiladi."""
    while True:
        try:
            await asyncio.sleep(60)
            pay_window = config.pay_window_seconds()
            expired = await db.expire_stale_payments(pay_window)
            for payment_id, user_id, amount, ref in expired:
                try:
                    await bot.send_message(
                        user_id,
                        f"⏰ <b>To'lov muddati tugadi.</b>\n\n"
                        f"To'lov: <code>#{payment_id}</code>\n"
                        f"Summa: <b>{format_price(amount)} so'm</b>\n\n"
                        f"Agar pul o'tkazgan bo'lsangiz, admin bilan bog'laning.",
                    )
                except Exception:
                    pass

            # Chek eslatmasi: chek yubormaganlarga bir marta eslatma
            if not config.bool_setting("chek_reminder_enabled", True):
                stale = []
            else:
                stale = await db.get_stale_chek_payments(pay_window - 60)
            for r in stale:
                try:
                    await bot.send_message(
                        r["user_id"],
                        f"📸 <b>Chek eslatma</b> (To'lov #{r['id']})\n\n"
                        f"Summa: <b>{format_price(r['amount'] or 0)} so'm</b> — chek hali yuborilmadi.\n\n"
                        f"Pulni o'tkazgan bo'lsangiz — chek/screenshot RASMIni shu yerga yuboring! ⏳",
                    )
                    await db.mark_payment_reminded(r["id"])
                except Exception:
                    pass
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logging.getLogger("bot").warning("expire_payments_loop xatosi: %s", e)
            await asyncio.sleep(10)


async def _order_reminder_loop(bot):
    """Kutilmoqda qolgan buyurtmalar uchun foydalanuvchiga bir marta eslatma."""
    while True:
        try:
            await asyncio.sleep(60)
            minutes = config._int_setting("order_reminder_min", 30)
            if minutes <= 0 or not config.bool_setting("order_reminder_enabled", True):
                continue
            stale = await db.get_stale_pending_orders(minutes)
            for o in stale:
                await db.mark_order_reminded(o["id"])
                try:
                    lang = await order_notify.lang_of(o["user_id"])
                    await bot.send_message(o["user_id"], order_notify.reminder_message(o, lang))
                except Exception:
                    pass
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logging.getLogger("bot").warning("order_reminder_loop xatosi: %s", e)
            await asyncio.sleep(10)


async def _send_notifications_loop(bot):
    """Bildirishnomalar navbatini har 5s da tekshirib yuboradi."""
    cycle = 0
    while True:
        try:
            await asyncio.sleep(5)
            notes = await db.fetch_notifications(50)
            sent_ids = []
            for n in notes:
                sent_ids.append(n["id"])
                try:
                    await bot.send_message(n["user_id"], n["text"], parse_mode="HTML")
                except Exception:
                    pass
            await db.mark_notifications_done(sent_ids)
            cycle += 1
            if cycle % 120 == 0:
                await db.purge_sent_notifications(7)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logging.getLogger("bot").warning("send_notifications_loop xatosi: %s", e)
            await asyncio.sleep(10)


MAIN_LOOP = None
_DP = None
_BOT = None
def _load_webhook_secret():
    try:
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".webhook_secret")
        return open(p, encoding="utf-8").read().strip()
    except Exception:
        return ""


_WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "") or _load_webhook_secret()
USE_WEBHOOK = os.getenv("USE_WEBHOOK", "0") == "1"


async def feed_update(data: dict):
    if _DP is None or _BOT is None:
        return
    try:
        update = Update.model_validate(data)
        await _DP.feed_update(_BOT, update)
    except Exception as e:
        logging.getLogger("bot").error("feed_update xatosi: %s", e)


async def _webhook_watch_loop(bot: Bot):
    """Tunnel URL o'zgarsa — webhookni yangilaydi."""
    forced = True
    while True:
        try:
            await asyncio.sleep(3 if forced else 15)
            url = config.get_settings().get("webapp_url", "").rstrip("/")
            expected = f"{url}/tg-webhook" if url else ""
            actual = ""
            try:
                info = await bot.get_webhook_info()
                actual = info.url or ""
            except Exception:
                pass
            if expected and (actual != expected or forced):
                await bot.set_webhook(
                    url=expected,
                    secret_token=_WEBHOOK_SECRET,
                    drop_pending_updates=True,
                    allowed_updates=["message", "callback_query", "pre_checkout_query"],
                )
                logging.getLogger("bot").info("Webhook o'rnatildi/tiklandi: %s", expected)
                forced = False
        except Exception as e:
            logging.getLogger("bot").error("webhook o'rnatish xatosi: %s", e)
            await asyncio.sleep(10)


async def _webapp_url_watch_loop(bot: Bot):
    """Tunnel URL o'zgarsa — menyu tugmasi va ichki havolalar ham yangilansin.

    (faqat webhook emas: 'Do'kon' menyu tugmasi eski/o'lik URLda qolib
    ketmasligi uchun ham)
    """
    current = (config.get_settings().get("webapp_url") or "").rstrip("/")
    while True:
        try:
            await asyncio.sleep(10)
            url = (config.get_settings().get("webapp_url") or "").rstrip("/")
            if not url or url == current:
                continue
            current = url
            services.set_webapp_url(url)
            try:
                await bot.set_chat_menu_button(
                    menu_button=MenuButtonWebApp(
                        text="🛍 Do'kon",
                        web_app=WebAppInfo(url=url),
                    )
                )
            except Exception:
                pass
            logging.getLogger("bot").info("Webapp URL yangilandi: %s", url)
        except Exception as e:
            logging.getLogger("bot").warning("webapp_url watch xatosi: %s", e)
            await asyncio.sleep(10)


async def run_bot():
    await db.init_db()

    # IPv6 muammo oldini olish — faqat IPv4
    try:
        import socket

        from aiogram.client.session.aiohttp import AiohttpSession
        session = AiohttpSession()
        session._connector_init["family"] = socket.AF_INET
    except Exception:
        session = None

    kwargs = {
        "token": config.BOT_TOKEN,
        "default": DefaultBotProperties(parse_mode=ParseMode.HTML),
    }
    if session is not None:
        kwargs["session"] = session
    bot = Bot(**kwargs)
    dp = Dispatcher()
    # Qayta ishga tushirishda (retry) barcha routerlar eski parent'dan
    # ajratilishi shunki, aks holda "Router is already attached" xatosi chiqadi.
    for _r in (start_router, catalog_router, payments_router, router):
        if _r.parent_router is not None:
            _r._parent_router = None
    # Muhim: aniq handlerlar (start/katalog) catch-all F.text dan OLDIN tekshiriladi.
    # Aks holda /start kabi buyruqlar unified text_handler'ga yutilib ketadi.
    dp.include_router(start_router)
    dp.include_router(catalog_router)
    dp.include_router(payments_router)
    dp.include_router(router)

    services.set_bot(bot, asyncio.get_running_loop())

    global MAIN_LOOP, _DP, _BOT
    MAIN_LOOP = asyncio.get_running_loop()
    _DP = dp
    _BOT = bot

    # Adminlarni DB dan yuklash
    await refresh_admins()

    try:
        me = await bot.get_me()
        bot_username = me.username or ""
        if bot_username:
            config.update_settings({"bot_username": bot_username})
    except Exception:
        pass

    weburl = config.get_settings().get("webapp_url") or config.WEBAPP_URL
    if weburl:
        services.set_webapp_url(weburl)
        # Global menu tugmasi: tunnel URL o'zgarsa — barchada avtomat yangilansin
        try:
            await bot.set_chat_menu_button(
                menu_button=MenuButtonWebApp(
                    text="🛍 Do'kon",
                    web_app=WebAppInfo(url=weburl),
                )
            )
        except Exception:
            pass

    # Buyruqlar menyusi (/): userlarga faqat eng keraklilari.
    # BotFather'dagi keraksizlar shu bilan o'chadi, restartda qaytib kelmaydi.
    try:
        from aiogram.types import (
            BotCommand as _BotCommand,
        )
        from aiogram.types import (
            BotCommandScopeChat as _ScopeChat,
        )
        from aiogram.types import (
            BotCommandScopeDefault as _ScopeDefault,
        )
        await bot.set_my_commands(
            [
                _BotCommand(command="start", description="🛍 Do'konni ochish"),
                _BotCommand(command="promo", description="🎟 Promokod"),
                _BotCommand(command="invite", description="🤝 Do'st taklif qilish"),
                _BotCommand(command="help", description="❓ Yordam"),
                _BotCommand(command="cancel", description="❌ Bekor qilish"),
            ],
            scope=_ScopeDefault(),
        )
        for admin_id in _admin_ids_cache:
            try:
                await bot.set_my_commands(
                    [
                        _BotCommand(command="start", description="🛍 Do'konni ochish"),
                        _BotCommand(command="admin", description="🛠 Admin panel"),
                        _BotCommand(command="stats", description="📊 Statistika"),
                        _BotCommand(command="orders", description="📦 Buyurtmalar"),
                        _BotCommand(command="cancel", description="❌ Bekor qilish"),
                    ],
                    scope=_ScopeChat(chat_id=admin_id),
                )
            except Exception:
                pass
    except Exception:
        pass

    # Avtomatik delivery worker
    import delivery
    asyncio.create_task(delivery.process_orders_loop(bot))

    # Avtomatik to'lov muddati o'tganlarni bekor qilish (har 60s)
    asyncio.create_task(_expire_payments_loop(bot))

    # Bildirishnomalar yuboruvchi (har 5s)
    asyncio.create_task(_send_notifications_loop(bot))

    # Kutilmoqda turgan buyurtmalarga eslatma (har 60s)
    asyncio.create_task(_order_reminder_loop(bot))

    # PRO obuna muddati nazorati (soatda bir marta)
    asyncio.create_task(_pro_expire_loop())

    # Tunnel URL o'zgarsa — menyu tugmasi/ichki havolalar avtomat yangilansin
    asyncio.create_task(_webapp_url_watch_loop(bot))

    if USE_WEBHOOK:
        asyncio.create_task(_webhook_watch_loop(bot))
        logging.getLogger("bot").info("Webhook rejimi yoqildi (polling o'chiq).")
        await asyncio.Event().wait()
        return bot, dp

    # Kutilayotgan update'larNI YO'Q QILMAYDI: drop_pending_updates=True bo'lsa,
    # har restartda userlarning yuborgan xabarlari (buyurtma/promo/to'lov) yo'qoladi.
    # Eski webhook tozalansin, lekin navbat saqlansin.
    await bot.delete_webhook(drop_pending_updates=False)
    await _poll_with_retry(dp, bot)
    return bot, dp


if __name__ == "__main__":
    asyncio.run(run_bot())