"""START / MENU handlerlari — bot.py dan ko'chirildi (faza 2)."""
from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MenuButtonWebApp,
    Message,
    WebAppInfo,
)

import config
import database as db
import keyboards as kb
import text as ls
from handlers.helpers import _ensure_not_banned, _lang

router = Router()


def _find_banner():
    """data/banner.png (yoki .jpg) bo'lsa — /start da rasm bilan chiqadi."""
    import os

    base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    for name in ("banner.png", "banner.jpg", "banner.webp"):
        p = os.path.join(base, name)
        if os.path.isfile(p):
            return p
    return None


@router.message(CommandStart())
async def cmd_start(message: Message):
    user = await db.get_user(message.from_user.id)
    if user and user["is_banned"]:
        await message.answer(ls.banned_message(_lang(message)))
        return

    # Deep-link referral:  /start ref_<user_id>
    referrer_id = 0
    arg = (message.text or "").strip().split()[-1] if (message.text or "").startswith("/start") else ""
    if arg.startswith("ref_"):
        try:
            rid = int(arg.split("_")[1])
            if rid != message.from_user.id:
                referrer_id = rid
        except (ValueError, IndexError):
            referrer_id = 0

    await db.register_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.full_name,
        referrer_id,
    )
    kb_start = InlineKeyboardMarkup(inline_keyboard=[])
    weburl = config.get_settings().get("webapp_url") or config.WEBAPP_URL
    if weburl:
        kb_start = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🛍 Mini App'ni ochish",
                        web_app=WebAppInfo(url=weburl),
                    )
                ]
            ]
        )
    add_text = ""
    if referrer_id:
        add_text = "\n\n🎁 Siz <b>taklif havolasi</b> orqali keldingiz!"
    advert = (
        "\n\n━━━━━━━━━━━━━━━\n"
        "🎮 <b>Free Fire, PUBG, MLBB, Roblox va boshqalar</b> — diamond, UC, star va premium paketlar\n"
        "💰 Balans, ⭐️ Telegram Stars yoki 💳 karta orqali to'lov\n"
        "🎟 Promokodlar, 🤝 referral bonus, 💎 PRO keshbek\n"
        "⚡️ Buyurtma 5–30 daqiqada bajariladi"
    )
    start_body = ls.start_text(_lang(message)) + add_text + advert
    banner = _find_banner()
    if banner:
        try:
            from aiogram.types import FSInputFile

            await message.answer_photo(
                FSInputFile(banner),
                caption=start_body[:1024],
                reply_markup=kb_start,
            )
        except Exception:
            await message.answer(start_body, reply_markup=kb_start)
    else:
        await message.answer(start_body, reply_markup=kb_start)
    ann = str(config.get_settings().get("announcement") or "").strip()
    if ann:
        try:
            await message.answer(f"📢 <b>E'lon</b>\n\n{ann}")
        except Exception:
            pass
    if weburl:
        try:
            await message.bot.set_chat_menu_button(
                chat_id=message.from_user.id,
                menu_button=MenuButtonWebApp(
                    text="🛍 Do'kon",
                    web_app=WebAppInfo(url=weburl),
                ),
            )
        except Exception:
            pass


@router.message(F.text == "🏠 Bosh sahifa")
async def home_menu(message: Message):
    if not await _ensure_not_banned(message): return
    await message.answer(ls.menu_text(_lang(message)), reply_markup=kb.games_menu_kb())


@router.message(F.text == "🛒 O'yinlar")
async def games_menu(message: Message):
    if not await _ensure_not_banned(message): return
    await message.answer(
        "🎮 <b>O'yinlar katalogi</b>\n\nTanlang 👇",
        reply_markup=kb.games_menu_kb(),
    )


@router.message(F.text == "💰 Balans")
async def show_balance(message: Message):
    if not await _ensure_not_banned(message): return
    user = await db.get_user(message.from_user.id)
    await message.answer(ls.balance_text(user), reply_markup=kb.balance_kb())


@router.message(F.text == "📜 Tarix")
async def show_history(message: Message):
    if not await _ensure_not_banned(message): return
    user_id = message.from_user.id
    orders = await db.get_user_orders(user_id, 5)
    payments = await db.get_user_payments(user_id, 5)
    weburl = config.get_settings().get("webapp_url") or config.WEBAPP_URL
    kb_hist = None
    if weburl:
        kb_hist = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📜 Mini App'da to'liq tarix", web_app=WebAppInfo(url=weburl))]
            ]
        )
    await message.answer(ls.history_text(orders, payments, _lang(message)), reply_markup=kb_hist)
