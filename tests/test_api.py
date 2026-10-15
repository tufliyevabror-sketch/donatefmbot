"""WebApp API (FastAPI) testlari — lokal server, internet talab qilmaydi.

tekshiriladi: /health, /api/init'ning initData validatsiyasi,
himoya endpoint'lari (banned/maintenance), soxta cheq tekshiruvi mantiqi.
"""
import sys

sys.path.insert(0, "/home/abror69/donatefmbot")

import server

BASE = "/home/abror69/donatefmbot"


def client():
    from fastapi.testclient import TestClient

    return TestClient(server.app)


def test_health_ok():
    r = client().get("/health")
    assert r.status_code in (200, 503), r.text
    d = r.json()
    assert "ok" in d and "db" in d and "webapp_url" in d
    print(f"  OK  /health -> {r.status_code} ok={d['ok']} db={d['db']}")


def test_init_rejects_bad_initdata():
    """Noto'g'ri initData -> 400 (autentifikatsiya tekshiruvi ishlaydi)."""
    r = client().post("/api/init", json={"initData": "forged=1&hash=bogus"})
    assert r.status_code == 400, f"kutilgan 400, kelgan {r.status_code}: {r.text[:120]}"
    assert r.json().get("error") == "init_data"
    print("  OK  /api/init (soxta initData) -> 400 init_data")


def test_init_rejects_empty_initdata():
    r = client().post("/api/init", json={"initData": ""})
    assert r.status_code == 400
    print("  OK  /api/init (bo'sh initData) -> 400")


def test_init_rejects_missing_hash():
    """hash'siz initData rad etilishi kerak."""
    r = client().post("/api/init", json={"initData": "user=%7B%22id%22%3A1%7D&auth_date=1"})
    assert r.status_code == 400
    print("  OK  /api/init (hash yo'q) -> 400")


def test_webhook_secret_protected():
    """/tg-webhook USE_WEBHOOK=0 da 404 beradi (ochiq emas)."""
    r = client().post("/tg-webhook", json={})
    assert r.status_code == 404, f"kutilgan 404, kelgan {r.status_code}"
    print("  OK  /tg-webhook -> 404 (ochiq emas)")


def test_admin_api_rejects_forged_initdata():
    """Admin endpointlari soxta initData bilan 400 berishi kerak."""
    for ep in ("/api/admin/stats", "/api/admin/orders", "/api/admin/promos"):
        r = client().post(ep, json={"initData": "hash=bogus"})
        assert r.status_code in (400, 403), f"{ep} -> {r.status_code}"
    print("  OK  /api/admin/* (soxta initData) -> 400/403")


def test_order_rejects_bad_amount_type():
    """_parse_amount: arab raqami/1e10/bo'sh qiymatni rad etishi kerak."""
    assert server._parse_amount("50000") == 50000
    assert server._parse_amount("50 000") == 50000
    assert server._parse_amount("50,000") == 50000
    assert server._parse_amount("") is None
    assert server._parse_amount("abc") is None
    assert server._parse_amount("1e10") is None
    assert server._parse_amount("٥٠٠٠٠") is None   # arab raqamlari
    assert server._parse_amount("0") is None
    assert server._parse_amount("1.5") is None
    assert server._parse_amount("9" * 20) is None   # juda uzun
    print("  OK  _parse_amount -> faqat butun ASCII raqamlar qabul qiladi")


def test_init_data_signature_verification():
    """Telegram initData HMAC tekshiruvi: noto'g'ri hash rad etiladi."""
    assert server.parse_init_data("hash=abc&auth_date=99999999999&user=%7B%22id%22%3A1%7D") is None
    assert server.parse_init_data("") is None
    assert server.parse_init_data("no_hash_here=1") is None
    print("  OK  parse_init_data -> soxta hash rad etiladi")


def test_cheq_verdict_has_all_levels():
    """Chek caption: mos / mos emas / karta mos emas holatlari."""
    import cheq_ocr

    ok = cheq_ocr.verdict_line({"amount_ok": True, "card_ok": True, "found": [50000]}, 50000)
    assert "summa mos" in ok

    bad_amount = cheq_ocr.verdict_line({"amount_ok": False, "found": [1000]}, 50000)
    assert "summa topilmadi" in bad_amount

    bad_card = cheq_ocr.verdict_line({"amount_ok": True, "card_ok": False, "found": [50000]}, 50000)
    assert "karta raqami mos emas" in bad_card
    print("  OK  cheq_ocr.verdict_line -> 3 daraja (mos / summa / karta)")


def test_card_number_never_hardcoded():
    """config.py da haqiqiy karta raqami BO'LMASLIGI kerak."""
    with open(f"{BASE}/config.py", encoding="utf-8") as fh:
        src = fh.read()
    for needle in ("5614 6812", "9860 2466", "4466 1369", "4916 9903", "8800667035:AAF"):
        assert needle not in src, f"config.py da maxfiy ma'lumot: {needle}"
    print("  OK  config.py -> karta raqami/token yo'q")


def test_gitignore_protects_runtime_secrets():
    with open(f"{BASE}/.gitignore", encoding="utf-8") as fh:
        gi = fh.read()
    for needle in (".env", "data/settings.json", "data/*.db", "logs/"):
        assert needle in gi, f".gitignore da yo'q: {needle}"
    print("  OK  .gitignore -> .env/settings.json/DB/loglar himoyalangan")


def main():
    print("=== WEBAPP API VA XAVFSIZLIK ===")
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
    print(f"BARCHA {len(tests)} TA TEST O'TDI")


if __name__ == "__main__":
    main()