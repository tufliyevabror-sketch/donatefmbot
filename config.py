import json
import os
import threading


def _load_dotenv():
    """Minimal .env yuklovchi (python-dotenv shart emas)."""
    base = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base, ".env")
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip().strip("'\"")
                if k and k not in os.environ:
                    os.environ[k] = v
    except FileNotFoundError:
        pass


_load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi: .env fayliga BOT_TOKEN=... yozing")

WEBAPP_URL = os.getenv("WEBAPP_URL", "") or os.getenv("RENDER_EXTERNAL_URL", "")

ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "7366064785").split(",") if x.strip().isdigit()]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "bot.db")
PACKAGES_PATH = os.path.join(BASE_DIR, "data", "packages.json")
SETTINGS_PATH = os.path.join(BASE_DIR, "data", "settings.json")

DEFAULT_SETTINGS = {
    # Karta raqamlari, egasi, telefon va email BO'SH qoldiriladi: ular
    # faqat data/settings.json (Git'dan tashqarida) va admin panel orqali
    # saqlanadi. Kodda saqlash xavfli — repo'ga tasodifan tushib qolishi mumkin.
    "card_uzcard": "",
    "card_humo": "",
    "card_tbc": "",
    "card_uzum": "",
    "card_holder": "",
    "card_holder_uzcard": "",
    "card_holder_humo": "",
    "card_holder_tbc": "",
    "card_holder_uzum": "",
    "card_active": "uzcard",
    "support_username": "donatefm_support",
    "support_phone": "",
    "support_email": "",
    "card_phone": "",
    "admin_username": "donatefm_support",
    "pay_window_seconds": 300,
    "star_rate_1000": 270000,
    "min_topup_card": 10000,
    "max_topup_card": 1000000,
    "min_topup_stars": 2,
    "max_topup_stars": 5000,
    "webapp_url": "",
    "keshbek_percent": 10,
    "referral_reward_topup_percent": 5,
    "delivery_provider": "manual",
    "delivery_api_url": "",
    "delivery_api_key": "",
    "delivery_interval_sec": 30,
    "bot_username": "",
    "order_reminder_enabled": True,
    "order_reminder_min": 30,
    "pro_price_month": 50000,
    "pro_discount_percent": 5,
    "pro_keshbek_bonus_percent": 5,
    "pro_enabled": True,
}

_settings_cache = None
_settings_mtime = 0.0
_settings_lock = threading.RLock()


def _load_settings():
    global _settings_cache, _settings_mtime
    try:
        mtime = os.path.getmtime(SETTINGS_PATH)
        if _settings_cache is not None and mtime == _settings_mtime:
            return _settings_cache
        with _settings_lock:
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            updated = False
            for k, v in DEFAULT_SETTINGS.items():
                if k not in data:
                    data[k] = v
                    updated = True
            if updated:
                _save_settings(data)
            _settings_cache = data
            _settings_mtime = os.path.getmtime(SETTINGS_PATH)
            return data
    except Exception:
        return DEFAULT_SETTINGS.copy()


def _save_settings(data):
    global _settings_cache, _settings_mtime
    try:
        os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
        tmp = SETTINGS_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, SETTINGS_PATH)
        _settings_cache = data
        _settings_mtime = os.path.getmtime(SETTINGS_PATH)
    except Exception:
        pass


def _settings_file_lock():
    """Jarayonlararo lock: bot va tunnel bir vaqtda settings.json ni yozmasligi kerak."""
    lock_path = SETTINGS_PATH + ".lock"
    handle = open(lock_path, "a+", encoding="utf-8")  # noqa: SIM115 — flock uchun ochiq turadi
    try:
        import fcntl
        fcntl.flock(handle, fcntl.LOCK_EX)
    except Exception:
        pass
    return handle


def get_settings():
    return _load_settings()


def update_settings(new_data):
    global _settings_mtime
    with _settings_lock:
        lock = _settings_file_lock()
        try:
            _settings_mtime = 0.0
            data = _load_settings()
            data.update(new_data)
            _save_settings(data)
        finally:
            try:
                import fcntl
                fcntl.flock(lock, fcntl.LOCK_UN)
            except Exception:
                pass
            lock.close()


def get_active_card():
    s = get_settings()
    active = str(s.get("card_active", "uzcard") or "uzcard").strip().lower()
    key = active if active.startswith("card_") else f"card_{active}"
    return s.get(key) or s.get("card_uzcard", "")


CARD_KEYS = [
    ("uzcard", "Uzcard"),
    ("humo", "Humo"),
    ("tbc", "Tbc"),
    ("uzum", "Uzum"),
]


def all_cards():
    s = get_settings()
    out = []
    for key, label in CARD_KEYS:
        num = str(s.get(f"card_{key}", "") or "").strip()
        if not num:
            continue
        holder = str(
            s.get(f"card_holder_{key}", "") or s.get("card_holder", "") or ""
        ).strip()
        out.append({"key": key, "label": label, "number": num, "holder": holder})
    return out


def _int_setting(key, default):
    try:
        return int(str(get_settings().get(key, default)).replace(" ", "").replace(",", ""))
    except (TypeError, ValueError):
        return default


def bool_setting(key, default=True):
    """Sozlama qiymatini bool'ga o'giradi: 1/true/yes/on/yoq/ha -> True."""
    val = get_settings().get(key, None)
    if val is None:
        return bool(default)
    if isinstance(val, bool):
        return val
    s = str(val).strip().lower()
    if s in ("1", "true", "yes", "on", "yoq", "ha", "yana", "enabled"):
        return True
    if s in ("0", "false", "no", "off", "yo'q", "yo'q ", "disabled", ""):
        return False
    return bool(default)


def toggle_setting(key):
    """Sozlamani teskariladi (true <-> false) va yangi qiymatni qaytaradi."""
    new_val = not bool_setting(key, True)
    update_settings({key: new_val})
    return new_val


def stars_rate_per_1000():
    return _int_setting("star_rate_1000", 270000)


def stars_count_for_price(price):
    rate = stars_rate_per_1000()
    if rate <= 0:
        return 1
    stars = price * 1000 // rate
    if price * 1000 % rate:
        stars += 1
    return max(1, stars)


def min_topup_card():
    return _int_setting("min_topup_card", 10000)


def max_topup_card():
    return _int_setting("max_topup_card", 1000000)


def min_topup_stars():
    return _int_setting("min_topup_stars", 2)


def max_topup_stars():
    return _int_setting("max_topup_stars", 5000)


def card_number():
    return get_active_card()


def card_holder():
    return get_settings().get("card_holder", "DONATE FM")


def pay_window_seconds():
    return _int_setting("pay_window_seconds", 300)


FREE_BILLING_SERVICE = os.getenv("FREE_BILLING_SERVICE", "game-shop-topup")


def get_delivery_config():
    s = get_settings()
    return {
        "provider": s.get("delivery_provider", "manual"),
        "api_url": s.get("delivery_api_url", ""),
        "api_key": s.get("delivery_api_key", ""),
        "interval": _int_setting("delivery_interval_sec", 30),
    }


GAME_ICONS = {
    "freefire": "🔥",
    "pubg": "🪂",
    "ml": "🥷",
    "roblox": "👾",
    "standoff": "🔫",
    "stars": "⭐️",
    "premium": "👑",
}
