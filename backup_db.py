#!/usr/bin/env python3
"""SQLite DB zaxira nusxasi.

Ishlatilishi:
    venv/bin/python backup_db.py            # faqat zaxira oladi
    venv/bin/python backup_db.py --send     # zaxira + admin'ga Telegram orqali yuboradi
"""
import asyncio
import glob
import os
import sqlite3
import sys
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "data", "bot.db")
BACKUP_DIR = os.path.join(BASE, "data", "backups")
LOG = os.path.join(BASE, "logs", "backup.log")
KEEP = 168  # ~hafta (soatda)


def log(msg: str) -> None:
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S} {msg}"
    print(line)
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def make_backup() -> str:
    os.makedirs(BACKUP_DIR, exist_ok=True)
    out = os.path.join(BACKUP_DIR, f"bot-{datetime.now():%Y%m%d-%H%M%S}.db")
    src = sqlite3.connect(DB)
    dst = sqlite3.connect(out)
    try:
        with dst:
            src.backup(dst)  # yozuv davom e ham xavfsiz nusxa
    finally:
        dst.close()
        src.close()
    size = os.path.getsize(out)
    old = sorted(glob.glob(os.path.join(BACKUP_DIR, "bot-*.db")))
    for f in old[:-KEEP]:
        try:
            os.remove(f)
        except OSError:
            pass
    log(f"backup OK -> {os.path.relpath(out, BASE)} ({size} bayt), jami {min(len(old), KEEP)} ta nusxa")
    return out


def _read_bytes(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()


async def send_to_admin(path: str) -> None:
    import aiohttp

    from config import ADMIN_IDS, BOT_TOKEN

    if not ADMIN_IDS:
        log("yuborilmadi: ADMIN_IDS bo'sh")
        return
    chat_id = ADMIN_IDS[0]
    caption = f"🗄 DB zaxira — {datetime.now():%Y-%m-%d %H:%M} ({os.path.getsize(path)} bayt)"
    form = aiohttp.FormData()
    form.add_field("chat_id", str(chat_id))
    form.add_field("caption", caption)
    data = await asyncio.to_thread(_read_bytes, path)
    form.add_field(
        "document",
        data,
        filename=os.path.basename(path),
        content_type="application/octet-stream",
    )
    try:
        async with aiohttp.ClientSession() as session, session.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument",
            data=form,
            timeout=aiohttp.ClientTimeout(total=60),
        ) as r:
            ok = r.status == 200
            body = await r.text()
    except Exception as e:
        log(f"yuborishda xatolik: {e}")
        return
    if ok:
        log(f"admin'ga yuborildi (chat {chat_id})")
    else:
        log(f"yuborish xato HTTP {r.status}: {body[:200]}")


def main() -> int:
    if not os.path.exists(DB):
        log("DB topilmadi, nusxa olinmadi")
        return 1
    try:
        path = make_backup()
    except Exception as e:
        log(f"backup XATOLIK: {e}")
        return 1
    if "--send" in sys.argv:
        try:
            asyncio.run(send_to_admin(path))
        except Exception as e:
            log(f"yuborish XATOLIK: {e}")
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
