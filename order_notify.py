"""Buyurtma holati o'zgarganda yuboriladigan yagona xabarlar (uz/ru/en).

Bot (aiogram loop) va server (uvicorn thread) tomonidan ham ishlatiladi:
xabar matni sinxron quriladi, yuborishni chaqiruvchi tomon bajaradi.
"""
import logging

import config
import database as db
from i18n import t as _t

logger = logging.getLogger("order_notify")

STATUS_KEY = {
    "kutilmoqda": "order_queued",
    "bajarildi": "order_done",
    "rad_etildi": "order_rejected",
    "to'lov_kutilmoqda": "order_payment_required",
}


def _esc(s):
    return (
        str(s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _money(v):
    try:
        return f"{int(v or 0):,}".replace(",", " ")
    except (TypeError, ValueError):
        return "0"


def _game_name(platform):
    try:
        import keyboards as kb
        g = kb.find_game(platform)
        if g:
            return g["name"]
    except Exception:
        pass
    return platform or ""


def build_message(order, status, detail="", lang=None):
    """Buyurtma holati uchun lokalizatsiyalangan xabar matnini qaytaradi."""
    lang = lang or "uz"
    key = STATUS_KEY.get(status, "order_queued")
    text = _t(
        lang,
        key,
        id=_esc(order["id"]),
        game=_esc(_game_name(order.get("platform"))),
        package=_esc(order.get("package_name")),
        player=_esc(order.get("game_id")),
        price=_money(order.get("price")),
        detail=_esc(detail or "—"),
    )
    if status == "bajarildi":
        text += "\n\n" + _t(lang, "order_done_footer", id=_esc(order["id"]))
    return text


def waited_minutes(order):
    from datetime import datetime

    try:
        created = datetime.strptime(order.get("created_at"), "%Y-%m-%d %H:%M")
    except (TypeError, ValueError):
        return 0
    return max(0, int((datetime.now() - created).total_seconds() // 60))


def reminder_message(order, lang=None, detail=""):
    lang = lang or "uz"
    minutes = waited_minutes(order)
    if minutes <= 0:
        minutes = config._int_setting("order_reminder_min", 30)
    text = _t(
        lang,
        "order_reminder",
        id=_esc(order["id"]),
        game=_esc(_game_name(order.get("platform"))),
        package=_esc(order.get("package_name")),
        minutes=str(minutes),
    )
    if detail:
        text += "\n\n" + _t(lang, "order_fail_hint", detail=_esc(detail))
    return text


def fail_message(order, detail, lang=None):
    lang = lang or "uz"
    return _t(
        lang,
        "order_auto_fail",
        id=_esc(order["id"]),
        package=_esc(order.get("package_name")),
        detail=_esc(str(detail or "")[:120]),
    )


async def lang_of(user_id, default="uz"):
    try:
        u = await db.get_user(user_id)
        if u:
            return u.get("lang") or default
    except Exception:
        pass
    return default


async def notify_user(bot, order, status, detail="", lang=None):
    """Foydalanuvchiga holat xabarini yuboradi (aiogram loop ichida)."""
    try:
        lang = lang or await lang_of(order["user_id"])
        await bot.send_message(order["user_id"], build_message(order, status, detail, lang))
        return True
    except Exception as e:
        logger.warning("notify_user xatosi (order=%s): %s", order.get("id"), e)
        return False


def safe_notify(bot, order, status, detail="", lang=None):
    """server.py (boshqa thread) uchun yuborish yordamchisi."""
    try:
        lang = lang or "uz"
        text = build_message(order, status, detail, lang)
        import services

        return services.safe_call_bot(
            lambda: services.get_bot().send_message(
                order["user_id"], text, parse_mode="HTML"
            )
        )
    except Exception as e:
        logger.warning("safe_notify xatosi (order=%s): %s", order.get("id"), e)
        return None
