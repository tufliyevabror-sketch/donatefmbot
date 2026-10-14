import asyncio
import base64
import hashlib
import hmac
import json
import logging
import os
import re as _re
import time
from collections import defaultdict
from urllib.parse import parse_qsl

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware

import config
import database as db
import i18n
import keyboards as kb
import order_notify
import services

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("server")

app = FastAPI()
_START_TIME = time.time()

def _load_webhook_secret():
    try:
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".webhook_secret")
        return open(p, encoding="utf-8").read().strip()
    except Exception:
        return ""


WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "") or _load_webhook_secret()
USE_WEBHOOK = os.getenv("USE_WEBHOOK", "0") == "1"


@app.post("/tg-webhook")
async def tg_webhook(request: Request):
    if not USE_WEBHOOK:
        return JSONResponse({"ok": False}, status_code=404)
    if request.headers.get("X-Telegram-Bot-Api-Secret-Token", "") != WEBHOOK_SECRET:
        return JSONResponse({"ok": False}, status_code=403)
    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"ok": False}, status_code=400)
    try:
        import bot as bot_module
        if bot_module.MAIN_LOOP is not None:
            asyncio.run_coroutine_threadsafe(bot_module.feed_update(data), bot_module.MAIN_LOOP)
    except Exception as e:
        logger.error("tg-webhook xatosi: %s", e)
    return JSONResponse({"ok": True})


@app.get("/health")
async def health():
    """Monitoring/healthcheck. Auth talab qilmaydi, rate limit ham tashqarida."""
    import sqlite3

    db_ok = False
    try:
        conn = sqlite3.connect(config.DB_PATH, timeout=3)
        db_ok = conn.execute("SELECT 1").fetchone()[0] == 1
        conn.close()
    except Exception:
        db_ok = False
    s = config.get_settings()
    payload = {
        "ok": db_ok,
        "db": db_ok,
        "webhook": USE_WEBHOOK,
        "webapp_url": s.get("webapp_url", ""),
        "maintenance": bool(s.get("maintenance", False)),
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    return JSONResponse(payload, status_code=200 if db_ok else 503)


@app.post("/api/admin/metrics")
async def api_admin_metrics(request: Request):
    """Admin uchun monitoring: uptime, sonlar, backup holati, fayl o'lchamlari."""
    body = await _parse_body(request)
    if body is None:
        return JSONResponse({"ok": False, "error": "bad_request"}, status_code=400)
    _user, err = await _admin_guard(body.get("initData", ""))
    if err:
        return err

    async def _db_count(sql: str) -> int:
        conn = await db.get_connection()
        try:
            rows = await conn.execute_fetchall(sql)
            return rows[0][0] if rows else 0
        finally:
            await conn.close()

    backups_dir = os.path.join(config.BASE_DIR, "data", "backups")
    backups = []
    try:
        for name in os.listdir(backups_dir):
            if name.endswith(".db"):
                p = os.path.join(backups_dir, name)
                backups.append((os.path.getmtime(p), os.path.getsize(p), name))
    except Exception:
        backups = []
    backups.sort(reverse=True)

    return {
        "ok": True,
        "uptime_sec": int(time.time() - _START_TIME),
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "db": {
            "users": await _db_count("SELECT COUNT(*) FROM users"),
            "orders": await _db_count("SELECT COUNT(*) FROM orders"),
            "payments": await _db_count("SELECT COUNT(*) FROM payments"),
        },
        "backups": {
            "count": len(backups),
            "latest": backups[0][2] if backups else None,
            "latest_size": backups[0][1] if backups else 0,
            "latest_age_sec": int(time.time() - backups[0][0]) if backups else None,
        },
        "webhook": USE_WEBHOOK,
        "maintenance": bool(config.get_settings().get("maintenance", False)),
    }


def _latest_daily_report() -> dict | None:
    folder = os.path.join(config.BASE_DIR, "data", "reports")
    try:
        files = []
        for name in os.listdir(folder):
            if name.endswith(".json"):
                path = os.path.join(folder, name)
                files.append((os.path.getmtime(path), path))
        if not files:
            return None
        files.sort(reverse=True)
        _, path = files[0]
        with open(path, encoding="utf-8") as f:
            return {"path": os.path.basename(path), "data": json.load(f)}
    except (OSError, ValueError, json.JSONDecodeError):
        return None


@app.post("/api/admin/daily_report/latest")
async def api_admin_latest_report(request: Request):
    body = await _parse_body(request)
    if body is None:
        return JSONResponse({"ok": False, "error": "bad_request"}, status_code=400)
    _user, err = await _admin_guard(body.get("initData", ""))
    if err:
        return err
    report = await asyncio.to_thread(_latest_daily_report)
    return {"ok": True, "report": report}


# --- Simple in-memory rate limiter (token bucket per user/IP) ---
_rate_buckets = defaultdict(lambda: {"tokens": 30.0, "last": time.time()})
RATE_LIMIT = 30  # requests per minute
RATE_REFILL = 0.5  # tokens per second
RATE_BUCKET_MAX = 10000  # xotira himoyasi: bu miqdordan keyin bucket tozalanadi


def _prune_rate_buckets():
    """Uzoq vaqt ishlatilmagan bucketlarni tozalaydi (xotira osmasligi uchun)."""
    if len(_rate_buckets) <= RATE_BUCKET_MAX:
        return
    cutoff = time.time() - 3600
    for k in [k for k, v in _rate_buckets.items() if v["last"] < cutoff]:
        _rate_buckets.pop(k, None)


def _check_rate_limit(key: str) -> bool:
    now = time.time()
    bucket = _rate_buckets[key]
    elapsed = now - bucket["last"]
    bucket["tokens"] = min(RATE_LIMIT, bucket["tokens"] + elapsed * RATE_REFILL)
    bucket["last"] = now
    if bucket["tokens"] >= 1:
        bucket["tokens"] -= 1
        return True
    return False

# Kerak emas: webapp o'z serveridan xizmat qiladi (same-origin).
# "true" credentials + "*" kombinatsiyasi ham bekor qilindi.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Global per-IP rate limit (hamma /api/* uchun, auth'dan oldin) ---
IP_RATE_LIMIT = 120  # requests per minute per IP
IP_RATE_REFILL = 2.0  # tokens per second
_ip_buckets = defaultdict(lambda: {"tokens": float(IP_RATE_LIMIT), "last": time.time()})


@app.middleware("http")
async def _global_rate_limit(request: Request, call_next):
    path = request.url.path
    if path.startswith("/api/"):
        ip = request.client.host if request.client else "unknown"
        now = time.time()
        b = _ip_buckets[ip]
        elapsed = now - b["last"]
        b["tokens"] = min(IP_RATE_LIMIT, b["tokens"] + elapsed * IP_RATE_REFILL)
        b["last"] = now
        if b["tokens"] < 1:
            if len(_ip_buckets) > RATE_BUCKET_MAX:
                cutoff = now - 3600
                for k in [k for k, v in _ip_buckets.items() if v["last"] < cutoff]:
                    _ip_buckets.pop(k, None)
            return JSONResponse({"ok": False, "error": "rate_limited"}, status_code=429)
        b["tokens"] -= 1
    return await call_next(request)

PAY_METHOD_LABELS = {
    "paynet": "PAYNET",
    "uzqr": "UzQR Tezkor",
    "card": "Karta",
    "stars": "Telegram Stars",
}


@app.exception_handler(Exception)
async def global_exc_handler(request, exc):
    logger.exception("Serverda kutilmagan xato: %s", exc)
    return JSONResponse({"ok": False, "error": "server"}, status_code=500)


def parse_init_data(init_data: str):
    """Telegram Mini App initData validatsiyasi."""
    try:
        params = dict(parse_qsl(init_data, keep_blank_values=True))
    except Exception:
        return None
    received_hash = params.pop("hash", None)
    if not received_hash:
        return None
    secret = hmac.new(
        b"WebAppData", config.BOT_TOKEN.encode(), hashlib.sha256
    ).digest()
    data_check = "\n".join(f"{k}={params[k]}" for k in sorted(params))
    calc_hash = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calc_hash, received_hash):
        return None
    try:
        auth_date = int(params.get("auth_date", 0))
    except (TypeError, ValueError):
        auth_date = 0
    if auth_date <= 0 or time.time() - auth_date > 86400:
        return None
    user = params.get("user")
    if not user:
        return None
    try:
        parsed = json.loads(user)
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(parsed, dict) or "id" not in parsed:
        return None
    return parsed


def _parse_amount(raw):
    """Summani xavfsiz parse qiladi. FAQAT oddiy raqam qabul qilinadi.

    '٥٠٠٠٠' (arab raqamlari), '1e10', '1.5', bo'sh qiymat — rad etiladi.
    """
    raw = str(raw if raw is not None else "").strip()
    raw = raw.replace(" ", "").replace("\u00a0", "").replace(",", "")
    # FAQAT ASCII raqamlar (0-9). isdigit() arab raqamlari ham qabul qiladi —
    # shuning uchun alohida tekshiramiz.
    if not raw or len(raw) > 15:
        return None
    if not all(ch in "0123456789" for ch in raw):
        return None
    try:
        val = int(raw)
    except (TypeError, ValueError):
        return None
    return val if val > 0 else None


def stars_count_for_price(price):
    stars = price * 1000 // config.stars_rate_per_1000()
    if price * 1000 % config.stars_rate_per_1000():
        stars += 1
    return max(1, stars)


def format_price(value):
    return f"{(value or 0):,}".replace(",", " ")


def client_line(db_user, uid, prefix="👤 Mijoz"):
    """Mijoz ID + username/ismini qator blokida qaytaradi."""
    ident = ""
    if db_user:
        try:
            uname = db_user["username"] or ""
        except (KeyError, IndexError, TypeError):
            uname = ""
        try:
            name = db_user["full_name"] or ""
        except (KeyError, IndexError, TypeError):
            name = ""
        parts = []
        if uname:
            parts.append("@" + str(uname))
        if name:
            parts.append(str(name))
        ident = " \u2014 ".join(parts)
    return f"{prefix}: <code>{uid}</code>" + (f"\n💠 {ident}" if ident else "")


def verify_init(init_data):
    user = parse_init_data(init_data)
    if not user:
        return None
    return user


def card_pay_info(method, amount):
    s = config.get_settings()
    cards_list = config.all_cards()
    return {
        "method": method,
        "card_number": config.get_active_card(),
        "card_uzcard": s.get("card_uzcard", ""),
        "card_humo": s.get("card_humo", ""),
        "card_tbc": s.get("card_tbc", ""),
        "card_uzum": s.get("card_uzum", ""),
        "card_name": s.get("card_holder", ""),
        "card_phone": s.get("card_phone") or s.get("support_phone", ""),
        "support": f"@{s.get('support_username') or 'donatefm_support'}",
        "support_phone": s.get("support_phone") or s.get("card_phone") or "",
        "support_email": s.get("support_email") or "",
        "admin_username": s.get("admin_username") or s.get("support_username") or "donatefm_support",
        "cards": cards_list,
        "pay_window_seconds": config.pay_window_seconds(),
        "amount": amount,
    }


