"""Avtomatik top-up yetkazish (delivery) moduli (Enhanced Auto-Fulfillment API connector)."""
import asyncio
import logging
import re

import config
import database as db
import order_notify

logger = logging.getLogger("delivery")

PROVIDER_LABELS = {
    "manual": "Qo'lda (admin)",
    "custom": "O'z HTTP API",
    "baulu": "Baulu API",
    "liveop": "LiveOP API",
}

DEFAULT_INTERVAL = 30


def order_parts(o):
    return {
        "order_id": o["id"],
        "game": o["platform"],
        "package": o["package_name"],
        "amount_label": o["amount"],
        "price": o["price"],
        "player": o["game_id"],
        "user_id": o["user_id"],
    }


def _http_post(url, payload, timeout=15):
    import requests
    return requests.post(url, json=payload, timeout=timeout, headers={"User-Agent": "GameShopBot/2.0", "Accept": "application/json"})


def _http_get(url, timeout=12):
    import requests
    return requests.get(url, timeout=timeout, headers={"User-Agent": "GameShopBot/2.0", "Accept": "application/json"})


async def _verify_standoff(player_id):
    """Standoff 2: nick -> o'yinchi nomi (o'z sayti orqali, bepul)."""
    nick = str(player_id or "").strip()
    if not nick or len(nick) > 24 or not re.fullmatch(r"[A-Za-z0-9_.\-]{3,24}", nick):
        return None
    try:
        from urllib.parse import quote

        def _get():
            import requests

            return requests.get(
                f"https://standoff-2.com/en/profile/{quote(nick)}",
                timeout=12,
                allow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0 (compatible; GameShopBot/1.0)"},
            )

        resp = await asyncio.to_thread(_get)
        if resp.status_code != 200:
            return None
        html = resp.text or ""
        m = re.search(r'og:title"\s*content="([^"]+)"', html)
        title = (m.group(1) if m else "").strip()
        low = title.lower()
        if not title or "not found" in low or "страница не найдена" in low or "404" in low:
            return None
        return {"ok": True, "name": title[:40]}
    except Exception:
        return None


GAME_ID_RULES = {
    "freefire": (re.compile(r"^\d{5,15}$"), "faqat raqamlar, 5–15 ta (masalan: 2627497746)"),
    "standoff": (re.compile(r"^[A-Za-z0-9_.\-]{3,24}$"), "nickname: 3–24 ta lotin harfi/raqam (masalan: ProGamer)"),
    "pubg": (re.compile(r"^(?:\d{6,13}|[A-Za-z][A-Za-z0-9_]{5,23})$"), "6–13 ta raqam yoki 6–24 ta lotin (masalan: 512000001)"),
    "ml": (re.compile(r"^\d{4,12}$"), "User ID — faqat raqamlar, 4–12 ta (masalan: 123456789)"),
    "roblox": (re.compile(r"^[A-Za-z0-9_]{1,32}$"), "username yoki raqam (masalan: Builderman)"),
}


def validate_player_id(game_id, value):
    """(to'g'rimi, qo'llanma matni) — ID formati tekshiruvi."""
    if not config.bool_setting("id_validation_enabled", True):
        return True, ""
    rule = GAME_ID_RULES.get(game_id)
    if not rule:
        return True, ""
    rx, hint = rule
    v = str(value or "").strip()
    if rx.match(v):
        return True, ""
    return False, hint


async def verify_player(game_id, player_id):
    player_id = str(player_id).strip()
    if not player_id:
        return None
    try:
        if game_id == "freefire":
            return await _verify_freefire(player_id)
        if game_id == "roblox":
            return await _verify_roblox(player_id)
        if game_id == "standoff":
            return await _verify_standoff(player_id)
        cfg = config.get_delivery_config()
        if cfg["provider"] in ("custom", "baulu", "liveop") and cfg["api_url"]:
            resp = await asyncio.to_thread(
                _http_post,
                cfg["api_url"].rstrip("/") + "/verify",
                {"auth": cfg["api_key"], "game": game_id, "userid": player_id},
            )
            if resp.status_code == 200:
                data = resp.json()
                name = (
                    data.get("name")
                    or (data.get("data") or {}).get("name")
                    or data.get("player_name")
                    or data.get("nickname")
                )
                if name:
                    return {"ok": True, "name": name}
    except Exception as e:
        logger.warning("verify_player xatosi (%s): %s", game_id, e)
    return None


async def _verify_freefire(player_id):
    try:
        from FlexbaseGFFT import UTN
        name = await asyncio.to_thread(UTN, str(player_id))
        bad = {"ID_NOT_FOUND", "NOT_FOUND", "ERROR_FETCHING_NAME", ""}
        if isinstance(name, str) and name.strip() and name.strip().upper() not in bad:
            return {"ok": True, "name": name.strip()}
    except Exception as e:
        logger.warning("FF verify xatosi: %s", e)
    return None


