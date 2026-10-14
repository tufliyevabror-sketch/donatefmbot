"""Kunlik yakuniy hisobot — har kuni 00:00 (Asia/Tashkent) da adminlarga.

Muhim: 00:00 da YAKUNLAYDIGAN kunni hisoblaydi (joriy emas), chunki
00:00 da joriy kun allaqon boshlanadi.

Qo'lda qayta ishga tushirish:
    ./venv/bin/python reports/daily_report.py              # kechagi kun
    ./venv/bin/python reports/daily_report.py 2026-10-04   # aniq sana

Bir kun uchun faqat bir marta yuboriladi (data/.last_report marker).
Jonli botga tegmaydi: alohida process, faqat o'qiydi + sendMessage.
"""
import asyncio
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
import database as db

MARKER = os.path.join(os.path.dirname(config.DB_PATH), ".last_report")
REPORTS_DIR = os.path.join(os.path.dirname(config.DB_PATH), "reports")
LIST_LIMIT = 30
WEEKDAYS = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"]


def fmt(v):
    return f"{(v or 0):,}".replace(",", " ")


def send(chat_id: int, text: str, retries: int = 3):
    """Telegram'ga yuborish. Tarmoq xatosida (boot'da DNS tayyor bo'lmasa)
    3 martagacha 10s oralig'ida qayta urinadi."""
    url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage"
    data = urllib.parse.urlencode(
        {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    ).encode()
    req = urllib.request.Request(url, data=data)
    last_err = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return r.status
        except urllib.error.HTTPError as e:
            # 403 (bot bloklangan) / 400 kabi mijoz xatolarini takrorlamaymiz
            if getattr(e, "code", 500) < 500:
                raise
            last_err = e
        except Exception as e:  # noqa: BLE001
            last_err = e
        if attempt < retries - 1:
            time.sleep(10)
    raise last_err


def target_day():
    """Hisobot qilinadigan sana: odatda kechagi kun."""
    if len(sys.argv) > 1:
        return datetime.strptime(sys.argv[1].strip(), "%Y-%m-%d").date()
    return (datetime.now() - timedelta(days=1)).date()


def _marker_matches(day_s: str) -> bool:
    try:
        with open(MARKER, encoding="utf-8") as f:
            return f.read().strip() == day_s
    except OSError:
        return False


def _write_marker(day_s: str) -> None:
    try:
        with open(MARKER, "w", encoding="utf-8") as f:
            f.write(day_s)
    except OSError:
        pass


def _write_report(payload: dict) -> str | None:
    try:
        os.makedirs(REPORTS_DIR, exist_ok=True)
        path = os.path.join(REPORTS_DIR, payload["date"] + ".json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return path
    except (OSError, KeyError):
        return None


async def main():
    day = target_day()
    day_s = day.strftime("%Y-%m-%d")
    weekday = WEEKDAYS[day.weekday()]

    try:
        if await asyncio.to_thread(_marker_matches, day_s):
            print(f"{day_s} uchun allaqachon yuborilgan, o'tkazildi")
            return
    except OSError:
        pass

    s = await db.get_stats()
    conn = await db.get_connection()
    try:
        new_users = await conn.execute_fetchall(
            "SELECT user_id, username, full_name FROM users WHERE reg_date LIKE ?"
            " ORDER BY reg_date DESC LIMIT ?",
            (day_s + "%", LIST_LIMIT),
        )
        new_users_count = (
            await conn.execute_fetchall(
                "SELECT COUNT(*) AS c FROM users WHERE reg_date LIKE ?", (day_s + "%",)
            )
        )[0]["c"]
        done = await conn.execute_fetchall(
            "SELECT COUNT(*) AS c, COALESCE(SUM(price),0) AS s FROM orders"
            " WHERE status='bajarildi' AND created_at LIKE ?",
            (day_s + "%",),
        )
        new_orders = await conn.execute_fetchall(
            "SELECT COUNT(*) AS c FROM orders WHERE created_at LIKE ?", (day_s + "%",)
        )
        topups = await conn.execute_fetchall(
            "SELECT COUNT(*) AS c, COALESCE(SUM(amount),0) AS s FROM payments"
            " WHERE status='tasdiqlandi' AND created_at LIKE ?",
            (day_s + "%",),
        )
        refunds = await conn.execute_fetchall(
            "SELECT COUNT(*) AS c, COALESCE(SUM(price),0) AS s FROM orders"
            " WHERE status='rad_etildi' AND created_at LIKE ?",
            (day_s + "%",),
        )
        banned = await conn.execute_fetchall(
            "SELECT COUNT(*) AS c FROM users WHERE is_banned=1"
        )
    finally:
        await conn.close()

    lines = []
    for u in new_users:
        try:
            name = (u["username"] and "@" + u["username"]) or (u["full_name"] or "")
        except (KeyError, TypeError):
            name = ""
        lines.append(f"• <code>{u['user_id']}</code> {name}")
    shown = len(new_users)
    more = new_users_count - shown
    users_block = "\n".join(lines) if lines else "—"
    if more > 0:
        users_block += f"\n<i>…va yana {more}</i>"

    text = (
        f"🌙 <b>Kun yakuni — {day_s} ({weekday})</b>\n\n"
        f"👥 Yangi qo'shilganlar: <b>{new_users_count}</b>\n{users_block}\n\n"
        f"🛒 Yangi orderlar: <b>{new_orders[0]['c']}</b>\n"
        f"✅ Bajarildi: <b>{done[0]['c']}</b> ({fmt(done[0]['s'])} so'm)\n"
        f"↩️ Rad etildi: <b>{refunds[0]['c']}</b> ({fmt(refunds[0]['s'])} so'm)\n"
        f"💳 Tasdiqlangan to'lov: <b>{topups[0]['c']}</b> ({fmt(topups[0]['s'])} so'm)\n"
        f"⏳ Hozir kutilmoqda: <b>{s['pending']}</b> order\n"
        f"🚫 Banlangan (jami): <b>{banned[0]['c']}</b>\n\n"
        f"📦 Umumiy: {s['orders']} order, {fmt(s['revenue'])} so'm | 👥 {s['users']} user"
    )

    sent = 0
    for admin_id in sorted(set(config.ADMIN_IDS) | set(await db.db_admins())):
        try:
            send(admin_id, text)
            sent += 1
            print(f"OK {admin_id}")
        except Exception as e:
            print(f"FAIL {admin_id}: {e}")

    # Report JSON HAR DOIM saqlanadi (yuborilmagan bo'lsa ham) —
    # WebApp admin paneli /api/admin/daily_report/latest shu faylni o'qiydi.
    report = {
        "date": day_s,
        "weekday": weekday,
        "new_users": new_users_count,
        "new_orders": new_orders[0]["c"],
        "done_orders": done[0]["c"],
        "done_revenue": done[0]["s"],
        "refunds": refunds[0]["c"],
        "refund_amount": refunds[0]["s"],
        "topups": topups[0]["c"],
        "topup_amount": topups[0]["s"],
        "pending_orders": s["pending"],
        "banned_users": banned[0]["c"],
        "total_orders": s["orders"],
        "total_revenue": s["revenue"],
        "total_users": s["users"],
        "sent_to_admins": sent,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    report_path = await asyncio.to_thread(_write_report, report)
    if report_path:
        print(f"Report saqlandi: {report_path}")
    else:
        print("Reportni saqlashda xatolik")

    if sent:
        await asyncio.to_thread(_write_marker, day_s)
        print(f"{day_s}: {sent} ta adminga yuborildi")
    else:
        print(f"{day_s}: hech kimga yuborilmadi (keyingi urinda qayta uriniladi)")


if __name__ == "__main__":
    asyncio.run(main())