async def notify_user_manual_payment(user_id, payment_id, order_id, method, amount):
    """Karta/terminal to'lovi uchun foydalanuvchiga bot xabarini yuboradi."""
    src = card_pay_info(method, amount)
    if method == "card":
        lines = []
        labels = {"uzcard": "UzCard", "humo": "Humo", "tbc": "Tbc", "uzum": "Uzum"}
        for c in src.get("cards") or []:
            num = (c.get("number") or "").strip()
            if num:
                holder = f" ({c['holder']})" if c.get("holder") else ""
                lines.append(f"💳 {labels.get(c['key'], c['label'])}: <code>{num}</code>{holder}")
        details = "\n".join(lines) or f"💳 Karta: <code>{src.get('card_number', '')}</code>"
        if src.get("support_phone"):
            details += f"\n📞 Tel: <code>{src['support_phone']}</code>"
        if src.get("support_email"):
            details += f"\n📧 Email: <code>{src['support_email']}</code>"
        if src.get("admin_username"):
            details += f"\n👤 Murojaat uchun: @{src['admin_username']}"
    else:
        details = (
            f"📲 <b>{PAY_METHOD_LABELS.get(method, method)}</b> orqali o'tkazing:\n"
            f"📞 <code>{src['card_phone']}</code>"
        )
    mins = max(1, src["pay_window_seconds"] // 60)
    text = (
        "💳 <b>To'lov uchun ma'lumotlar</b>\n\n"
        f"Summa: <b>{format_price(amount)} so'm</b>\n"
        f"To'lov raqami: <code>#{payment_id}</code>\n"
        f"{details}\n\n"
        f"⏱ To'lov uchun <b>{mins} daqiqa</b> vaqtingiz bor.\n\n"
        "Pulni o'tkazgach, <b>chek/screenshot</b> rasmni shu yerga yuboring — "
        "u <b>avtomatik admin</b>ga boradi.\n\n"
        f"⏰ Vaqt o'tgach ham pul o'tkazgan bo'lsangiz: {src['support']}"
    )
    await asyncio.to_thread(
        services.safe_call_bot,
        lambda: services.get_bot().send_message(user_id, text, parse_mode="HTML"),
    )


# ---------------- Telegram helpers via bot ----------------

async def notify_admins(message, kb=None):
    bot = services.get_bot()
    admin_ids = set(config.ADMIN_IDS)
    for uid in await db.db_admins():
        admin_ids.add(uid)

    def _send_all():
        for admin_id in admin_ids:
            try:
                services.call_bot(
                    lambda admin_id=admin_id: bot.send_message(
                        admin_id, message, parse_mode="HTML", reply_markup=kb
                    )
                )
            except Exception:
                pass

    await asyncio.to_thread(_send_all)


async def send_stars_invoice(chat_id, title, description, stars, payload):
    from aiogram.types import LabeledPrice

    bot = services.get_bot()

    def _send():
        return bot.send_invoice(
            chat_id,
            title=title,
            description=description[:100],
            payload=payload,
            currency="XTR",
            prices=[LabeledPrice(label="XTR", amount=stars)],
            provider_token="",
        )

    try:
        await asyncio.to_thread(services.call_bot, _send)
        return True
    except Exception as e:
        logger.warning("Stars invoice yuborilmadi: %s", e)
        return False


async def get_user_full(init_data):
    user = verify_init(init_data)
    if not user:
        return None, None
    uid = user["id"]
    db_user = await db.get_user(uid)
    if not db_user:
        await db.register_user(uid, user.get("username"), user.get("first_name", ""))
        db_user = await db.get_user(uid)
    return user, db_user


async def _parse_body(request):
    try:
        return await request.json()
    except Exception:
        return None


# ---------------- API ----------------

@app.post("/api/init")
async def api_init(request: Request):
    body = await _parse_body(request)
    if body is None:
        return JSONResponse({"ok": False, "error": "bad_request"}, status_code=400)
    user, db_user = await get_user_full(body.get("initData", ""))
    if not user:
        return JSONResponse({"ok": False, "error": "init_data"}, status_code=400)
    if db_user and "is_banned" in db_user and db_user["is_banned"]:
        return JSONResponse({"ok": False, "error": "banned", "message": "Siz bloklangansiz."}, status_code=403)
    games = kb.load_games()
    s = config.get_settings()
    bot_username = s.get("bot_username") or ""
    # i18n for webapp
    import i18n
    webapp_i18n = i18n.WEBAPP_I18N
    return {
        "ok": True,
        "user": {
            "id": db_user["user_id"],
            "username": db_user["username"],
            "full_name": db_user["full_name"],
            "balance": db_user["balance"],
            "keshbek": db_user.get("keshbek", 0),
            "phone": db_user.get("phone", ""),
            "lang": db_user.get("lang", "uz"),
            "theme": db_user.get("theme", "dark"),
            "ref_count": (await db.get_referral_stats(db_user["user_id"]))["count"],
        },
        "is_admin": user["id"] in (await db.all_admin_ids()),
        "games": games,
        "favorites": await db.list_favorites(db_user["user_id"]),
        "unread_notifs": await db.count_unread_notifications(db_user["user_id"]),
        "card_number": config.get_active_card(),
        "card_name": s.get("card_holder", ""),
        "cards": {c["key"]: c["number"] for c in config.all_cards()},
        "cards_list": config.all_cards(),
        "star_rate_1000": int(s.get("star_rate_1000", 270000)),
        "keshbek_percent": int(s.get("keshbek_percent", 10)),
        "referral_percent": int(s.get("referral_reward_topup_percent", 5)),
        "support": f"@{s.get('support_username') or 'donatefm_support'}",
        "support_phone": s.get("support_phone") or "",
        "support_email": s.get("support_email") or "",
        "invite_link": f"https://t.me/{bot_username}?start=ref_{db_user['user_id']}" if bot_username else "",
        "bot_username": bot_username,
        "admin_username": s.get("admin_username") or s.get("support_username") or "donatefm_support",
        "pay_window_seconds": config.pay_window_seconds(),
        "min_topup": config.min_topup_card(),
        "i18n": webapp_i18n,
        "maintenance": bool(s.get("maintenance", False)),
    }


@app.post("/api/game")
async def api_game(request: Request):
    body = await _parse_body(request)
    if body is None or not body.get("initData"):
        return JSONResponse({"ok": False, "error": "bad_request"}, status_code=400)
    user, _db_user = await get_user_full(body.get("initData", ""))
    if not user:
        return JSONResponse({"ok": False, "error": "init_data"}, status_code=400)
    game = kb.find_game(body.get("game_id", ""))
    if not game:
        return JSONResponse({"ok": False, "error": "game"}, status_code=404)
    saved = await db.get_saved_ids(user["id"], game["id"])
    cfg = config.get_delivery_config()
    can_verify = game["id"] == "freefire" or (
        cfg["provider"] in ("custom", "baulu", "liveop") and cfg["api_url"]
    )
    return {"ok": True, "game": game, "saved_ids": saved, "can_verify": can_verify}


@app.post("/api/save_id")
async def api_save_id(request: Request):
    body = await _parse_body(request)
    if body is None:
        return JSONResponse({"ok": False, "error": "bad_request"}, status_code=400)
    user, db_user = await get_user_full(body.get("initData", ""))
    if not user:
        return JSONResponse({"ok": False, "error": "init_data"}, status_code=400)
    if db_user and "is_banned" in db_user and db_user["is_banned"]:
        return {"ok": False, "error": "banned", "message": "Siz bloklangansiz."}
    game_id = body.get("game_id", "")
    player_id = str(body.get("player_id", "")).strip()
    if not game_id or not player_id or len(player_id) > 100:
        return JSONResponse({"ok": False, "error": "params"}, status_code=400)
    await db.add_saved_id(user["id"], game_id, player_id)
    saved = await db.get_saved_ids(user["id"], game_id)
    return {"ok": True, "saved_ids": saved}


@app.post("/api/verify")
async def api_verify(request: Request):
    body = await _parse_body(request)
    if body is None:
        return JSONResponse({"ok": False, "error": "bad_request"}, status_code=400)
    user, db_user = await get_user_full(body.get("initData", ""))
    if not user:
        return JSONResponse({"ok": False, "error": "init_data"}, status_code=400)
    if db_user and "is_banned" in db_user and db_user["is_banned"]:
        return {"ok": False, "error": "banned", "message": "Siz bloklangansiz."}
    game_id = body.get("game_id", "")
    player_id = str(body.get("player_id", "")).strip()
    if not game_id or not player_id or len(player_id) > 100:
        return JSONResponse({"ok": False, "error": "params"}, status_code=400)
    await db.add_saved_id(user["id"], game_id, player_id)

    import delivery

    result = await delivery.verify_player(game_id, player_id)
    if result:
        return {"ok": True, "name": result["name"]}
    return {"ok": False, "error": "not_found", "message": "Tekshiruv imkoniyati yo'q. ID'ni davom ettirish mumkin."}


@app.post("/api/order")
async def api_order(request: Request):
    body = await _parse_body(request)
    if body is None:
        return JSONResponse({"ok": False, "error": "bad_request"}, status_code=400)
    user, db_user = await get_user_full(body.get("initData", ""))
    if not user:
        return JSONResponse({"ok": False, "error": "init_data"}, status_code=400)
    if not _check_rate_limit(f"order:{user['id']}"):
        return JSONResponse({"ok": False, "error": "rate_limited"}, status_code=429)
    if db_user and "is_banned" in db_user and db_user["is_banned"]:
        return {"ok": False, "error": "banned", "message": "Siz bloklangansiz."}
    if config.get_settings().get("maintenance") and user["id"] not in (await db.all_admin_ids()):
        return {"ok": False, "error": "maintenance", "message": "Texnik ishlar"}

    uid = user["id"]
    game_id = body.get("game_id", "")
    package_id = body.get("package_id", "")
    player_id = str(body.get("player_id", "")).strip()
    method = body.get("method", "balance")
    if method not in ("balance", "stars", "card", "paynet", "uzqr"):
        return JSONResponse({"ok": False, "error": "method"}, status_code=400)

    game = kb.find_game(game_id)
    pkg = kb.find_package(game_id, package_id)
    if not game or not pkg:
        return JSONResponse({"ok": False, "error": "product"}, status_code=404)
    if not player_id:
        return JSONResponse({"ok": False, "error": "player_id"}, status_code=400)
    if len(player_id) > 100:
        return JSONResponse({"ok": False, "error": "player_id"}, status_code=400)
    try:
        import delivery as _dlv_chk
        ok_id, id_hint = _dlv_chk.validate_player_id(game["id"], player_id)
    except Exception:
        ok_id, id_hint = True, ""
    if not ok_id:
        return JSONResponse(
            {
                "ok": False,
                "error": "bad_player_id",
                "message": f"ID formatida xato. Kutilgan: {id_hint}",
            },
            status_code=400,
        )
    price = pkg["price"]

    # Avtomatik o'yinchi nomini aniqlash (Free Fire / Roblox / custom provider)
    player_name = ""
    try:
        import delivery as _dlv
        _res = await asyncio.wait_for(_dlv.verify_player(game["id"], player_id), timeout=12)
        if _res and _res.get("ok") and _res.get("name"):
            player_name = str(_res["name"])[:40]
    except Exception:
        player_name = ""

    if method == "balance":
        if (db_user["balance"] if db_user else 0) < price:
            return {
                "ok": True,
                "need_balance": True,
                "balance": db_user["balance"] if db_user else 0,
                "price": price,
                "message": "Balans yetarli emas",
            }
        order_id, err = await db.purchase(
            uid, game["id"], pkg["name"], str(pkg["amount"]), price, player_id, package_id
        )
        if err == "duplicate" and order_id:
            # Ikki marta bosilgan: balans ikkinchi marta ayirilmasin, yangi
            # order yaratilmasin — mijozga xuddi shu order ko'rsatiladi.
            fresh = await db.get_user(uid)
            return {
                "ok": True,
                "order_id": order_id,
                "duplicate": True,
                "balance": fresh["balance"] if fresh else 0,
                "message": "Bu buyurtma allaqachon berilgan — takrorlanmadi ✅",
            }
        if not order_id:
            return {
                "ok": True,
                "need_balance": True,
                "balance": db_user["balance"] if db_user else 0,
                "price": price,
                "message": "Balans yetarli emas" if err == "balance_low" else "Xatolik yuz berdi",
            }
        await notify_admins(
            f"📦 <b>Yangi buyurtma!</b>\n\n"
            f"🎮 {game['name']}\n📦 {pkg['name']}\n"
            f"🆔 O'yin ID: <code>{player_id}</code>"
            + (f"\n👤 O'yinchi nomi: <b>{player_name}</b>" if player_name else "")
            + f"\n{client_line(db_user, uid)}\n💰 {format_price(price)} so'm\n"
            f"💠 To'lov: Balans",
            kb.order_admin_kb(order_id),
        )
        return {
            "ok": True,
            "order_id": order_id,
            "player_name": player_name,
            "message": "Buyurtma qabul qilindi! 😊",
        }

    if method == "stars":
        stars = stars_count_for_price(price)
        payload = f"buy:{game_id}:{package_id}:{base64.urlsafe_b64encode(player_id.encode()).decode()}"
        sent = await send_stars_invoice(
            uid,
            title=f"{game['name']} — {pkg['name']}",
            description=f"{pkg['name']} uchun to'lov ({format_price(price)} so'm ≈ {stars} ⭐️)",
            stars=stars,
            payload=payload,
        )
        if not sent:
            return JSONResponse({"ok": False, "error": "invoice_failed", "message": "To'lov so'rovini yuborib bo'lmadi"}, status_code=502)
        return {"ok": True, "need_payment": True, "method": "stars", "message": "To'lov so'rovi chatga yuborildi. To'lab bo'lgach buyurtma bajariladi."}

    # manual methods (paynet / uzqr / card)
    # Idempotency: 10 daqiqa ichida bir xil buyurtma kutilmoqda bo'lsa —
    # yangisini yaratmaymiz (ikki marta bosishda 2 ta to'lov so'rovi chiqmasin).
    dup = await db.find_recent_duplicate_order(uid, game["id"], package_id, player_id)
    if dup:
        existing_pay = await db.get_payment_by_ref(f"ord:{int(dup['id'])}")
        return {
            "ok": True,
            "need_manual": True,
            "duplicate": True,
            "payment_id": int(existing_pay["id"]) if existing_pay else 0,
            "order_id": int(dup["id"]),
            "method": method,
            "amount": price,
            "instructions": "Bu buyurtma allaqachon rasmiylashtirilgan ✅",
            "message": "Takrorlanmadi — avvalgi to'lov so'rovi ko'rsatildi.",
            "support": f"@{config.get_settings().get('support_username') or 'donatefm_support'}",
        }

    order_id = await db.create_order(
        uid, game["id"], pkg["name"], str(pkg["amount"]), price, player_id, package_id
    )
    await db.set_order_status(order_id, "to'lov_kutilmoqda")
    payment_id = await db.create_payment(
        uid, method, price, ref=f"ord:{order_id}"
    )
    info = card_pay_info(method, price)
    card_info = []
    if method == "card":
        labels = {"uzcard": "UzCard", "humo": "Humo", "tbc": "Tbc", "uzum": "Uzum"}
        for c in info.get("cards") or []:
            num = (c.get("number") or "").strip()
            if num:
                card_info.append(f"{labels.get(c['key'], c['label'])}: <code>{num}</code>")
        if info.get("card_name"):
            card_info.append(f"Egasi: <b>{info['card_name']}</b>")
        if info.get("support_phone"):
            card_info.append(f"Tel: <code>{info['support_phone']}</code>")
        if info.get("support_email"):
            card_info.append(f"Email: <code>{info['support_email']}</code>")
        if info.get("admin_username"):
            card_info.append(f"Murojaat: @{info['admin_username']}")
        card_info = "\n".join(card_info) or f"Karta: <code>{info['card_number']}</code>"
    else:
        card_info = f"{PAY_METHOD_LABELS.get(method, method)} orqali o'tkazing: <code>{info['card_phone']}</code>"
    pay_method_label = PAY_METHOD_LABELS.get(method, method)
    await notify_admins(
        f"🛒 <b>Yangi buyurtma (to'lov kutilmoqda)</b>\n\n"
        f"🎮 {game['name']}\n📦 {pkg['name']}\n"
        f"🆔 O'yin ID: <code>{player_id}</code>\n"
        f"{client_line(db_user, uid)}\n💰 {format_price(price)} so'm\n"
        f"💠 Usul: {pay_method_label}\n"
        f"💳 To'lov: <code>#{payment_id}</code>",
        kb.confirm_topup_kb(payment_id),
    )
    await notify_user_manual_payment(uid, payment_id, order_id, method, price)
    return {
        "ok": True,
        "need_manual": True,
        "payment_id": payment_id,
        "order_id": order_id,
        "method": method,
        "amount": price,
        "instructions": card_info,
        "message": "To'lov ko'rsatmalari chatga yuborildi. Chekni botga yuboring — admin avtomatik xabar oladi.",
        "card_uzcard": info.get("card_uzcard", ""),
        "card_humo": info.get("card_humo", ""),
        "card_tbc": info.get("card_tbc", ""),
        "card_uzum": info.get("card_uzum", ""),
        "card_name": info.get("card_name", ""),
        "card_phone": info.get("card_phone", ""),
        "cards": info.get("cards", []),
        "support": info.get("support", ""),
        "support_phone": info.get("support_phone", ""),
        "support_email": info.get("support_email", ""),
        "admin_username": info.get("admin_username", ""),
        "pay_window_seconds": info.get("pay_window_seconds", 300),
    }


@app.post("/api/topup")
async def api_topup(request: Request):
    body = await _parse_body(request)
    if body is None:
        return JSONResponse({"ok": False, "error": "bad_request"}, status_code=400)
    user, db_user = await get_user_full(body.get("initData", ""))
    if not user:
        return JSONResponse({"ok": False, "error": "init_data"}, status_code=400)
    if not _check_rate_limit(f"topup:{user['id']}"):
        return JSONResponse({"ok": False, "error": "rate_limited"}, status_code=429)
    if db_user and "is_banned" in db_user and db_user["is_banned"]:
        return {"ok": False, "error": "banned", "message": "Siz bloklangansiz."}
    if config.get_settings().get("maintenance") and user["id"] not in (await db.all_admin_ids()):
        return {"ok": False, "error": "maintenance", "message": "Texnik ishlar"}

    uid = user["id"]
    method = str(body.get("method", "card"))
    if method not in ("card", "paynet", "uzqr", "stars"):
        return JSONResponse({"ok": False, "error": "method"}, status_code=400)
    try:
        amount = _parse_amount(body.get("amount"))
    except Exception:
        amount = None
    if amount is None:
        return JSONResponse({"ok": False, "error": "amount"}, status_code=400)
    min_topup = config.min_topup_card()
    max_topup = config.max_topup_card()
    if amount < min_topup:
        return {"ok": False, "error": "min", "min": min_topup}
    if amount > max_topup:
        return {"ok": False, "error": "max", "max": max_topup}

    if method == "stars":
        stars = stars_count_for_price(amount)
        sent = await send_stars_invoice(
            uid,
            title="Hisobni to'ldirish (Stars)",
            description=f"Balansga {format_price(amount)} so'm qo'shiladi ({stars} ⭐️)",
            stars=stars,
            payload=f"topup:{amount}",
        )
        if not sent:
            return JSONResponse({"ok": False, "error": "invoice_failed", "message": "To'lov so'rovini yuborib bo'lmadi"}, status_code=502)
        return {
            "ok": True,
            "need_payment": True,
            "method": "stars",
            "stars": stars,
            "message": "To'lov so'rovi chatga yuborildi.",
        }

    payment_id = await db.create_payment(uid, method, amount, ref="")
    info = card_pay_info(method, amount)
    if method == "card":
        card_info = []
        labels = {"uzcard": "UzCard", "humo": "Humo", "tbc": "Tbc", "uzum": "Uzum"}
        for c in info.get("cards") or []:
            num = (c.get("number") or "").strip()
            if num:
                card_info.append(f"{labels.get(c['key'], c['label'])}: {num}")
        if info.get("card_name"):
            card_info.append(f"Egasi: {info['card_name']}")
        if info.get("support_phone"):
            card_info.append(f"Tel: {info['support_phone']}")
        if info.get("support_email"):
            card_info.append(f"Email: {info['support_email']}")
        if info.get("admin_username"):
            card_info.append(f"Murojaat: @{info['admin_username']}")
        card_info = "\n".join(card_info) or f"Karta: {info['card_number']}"
    else:
        card_info = f"{PAY_METHOD_LABELS.get(method, method)} orqali o'tkazing: {info['card_phone']}"
    await notify_admins(
        f"💰 <b>Hisobni to'ldirish</b>\n\n"
        f"{client_line(db_user, uid)}\n💰 {format_price(amount)} so'm\n"
        f"💠 Usul: {PAY_METHOD_LABELS.get(method, method)}\n"
        f"💳 To'lov: <code>#{payment_id}</code>",
        kb.confirm_topup_kb(payment_id),
    )
    await notify_user_manual_payment(uid, payment_id, 0, method, amount)
    return {
        "ok": True,
        "need_manual": True,
        "payment_id": payment_id,
        "method": method,
        "amount": amount,
        "instructions": card_info,
        "message": "To'lov ko'rsatmalari chatga yuborildi. Chekni botga yuboring — admin avtomatik xabar oladi.",
        "card_uzcard": info.get("card_uzcard", ""),
        "card_humo": info.get("card_humo", ""),
        "card_tbc": info.get("card_tbc", ""),
        "card_uzum": info.get("card_uzum", ""),
        "card_name": info.get("card_name", ""),
        "card_phone": info.get("card_phone", ""),
        "cards": info.get("cards", []),
        "support": info.get("support", ""),
        "support_phone": info.get("support_phone", ""),
        "support_email": info.get("support_email", ""),
        "admin_username": info.get("admin_username", ""),
        "pay_window_seconds": info.get("pay_window_seconds", 300),
    }


@app.post("/api/promo")
async def api_promo(request: Request):
    body = await _parse_body(request)
    if body is None:
        return JSONResponse({"ok": False, "error": "bad_request"}, status_code=400)
    user, db_user = await get_user_full(body.get("initData", ""))
    if not user:
        return JSONResponse({"ok": False, "error": "init_data"}, status_code=400)
    if db_user and "is_banned" in db_user and db_user["is_banned"]:
        return {"ok": False, "error": "banned", "message": "Siz bloklangansiz."}
    if not _check_rate_limit(f"promo:{user['id']}"):
        return JSONResponse({"ok": False, "error": "rate_limited"}, status_code=429)
    code = str(body.get("code", "")).strip()
    if not code:
        return JSONResponse({"ok": False, "error": "code"}, status_code=400)
    if len(code) > 64:
        return JSONResponse({"ok": False, "error": "code"}, status_code=400)
    ok, msg = await db.redeem_promo(user["id"], code)
    if ok:
        db_user = await db.get_user(user["id"])
        return {"ok": True, "message": f"{format_price(int(msg))} so'm qo'shildi", "balance": db_user["balance"]}
    return {"ok": False, "error": "promo", "message": msg}


@app.post("/api/referral")
async def api_referral(request: Request):
    body = await _parse_body(request)
    if body is None:
        return JSONResponse({"ok": False, "error": "bad_request"}, status_code=400)
    user, db_user = await get_user_full(body.get("initData", ""))
    if not user:
        return JSONResponse({"ok": False, "error": "init_data"}, status_code=400)
    if db_user and "is_banned" in db_user and db_user["is_banned"]:
        return {"ok": False, "error": "banned", "message": "Siz bloklangansiz."}
    s = config.get_settings()
    bot_username = s.get("bot_username") or ""
    stats = await db.get_referral_stats(user["id"])
    return {
        "ok": True,
        "link": f"https://t.me/{bot_username}?start=ref_{user['id']}" if bot_username else "",
        "count": stats["count"],
        "total_reward": stats["total_reward"],
        "percent": int(s.get("referral_reward_topup_percent", 5)),
    }


@app.post("/api/history")
async def api_history(request: Request):
    body = await _parse_body(request)
    if body is None:
        return JSONResponse({"ok": False, "error": "bad_request"}, status_code=400)
    user, db_user = await get_user_full(body.get("initData", ""))
    if not user:
        return JSONResponse({"ok": False, "error": "init_data"}, status_code=400)
    if db_user and "is_banned" in db_user and db_user["is_banned"]:
        return {"ok": False, "error": "banned", "message": "Siz bloklangansiz."}
    orders = await db.get_user_orders(user["id"], 40)
    payments = await db.get_user_payments(user["id"], 40)
    games = {g["id"]: g["name"] for g in kb.load_games()}
    return {
        "ok": True,
        "orders": [
            {
                "id": o["id"],
                "platform": o["platform"],
                "platform_name": games.get(o["platform"], o["platform"]),
                "package_name": o["package_name"],
                "amount": o["amount"],
                "player_id": o["game_id"],
                "price": o["price"],
                "status": o["status"],
                "created_at": o["created_at"],
                "package_id": o.get("package_id", ""),
                "rating": o.get("rating", 0),
            }
            for o in orders
        ],
        "payments": [
            {
                "id": p["id"],
                "method": p["method"],
                "amount": p["amount"],
                "status": p["status"],
                "created_at": p["created_at"],
            }
            for p in payments
        ],
    }


@app.post("/api/save_phone")
async def api_save_phone(request: Request):
    body = await _parse_body(request)
    if body is None:
        return JSONResponse({"ok": False, "error": "bad_request"}, status_code=400)
    user, db_user = await get_user_full(body.get("initData", ""))
    if not user:
        return JSONResponse({"ok": False, "error": "init_data"}, status_code=400)
    if db_user and "is_banned" in db_user and db_user["is_banned"]:
        return {"ok": False, "error": "banned", "message": "Siz bloklangansiz."}
    phone = str(body.get("phone", "")).strip()
    await db.save_phone(user["id"], phone)
    return {"ok": True, "phone": phone}


@app.post("/api/save_lang")
async def api_save_lang(request: Request):
    body = await _parse_body(request)
    if body is None:
        return JSONResponse({"ok": False, "error": "bad_request"}, status_code=400)
    user, db_user = await get_user_full(body.get("initData", ""))
    if not user:
        return JSONResponse({"ok": False, "error": "init_data"}, status_code=400)
    if db_user and "is_banned" in db_user and db_user["is_banned"]:
        return {"ok": False, "error": "banned", "message": "Siz bloklangansiz."}
    lang = str(body.get("lang", "uz")).strip()
    if lang not in ("uz", "ru", "en"):
        return JSONResponse({"ok": False, "error": "lang"}, status_code=400)
    await db.save_lang(user["id"], lang)
    return {"ok": True, "lang": lang}


@app.post("/api/save_theme")
async def api_save_theme(request: Request):
    body = await _parse_body(request)
    if body is None:
        return JSONResponse({"ok": False, "error": "bad_request"}, status_code=400)
    user, _db_user = await get_user_full(body.get("initData", ""))
    if not user:
        return JSONResponse({"ok": False, "error": "init_data"}, status_code=400)
    theme = await db.save_theme(user["id"], body.get("theme", "dark"))
    return {"ok": True, "theme": theme}


@app.post("/api/favorites")
async def api_favorites(request: Request):
    body = await _parse_body(request)
    if body is None:
        return JSONResponse({"ok": False, "error": "bad_request"}, status_code=400)
    user, _db_user = await get_user_full(body.get("initData", ""))
    if not user:
        return JSONResponse({"ok": False, "error": "init_data"}, status_code=400)
    game_id = str(body.get("game_id", "")).strip()
    package_id = str(body.get("package_id", "")).strip()
    if not game_id:
        return JSONResponse({"ok": False, "error": "params"}, status_code=400)
    if body.get("toggle"):
        active = await db.toggle_favorite(user["id"], game_id, package_id)
        favorites = await db.list_favorites(user["id"])
        return {"ok": True, "active": active, "favorites": favorites}
    favorites = await db.list_favorites(user["id"])
    active = await db.is_favorite(user["id"], game_id, package_id)
    return {"ok": True, "active": active, "favorites": favorites}


REVIEWS_DIR = os.path.join(config.BASE_DIR, "data", "reviews")
_REVIEW_FNAME_RE = _re.compile(r"^r\d+_[0-9a-f]{10}\.(jpg|png|webp)$")
_REVIEW_PHOTO_MAX = 3 * 1024 * 1024  # 3 MB


def _save_review_photo(order_id, data_url):
    """Base64 dataURL ni data/reviews/ ga yozadi — fayl nomini qaytaradi (xatolikda '')."""
    try:
        os.makedirs(REVIEWS_DIR, exist_ok=True)
        raw = str(data_url or "")
        if raw.startswith("data:"):
            marker = "base64,"
            idx = raw.find(marker)
            if idx < 0:
                return ""
            raw = raw[idx + len(marker):]
        data = base64.b64decode(raw, validate=False)
        if not data or len(data) > _REVIEW_PHOTO_MAX:
            return ""
        if data[:3] == b"\xff\xd8\xff":
            ext = "jpg"
        elif data[:8] == b"\x89PNG\r\n\x1a\n":
            ext = "png"
        elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            ext = "webp"
        else:
            return ""
        fname = f"r{int(order_id)}_{os.urandom(5).hex()}.{ext}"
        with open(os.path.join(REVIEWS_DIR, fname), "wb") as f:
            f.write(data)
        return fname
    except Exception:
        logger.warning("review photo saqlanmadi")
        return ""


@app.get("/reviews/{fname}")
async def serve_review_photo(fname: str):
    if not _REVIEW_FNAME_RE.match(fname):
        return JSONResponse({"ok": False}, status_code=404)
    path = os.path.join(REVIEWS_DIR, fname)
    if not os.path.isfile(path):
        return JSONResponse({"ok": False}, status_code=404)
    media = {"jpg": "image/jpeg", "png": "image/png", "webp": "image/webp"}[fname.rsplit(".", 1)[1]]
    return FileResponse(path, media_type=media, headers={"Cache-Control": "public, max-age=86400"})


@app.post("/api/rate")
async def api_rate(request: Request):
    body = await _parse_body(request)
    if body is None:
        return JSONResponse({"ok": False, "error": "bad_request"}, status_code=400)
    user, _db_user = await get_user_full(body.get("initData", ""))
    if not user:
        return JSONResponse({"ok": False, "error": "init_data"}, status_code=400)
    try:
        order_id = int(body.get("order_id", 0))
        stars = int(body.get("stars", 0))
    except (TypeError, ValueError):
        return JSONResponse({"ok": False, "error": "params"}, status_code=400)
    review = str(body.get("review", "")).strip()[:500]
    photo = ""
    photo_raw = body.get("photo")
    if photo_raw:
        if len(str(photo_raw)) > _REVIEW_PHOTO_MAX * 2:
            return {"ok": False, "error": "too_big", "message": "Rasm hajmi juda katta."}
        photo = _save_review_photo(order_id, str(photo_raw))
        if not photo:
            return {"ok": False, "error": "photo", "message": "Rasm qabul qilinmadi."}
    ok, info = await db.set_order_rating(order_id, user["id"], stars, review, photo)
    if not ok:
        return {"ok": False, "error": info, "message": info}
    return {"ok": True, "stars": info, "message": f"Rahmat! {info}⭐️ qabul qilindi."}


@app.post("/api/reviews")
async def api_reviews(request: Request):
    body = await _parse_body(request)
    if body is None:
        return JSONResponse({"ok": False, "error": "bad_request"}, status_code=400)
    user, _db_user = await get_user_full(body.get("initData", ""))
    if not user:
        return JSONResponse({"ok": False, "error": "init_data"}, status_code=400)
    game_id = str(body.get("game_id", "")).strip()
    if not game_id or len(game_id) > 64:
        return JSONResponse({"ok": False, "error": "params"}, status_code=400)
    rows = await db.list_game_reviews(game_id, 30)
    aggregate = await db.get_game_rating(game_id)
    reviews = []
    for r in rows:
        name = (r["full_name"] or "").strip()
        parts = name.split()
        if parts:
            author = parts[0] + (" " + parts[1][0] + "." if len(parts) > 1 and parts[1] else "")
        else:
            author = (r["username"] or "").strip() or "User"
        reviews.append({
            "order_id": r["order_id"],
            "stars": r["stars"],
            "review": r["review"] or "",
            "photo": r["photo"] or "",
            "created_at": r["created_at"],
            "author": author,
        })
    return {"ok": True, "reviews": reviews, "avg": round(aggregate["avg"] or 0, 1), "count": aggregate["count"]}


@app.post("/api/notifications")
async def api_notifications(request: Request):
    body = await _parse_body(request)
    if body is None:
        return JSONResponse({"ok": False, "error": "bad_request"}, status_code=400)
    user, _db_user = await get_user_full(body.get("initData", ""))
    if not user:
        return JSONResponse({"ok": False, "error": "init_data"}, status_code=400)
    mark_read = bool(body.get("mark_read"))
    if mark_read:
        await db.mark_notifications_read(user["id"])
    rows = await db.get_user_notifications(user["id"], 30)
    unread = await db.count_unread_notifications(user["id"])
    return {
        "ok": True,
        "unread": unread,
        "notifications": [
            {"id": r["id"], "text": r["text"], "created_at": r["created_at"], "is_read": r["is_read"]}
            for r in rows
        ],
    }


@app.post("/api/ref_leaderboard")
async def api_ref_leaderboard(request: Request):
    body = await _parse_body(request)
    if body is None:
        return JSONResponse({"ok": False, "error": "bad_request"}, status_code=400)
    user, _db_user = await get_user_full(body.get("initData", ""))
    if not user:
        return JSONResponse({"ok": False, "error": "init_data"}, status_code=400)
    rows = await db.get_ref_leaderboard(20)
    return {
        "ok": True,
        "board": [
            {
                "user_id": r["user_id"],
                "username": r["username"] or "",
                "full_name": r["full_name"] or "",
                "invites": r["invites"],
                "reward": r["reward"],
            }
            for r in rows
        ],
    }


@app.post("/api/reorder")
async def api_reorder(request: Request):
    body = await _parse_body(request)
    if body is None:
        return JSONResponse({"ok": False, "error": "bad_request"}, status_code=400)
    user, db_user = await get_user_full(body.get("initData", ""))
    if not user:
        return JSONResponse({"ok": False, "error": "init_data"}, status_code=400)
    if db_user and "is_banned" in db_user and db_user["is_banned"]:
        return {"ok": False, "error": "banned", "message": "Siz bloklangansiz."}
    if config.get_settings().get("maintenance") and user["id"] not in (await db.all_admin_ids()):
        return {"ok": False, "error": "maintenance", "message": "Texnik ishlar"}

    try:
        order_id = int(body.get("order_id", 0))
    except (TypeError, ValueError):
        return JSONResponse({"ok": False, "error": "params"}, status_code=400)
    o = await db.get_order(order_id)
    if not o or o["user_id"] != user["id"]:
        return JSONResponse({"ok": False, "error": "not_found"}, status_code=404)
    package_id = o.get("package_id", "")
    if not package_id:
        return {"ok": False, "error": "no_package", "message": "Bu buyurtmani qayta buyurtma qilib bo'lmaydi."}
    game = kb.find_game(o["platform"])
    pkg = kb.find_package(o["platform"], package_id)
    if not game or not pkg:
        return {"ok": False, "error": "product", "message": "Mahsulot topilmadi."}
    player_id = o["game_id"]
    price = pkg["price"]
    if (db_user["balance"] if db_user else 0) < price:
        return {"ok": False, "error": "balance_low", "message": "Balans yetarli emas."}
    new_id, _err = await db.purchase(
        user["id"], game["id"], pkg["name"], str(pkg["amount"]), price, player_id, package_id
    )
    if not new_id:
        return {"ok": False, "error": "error", "message": "Xatolik yuz berdi."}
    await notify_admins(
        f"🔁 <b>Qayta buyurtma #{new_id}</b>\n\n"
        f"🎮 {game['name']}\n📦 {pkg['name']}\n"
        f"🆔 O'yin ID: <code>{player_id}</code>\n"
        f"{client_line(db_user, user['id'])}\n💰 {format_price(price)} so'm\n"
        f"💠 To'lov: Balans",
        kb.order_admin_kb(new_id),
    )
    fresh = await db.get_user(user["id"])
    return {
        "ok": True,
        "order_id": new_id,
        "balance": fresh["balance"] if fresh else 0,
        "message": f"Buyurtma #{new_id} qabul qilindi! 😊",
    }


@app.post("/api/last_order")
async def api_last_order(request: Request):
    body = await _parse_body(request)
    if body is None:
        return JSONResponse({"ok": False, "error": "bad_request"}, status_code=400)
    user, db_user = await get_user_full(body.get("initData", ""))
    if not user:
        return JSONResponse({"ok": False, "error": "init_data"}, status_code=400)
    if db_user and "is_banned" in db_user and db_user["is_banned"]:
        return {"ok": False, "error": "banned", "message": "Siz bloklangansiz."}
    game_id = str(body.get("game_id", "")).strip()
    if not game_id or len(game_id) > 64:
        return JSONResponse({"ok": False, "error": "params"}, status_code=400)
    orders = await db.get_user_orders(user["id"], 50)
    for o in orders:
        if (
            o["platform"] == game_id
            and o.get("package_id")
            and o["status"] in ("bajarildi", "kutilmoqda", "to'lov_kutilmoqda")
        ):
            return {
                "ok": True,
                "order": {
                    "id": o["id"],
                    "package_name": o["package_name"],
                    "price": o["price"],
                    "player_id": o["game_id"],
                },
            }
    return {"ok": True, "order": None}


@app.post("/api/admin/chart")
async def api_admin_chart(request: Request):
    body = await _parse_body(request)
    if body is None:
        return JSONResponse({"ok": False, "error": "bad_request"}, status_code=400)
    _user, err = await _admin_guard(body.get("initData", ""))
    if err:
        return err
    series = await db.get_daily_series(7)
    return {"ok": True, "series": series}


@app.post("/api/admin/promos")
async def api_admin_promos(request: Request):
    body = await _parse_body(request)
    if body is None:
        return JSONResponse({"ok": False, "error": "bad_request"}, status_code=400)
    _user, err = await _admin_guard(body.get("initData", ""))
    if err:
        return err
    promos = await db.list_promos()
    return {
        "ok": True,
        "promos": [
            {
                "code": p["code"],
                "reward_amount": p["reward_amount"],
                "max_uses": p["max_uses"],
                "used_count": p.get("used_count", 0),
                "expires_at": p["expires_at"] or "",
            }
            for p in promos
        ],
    }


@app.post("/api/admin/promo_create")
async def api_admin_promo_create(request: Request):
    body = await _parse_body(request)
    if body is None:
        return JSONResponse({"ok": False, "error": "bad_request"}, status_code=400)
    user, err = await _admin_guard(body.get("initData", ""))
    if err:
        return err
    code = str(body.get("code", "")).strip().upper()
    if not code or len(code) > 32:
        return {"ok": False, "error": "code", "message": "Noto'g'ri kod."}
    try:
        amount = int(body.get("amount", 0))
        max_uses = int(body.get("max_uses", 100))
    except (TypeError, ValueError):
        return {"ok": False, "error": "amount", "message": "Noto'g'ri summa."}
    if amount <= 0:
        return {"ok": False, "error": "amount", "message": "Summa 0 dan katta bo'lishi kerak."}
    existing = await db.get_promo(code)
    if existing:
        return {"ok": False, "error": "exists", "message": "Bunday kod allaqachon bor."}
    await db.create_promo(code, amount, max(1, max_uses))
    await db.record_admin_audit(user["id"], "promo_create", f"{code} → {amount} so'm x{max_uses}")
    return {"ok": True, "message": f"Promokod {code} yaratildi ✅"}


@app.post("/api/admin/promo_delete")
async def api_admin_promo_delete(request: Request):
    body = await _parse_body(request)
    if body is None:
        return JSONResponse({"ok": False, "error": "bad_request"}, status_code=400)
    user, err = await _admin_guard(body.get("initData", ""))
    if err:
        return err
    code = str(body.get("code", "")).strip().upper()
    if not code or len(code) > 32:
        return {"ok": False, "error": "params"}
    from database import get_connection
    conn = await get_connection()
    try:
        await conn.execute("DELETE FROM promocodes WHERE code = ?", (code,))
        await conn.commit()
    finally:
        await conn.close()
    await db.record_admin_audit(user["id"], "promo_delete", code)
    return {"ok": True, "message": f"Promokod {code} o'chirildi"}


# ---------------- ADMIN API (Mini App) ----------------

async def _admin_guard(init_data):
    user, _db_user = await get_user_full(init_data)
    if not user:
        return None, JSONResponse({"ok": False, "error": "init_data"}, status_code=400)
    if user["id"] not in (await db.all_admin_ids()):
        return None, JSONResponse({"ok": False, "error": "not_admin"}, status_code=403)
    return user, None


@app.post("/api/admin/stats")
async def api_admin_stats(request: Request):
    body = await _parse_body(request)
    if body is None:
        return JSONResponse({"ok": False, "error": "bad_request"}, status_code=400)
    _user, err = await _admin_guard(body.get("initData", ""))
    if err:
        return err
    s = await db.get_stats()
    from config import get_delivery_config
    cfg = get_delivery_config()
    return {
        "ok": True,
        "stats": {
            "users": s["users"],
            "orders_done": s["orders"],
            "revenue": s["revenue"],
            "pending_orders": s["pending"],
            "pending_payments": s["pending_pay"],
            "topups": s["topups"],
            "today_orders": s["today_orders"],
            "month_users": s.get("month_users", 0),
            "month_new_users": s.get("month_new_users", 0),
            "month_revenue": s.get("month_revenue", 0),
            "month_topups": s.get("month_topups", 0),
        },
        "delivery": {
            "provider": cfg["provider"],
            "api_url": cfg["api_url"],
            "interval": cfg["interval"],
        },
        "settings": {
            "card_active": config.get_settings().get("card_active", "uzcard"),
            "star_rate_1000": config.get_settings().get("star_rate_1000", 270000),
            "keshbek_percent": config.get_settings().get("keshbek_percent", 10),
            "referral_percent": config.get_settings().get("referral_reward_topup_percent", 5),
            "delivery_provider": cfg["provider"],
            "min_topup_card": config.min_topup_card(),
            "max_topup_card": config.max_topup_card(),
        },
    }


@app.post("/api/admin/orders")
async def api_admin_orders(request: Request):
    body = await _parse_body(request)
    if body is None:
        return JSONResponse({"ok": False, "error": "bad_request"}, status_code=400)
    user, err = await _admin_guard(body.get("initData", ""))
    if err:
        return err
    # Rate limit check
    if not _check_rate_limit(f"admin:{user['id']}"):
        return JSONResponse({"ok": False, "error": "rate_limited"}, status_code=429)
    try:
        limit = int(body.get("limit", 30))
    except (TypeError, ValueError):
        limit = 30
    query = str(body.get("query", "")).strip()
    orders = await db.get_orders_by_filter(
        platform=body.get("platform", ""),
        status=body.get("status", "kutilmoqda"),
        limit=min(limit, 100),
        query=query,
    )
    games = {g["id"]: g["name"] for g in kb.load_games()}
    return {
        "ok": True,
        "orders": [
            {
                "id": o["id"],
                "platform": o["platform"],
                "platform_name": games.get(o["platform"], o["platform"]),
                "package_name": o["package_name"],
                "player_id": o["game_id"],
                "price": o["price"],
                "status": o["status"],
                "user_id": o["user_id"],
                "created_at": o["created_at"],
            }
            for o in orders
        ],
    }


@app.post("/api/admin/order_action")
async def api_admin_order_action(request: Request):
    body = await _parse_body(request)
    if body is None:
        return JSONResponse({"ok": False, "error": "bad_request"}, status_code=400)
    user, err = await _admin_guard(body.get("initData", ""))
    if err:
        return err
    try:
        order_id = int(body.get("order_id", 0))
    except (TypeError, ValueError):
        return JSONResponse({"ok": False, "error": "order_id"}, status_code=400)
    action = body.get("action", "")
    o = await db.get_order(order_id)
    if not o:
        return {"ok": False, "error": "not_found"}
    if action == "ok":
        if o["status"] != "kutilmoqda":
            return {"ok": False, "error": "wrong_status", "message": f"Holat: {o['status']}"}
        await db.set_order_status(order_id, "bajarildi")
        await db.record_admin_audit(user["id"], "order_ok", f"order={order_id} user={o['user_id']} price={o['price']}")
        lang = (await db.get_user(o["user_id"]) or {}).get("lang", "uz")
        await asyncio.to_thread(order_notify.safe_notify, None, o, "bajarildi", "", lang)
        return {"ok": True, "message": "Bajarildi"}
    if action == "refund":
        if o["status"] == "rad_etildi":
            return {"ok": False, "error": "already_refunded"}
        if o["status"] == "to'lov_kutilmoqda":
            return {"ok": False, "error": "unpaid", "message": "To'lov hali tasdiqlanmagan"}
        # Atomar o'tish: faqat shu holatdan rad_etildi ga o'tsa, pul qaytaramiz
        changed = await db.set_order_status_if(order_id, "rad_etildi", o["status"])
        if not changed:
            return {"ok": False, "error": "race", "message": "Holat o'zgargan, qayta yuklang"}
        await db.refund_balance(o["user_id"], o["price"], ref=f"ord:{order_id}")
        await db.record_admin_audit(user["id"], "order_refund", f"order={order_id} user={o['user_id']} price={o['price']}")
        lang = (await db.get_user(o["user_id"]) or {}).get("lang", "uz")
        await asyncio.to_thread(
            order_notify.safe_notify, None, o, "rad_etildi",
            i18n.t(lang, "order_reason_admin"), lang,
        )
        return {"ok": True, "message": "Rad etildi va pul qaytarildi"}
    if action == "delivery":
        import delivery as dlv
        res = await dlv.deliver_order(o)
        lang = (await db.get_user(o["user_id"]) or {}).get("lang", "uz")
        if res["status"] == "done":
            await asyncio.to_thread(order_notify.safe_notify, None, o, "bajarildi", "", lang)
        elif res["status"] in ("fail", "error"):
            await db.add_notification(o["user_id"], order_notify.reminder_message(o, lang, res["msg"]))
        return {"ok": True, "status": res["status"], "message": res["msg"]}
    return {"ok": False, "error": "action"}


def _norm_q(raw) -> str:
    q = str(raw or "").strip()
    if "t.me/" in q:
        q = q.split("t.me/", 1)[1]
        q = q.split("/", 1)[0].split("?", 1)[0].split("#", 1)[0]
    q = q.removeprefix("@")
    return q.strip()[:200]


@app.post("/api/admin/payments")
async def api_admin_payments(request: Request):
    body = await _parse_body(request)
    if body is None:
        return JSONResponse({"ok": False, "error": "bad_request"}, status_code=400)
    user, err = await _admin_guard(body.get("initData", ""))
    if err:
        return err
    if not _check_rate_limit(f"admin:{user['id']}"):
        return JSONResponse({"ok": False, "error": "rate_limited"}, status_code=429)
    query = _norm_q(body.get("query", ""))
    if body.get("all"):
        payments = await db.search_payments(query, 50)
    else:
        payments = await db.get_confirmable_payments()
        if query:
            payments = [p for p in payments if query.lower() in str(p["id"]).lower() or query.lower() in str(p["user_id"]).lower() or query.lower() in (p["method"] or "").lower() or query.lower() in (p["ref"] or "").lower()]
    return {
        "ok": True,
        "payments": [
            {
                "id": p["id"],
                "user_id": p["user_id"],
                "method": p["method"],
                "amount": p["amount"],
                "status": p["status"],
                "ref": p["ref"],
                "created_at": p["created_at"],
            }
            for p in payments
        ],
    }


@app.post("/api/admin/payment_action")
async def api_admin_payment_action(request: Request):
    body = await _parse_body(request)
    if body is None:
        return JSONResponse({"ok": False, "error": "bad_request"}, status_code=400)
    user, err = await _admin_guard(body.get("initData", ""))
    if err:
        return err
    try:
        payment_id = int(body.get("payment_id", 0))
    except (TypeError, ValueError):
        return JSONResponse({"ok": False, "error": "payment_id"}, status_code=400)
    action = body.get("action", "")
    p = await db.get_payment(payment_id)
    if not p:
        return {"ok": False, "error": "not_found"}
    if p["status"] not in ("kutilmoqda", "rad_etildi"):
        return {"ok": False, "error": "already", "message": "Bu to'lov allaqachon hal qilingan"}
    if p["method"] == "refund":
        return {"ok": False, "error": "refund", "message": "Bu qaytaruv to'lovi — tasdiqlab bo'lmaydi"}
    late = p["status"] == "rad_etildi"
    if action == "ok":
        if p["ref"] and p["ref"].startswith("ord:"):
            order_id = int(p["ref"].split(":")[1])
            o = await db.get_order(order_id)
            if not o or o["user_id"] != p["user_id"]:
                return {"ok": False, "error": "order_missing"}
            if o["status"] not in ("to'lov_kutilmoqda", "rad_etildi"):
                return {"ok": False, "error": "already", "message": "Buyurtma holati o'zgargan"}
            await db.set_payment_status(payment_id, "tasdiqlandi")
            await db.set_order_status(order_id, "kutilmoqda")
            await db.record_admin_audit(user["id"], "payment_ok", f"payment={payment_id} order={order_id} user={p['user_id']} amount={p['amount']}")
            lang = (await db.get_user(o["user_id"]) or {}).get("lang", "uz")
            await asyncio.to_thread(order_notify.safe_notify, None, o, "kutilmoqda", "", lang)
            return {"ok": True, "message": f"To'lov tasdiqlandi. Buyurtma #{order_id} kutilmoqda." + (" (muddati o'tgan edi)" if late else "")}
        ok = await db.confirm_payment(payment_id, p["user_id"], p["amount"])
        if not ok:
            return {"ok": False, "error": "already"}
        await db.record_admin_audit(user["id"], "payment_ok", f"payment={payment_id} user={p['user_id']} amount={p['amount']}")
        try:
            await asyncio.to_thread(
                services.safe_call_bot,
                lambda: services.get_bot().send_message(
                    p["user_id"],
                    f"✅ <b>To'lovingiz tasdiqlandi!</b>\n\n"
                    f"Summa: <b>{format_price(p['amount'])} so'm</b> balansingizga qo'shildi.",
                    parse_mode="HTML",
                ),
            )
        except Exception:
            pass
        return {"ok": True, "message": f"{format_price(p['amount'])} so'm qo'shildi." + (" (muddati o'tgan edi)" if late else "")}
    if action == "no":
        await db.set_payment_status(payment_id, "rad_etildi")
        await db.record_admin_audit(user["id"], "payment_reject", f"payment={payment_id} user={p['user_id']} amount={p['amount']}")
        try:
            await asyncio.to_thread(
                services.safe_call_bot,
                lambda: services.get_bot().send_message(
                    p["user_id"],
                    f"❌ To'lov rad etildi.\nTo'lov: #{payment_id}\n"
                    f"Agar xato bo'lsa, admin bilan bog'laning.",
                    parse_mode="HTML",
                ),
            )
        except Exception:
            pass
        return {"ok": True, "message": "Rad etildi"}
    return {"ok": False, "error": "action"}


@app.post("/api/admin/users")
async def api_admin_users(request: Request):
    body = await _parse_body(request)
    if body is None:
        return JSONResponse({"ok": False, "error": "bad_request"}, status_code=400)
    _user, err = await _admin_guard(body.get("initData", ""))
    if err:
        return err
    q = _norm_q(body.get("query", ""))
    if q:
        users = await db.search_users(q)
    else:
        users = await db.get_all_users()
    return {
        "ok": True,
        "users": [
            {
                "id": u["user_id"],
                "username": u["username"],
                "full_name": u["full_name"],
                "balance": u["balance"],
                "total_topup": u["total_topup"],
                "is_banned": u["is_banned"],
                "reg_date": u["reg_date"],
            }
            for u in users[:50]
        ],
    }


@app.post("/api/admin/user_action")
async def api_admin_user_action(request: Request):
    body = await _parse_body(request)
    if body is None:
        return JSONResponse({"ok": False, "error": "bad_request"}, status_code=400)
    user, err = await _admin_guard(body.get("initData", ""))
    if err:
        return err
    try:
        target = int(body.get("user_id", 0))
    except (TypeError, ValueError):
        return JSONResponse({"ok": False, "error": "user_id"}, status_code=400)
    action = body.get("action", "")
    if action in ("ban", "unban"):
        if target == user["id"]:
            return {"ok": False, "error": "self_ban", "message": "O'zingizni ban qila olmaysiz"}
        if action == "ban" and target in (await db.all_admin_ids()):
            return {"ok": False, "error": "admin_user", "message": "Adminlarni ban qilib bo'lmaydi"}
        if not (await db.get_user(target)):
            return JSONResponse({"ok": False, "error": "not_found"}, status_code=404)
        await db.set_user_ban(target, 1 if action == "ban" else 0)
        await db.record_admin_audit(user["id"], f"user_{action}", f"target={target}")
        return {"ok": True, "message": "Ban qo'yildi" if action == "ban" else "Ban olib tashlandi"}
    if action in ("plus", "minus"):
        try:
            amount = _parse_amount(body.get("amount"))
        except Exception:
            amount = None
        if amount is None:
            return JSONResponse({"ok": False, "error": "amount"}, status_code=400)
        if not (await db.get_user(target)):
            return JSONResponse({"ok": False, "error": "not_found"}, status_code=404)
        if action == "plus":
            await db.add_balance(target, amount, method="admin")
        else:
            u = await db.get_user(target)
            await db.set_user_balance(target, max(0, u["balance"] - amount))
        u = await db.get_user(target)
        await db.record_admin_audit(user["id"], f"balance_{action}", f"target={target} amount={amount}")
        new_bal = u["balance"] if u else 0
        return {
            "ok": True,
            "balance": new_bal,
            "message": f"Balans yangilandi: <b>{format_price(new_bal)} so'm</b>",
        }
    return {"ok": False, "error": "action"}


@app.post("/api/admin/audit")
async def api_admin_audit(request: Request):
    body = await _parse_body(request)
    if body is None:
        return JSONResponse({"ok": False, "error": "bad_request"}, status_code=400)
    _user, err = await _admin_guard(body.get("initData", ""))
    if err:
        return err
    limit = int(body.get("limit", 100))
    rows = await db.get_admin_audit(min(limit, 200))
    return {
        "ok": True,
        "audit": [
            {
                "id": r["id"],
                "admin_id": r["admin_id"],
                "action": r["action"],
                "detail": r["detail"],
                "created_at": r["created_at"],
            }
            for r in rows
        ],
    }


import re as _re

# ==================== ADMIN: SETTINGS ====================

_SETTINGS_INT_FIELDS = {
    "keshbek_percent": (0, 100),
    "referral_reward_topup_percent": (0, 100),
    "star_rate_1000": (1, 10_000_000_000),
    "min_topup_card": (0, 10_000_000_000),
    "max_topup_card": (0, 10_000_000_000),
    "pay_window_seconds": (30, 86400),
}
_SETTINGS_STR_FIELDS = ("support_username", "support_phone", "support_email", "admin_username")
_CARD_OPTIONS = ("uzcard", "humo", "tbc", "uzum")
# Yoqish/o'chirish mumkin bo'lgan funksiya sozlamalari
_SETTINGS_BOOL_FIELDS = (
    "auto_delivery_enabled",
    "ocr_enabled",
    "nickname_check_enabled",
    "id_validation_enabled",
    "chek_reminder_enabled",
    "maintenance",
)


@app.post("/api/admin/settings_get")
async def api_admin_settings_get(request: Request):
    body = await _parse_body(request)
    if body is None:
        return JSONResponse({"ok": False, "error": "bad_request"}, status_code=400)
    _user, err = await _admin_guard(body.get("initData", ""))
    if err:
        return err
    s = config.get_settings()
    return {
        "ok": True,
        "settings": {
            "keshbek_percent": int(s.get("keshbek_percent", 10)),
            "referral_reward_topup_percent": int(s.get("referral_reward_topup_percent", 5)),
            "star_rate_1000": int(s.get("star_rate_1000", 270000)),
            "min_topup_card": int(s.get("min_topup_card", 10000)),
            "max_topup_card": int(s.get("max_topup_card", 1000000)),
            "pay_window_seconds": int(s.get("pay_window_seconds", 300)),
            "card_active": str(s.get("card_active", "uzcard")),
            "support_username": str(s.get("support_username", "")),
            "support_phone": str(s.get("support_phone", "")),
            "support_email": str(s.get("support_email", "")),
            "admin_username": str(s.get("admin_username", "")),
            "maintenance": bool(s.get("maintenance", False)),
            **{key: config.bool_setting(key, True) for key in _SETTINGS_BOOL_FIELDS},
        },
    }


@app.post("/api/admin/settings_save")
async def api_admin_settings_save(request: Request):
    body = await _parse_body(request)
    if body is None:
        return JSONResponse({"ok": False, "error": "bad_request"}, status_code=400)
    user, err = await _admin_guard(body.get("initData", ""))
    if err:
        return err
    if not _check_rate_limit(f"admin:{user['id']}"):
        return JSONResponse({"ok": False, "error": "rate_limited"}, status_code=429)
    incoming = body.get("settings")
    if not isinstance(incoming, dict):
        return JSONResponse({"ok": False, "error": "bad_request"}, status_code=400)
    updates = {}
    for key, (lo, hi) in _SETTINGS_INT_FIELDS.items():
        if key not in incoming:
            continue
        try:
            val = int(str(incoming[key]).replace(" ", "").replace(",", ""))
        except (TypeError, ValueError):
            return JSONResponse({"ok": False, "error": "invalid", "field": key}, status_code=400)
        if not (lo <= val <= hi):
            return JSONResponse({"ok": False, "error": "range", "field": key}, status_code=400)
        updates[key] = val
    for key in _SETTINGS_STR_FIELDS:
        if key not in incoming:
            continue
        updates[key] = str(incoming[key]).strip().lstrip("@")[:150]
    if "card_active" in incoming:
        ca = str(incoming["card_active"]).strip().lower()
        if ca not in _CARD_OPTIONS:
            return JSONResponse({"ok": False, "error": "invalid", "field": "card_active"}, status_code=400)
        updates["card_active"] = ca
    for key in _SETTINGS_BOOL_FIELDS:
        if key in incoming:
            updates[key] = bool(incoming[key])
    if not updates:
        return {"ok": False, "error": "nothing"}
    config.update_settings(updates)
    await db.record_admin_audit(user["id"], "settings_save", ", ".join(sorted(updates)))
    return {"ok": True}


# ==================== ADMIN: GAMES ====================

def _load_games_file():
    with open(config.PACKAGES_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict) or not isinstance(data.get("games"), list):
        raise TypeError("bad packages file")
    return data


def _save_games_file(data):
    tmp = config.PACKAGES_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, config.PACKAGES_PATH)