async def _verify_roblox(player_id):
    import re
    pid = str(player_id).strip()
    try:
        if pid.isdigit():
            resp = await asyncio.to_thread(_http_get, f"https://users.roblox.com/v1/users/{pid}")
            if resp.status_code == 200:
                data = resp.json()
                name = data.get("displayName") or data.get("name")
                if name:
                    return {"ok": True, "name": name}
        elif re.match(r"^[A-Za-z0-9_]{3,20}$", pid):
            resp = await asyncio.to_thread(
                _http_post,
                "https://users.roblox.com/v1/usernames/users",
                {"usernames": [pid], "excludeBannedUsers": False},
            )
            if resp.status_code == 200:
                data = resp.json()
                users = data.get("data", [])
                if users:
                    name = users[0].get("displayName") or users[0].get("name")
                    if name:
                        return {"ok": True, "name": name}
    except Exception as e:
        logger.warning("Roblox verify xatosi: %s", e)
    return None


async def test_provider():
    """Provider ulanganini tekshirish."""
    cfg = config.get_delivery_config()
    url = (cfg.get("api_url") or "").rstrip("/")
    key = cfg.get("api_key") or ""
    if not url or not key:
        return "sozlanmagan ❌ (URL yoki kalit yo'q)"
    payload = {"auth": key, "game": "freefire", "userid": "0"}
    try:
        resp = await asyncio.to_thread(_http_post, url + "/verify", payload)
        return f"HTTP {resp.status_code} — {(resp.text or '')[:120]}"
    except Exception as e:
        return f"ULANISH YO'Q: {type(e).__name__}: {str(e)[:100]}"


async def deliver_order(order):
    p = order_parts(order)
    cfg = config.get_delivery_config()

    if order["status"] != "kutilmoqda":
        return {"status": "skip", "msg": "holat o'zgarmagan"}

    if not config.bool_setting("auto_delivery_enabled", True):
        return {"status": "manual", "msg": "Avto-yetkazish o'chirilgan — admin qo'lda bajaradi"}

    if cfg["provider"] == "manual" or not cfg["api_url"]:
        return {"status": "manual", "msg": "Provider sozlanmagan — admin qo'lda bajaradi"}

    payload = {
        "auth": cfg["api_key"],
        "game": p["game"],
        "userid": p["player"],
        "sku": p["package"],
        "qty": p["amount_label"],
        "order_id": p["order_id"],
        "price": p["price"],
    }
    try:
        # Retry mechanism for robust auto-fulfillment
        resp = None
        for attempt in range(2):
            try:
                resp = await asyncio.to_thread(
                    _http_post, cfg["api_url"].rstrip("/") + "/fulfill", payload
                )
                if resp.status_code in (200, 201):
                    break
            except Exception:
                if attempt == 1:
                    raise
                await asyncio.sleep(1)

        if not resp or resp.status_code not in (200, 201):
            code = resp.status_code if resp else "NO_RESP"
            text = resp.text[:200] if resp else "timeout"
            return {"status": "error", "msg": f"HTTP {code}: {text}"}
        
        data = resp.json()
        ok = data.get("ok") if "ok" in data else data.get("status") in ("ok", "success", "done", "completed")
        if ok:
            await db.set_order_status(order["id"], "bajarildi")
            return {"status": "done", "msg": str(data.get("message", "success"))}
        return {"status": "fail", "msg": str(data.get("error", data.get("message", "muvaffaqiyatsiz")))}
    except Exception as e:
        logger.exception("deliver_order xatosi #%s", order["id"])
        return {"status": "error", "msg": str(e)}


async def _notify_admins_delivery_fail(order, res, bot):
    """Buyurtma avto-delivery muvaffaqiyatsiz bo'lsa, adminga xabar beradi."""
    try:
        p = order_parts(order)
        import database as db2
        from config import ADMIN_IDS
        admin_ids = set(ADMIN_IDS)
        for uid in await db2.db_admins():
            admin_ids.add(uid)
        for admin_id in admin_ids:
            try:
                await bot.send_message(
                    admin_id,
                    f"⚠️ <b>Avtomatik delivery xatosi</b>\n\n"
                    f"📦 #{p['order_id']} {p['package']}\n"
                    f"🆔 {p['player']}\n"
                    f"❌ {res['msg'][:150]}",
                )
            except Exception:
                pass
    except Exception:
        pass


async def process_pending_orders(bot):
    cfg = config.get_delivery_config()
    if cfg["provider"] == "manual" or not cfg["api_url"]:
        return 0
    orders = await db.get_pending_orders()
    done = 0
    for o in orders:
        res = await deliver_order(o)
        p = order_parts(o)
        if res["status"] in ("done", "fail", "error"):
            done += 1
            try:
                if res["status"] == "done":
                    await order_notify.notify_user(bot, o, "bajarildi")
                else:
                    lang = await order_notify.lang_of(o["user_id"])
                    await bot.send_message(p["user_id"], order_notify.fail_message(o, res["msg"], lang))
                    if bot:
                        await _notify_admins_delivery_fail(o, res, bot)
            except Exception:
                pass
    if done:
        logger.info("Avtomatik delivery: %d buyurtma ishlandi", done)
    return done


async def process_orders_loop(bot):
    while True:
        try:
            await process_pending_orders(bot)
        except Exception:
            logger.exception("process_orders_loop xatosi")
        try:
            interval = config.get_delivery_config().get("interval") or DEFAULT_INTERVAL
        except Exception:
            interval = DEFAULT_INTERVAL
        await asyncio.sleep(interval)
