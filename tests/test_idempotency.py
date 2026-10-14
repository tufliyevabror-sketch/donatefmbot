"""Idempotency testlari: ikki marta bosishda 1 ta order.

Haqiqiy (oddiy) SQLite faylda ishlaydi — asl bot DB'siga tegilmaydi.
"""
import asyncio
import os
import sys
import tempfile
from datetime import datetime, timedelta

sys.path.insert(0, "/home/abror69/donatefmbot")

TMP = tempfile.mkdtemp(prefix="donatefm_test_")
DB = os.path.join(TMP, "test.db")

import database as db

db.DB_PATH = DB


async def main():
    await db.init_db()
    uid = 900001
    await db.register_user(uid, "tester", "Tester")

    print("=== IDEMPOTENCY ===")

    # 1) xarid qilish (balans yetarli bo'lishi uchun)
    await db.add_balance(uid, 500000, method="test", ref="seed-1")
    before = (await db.get_user(uid))["balance"]

    oid1, err1 = await db.purchase(uid, "freefire", "100 Diamonds", "100", 10990, "123456789", "ff-100")
    assert oid1 and err1 is None, f"birinchi xarid muvaffaqiyatsiz: {oid1} {err1}"
    after1 = (await db.get_user(uid))["balance"]
    print(f"  1-xarid: order #{oid1}, xato={err1}, balans {before} -> {after1}")
    assert after1 == before - 10990, "balans ayirilmadi"

    # 2) XUDDI shu xarid (ikkinchi marta bosish)
    oid2, err2 = await db.purchase(uid, "freefire", "100 Diamonds", "100", 10990, "123456789", "ff-100")
    after2 = (await db.get_user(uid))["balance"]
    print(f"  2-xarid: order #{oid2}, xato={err2}, balans {after2}")
    assert err2 == "duplicate", f"'duplicate' kutilgan edi, kelgan: {err2}"
    assert int(oid2) == int(oid1), "turli order id qaytarildi"
    assert after2 == after1, f"BALANS IKKINCHI MARTA AYIRILDI: {after1} -> {after2}"
    print("  OK  balans bir marta ayirildi, order takrorlanmadi")

    # 3) boshqa o'yinchi ID = yangi xarid
    oid3, err3 = await db.purchase(uid, "freefire", "100 Diamonds", "100", 10990, "987654321", "ff-100")
    assert err3 is None and int(oid3) != int(oid1), "boshqa ID uchun duplicate bo'ldi"
    print(f"  OK  boshqa o'yinchi ID ({'987654321'}) -> yangi order #{oid3}")

    # 4) boshqa paket = yangi xarid
    oid4, err4 = await db.purchase(uid, "freefire", "341 Diamonds", "341", 33990, "123456789", "ff-341")
    assert err4 is None and int(oid4) != int(oid1), "boshqa paket uchun duplicate bo'ldi"
    print(f"  OK  boshqa paket ({'341 Diamonds'}) -> yangi order #{oid4}")

    # 5) bajarilgan order keyin qayta xarid = YANGI order bo'lishi kerak
    await db.set_order_status(int(oid1), "bajarildi")
    oid5, err5 = await db.purchase(uid, "freefire", "100 Diamonds", "100", 10990, "123456789", "ff-100")
    assert err5 is None and int(oid5) != int(oid1), "bajarilgan order duplicate bo'ldi"
    print(f"  OK  bajarilgan order'dan keyin qayta xarid -> yangi order #{oid5} (to'g'ri)")

    # 6) vaqt oynasi: ESKI order duplicate bo'lmasligi kerak.
#    (created_at daqiqa aniqligida saqlanadi — 2 soat oldingi order oynadan tashqarida)
    old_at = (datetime.now() - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M")
    conn = await db.get_connection()
    try:
        await conn.execute(
            "INSERT INTO orders (user_id, game_id, platform, package_name, amount, price,"
            " status, created_at, package_id) VALUES (?,?,?,?,?,?,'kutilmoqda',?,?)",
            (uid, "777777777", "freefire", "100 Diamonds", "100", 10990, old_at, "ff-100"),
        )
        await conn.commit()
    finally:
        await conn.close()

    dup = await db.find_recent_duplicate_order(
        uid, "freefire", "ff-100", "777777777", minutes=10
    )
    assert dup is None, f"2 soatlik order 10 daqiqalik oynada duplicate bo'ldi: {dup}"
    print("  OK  vaqt oynasi ishlaydi (2 soatlik order -> duplicate yo'q)")

    # ...va 30 daqiqalik oynada esa topilishi kerak
    dup_wide = await db.find_recent_duplicate_order(
        uid, "freefire", "ff-100", "777777777", minutes=180
    )
    assert dup_wide is not None, "keng oynada eski order topilmadi"
    print("  OK  keng oynada (180 daqiqa) eski order topildi")

    # 7) boshqa foydalanuvchining orderi aralashmasin
    uid2 = 900002
    await db.register_user(uid2, "tester2", "Tester2")
    await db.add_balance(uid2, 500000, method="test", ref="seed-2")
    o_a, _ = await db.purchase(uid2, "freefire", "100 Diamonds", "100", 10990, "5550001", "ff-100")
    dup_other = await db.find_recent_duplicate_order(
        900003, "freefire", "ff-100", "5550001", minutes=10
    )
    assert dup_other is None, "boshqa user uchun duplicate topildi"
    print("  OK  boshqa foydalanuvchining orderi aralashmaydi")

    print(f"\nBARCHA IDEMPOTENCY TESTLARI O'TDI ({len(await db.get_user_orders(uid, 50))} ta order yaratildi)")


if __name__ == "__main__":
    asyncio.run(main())