@app.post("/api/admin/games")
async def api_admin_games(request: Request):
    body = await _parse_body(request)
    if body is None:
        return JSONResponse({"ok": False, "error": "bad_request"}, status_code=400)
    _user, err = await _admin_guard(body.get("initData", ""))
    if err:
        return err
    try:
        data = _load_games_file()
    except Exception:
        return JSONResponse({"ok": False, "error": "io"}, status_code=500)
    return {"ok": True, "games": data["games"]}


@app.post("/api/admin/game_save")
async def api_admin_game_save(request: Request):
    body = await _parse_body(request)
    if body is None:
        return JSONResponse({"ok": False, "error": "bad_request"}, status_code=400)
    user, err = await _admin_guard(body.get("initData", ""))
    if err:
        return err
    if not _check_rate_limit(f"admin:{user['id']}"):
        return JSONResponse({"ok": False, "error": "rate_limited"}, status_code=429)
    g = body.get("game")
    if not isinstance(g, dict):
        return JSONResponse({"ok": False, "error": "bad_request"}, status_code=400)
    gid = str(g.get("id", "")).strip()
    name = str(g.get("name", "")).strip()
    if not _re.fullmatch(r"[A-Za-z0-9_-]{1,64}", gid):
        return JSONResponse({"ok": False, "error": "bad_id"}, status_code=400)
    if not name or len(name) > 100:
        return JSONResponse({"ok": False, "error": "bad_name"}, status_code=400)
    raw_pkgs = g.get("packages")
    if not isinstance(raw_pkgs, list) or len(raw_pkgs) > 500:
        return JSONResponse({"ok": False, "error": "bad_packages"}, status_code=400)
    packages = []
    seen_ids = set()
    for p in raw_pkgs:
        if not isinstance(p, dict):
            return JSONResponse({"ok": False, "error": "bad_packages"}, status_code=400)
        pid = str(p.get("id", "")).strip()
        pname = str(p.get("name", "")).strip()
        if not _re.fullmatch(r"[A-Za-z0-9_-]{1,64}", pid) or not pname or pid in seen_ids:
            return JSONResponse({"ok": False, "error": "bad_packages"}, status_code=400)
        try:
            price = int(str(p.get("price", 0)).replace(" ", "").replace(",", ""))
        except (TypeError, ValueError):
            return JSONResponse({"ok": False, "error": "bad_packages"}, status_code=400)
        if price < 0 or price > 10_000_000_000:
            return JSONResponse({"ok": False, "error": "bad_packages"}, status_code=400)
        seen_ids.add(pid)
        packages.append({
            "id": pid,
            "name": pname[:120],
            "amount": str(p.get("amount", ""))[:60],
            "price": price,
            "category": str(p.get("category", ""))[:60],
        })
    categories = {}
    raw_cats = g.get("categories")
    if isinstance(raw_cats, dict) and len(raw_cats) <= 30:
        for k, v in list(raw_cats.items())[:30]:
            categories[str(k)[:32]] = str(v)[:60]
    try:
        data = _load_games_file()
    except Exception:
        return JSONResponse({"ok": False, "error": "io"}, status_code=500)
    games = data["games"]
    idx = next((i for i, x in enumerate(games) if str(x.get("id", "")) == gid), None)
    base = dict(games[idx]) if idx is not None else {}
    base.update({
        "id": gid,
        "name": name,
        "emoji": str(g.get("emoji", ""))[:16],
        "desc": str(g.get("desc", ""))[:300],
        "grid_mode": bool(g.get("grid_mode", False)),
        "categories": categories,
        "packages": packages,
    })
    if idx is None:
        games.append(base)
    else:
        games[idx] = base
    try:
        _save_games_file(data)
    except Exception:
        return JSONResponse({"ok": False, "error": "io"}, status_code=500)

    # --- Narx o'zgarishi: o'yinni yoqtirgan foydalanuvchilarga xabar ---
    try:
        old_pkgs = {str(p.get("id")): p for p in (base.get("packages") or []) if isinstance(p, dict)}
        changes = []
        for p in packages:
            old = old_pkgs.get(p["id"])
            if not old:
                continue
            try:
                old_price = int(old.get("price", 0))
            except (TypeError, ValueError):
                old_price = 0
            if old_price and old_price != p["price"]:
                changes.append((p["name"], old_price, p["price"]))
        if changes and idx is not None:
            def _h(s):
                return (str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                        .replace('"', "&quot;"))
            link = (config.get_settings() or {}).get("webapp_url") or ""
            fav_users = await db.users_with_favorite_game(gid)
            if fav_users:
                for cname, old_p, new_p in changes[:30]:
                    direction = "arzonlashdi" if new_p < old_p else "qimmatladi"
                    arrow = "⬇️" if new_p < old_p else "⬆️"
                    old_s = f"{old_p:,} so'm".replace(",", " ")
                    new_s = f"{new_p:,} so'm".replace(",", " ")
                    txt = (
                        f"🔔 <b>Narx {direction}!</b> {arrow}\n\n"
                        f"🎮 {_h(name)}\n"
                        f"📦 {_h(cname)}\n"
                        f"💰 <s>{old_s}</s> → <b>{new_s}</b>\n\n"
                        + (f'🛍 <a href="{_h(link)}">Do\'konni ochish</a>' if link else "")
                    )
                    for uid in fav_users[:5000]:
                        await db.add_notification(int(uid), txt)
    except Exception:
        pass

    await db.record_admin_audit(user["id"], "game_save", f"{gid} ({len(packages)} pkg)")
    return {"ok": True}


