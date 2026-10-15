import os
import time
from datetime import datetime, timedelta

import aiosqlite

from config import DB_PATH


class DBRow(dict):
    """sqlite3.Row kabi ishlaydi: ['kolonn'] ham, [0] ham, .get() ham ishlaydi."""

    def __getitem__(self, key):
        if isinstance(key, int):
            return tuple(self.values())[key]
        return dict.__getitem__(self, key)


def _row_factory(cursor, row):
    if row is None:
        return None
    return DBRow(zip([c[0] for c in cursor.description], row))


_shared: aiosqlite.Connection | None = None


class _SharedConn:
    """Bitta persistent (WAL) ulanish — har funksiyada yangi gacha bo'lgan 88 ta
    `aiosqlite.connect()` o'rniga. `close()` real yopilish emas (saqlanadi).
    Hamma kod bitta event-loop'da ishlagani uchun aiosqlite xavfsiz."""
    __slots__ = ("_c",)

    def __init__(self, conn: aiosqlite.Connection):
        object.__setattr__(self, "_c", conn)

    def __getattr__(self, item):
        return getattr(object.__getattribute__(self, "_c"), item)

    def __setattr__(self, key, value):
        object.__setattr__(object.__getattribute__(self, "_c"), key, value)

    async def close(self) -> None:
        return None  # MAX SPEED: ulanishni yopmang — keyingi so'rovda qayta qo'llanadi


async def get_connection():
    global _shared
    if _shared is None:
        conn = await aiosqlite.connect(DB_PATH, timeout=15)
        conn.row_factory = _row_factory
        await conn.execute("PRAGMA journal_mode=WAL")
        await conn.execute("PRAGMA busy_timeout=10000")
        _shared = conn
    return _SharedConn(_shared)