@app.post("/api/admin/game_delete")
async def api_admin_game_delete(request: Request):
    body = await _parse_body(request)
    if body is None:
        return JSONResponse({"ok": False, "error": "bad_request"}, status_code=400)
    user, err = await _admin_guard(body.get("initData", ""))
    if err:
        return err
    if not _check_rate_limit(f"admin:{user['id']}"):
        return JSONResponse({"ok": False, "error": "rate_limited"}, status_code=429)
    gid = str(body.get("game_id", "")).strip()
    if not gid:
        return JSONResponse({"ok": False, "error": "bad_request"}, status_code=400)
    try:
        data = _load_games_file()
    except Exception:
        return JSONResponse({"ok": False, "error": "io"}, status_code=500)
    games = data["games"]
    idx = next((i for i, x in enumerate(games) if str(x.get("id", "")) == gid), None)
    if idx is None:
        return JSONResponse({"ok": False, "error": "not_found"}, status_code=404)
    games.pop(idx)
    try:
        _save_games_file(data)
    except Exception:
        return JSONResponse({"ok": False, "error": "io"}, status_code=500)
    await db.record_admin_audit(user["id"], "game_delete", gid)
    return {"ok": True}


# ==================== ADMIN: ADMINS ====================

@app.post("/api/admin/admins")
async def api_admin_admins(request: Request):
    body = await _parse_body(request)
    if body is None:
        return JSONResponse({"ok": False, "error": "bad_request"}, status_code=400)
    _user, err = await _admin_guard(body.get("initData", ""))
    if err:
        return err
    conn = await db.get_connection()
    try:
        rows = await conn.execute_fetchall(
            """
            SELECT a.user_id, a.added_by, a.created_at, u.username, u.full_name
            FROM admins a LEFT JOIN users u ON u.user_id = a.user_id
            ORDER BY a.created_at DESC
            """
        )
    finally:
        await conn.close()
    base = set(config.ADMIN_IDS)
    return {
        "ok": True,
        "admins": [
            {
                "user_id": r["user_id"],
                "username": r["username"] or "",
                "full_name": r["full_name"] or "",
                "added_by": r["added_by"] or 0,
                "created_at": r["created_at"] or "",
                "is_base": r["user_id"] in base,
            }
            for r in rows
        ],
        "base_admins": sorted(base),
    }


@app.post("/api/admin/admin_add")
async def api_admin_admin_add(request: Request):
    body = await _parse_body(request)
    if body is None:
        return JSONResponse({"ok": False, "error": "bad_request"}, status_code=400)
    user, err = await _admin_guard(body.get("initData", ""))
    if err:
        return err
    if not _check_rate_limit(f"admin:{user['id']}"):
        return JSONResponse({"ok": False, "error": "rate_limited"}, status_code=429)
    try:
        target = int(body.get("user_id", 0))
    except (TypeError, ValueError):
        return JSONResponse({"ok": False, "error": "bad_request"}, status_code=400)
    target_user = await db.get_user(target)
    if not target_user:
        return {"ok": False, "error": "no_user"}
    if target in (await db.all_admin_ids()):
        return {"ok": False, "error": "exists"}
    await db.add_admin_db(target, user["id"])
    await db.record_admin_audit(user["id"], "admin_add", f"user={target}")
    return {"ok": True}


@app.post("/api/admin/admin_remove")
async def api_admin_admin_remove(request: Request):
    body = await _parse_body(request)
    if body is None:
        return JSONResponse({"ok": False, "error": "bad_request"}, status_code=400)
    user, err = await _admin_guard(body.get("initData", ""))
    if err:
        return err
    if not _check_rate_limit(f"admin:{user['id']}"):
        return JSONResponse({"ok": False, "error": "rate_limited"}, status_code=429)
    try:
        target = int(body.get("user_id", 0))
    except (TypeError, ValueError):
        return JSONResponse({"ok": False, "error": "bad_request"}, status_code=400)
    if target == user["id"]:
        return {"ok": False, "error": "self"}
    if target in config.ADMIN_IDS:
        return {"ok": False, "error": "base"}
    db_admins_list = await db.db_admins()
    if target not in db_admins_list:
        return {"ok": False, "error": "not_admin"}
    if len(db_admins_list) <= 1:
        return {"ok": False, "error": "last"}
    await db.remove_admin_db(target)
    await db.record_admin_audit(user["id"], "admin_remove", f"user={target}")
    return {"ok": True}