async def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = await get_connection()
    await conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            balance INTEGER DEFAULT 0,
            total_topup INTEGER DEFAULT 0,
            is_banned INTEGER DEFAULT 0,
            reg_date TEXT
        );

        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            game_id INTEGER,
            platform TEXT,
            package_name TEXT,
            amount TEXT,
            price INTEGER,
            status TEXT DEFAULT 'kutilmoqda',
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            method TEXT,
            amount INTEGER,
            ref TEXT,
            status TEXT DEFAULT 'kutilmoqda',
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS saved_ids (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            game_id TEXT,
            player_id TEXT,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );

        CREATE TABLE IF NOT EXISTS promocodes (
            code TEXT PRIMARY KEY,
            reward_amount INTEGER DEFAULT 0,
            max_uses INTEGER DEFAULT 1,
            used_count INTEGER DEFAULT 0,
            expires_at TEXT DEFAULT '',
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS user_promocodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            code TEXT,
            used_at TEXT
        );

        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY,
            added_by INTEGER DEFAULT 0,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS referral_rewards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER,
            invitee_id INTEGER,
            amount INTEGER,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            text TEXT,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS admin_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER,
            action TEXT,
            detail TEXT,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS gift_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            amount INTEGER NOT NULL,
            buyer_id INTEGER NOT NULL,
            recipient_id INTEGER DEFAULT 0,
            status TEXT DEFAULT 'available', -- available, redeemed, expired
            created_at TEXT,
            redeemed_at TEXT DEFAULT '',
            expires_at TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS auto_donate (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            frequency TEXT NOT NULL, -- monthly, weekly
            next_run TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            payment_method TEXT DEFAULT 'balance', -- balance, card, stars
            card_last4 TEXT DEFAULT '',
            created_at TEXT,
            last_run TEXT DEFAULT '',
            fails INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            game_id TEXT,
            package_id TEXT DEFAULT '',
            created_at TEXT,
            UNIQUE(user_id, game_id, package_id)
        );

        CREATE TABLE IF NOT EXISTS ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            user_id INTEGER,
            stars INTEGER,
            review TEXT DEFAULT '',
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS receipts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            payment_id INTEGER,
            user_id INTEGER,
            file_id TEXT DEFAULT '',
            note TEXT DEFAULT '',
            status TEXT DEFAULT 'pending',
            created_at TEXT
        );
        """
    )
    await add_column_if_missing(conn, "users", "phone", "TEXT DEFAULT ''")
    await add_column_if_missing(conn, "users", "lang", "TEXT DEFAULT 'uz'")
    await add_column_if_missing(conn, "users", "keshbek", "INTEGER DEFAULT 0")
    await add_column_if_missing(conn, "users", "referrer_id", "INTEGER DEFAULT 0")
    await add_column_if_missing(conn, "users", "theme", "TEXT DEFAULT 'dark'")
    await add_column_if_missing(conn, "users", "last_bonus_at", "TEXT DEFAULT ''")
    await add_column_if_missing(conn, "orders", "package_id", "TEXT DEFAULT ''")
    await add_column_if_missing(conn, "notifications", "is_read", "INTEGER DEFAULT 0")
    await add_column_if_missing(conn, "notifications", "status", "INTEGER DEFAULT 0")
    await add_column_if_missing(conn, "orders", "reminded", "INTEGER DEFAULT 0")
    await add_column_if_missing(conn, "users", "pro_until", "TEXT DEFAULT ''")
    await add_column_if_missing(conn, "users", "pro_notified", "INTEGER DEFAULT 0")
    await add_column_if_missing(conn, "orders", "rating", "INTEGER DEFAULT 0")
    await add_column_if_missing(conn, "ratings", "photo", "TEXT DEFAULT ''")
    await add_column_if_missing(conn, "payments", "chek", "INTEGER DEFAULT 0")
    await add_column_if_missing(conn, "payments", "reminded", "INTEGER DEFAULT 0")
    await add_column_if_missing(conn, "payments", "file_uid", "TEXT DEFAULT ''")
    await add_column_if_missing(conn, "users", "reseller", "INTEGER DEFAULT 0")
    # Idempotency: bir xil ref (Stars charge_id) faqat bir marta ishlatilishi uchun.
    # NULL/bo'sh ref'lar cheklanmaydi.
    try:
        await conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_payments_ref_unique "
            "ON payments(ref) WHERE ref IS NOT NULL AND ref != ''"
        )
    except Exception:
        pass
    await conn.commit()
    await conn.close()


async def add_column_if_missing(conn, table, column, definition):
    cols = await conn.execute_fetchall(f"PRAGMA table_info({table})")
    names = [c["name"] for c in cols]
    if column not in names:
        await conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _safe_int(val, default=0):
    try:
        return int(str(val).replace(" ", "").replace(",", ""))
    except (TypeError, ValueError):
        return default


def _escape_like(q):
    return q.replace("%", "%%").replace("_", "%%")


async def register_user(user_id, username, full_name, referrer_id=0):
    conn = await get_connection()
    try:
        row = await conn.execute_fetchall(
            "SELECT user_id, referrer_id FROM users WHERE user_id = ?", (user_id,)
        )
        if not row:
            await conn.execute(
                "INSERT INTO users (user_id, username, full_name, balance, reg_date, referrer_id) VALUES (?, ?, ?, 0, ?, ?)",
                (user_id, username, full_name, datetime.now().strftime("%Y-%m-%d %H:%M"), referrer_id or 0),
            )
        else:
            await conn.execute(
                "UPDATE users SET username = ?, full_name = ? WHERE user_id = ?",
                (username, full_name, user_id),
            )
            if referrer_id and int(referrer_id) != int(user_id) and not (row[0]["referrer_id"] or 0):
                await conn.execute(
                    "UPDATE users SET referrer_id = ? WHERE user_id = ?", (referrer_id, user_id)
                )
        await conn.commit()
    finally:
        await conn.close()


async def get_user(user_id):
    conn = await get_connection()
    try:
        row = await conn.execute_fetchall(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        )
        return row[0] if row else None
    finally:
        await conn.close()


async def get_or_create_user(user_id, username, full_name, referrer_id=0):
    user = await get_user(user_id)
    if not user:
        await register_user(user_id, username, full_name, referrer_id)
        user = await get_user(user_id)
    return user


async def get_user_by_username(username):
    name = str(username or "").strip().lstrip("@")[:64]
    if not name:
        return None
    conn = await get_connection()
    try:
        rows = await conn.execute_fetchall(
            "SELECT * FROM users WHERE username = ? COLLATE NOCASE LIMIT 1", (name,)
        )
        return rows[0] if rows else None
    finally:
        await conn.close()


async def add_balance(user_id, amount, method="admin", ref=""):
    if amount <= 0:
        return
    conn = await get_connection()
    try:
        # Idempotency: 'ref' bilan birinchi INSERT g'olib qiladi (UNIQUE index).
        # Parallel so'rovlarda faqat bittasi qator yaratadi -> balans bir marta qo'shiladi.
        if ref:
            await conn.execute("BEGIN IMMEDIATE")
            try:
                await conn.execute(
                    "INSERT INTO payments (user_id, method, amount, ref, status, created_at) "
                    "VALUES (?, ?, ?, ?, 'tasdiqlandi', ?)",
                    (user_id, method, amount, ref, datetime.now().strftime("%Y-%m-%d %H:%M")),
                )
                await conn.execute(
                    "UPDATE users SET balance = balance + ?, total_topup = total_topup + ? WHERE user_id = ?",
                    (amount, amount, user_id),
                )
                await conn.commit()
            except Exception:
                await conn.execute("ROLLBACK")
                return  # ref allaqachon ishlatilgan (parallel/takroriy so'rov)
        else:
            await conn.execute(
                "UPDATE users SET balance = balance + ?, total_topup = total_topup + ? WHERE user_id = ?",
                (amount, amount, user_id),
            )
            await conn.execute(
                "INSERT INTO payments (user_id, method, amount, ref, status, created_at) VALUES (?, ?, ?, ?, 'tasdiqlandi', ?)",
                (user_id, method, amount, ref or "", datetime.now().strftime("%Y-%m-%d %H:%M")),
            )
            await conn.commit()
    finally:
        await conn.close()
    # Keshbek yangilash
    old_user = await get_user(user_id)
    old_keshbek = old_user["keshbek"] if old_user else 0
    await set_keshbek(user_id)
    new_user = await get_user(user_id)
    new_keshbek = new_user["keshbek"] if new_user else 0
    if new_keshbek > old_keshbek:
        await add_notification(user_id, f"💎 <b>Keshbek yangilandi!</b>\nSizning keshbekingiz: <b>{new_keshbek:,} so'm</b> ga oshdi.")
    # Referral mukofoti
    reward = await maybe_referral_reward(user_id, amount)
    if reward:
        await add_notification(user_id, f"🤝 <b>Referral bonus!</b>\nDo'stingiz to'lov qildi, sizga <b>{reward:,} so'm</b> bonus qo'shildi.")


async def deduct_balance(user_id, amount):
    if amount <= 0:
        return False
    conn = await get_connection()
    try:
        cur = await conn.execute(
            "UPDATE users SET balance = balance - ? WHERE user_id = ? AND balance >= ?",
            (amount, user_id, amount),
        )
        await conn.commit()
        return cur.rowcount > 0
    finally:
        await conn.close()


async def create_order(user_id, platform, package_name, amount, price, game_id, package_id=""):
    conn = await get_connection()
    try:
        cur = await conn.execute(
            "INSERT INTO orders (user_id, game_id, platform, package_name, amount, price, status, created_at, package_id) VALUES (?, ?, ?, ?, ?, ?, 'kutilmoqda', ?, ?)",
            (user_id, game_id, platform, package_name, amount, price, datetime.now().strftime("%Y-%m-%d %H:%M"), package_id or ""),
        )
        await conn.commit()
        return cur.lastrowid
    finally:
        await conn.close()


async def find_recent_duplicate_order(user_id, platform, package_id, game_id, method_hint="", minutes=10):
    """Idempotency: bir xil xarid yaqinda yaratilganmi?

    Ikki marta bosilganda (yoki Telegram update qayta yuborilganda) bir xil
    order ikki marta yaratilmasligi kerak. Faqat hali 'kutilmoqda' holatdagi
    orderlar hisobga olinadi — bajarilgan/rad etilgan order esa yangi xarid
    deb qaraladi (mijoz qayta buyurtma qilmoqchi bo'lishi mumkin).
    """
    if not package_id:
        return None
    conn = await get_connection()
    try:
        since = (datetime.now() - timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M")
        rows = await conn.execute_fetchall(
            "SELECT id, price, status FROM orders WHERE user_id=? AND platform=?"
            " AND package_id=? AND game_id=? AND status='kutilmoqda' AND created_at>=?"
            " ORDER BY id DESC LIMIT 1",
            (user_id, platform, package_id, game_id, since),
        )
        return rows[0] if rows else None
    finally:
        await conn.close()


async def purchase(user_id, platform, package_name, amount, price, game_id, package_id=""):
    """Atomar xarid: balans ayirish + order yaratish. Muvaffaqiyatsiz — refund."""
    # Idempotency: 10 daqiqa ichida bir xil xarid bo'lsa — yangisini yaratmaymiz.
    dup = await find_recent_duplicate_order(user_id, platform, package_id, game_id)
    if dup:
        return int(dup["id"]), "duplicate"

    conn = await get_connection()
    try:
        await conn.execute("BEGIN IMMEDIATE")
        cur = await conn.execute(
            "UPDATE users SET balance = balance - ? WHERE user_id = ? AND balance >= ?",
            (price, user_id, price),
        )
        if cur.rowcount == 0:
            await conn.execute("ROLLBACK")
            return None, "balance_low"
        cur2 = await conn.execute(
            "INSERT INTO orders (user_id, game_id, platform, package_name, amount, price, status, created_at, package_id) VALUES (?, ?, ?, ?, ?, ?, 'kutilmoqda', ?, ?)",
            (user_id, game_id, platform, package_name, amount, price, datetime.now().strftime("%Y-%m-%d %H:%M"), package_id or ""),
        )
        await conn.commit()
        # Xaridda keshbek BERILMAYDI — faqat to'lov (topup) qilinganda.
        return cur2.lastrowid, None
    except Exception:
        try:
            await conn.execute("ROLLBACK")
        except Exception:
            pass
        return None, "error"
    finally:
        await conn.close()


async def set_order_status(order_id, status):
    conn = await get_connection()
    try:
        await conn.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
        await conn.commit()
    finally:
        await conn.close()


async def set_order_status_if(order_id, status, expected):
    """Atomar: faqat joriy holat `expected` bo'lsa o'zgartiradi. True qaytaradi."""
    conn = await get_connection()
    try:
        cur = await conn.execute(
            "UPDATE orders SET status = ? WHERE id = ? AND status = ?",
            (status, order_id, expected),
        )
        await conn.commit()
        return cur.rowcount > 0
    finally:
        await conn.close()


async def get_order(order_id):
    conn = await get_connection()
    try:
        row = await conn.execute_fetchall("SELECT * FROM orders WHERE id = ?", (order_id,))
        return row[0] if row else None
    finally:
        await conn.close()


async def get_user_order_statuses(user_id, limit=20):
    conn = await get_connection()
    try:
        rows = await conn.execute_fetchall(
            "SELECT id, status FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, min(limit, 50)),
        )
        return {r["id"]: r["status"] for r in rows}
    finally:
        await conn.close()


async def create_payment(user_id, method, amount, ref="", chek=0):
    conn = await get_connection()
    try:
        # 'ref' takrorlanmasligi UNIQUE indeks bilan kafolatlanadi.
        # Stars charge_id kabi bir xil ref kelganda xato tashlamaslik uchun
        # avval mavjudligini tekshiramiz (idempotency).
        if ref:
            row = await conn.execute_fetchall(
                "SELECT id FROM payments WHERE ref = ? LIMIT 1", (ref,)
            )
            if row:
                return None
        cur = await conn.execute(
            "INSERT INTO payments (user_id, method, amount, ref, status, created_at, chek) VALUES (?, ?, ?, ?, 'kutilmoqda', ?, ?)",
            (user_id, method, amount, ref, datetime.now().strftime("%Y-%m-%d %H:%M"), int(chek)),
        )
        await conn.commit()
        return cur.lastrowid
    except Exception:
        return None
    finally:
        await conn.close()


async def set_payment_chek(payment_id):
    conn = await get_connection()
    try:
        await conn.execute("UPDATE payments SET chek=1 WHERE id=?", (int(payment_id),))
        await conn.commit()
    finally:
        await conn.close()


async def set_payment_file(payment_id, file_uid):
    """Chek fayl ID'sini saqlash (dublikat chek aniqlash uchun)."""
    conn = await get_connection()
    try:
        await conn.execute(
            "UPDATE payments SET file_uid=? WHERE id=?", (str(file_uid or ""), int(payment_id))
        )
        await conn.commit()
    finally:
        await conn.close()


async def find_payment_by_file(file_uid):
    """Avval shu fayl bilan yuborilgan to'lov bormi (soxta/qayta chek)."""
    if not file_uid:
        return None
    conn = await get_connection()
    try:
        rows = await conn.execute_fetchall(
            "SELECT id, user_id, amount, status FROM payments WHERE file_uid=? LIMIT 2",
            (str(file_uid),),
        )
        return rows[0] if rows else None
    finally:
        await conn.close()


async def get_stale_chek_payments(max_age_seconds):
    conn = await get_connection()
    try:
        rows = await conn.execute_fetchall(
            "SELECT id, user_id, amount, created_at FROM payments WHERE status='kutilmoqda' AND chek=0 AND reminded=0"
        )
        out = []
        for r in rows:
            try:
                created = datetime.strptime(r["created_at"], "%Y-%m-%d %H:%M")
                age = (datetime.now() - created).total_seconds()
                if 90 <= age <= max_age_seconds:
                    out.append(dict(r))
            except Exception:
                pass
        return out
    finally:
        await conn.close()


async def mark_payment_reminded(payment_id):
    conn = await get_connection()
    try:
        await conn.execute("UPDATE payments SET reminded=1 WHERE id=?", (int(payment_id),))
        await conn.commit()
    finally:
        await conn.close()


async def get_payment(payment_id):
    conn = await get_connection()
    try:
        row = await conn.execute_fetchall("SELECT * FROM payments WHERE id = ?", (payment_id,))
        return row[0] if row else None
    finally:
        await conn.close()


async def set_payment_status(payment_id, status):
    conn = await get_connection()
    try:
        await conn.execute("UPDATE payments SET status = ? WHERE id = ?", (status, payment_id))
        await conn.commit()
    finally:
        await conn.close()


async def get_user_orders(user_id, limit=10):
    conn = await get_connection()
    try:
        rows = await conn.execute_fetchall(
            "SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        )
        return rows
    finally:
        await conn.close()


async def get_user_payments(user_id, limit=10):
    conn = await get_connection()
    try:
        rows = await conn.execute_fetchall(
            "SELECT * FROM payments WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        )
        return rows
    finally:
        await conn.close()


async def get_all_users():
    conn = await get_connection()
    try:
        rows = await conn.execute_fetchall("SELECT * FROM users ORDER BY is_banned DESC, balance DESC")
        return rows
    finally:
        await conn.close()


async def get_all_user_ids():
    conn = await get_connection()
    try:
        rows = await conn.execute_fetchall("SELECT user_id FROM users")
        return [r["user_id"] for r in rows]
    finally:
        await conn.close()


async def search_users(query):
    conn = await get_connection()
    try:
        q = str(query)[:200]
        like = f"%{_escape_like(q)}%"
        rows = await conn.execute_fetchall(
            "SELECT * FROM users WHERE CAST(user_id AS TEXT) LIKE ? ESCAPE '\\' OR username LIKE ? ESCAPE '\\' OR full_name LIKE ? ESCAPE '\\' ORDER BY balance DESC LIMIT 20",
            (like, like, like),
        )
        return rows
    finally:
        await conn.close()


async def get_stale_pending_orders(minutes: int):
    """Kutilmoqda turgan va `minutes` daqiqadan oshgan buyurtmalar (eslatma uchun)."""
    conn = await get_connection()
    try:
        rows = await conn.execute_fetchall(
            "SELECT * FROM orders WHERE status = 'kutilmoqda' AND reminded = 0"
        )
        out = []
        for r in rows:
            try:
                created = datetime.strptime(r["created_at"], "%Y-%m-%d %H:%M")
            except (TypeError, ValueError):
                continue
            if (datetime.now() - created).total_seconds() >= minutes * 60:
                out.append(r)
        return out
    finally:
        await conn.close()


async def mark_order_reminded(order_id):
    conn = await get_connection()
    try:
        await conn.execute("UPDATE orders SET reminded = 1 WHERE id = ?", (order_id,))
        await conn.commit()
    finally:
        await conn.close()


async def get_pending_orders():
    conn = await get_connection()
    try:
        rows = await conn.execute_fetchall(
            "SELECT * FROM orders WHERE status = 'kutilmoqda' ORDER BY id DESC"
        )
        return rows
    finally:
        await conn.close()


async def get_orders_by_filter(platform="", status="", limit=30, query=""):
    conn = await get_connection()
    try:
        q = "SELECT * FROM orders WHERE 1=1"
        args = []
        if platform:
            q += " AND platform = ?"
            args.append(platform)
        if status:
            q += " AND status = ?"
            args.append(status)
        if query:
            like = f"%{_escape_like(query)}%"
            q += " AND (CAST(id AS TEXT) LIKE ? ESCAPE '\\' OR CAST(user_id AS TEXT) LIKE ? ESCAPE '\\' OR platform LIKE ? ESCAPE '\\' OR package_name LIKE ? ESCAPE '\\' OR game_id LIKE ? ESCAPE '\\')"
            args.extend([like, like, like, like, like])
        q += " ORDER BY id DESC LIMIT ?"
        args.append(min(_safe_int(limit, 30), 100))
        rows = await conn.execute_fetchall(q, tuple(args))
        return rows
    finally:
        await conn.close()


async def get_pending_payments():
    conn = await get_connection()
    try:
        rows = await conn.execute_fetchall(
            "SELECT * FROM payments WHERE status = 'kutilmoqda' ORDER BY id DESC"
        )
        return rows
    finally:
        await conn.close()


async def get_confirmable_payments(hours=24):
    """Kutilayotgan + muddati o'tgan (rad_etildi) so'nggi to'lovlarni qaytaradi.

    Muddati o'tgan to'lov haqiqatan to'langan bo'lsa, admin uni kech
    tasdiqlay olishi uchun ro'yxatda ko'rinadi.
    """
    from datetime import timedelta

    conn = await get_connection()
    try:
        cutoff = (datetime.now() - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M")
        rows = await conn.execute_fetchall(
            "SELECT * FROM payments WHERE status = 'kutilmoqda' "
            "OR (status = 'rad_etildi' AND created_at >= ?) "
            "ORDER BY id DESC",
            (cutoff,),
        )
        return rows
    finally:
        await conn.close()


async def get_recent_payments(limit=50):
    conn = await get_connection()
    try:
        rows = await conn.execute_fetchall(
            "SELECT * FROM payments ORDER BY id DESC LIMIT ?", (min(limit, 100),)
        )
        return rows
    finally:
        await conn.close()


async def search_payments(query, limit=50):
    """Search payments by id, user_id, method, ref."""
    conn = await get_connection()
    try:
        q = "SELECT * FROM payments WHERE 1=1"
        args = []
        if query:
            like = f"%{_escape_like(query)}%"
            q += " AND (CAST(id AS TEXT) LIKE ? ESCAPE '\\' OR CAST(user_id AS TEXT) LIKE ? ESCAPE '\\' OR method LIKE ? ESCAPE '\\' OR ref LIKE ? ESCAPE '\\')"
            args.extend([like, like, like, like])
        q += " ORDER BY id DESC LIMIT ?"
        args.append(min(_safe_int(limit, 50), 100))
        rows = await conn.execute_fetchall(q, tuple(args))
        return rows
    finally:
        await conn.close()


async def get_stats():
    conn = await get_connection()
    try:
        users = (await conn.execute_fetchall("SELECT COUNT(*) as c FROM users"))[0]["c"]
        orders = (
            await conn.execute_fetchall("SELECT COUNT(*) as c FROM orders WHERE status='bajarildi'")
        )[0]["c"]
        revenue = (
            await conn.execute_fetchall("SELECT COALESCE(SUM(price),0) as s FROM orders WHERE status='bajarildi'")
        )[0]["s"]
        pending = (
            await conn.execute_fetchall("SELECT COUNT(*) as c FROM orders WHERE status='kutilmoqda'")
        )[0]["c"]
        pending_pay = (
            await conn.execute_fetchall("SELECT COALESCE(SUM(amount),0) as s FROM payments WHERE status='kutilmoqda'")
        )[0]["s"]
        topups = (
            await conn.execute_fetchall("SELECT COALESCE(SUM(amount),0) as s FROM payments WHERE status='tasdiqlandi'")
        )[0]["s"]
        today = datetime.now().strftime("%Y-%m-%d")
        today_orders = (
            await conn.execute_fetchall("SELECT COUNT(*) as c FROM orders WHERE status='bajarildi' AND created_at LIKE ?", (today + "%",))
        )[0]["c"]
        # Oylik statistika
        month_start = datetime.now().strftime("%Y-%m-01")
        month_users = (
            await conn.execute_fetchall("SELECT COUNT(DISTINCT user_id) as c FROM orders WHERE status='bajarildi' AND created_at >= ?", (month_start,))
        )[0]["c"]
        month_new_users = (
            await conn.execute_fetchall("SELECT COUNT(*) as c FROM users WHERE reg_date >= ?", (month_start,))
        )[0]["c"]
        month_revenue = (
            await conn.execute_fetchall("SELECT COALESCE(SUM(price),0) as s FROM orders WHERE status='bajarildi' AND created_at >= ?", (month_start,))
        )[0]["s"]
        month_topups = (
            await conn.execute_fetchall("SELECT COALESCE(SUM(amount),0) as s FROM payments WHERE status='tasdiqlandi' AND created_at >= ?", (month_start,))
        )[0]["s"]
        return {
            "users": users, "orders": orders, "revenue": revenue, "pending": pending,
            "pending_pay": pending_pay, "topups": topups, "today_orders": today_orders,
            "month_users": month_users, "month_new_users": month_new_users,
            "month_revenue": month_revenue, "month_topups": month_topups,
        }
    finally:
        await conn.close()


async def daily_stats(days=7):
    """Oxirgi N kun: buyurtmalar, tushum, to'ldirilgan summa, yangi userlar.

    Har kun uchun qator (bo'sh kunlar 0 bilan) — /trend buyrug'i uchun.
    """
    conn = await get_connection()
    try:
        since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        orders = await conn.execute_fetchall(
            "SELECT substr(created_at,1,10) AS d, COUNT(*) AS c,"
            " COALESCE(SUM(price),0) AS r FROM orders"
            " WHERE status='bajarildi' AND created_at>=? GROUP BY d",
            (since,),
        )
        topups = await conn.execute_fetchall(
            "SELECT substr(created_at,1,10) AS d, COUNT(*) AS c,"
            " COALESCE(SUM(amount),0) AS s FROM payments"
            " WHERE status='tasdiqlandi' AND created_at>=? GROUP BY d",
            (since,),
        )
        new_users = await conn.execute_fetchall(
            "SELECT substr(reg_date,1,10) AS d, COUNT(*) AS c FROM users"
            " WHERE reg_date>=? GROUP BY d",
            (since,),
        )
        by_day = {}
        today = datetime.now().date()
        for i in range(days):
            d = (today - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
            by_day[d] = {"d": d, "orders": 0, "revenue": 0,
                         "topups": 0, "topup_sum": 0, "new_users": 0}
        for row in orders:
            if row["d"] in by_day:
                by_day[row["d"]]["orders"] = int(row["c"])
                by_day[row["d"]]["revenue"] = int(row["r"])
        for row in topups:
            if row["d"] in by_day:
                by_day[row["d"]]["topups"] = int(row["c"])
                by_day[row["d"]]["topup_sum"] = int(row["s"])
        for row in new_users:
            if row["d"] in by_day:
                by_day[row["d"]]["new_users"] = int(row["c"])
        return [by_day[d] for d in sorted(by_day)]
    finally:
        await conn.close()


async def set_user_balance(user_id, balance):
    conn = await get_connection()
    try:
        await conn.execute("UPDATE users SET balance = ? WHERE user_id = ?", (balance, user_id))
        await conn.commit()
    finally:
        await conn.close()


async def set_user_ban(user_id, is_banned):
    conn = await get_connection()
    try:
        await conn.execute("UPDATE users SET is_banned = ? WHERE user_id = ?", (int(bool(is_banned)), user_id))
        await conn.commit()
    finally:
        await conn.close()


async def save_phone(user_id, phone):
    conn = await get_connection()
    try:
        await conn.execute("UPDATE users SET phone = ? WHERE user_id = ?", (phone, user_id))
        await conn.commit()
    finally:
        await conn.close()


async def save_lang(user_id, lang):
    conn = await get_connection()
    try:
        await conn.execute("UPDATE users SET lang = ? WHERE user_id = ?", (lang, user_id))
        await conn.commit()
    finally:
        await conn.close()


async def get_saved_ids(user_id, game_id):
    conn = await get_connection()
    try:
        rows = await conn.execute_fetchall(
            "SELECT player_id FROM saved_ids WHERE user_id = ? AND game_id = ? ORDER BY id DESC LIMIT 10",
            (user_id, game_id),
        )
        return [r["player_id"] for r in rows]
    finally:
        await conn.close()


async def add_saved_id(user_id, game_id, player_id):
    conn = await get_connection()
    try:
        await conn.execute(
            "DELETE FROM saved_ids WHERE user_id = ? AND game_id = ? AND player_id = ?",
            (user_id, game_id, player_id),
        )
        await conn.execute(
            "INSERT INTO saved_ids (user_id, game_id, player_id, created_at) VALUES (?, ?, ?, ?)",
            (user_id, game_id, player_id, now_str()),
        )
        await conn.commit()
    finally:
        await conn.close()


async def get_payment_by_ref(ref):
    conn = await get_connection()
    try:
        rows = await conn.execute_fetchall(
            "SELECT * FROM payments WHERE ref = ? ORDER BY id DESC LIMIT 1", (ref,)
        )
        return rows[0] if rows else None
    finally:
        await conn.close()


def pro_active(pro_until, now=None):
    """PRO muddati ketti mi (YYYY-MM-DD HH:MM matni ustidan solishtirish)."""
    if not pro_until:
        return False
    now = now or datetime.now().strftime("%Y-%m-%d %H:%M")
    return str(pro_until) > now


async def get_pro_until(user_id):
    user = await get_user(user_id)
    if not user:
        return ""
    return user.get("pro_until") or ""


async def is_pro(user_id):
    return pro_active(await get_pro_until(user_id))


async def extend_pro(user_id, days=30):
    """PRO muddatini `days` kunga uzaytiradi (yoki hozirdan boshlab)."""
    now = datetime.now()
    cur = await get_pro_until(user_id)
    base = now
    if pro_active(cur, now.strftime("%Y-%m-%d %H:%M")):
        try:
            base = datetime.strptime(cur, "%Y-%m-%d %H:%M")
        except (TypeError, ValueError):
            base = now
    new_until = (base + timedelta(days=days)).strftime("%Y-%m-%d %H:%M")
    conn = await get_connection()
    try:
        await conn.execute(
            "UPDATE users SET pro_until = ?, pro_notified = 0 WHERE user_id = ?",
            (new_until, user_id),
        )
        await conn.commit()
    finally:
        await conn.close()
    await set_keshbek(user_id)
    return new_until


async def set_pro_until(user_id, value, notified=0):
    conn = await get_connection()
    try:
        await conn.execute(
            "UPDATE users SET pro_until = ?, pro_notified = ? WHERE user_id = ?",
            (value or "", notified, user_id),
        )
        await conn.commit()
    finally:
        await conn.close()
    await set_keshbek(user_id)


async def list_pro_users(active_only=True, limit=50):
    conn = await get_connection()
    try:
        rows = await conn.execute_fetchall(
            "SELECT * FROM users WHERE pro_until != '' ORDER BY pro_until DESC LIMIT ?",
            (limit,),
        )
    finally:
        await conn.close()
    if not active_only:
        return rows
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    return [r for r in rows if str(r["pro_until"]) > now]


async def expired_pro_users(limit=50):
    """Muddati yangi o'tgan va hali xabar yuborilmaganlar."""
    conn = await get_connection()
    try:
        rows = await conn.execute_fetchall(
            "SELECT * FROM users WHERE pro_until != '' AND pro_notified = 0 "
            "ORDER BY pro_until DESC LIMIT ?",
            (limit,),
        )
    finally:
        await conn.close()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    return [r for r in rows if str(r["pro_until"]) <= now]


async def mark_pro_notified(user_id):
    conn = await get_connection()
    try:
        await conn.execute("UPDATE users SET pro_notified = 1 WHERE user_id = ?", (user_id,))
        await conn.commit()
    finally:
        await conn.close()


async def set_keshbek(user_id):
    from config import get_settings
    user = await get_user(user_id)
    if not user:
        return
    percent = _safe_int(get_settings().get("keshbek_percent", 10), 10)
    if pro_active(user.get("pro_until")):
        percent += _safe_int(get_settings().get("pro_keshbek_bonus_percent", 5), 5)
    keshbek = min(user["total_topup"] * percent // 100, 1000000)
    conn = await get_connection()
    try:
        await conn.execute("UPDATE users SET keshbek = ? WHERE user_id = ?", (keshbek, user_id))
        await conn.commit()
    finally:
        await conn.close()


async def refund_balance(user_id, amount, ref=""):
    if amount <= 0:
        return
    conn = await get_connection()
    try:
        if ref:
            dup = await conn.execute_fetchall(
                "SELECT 1 FROM payments WHERE user_id=? AND method='refund' AND ref=? LIMIT 1",
                (user_id, ref),
            )
            if dup:
                await conn.commit()
                return
        await conn.execute(
            "UPDATE users SET balance = balance + ? WHERE user_id = ?",
            (amount, user_id),
        )
        await conn.execute(
            "INSERT INTO payments (user_id, method, amount, ref, status, created_at) VALUES (?, 'refund', ?, ?, 'qaytarildi', ?)",
            (user_id, amount, ref, datetime.now().strftime("%Y-%m-%d %H:%M")),
        )
        await conn.commit()
    finally:
        await conn.close()


async def confirm_payment(payment_id, user_id, amount=None):
    conn = await get_connection()
    try:
        row = await conn.execute_fetchall(
            "SELECT amount, method, status FROM payments WHERE id=?",
            (payment_id,),
        )
        if not row:
            await conn.commit()
            return False
        # Himoya: qaytaruv (refund) yoki allaqachon hal qilingan to'lovni
        # qayta tasdiqlash mumkin emas — aks holda pul ikki marta qo'shiladi.
        if row[0]["method"] == "refund" or row[0]["status"] not in ("kutilmoqda", "rad_etildi"):
            await conn.commit()
            return False
        if amount is None:
            amount = row[0]["amount"]
        # 'rad_etildi' ham qabul qilinadi: muddati o'tgan (lekin haqiqatan to'langan)
        # to'lovni admin kech tasdiqlashi mumkin.
        cur = await conn.execute(
            "UPDATE payments SET status='tasdiqlandi' WHERE id=? AND status IN ('kutilmoqda','rad_etildi')",
            (payment_id,),
        )
        if cur.rowcount > 0:
            await conn.execute(
                "UPDATE users SET balance=balance+?, total_topup=total_topup+? WHERE user_id=?",
                (amount, amount, user_id),
            )
            await conn.commit()
            await set_keshbek(user_id)
            await maybe_referral_reward(user_id, amount)
            return True
        await conn.commit()
        return False
    finally:
        await conn.close()


# ==================== PROMOCODES ====================
async def create_promo(code, reward_amount, max_uses, expires_at=""):
    conn = await get_connection()
    try:
        await conn.execute(
            "INSERT OR IGNORE INTO promocodes (code, reward_amount, max_uses, used_count, expires_at, created_at) VALUES (?, ?, ?, 0, ?, ?)",
            (code.strip().upper(), reward_amount, max_uses, expires_at, now_str()),
        )
        await conn.commit()
    finally:
        await conn.close()


async def get_promo(code):
    conn = await get_connection()
    try:
        rows = await conn.execute_fetchall("SELECT * FROM promocodes WHERE code = ?", (code.strip().upper(),))
        return rows[0] if rows else None
    finally:
        await conn.close()


async def list_promos():
    conn = await get_connection()
    try:
        rows = await conn.execute_fetchall("SELECT * FROM promocodes ORDER BY created_at DESC")
        return rows
    finally:
        await conn.close()


async def redeem_promo(user_id, code):
    code = code.strip().upper()
    promo = await get_promo(code)
    if not promo:
        return False, "Bunday promokod mavjud emas"
    if promo["expires_at"]:
        try:
            expires = datetime.strptime(promo["expires_at"], "%Y-%m-%d")
            if datetime.now() > expires:
                return False, "Promokod muddati tugagan"
        except Exception:
            pass
    conn = await get_connection()
    try:
        await conn.execute("BEGIN IMMEDIATE")
        used = await conn.execute_fetchall(
            "SELECT 1 FROM user_promocodes WHERE user_id = ? AND code = ?", (user_id, code)
        )
        if used:
            await conn.execute("ROLLBACK")
            return False, "Siz bu promokodni allaqachon ishlatgansiz"
        cur = await conn.execute(
            "UPDATE promocodes SET used_count = used_count + 1 WHERE code = ? AND used_count < max_uses",
            (code,)
        )
        if cur.rowcount == 0:
            await conn.execute("ROLLBACK")
            return False, "Promokod limiti tugagan"
        await conn.execute(
            "INSERT INTO user_promocodes (user_id, code, used_at) VALUES (?, ?, ?)",
            (user_id, code, now_str())
        )
        await conn.execute(
            "UPDATE users SET balance = balance + ? WHERE user_id = ?",
            (promo["reward_amount"], user_id)
        )
        await conn.execute("COMMIT")
        await set_keshbek(user_id)
        return True, promo["reward_amount"]
    except Exception:
        try:
            await conn.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        await conn.close()


# ==================== ADMINS (DB) ====================
async def db_admins():
    conn = await get_connection()
    try:
        rows = await conn.execute_fetchall("SELECT user_id FROM admins")
        return [r["user_id"] for r in rows]
    finally:
        await conn.close()


async def add_admin_db(user_id, added_by=0):
    conn = await get_connection()
    try:
        await conn.execute(
            "INSERT OR IGNORE INTO admins (user_id, added_by, created_at) VALUES (?, ?, ?)",
            (user_id, added_by, now_str()),
        )
        await conn.commit()
    finally:
        await conn.close()


async def remove_admin_db(user_id):
    conn = await get_connection()
    try:
        await conn.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
        await conn.commit()
    finally:
        await conn.close()


async def all_admin_ids():
    base = set()
    from config import ADMIN_IDS
    base = set(ADMIN_IDS)
    for uid in await db_admins():
        base.add(uid)
    return list(base)


# ==================== REFERRAL ====================
async def maybe_referral_reward(invitee_id, amount):
    from config import get_settings
    user = await get_user(invitee_id)
    if not user or not user["referrer_id"]:
        return
    referrer_id = int(user["referrer_id"])
    if referrer_id == int(invitee_id):
        return
    conn = await get_connection()
    try:
        already = await conn.execute_fetchall(
            "SELECT 1 FROM referral_rewards WHERE invitee_id = ?", (invitee_id,)
        )
        if already:
            return
        ref_row = await conn.execute_fetchall(
            "SELECT reseller FROM users WHERE user_id = ?", (referrer_id,)
        )
        is_reseller = bool(ref_row[0]["reseller"]) if ref_row else False
        if is_reseller:
            percent = _safe_int(get_settings().get("reseller_percent", 10), 10)
        else:
            percent = _safe_int(get_settings().get("referral_reward_topup_percent", 5), 5)
        reward = amount * percent // 100
        if reward <= 0:
            return
        tag = "🏪 Sotuvchi" if is_reseller else "🤝 Referral"
        await conn.execute("INSERT INTO referral_rewards (referrer_id, invitee_id, amount, created_at) VALUES (?, ?, ?, ?)",
                           (referrer_id, invitee_id, reward, now_str()))
        await conn.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (reward, referrer_id))
        await conn.commit()
        try:
            await add_notification(referrer_id, f"{tag} mukofoti: <b>{reward:,} so'm</b> balansingizga qo'shildi!".replace(",", " "))
        except Exception:
            pass
        return reward
    finally:
        await conn.close()


async def set_user_reseller(user_id, is_reseller):
    conn = await get_connection()
    try:
        await conn.execute(
            "UPDATE users SET reseller = ? WHERE user_id = ?", (int(bool(is_reseller)), int(user_id))
        )
        await conn.commit()
    finally:
        await conn.close()


async def user_stats(user_id):
    """Foydalanuvchi uchun shaxsiy statistika."""
    conn = await get_connection()
    try:
        u = (await conn.execute_fetchall("SELECT * FROM users WHERE user_id = ?", (user_id,)))[0]
        orders = (await conn.execute_fetchall(
            "SELECT COUNT(*) c, COALESCE(SUM(price),0) s FROM orders WHERE user_id = ?", (user_id,)
        ))[0]
        pend = (await conn.execute_fetchall(
            "SELECT COUNT(*) c FROM orders WHERE user_id = ? AND status = 'kutilmoqda'", (user_id,)
        ))[0]
        pays = (await conn.execute_fetchall(
            "SELECT COUNT(*) c, COALESCE(SUM(amount),0) s FROM payments WHERE user_id = ? AND status = 'tasdiqlandi'", (user_id,)
        ))[0]
        refs = (await conn.execute_fetchall(
            "SELECT COUNT(*) c FROM users WHERE referrer_id = ?", (user_id,)
        ))[0]
        refsum = (await conn.execute_fetchall(
            "SELECT COALESCE(SUM(amount),0) s FROM referral_rewards WHERE referrer_id = ?", (user_id,)
        ))[0]
        favs = (await conn.execute_fetchall(
            "SELECT COUNT(*) c FROM favorites WHERE user_id = ?", (user_id,)
        ))[0]
        return {
            "balance": u["balance"] or 0,
            "total_topup": u["total_topup"] or 0,
            "keshbek": u["keshbek"] or 0,
            "reg_date": u["reg_date"] or "",
            "is_reseller": bool(u["reseller"]) if "reseller" in u else False,
            "orders": orders["c"] or 0,
            "spent": orders["s"] or 0,
            "orders_pending": pend["c"] or 0,
            "payments": pays["c"] or 0,
            "paid_total": pays["s"] or 0,
            "referrals": refs["c"] or 0,
            "referral_earned": refsum["s"] or 0,
            "favorites": favs["c"] or 0,
        }
    finally:
        await conn.close()


async def users_with_favorite_game(game_id):
    """O'yinni yoqtirgan foydalanuvchilar (narx o'zgarishi xabari uchun)."""
    conn = await get_connection()
    try:
        rows = await conn.execute_fetchall(
            "SELECT DISTINCT user_id FROM favorites WHERE game_id = ?", (game_id,)
        )
        return [r["user_id"] for r in rows]
    finally:
        await conn.close()


async def get_referrals(referrer_id):
    conn = await get_connection()
    try:
        rows = await conn.execute_fetchall(
            "SELECT user_id, username, full_name, reg_date FROM users WHERE referrer_id = ? ORDER BY reg_date DESC LIMIT 50",
            (referrer_id,),
        )
        return rows
    finally:
        await conn.close()


async def get_referral_stats(referrer_id):
    conn = await get_connection()
    try:
        cnt = (await conn.execute_fetchall("SELECT COUNT(*) as c FROM users WHERE referrer_id = ?", (referrer_id,)))[0]["c"]
        total = (await conn.execute_fetchall("SELECT COALESCE(SUM(amount),0) as s FROM referral_rewards WHERE referrer_id = ?", (referrer_id,)))[0]["s"]
        return {"count": cnt, "total_reward": total}
    finally:
        await conn.close()


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


async def add_notification(user_id, text):
    conn = await get_connection()
    try:
        await conn.execute(
            "INSERT INTO notifications (user_id, text, created_at) VALUES (?, ?, ?)",
            (user_id, text, now_str()),
        )
        await conn.commit()
    finally:
        await conn.close()


async def count_notifications():
    conn = await get_connection()
    try:
        row = await conn.execute_fetchall("SELECT COUNT(*) as c FROM notifications WHERE status = 0")
        return row[0]["c"] if row else 0
    finally:
        await conn.close()


async def fetch_notifications(limit=50):
    conn = await get_connection()
    try:
        return await conn.execute_fetchall(
            "SELECT * FROM notifications WHERE status = 0 ORDER BY id ASC LIMIT ?", (limit,)
        )
    finally:
        await conn.close()


async def mark_notifications_done(ids):
    if not ids:
        return
    conn = await get_connection()
    try:
        await conn.execute(
            f"UPDATE notifications SET status = 1 WHERE id IN ({','.join('?' * len(ids))})", ids
        )
        await conn.commit()
    finally:
        await conn.close()


async def purge_sent_notifications(days=7):
    conn = await get_connection()
    try:
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M")
        await conn.execute("DELETE FROM notifications WHERE status = 1 AND created_at < ?", (cutoff,))
        await conn.commit()
    finally:
        await conn.close()


async def pop_notifications(limit=50):
    conn = await get_connection()
    try:
        rows = await conn.execute_fetchall(
            "SELECT * FROM notifications ORDER BY id ASC LIMIT ?", (limit,)
        )
        if rows:
            ids = [r["id"] for r in rows]
            await conn.execute(f"DELETE FROM notifications WHERE id IN ({','.join('?' * len(ids))})", ids)
            await conn.commit()
        return rows
    finally:
        await conn.close()


async def expire_stale_payments(seconds):
    """Eski to'lovlarni (pay_window o'tgan) rad_etildi qiluvchi. Qaytaradi: [(payment_id, user_id, amount, ref)]."""
    conn = await get_connection()
    try:
        rows = await conn.execute_fetchall(
            "SELECT id, user_id, amount, ref, created_at FROM payments WHERE status='kutilmoqda'"
        )
        expired = []
        for r in rows:
            try:
                created = datetime.strptime(r["created_at"], "%Y-%m-%d %H:%M")
                if (datetime.now() - created).total_seconds() > seconds:
                    await conn.execute("UPDATE payments SET status='rad_etildi' WHERE id=?", (r["id"],))
                    if r["ref"] and r["ref"].startswith("ord:"):
                        order_id = int(r["ref"].split(":")[1])
                        await conn.execute(
                            "UPDATE orders SET status='rad_etildi' WHERE id=? AND status=?",
                            (order_id, "to'lov_kutilmoqda"),
                        )
                    expired.append((r["id"], r["user_id"], r["amount"], r["ref"]))
            except Exception:
                pass
        if expired:
            await conn.commit()
        return expired
    finally:
        await conn.close()


async def record_admin_audit(admin_id, action, detail=""):
    conn = await get_connection()
    try:
        await conn.execute(
            "INSERT INTO admin_audit (admin_id, action, detail, created_at) VALUES (?, ?, ?, ?)",
            (admin_id, action, detail, now_str()),
        )
        await conn.commit()
    finally:
        await conn.close()


async def get_admin_audit(limit=100):
    conn = await get_connection()
    try:
        rows = await conn.execute_fetchall(
            "SELECT * FROM admin_audit ORDER BY id DESC LIMIT ?", (limit,)
        )
        return rows
    finally:
        await conn.close()


# ==================== FAVORITES ====================
async def list_favorites(user_id):
    conn = await get_connection()
    try:
        rows = await conn.execute_fetchall(
            "SELECT game_id, package_id FROM favorites WHERE user_id = ? ORDER BY id DESC LIMIT 100",
            (user_id,),
        )
        return [{"game_id": r["game_id"], "package_id": r["package_id"] or ""} for r in rows]
    finally:
        await conn.close()


async def toggle_favorite(user_id, game_id, package_id=""):
    conn = await get_connection()
    try:
        row = await conn.execute_fetchall(
            "SELECT id FROM favorites WHERE user_id = ? AND game_id = ? AND package_id = ?",
            (user_id, game_id, package_id or ""),
        )
        if row:
            await conn.execute("DELETE FROM favorites WHERE id = ?", (row[0]["id"],))
            await conn.commit()
            return False
        await conn.execute(
            "INSERT INTO favorites (user_id, game_id, package_id, created_at) VALUES (?, ?, ?, ?)",
            (user_id, game_id, package_id or "", now_str()),
        )
        await conn.commit()
        return True
    finally:
        await conn.close()


async def is_favorite(user_id, game_id, package_id=""):
    conn = await get_connection()
    try:
        rows = await conn.execute_fetchall(
            "SELECT 1 FROM favorites WHERE user_id = ? AND game_id = ? AND package_id = ? LIMIT 1",
            (user_id, game_id, package_id or ""),
        )
        return bool(rows)
    finally:
        await conn.close()


# ==================== RATINGS ====================
async def set_order_rating(order_id, user_id, stars, review="", photo=""):
    stars = max(1, min(5, int(stars or 0)))
    conn = await get_connection()
    try:
        o = await conn.execute_fetchall("SELECT user_id, status FROM orders WHERE id = ?", (order_id,))
        if not o or o[0]["user_id"] != user_id:
            return False, "Topilmadi"
        if o[0]["status"] != "bajarildi":
            return False, "Faqat bajarilgan buyurtmani baholash mumkin"
        old = await conn.execute_fetchall("SELECT photo FROM ratings WHERE order_id = ?", (order_id,))
        prev_photo = (old[0]["photo"] if old else "") or ""
        await conn.execute("DELETE FROM ratings WHERE order_id = ?", (order_id,))
        await conn.execute(
            "INSERT INTO ratings (order_id, user_id, stars, review, photo, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (order_id, user_id, stars, (review or "")[:500], (photo or prev_photo)[:120], now_str()),
        )
        await conn.execute("UPDATE orders SET rating = ? WHERE id = ?", (stars, order_id))
        await conn.commit()
        return True, stars
    finally:
        await conn.close()


async def get_rating_stats(order_id=None):
    conn = await get_connection()
    try:
        if order_id:
            row = await conn.execute_fetchall("SELECT * FROM ratings WHERE order_id = ?", (order_id,))
            return row[0] if row else None
        avg = (await conn.execute_fetchall("SELECT AVG(stars) as a, COUNT(*) as c FROM ratings"))[0]
        return {"avg": avg["a"] or 0, "count": avg["c"]}
    finally:
        await conn.close()


async def get_user_ratings(user_id):
    conn = await get_connection()
    try:
        rows = await conn.execute_fetchall(
            "SELECT order_id, stars, review, photo, created_at FROM ratings WHERE user_id = ? ORDER BY id DESC LIMIT 20",
            (user_id,),
        )
        return rows
    finally:
        await conn.close()


async def list_game_reviews(game_id, limit=30):
    """Bajarilgan buyurtmalarning sharhlari (omshon: birinchi isim)."""
    conn = await get_connection()
    try:
        rows = await conn.execute_fetchall(
            """
            SELECT r.order_id, r.stars, r.review, r.photo, r.created_at,
                   u.username, u.full_name
            FROM ratings r
            JOIN orders o ON o.id = r.order_id
            LEFT JOIN users u ON u.user_id = r.user_id
            WHERE o.platform = ? AND o.status = 'bajarildi'
              AND (r.review != '' OR r.photo != '')
            ORDER BY r.id DESC LIMIT ?
            """,
            (game_id, min(limit, 100)),
        )
        return rows
    finally:
        await conn.close()


async def get_game_rating(game_id):
    conn = await get_connection()
    try:
        row = (await conn.execute_fetchall(
            """
            SELECT AVG(r.stars) as a, COUNT(*) as c
            FROM ratings r JOIN orders o ON o.id = r.order_id
            WHERE o.platform = ? AND o.status = 'bajarildi'
            """,
            (game_id,),
        ))[0]
        return {"avg": row["a"] or 0, "count": row["c"] or 0}
    finally:
        await conn.close()


# ==================== RECEIPTS ====================
async def add_receipt(payment_id, user_id, file_id="", note=""):
    conn = await get_connection()
    try:
        cur = await conn.execute(
            "INSERT INTO receipts (payment_id, user_id, file_id, note, status, created_at) VALUES (?, ?, ?, ?, 'pending', ?)",
            (payment_id or 0, user_id, file_id or "", (note or "")[:500], now_str()),
        )
        await conn.commit()
        return cur.lastrowid
    finally:
        await conn.close()


async def get_receipts(limit=50, status=""):
    conn = await get_connection()
    try:
        if status:
            rows = await conn.execute_fetchall(
                "SELECT * FROM receipts WHERE status = ? ORDER BY id DESC LIMIT ?", (status, min(limit, 100))
            )
        else:
            rows = await conn.execute_fetchall(
                "SELECT * FROM receipts ORDER BY id DESC LIMIT ?", (min(limit, 100),)
            )
        return rows
    finally:
        await conn.close()


async def set_receipt_status(receipt_id, status):
    conn = await get_connection()
    try:
        await conn.execute("UPDATE receipts SET status = ? WHERE id = ?", (status, receipt_id))
        await conn.commit()
    finally:
        await conn.close()


# ==================== CHARTS (7 kun) ====================
async def get_daily_series(days=7):
    from datetime import timedelta
    conn = await get_connection()
    try:
        out = []
        now = datetime.now()
        for i in range(days - 1, -1, -1):
            day = (now - timedelta(days=i)).strftime("%Y-%m-%d")
            rev = (
                await conn.execute_fetchall(
                    "SELECT COALESCE(SUM(price),0) as s, COUNT(*) as c FROM orders WHERE status='bajarildi' AND created_at LIKE ?",
                    (day + "%",),
                )
            )[0]
            top = (
                await conn.execute_fetchall(
                    "SELECT COALESCE(SUM(amount),0) as s FROM payments WHERE status='tasdiqlandi' AND created_at LIKE ?",
                    (day + "%",),
                )
            )[0]
            out.append({"day": day, "revenue": rev["s"], "orders": rev["c"], "topups": top["s"]})
        return out
    finally:
        await conn.close()


# ==================== REF LEADERBOARD ====================
async def get_ref_leaderboard(limit=20):
    conn = await get_connection()
    try:
        rows = await conn.execute_fetchall(
            """
            SELECT u.user_id, u.username, u.full_name,
                   COUNT(r.id) as invites,
                   COALESCE(SUM(r.amount),0) as reward
            FROM users u
            LEFT JOIN referral_rewards r ON r.referrer_id = u.user_id
            WHERE u.user_id IN (SELECT referrer_id FROM referral_rewards GROUP BY referrer_id)
            GROUP BY u.user_id
            ORDER BY reward DESC, invites DESC
            LIMIT ?
            """,
            (min(limit, 50),),
        )
        return rows
    finally:
        await conn.close()


# ==================== NOTIFICATIONS (Mini App) ====================
async def get_user_notifications(user_id, limit=30):
    conn = await get_connection()
    try:
        rows = await conn.execute_fetchall(
            "SELECT id, text, created_at, is_read FROM notifications WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, min(limit, 100)),
        )
        return rows
    finally:
        await conn.close()


async def mark_notifications_read(user_id):
    conn = await get_connection()
    try:
        await conn.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ?", (user_id,))
        await conn.commit()
    finally:
        await conn.close()


async def count_unread_notifications(user_id):
    conn = await get_connection()
    try:
        row = await conn.execute_fetchall(
            "SELECT COUNT(*) as c FROM notifications WHERE user_id = ? AND is_read = 0",
            (user_id,),
        )
        return row[0]["c"] if row else 0
    finally:
        await conn.close()


async def save_theme(user_id, theme):
    theme = "light" if str(theme).lower() == "light" else "dark"
    conn = await get_connection()
    try:
        await conn.execute("UPDATE users SET theme = ? WHERE user_id = ?", (theme, user_id))
        await conn.commit()
        return theme
    finally:
        await conn.close()


async def get_daily_bonus_state(user_id):
    """-> (last_ts, amount) — holat ko'rsatish uchun (claim'siz)."""
    from config import get_settings

    conn = await get_connection()
    try:
        row = await conn.execute_fetchall(
            "SELECT last_bonus_at FROM users WHERE user_id = ?", (user_id,)
        )
        last = 0
        if row:
            try:
                last = int(row[0].get("last_bonus_at") or 0)
            except (TypeError, ValueError):
                last = 0
        amount = _safe_int(get_settings().get("daily_bonus_amount", 5000), 5000)
        if amount < 0:
            amount = 5000
        return last, amount
    finally:
        await conn.close()


async def claim_daily_bonus(user_id):
    """24h cooldown bilan kunlik bonus. Atomik bitta UPDATE shart bilan —
    parallel so'rovlar uchun BEGIN kerak emas.
    -> (claimed: bool, amount, balance, next_ts)"""
    from config import get_settings

    now = int(time.time())
    amount = _safe_int(get_settings().get("daily_bonus_amount", 5000), 5000)
    if amount < 0:
        amount = 5000
    cutoff = now - 86400
    conn = await get_connection()
    try:
        cur = await conn.execute(
            "UPDATE users SET last_bonus_at = ?, balance = balance + ? "
            "WHERE user_id = ? AND COALESCE(CAST(last_bonus_at AS INTEGER), 0) < ?",
            (str(now), amount, user_id, cutoff),
        )
        if cur.rowcount == 0:
            row = await conn.execute_fetchall(
                "SELECT last_bonus_at FROM users WHERE user_id = ?", (user_id,)
            )
            last = 0
            if row:
                try:
                    last = int(row[0].get("last_bonus_at") or 0)
                except (TypeError, ValueError):
                    last = 0
            return False, amount, 0, last + 86400
        await conn.execute(
            "INSERT INTO payments (user_id, method, amount, ref, status, created_at) "
            "VALUES (?, 'daily_bonus', ?, ?, 'tasdiqlandi', ?)",
            (user_id, amount, f"daily_{user_id}_{now}", datetime.now().strftime("%Y-%m-%d %H:%M")),
        )
        await conn.commit()
        row = await conn.execute_fetchall(
            "SELECT balance FROM users WHERE user_id = ?", (user_id,)
        )
        balance = int(row[0].get("balance") or 0) if row else 0
        return True, amount, balance, now + 86400
    finally:
        await conn.close()