# ==================== ADMIN: BROADCAST ====================

@app.post("/api/admin/broadcast")
async def api_admin_broadcast(request: Request):
    body = await _parse_body(request)
    if body is None:
        return JSONResponse({"ok": False, "error": "bad_request"}, status_code=400)
    user, err = await _admin_guard(body.get("initData", ""))
    if err:
        return err
    if not _check_rate_limit(f"admin:{user['id']}"):
        return JSONResponse({"ok": False, "error": "rate_limited"}, status_code=429)
    text = str(body.get("text", "") or "").strip()[:4000]
    if not text:
        return {"ok": False, "error": "empty"}
    scope = str(body.get("scope", "all"))
    if scope == "user":
        try:
            target = int(body.get("user_id", 0))
        except (TypeError, ValueError):
            return {"ok": False, "error": "bad_user"}
        if not await db.get_user(target):
            return {"ok": False, "error": "no_user"}
        await db.add_notification(target, text)
        try:
            tgt = target

            def _send():
                return services.get_bot().send_message(tgt, text)

            services.safe_call_bot(_send)
        except Exception:
            pass
        await db.record_admin_audit(user["id"], "broadcast", f"user={target} ({len(text)} chars)")
        return {"ok": True, "sent": 1}
    conn = await db.get_connection()
    try:
        rows = await conn.execute_fetchall("SELECT user_id FROM users WHERE is_banned = 0")
        ids = [r["user_id"] for r in rows][:10000]
    finally:
        await conn.close()
    for uid in ids:
        await db.add_notification(uid, text)
    await db.record_admin_audit(user["id"], "broadcast", f"all → {len(ids)} ({len(text)} chars)")
    return {"ok": True, "sent": len(ids)}


# ==================== ADMIN: CSV EXPORT ====================

def _csv_escape(v):
    s = "" if v is None else str(v)
    if any(c in s for c in (',', '"', "\n", "\r")):
        return '"' + s.replace('"', '""') + '"'
    return s


@app.post("/api/admin/export")
async def api_admin_export(request: Request):
    body = await _parse_body(request)
    if body is None:
        return JSONResponse({"ok": False, "error": "bad_request"}, status_code=400)
    user, err = await _admin_guard(body.get("initData", ""))
    if err:
        return err
    if not _check_rate_limit(f"admin:{user['id']}"):
        return JSONResponse({"ok": False, "error": "rate_limited"}, status_code=429)
    kind = str(body.get("type", ""))
    games = {g["id"]: g["name"] for g in kb.load_games()}
    conn = await db.get_connection()
    try:
        if kind == "orders":
            rows = await conn.execute_fetchall(
                "SELECT id, user_id, platform, game_id, package_name, price, status, created_at "
                "FROM orders ORDER BY id DESC LIMIT 5000"
            )
            header = ["id", "user_id", "game", "player_id", "package_name", "price", "status", "created_at"]
            lines = [",".join(header)]
            for r in rows:
                lines.append(",".join(_csv_escape(v) for v in [
                    r["id"], r["user_id"], games.get(r["platform"], r["platform"]),
                    r["game_id"], r["package_name"], r["price"], r["status"], r["created_at"],
                ]))
            filename = f"orders_{int(time.time())}.csv"
        elif kind == "payments":
            rows = await conn.execute_fetchall(
                "SELECT id, user_id, method, amount, ref, status, created_at "
                "FROM payments ORDER BY id DESC LIMIT 5000"
            )
            header = ["id", "user_id", "method", "amount", "ref", "status", "created_at"]
            lines = [",".join(header)]
            for r in rows:
                lines.append(",".join(_csv_escape(r[h]) for h in header))
            filename = f"payments_{int(time.time())}.csv"
        else:
            return JSONResponse({"ok": False, "error": "bad_type"}, status_code=400)
    finally:
        await conn.close()
    csv_text = "\ufeff" + "\n".join(lines)
    await db.record_admin_audit(user["id"], "export", f"{kind} rows={max(len(lines) - 1, 0)}")
    return {"ok": True, "csv": csv_text, "filename": filename}


# ==================== ADMIN: REFERRAL STATS ====================

@app.post("/api/admin/refstats")
async def api_admin_refstats(request: Request):
    body = await _parse_body(request)
    if body is None:
        return JSONResponse({"ok": False, "error": "bad_request"}, status_code=400)
    _user, err = await _admin_guard(body.get("initData", ""))
    if err:
        return err
    rows = await db.get_ref_leaderboard(10)
    return {
        "ok": True,
        "referrers": [
            {
                "user_id": r["user_id"],
                "username": r["username"] or "",
                "full_name": r["full_name"] or "",
                "invites": r["invites"],
                "reward": r["reward"],
            }
            for r in rows
        ],
    }


if os.path.isdir(os.path.join(config.BASE_DIR, "webapp")):
    app.mount("/", StaticFiles(directory=os.path.join(config.BASE_DIR, "webapp"), html=True), name="webapp")