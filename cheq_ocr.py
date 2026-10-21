"""Chek (screenshot) rasmdan summani avtomatik tekshirish — Tesseract OCR.

Muhim: bu faqat YORDAMCHI — hech qanday to'lov avtomatik tasdiqlanmaydi,
faqat adminga "summa mos / mos emas" degan maslahat beriladi.
"""
import io
import re

_ENGINE_READY = None


def engine_ready() -> bool:
    """pytesseract + tesseract binary mavjudligini tekshiradi."""
    global _ENGINE_READY
    if _ENGINE_READY is None:
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            _ENGINE_READY = True
        except Exception:
            _ENGINE_READY = False
    return _ENGINE_READY


def _lang() -> str:
    try:
        import pytesseract

        langs = set(pytesseract.get_languages(config="") or [])
        want = [x for x in ("uzb", "uzb_cyrl", "eng", "rus") if x in langs]
        return "+".join(want) if want else "eng"
    except Exception:
        return "eng"


def extract_numbers(text: str):
    """Matndan barcha mumkin bo'lgan raqamlarni (minglik ajratkich bilan) chiqaradi."""
    out = set()
    cleaned = re.sub(r"(?i)(som|so'm|uzs|сум)", " ", text or "")
    for m in re.finditer(r"\d[\d \t.,]{1,15}\d", cleaned):
        raw = m.group(0)
        digits = re.sub(r"[^\d]", "", raw)
        if not digits:
            continue
        try:
            val = int(digits)
            if 100 <= val <= 100_000_000:  # Valid amount range
                out.add(val)
        except ValueError:
            pass
    for m in re.finditer(r"\d{1,3}(?:[., \t]\d{3})+", cleaned):
        digits = re.sub(r"[^\d]", "", m.group(0))
        if digits:
            try:
                val = int(digits)
                if 100 <= val <= 100_000_000:
                    out.add(val)
            except ValueError:
                pass
    return out


def extract_cards(text: str):
    """Matndan karta raqamiga o'xshash 16 xonali raqamlarni yoki oxirgi 4 talikni chiqaradi."""
    out = set()
    for m in re.finditer(r"(?:\d[ \t.-]?){16}", text or ""):
        digits = re.sub(r"[^\d]", "", m.group(0))
        if len(digits) == 16:
            out.add(digits)
    # Oxirgi 4 raqam (*4123 yoki card ending 4123)
    for m in re.finditer(r"(?:[*xX#]{2,12}\s*(\d{4})|card\s*(\d{4}))", text or "", re.IGNORECASE):
        d = m.group(1) or m.group(2)
        if d and len(d) == 4:
            out.add(d)
    return out


def check_receipt(image_bytes: bytes, expected_amount: int, expected_card_last4: str = ""):
    """Rasmni o'qib, summa + karta mosligini tekshiradi (Enhanced OCR)."""
    if not engine_ready() or not image_bytes:
        return None
    try:
        import pytesseract
        from PIL import Image, ImageEnhance, ImageOps

        img = Image.open(io.BytesIO(image_bytes))
        try:
            raw = pytesseract.image_to_string(img, lang=_lang())
        except Exception:
            img = ImageOps.grayscale(img)
            img = ImageEnhance.Contrast(img).enhance(2.0)
            raw = pytesseract.image_to_string(img, lang="eng")
        
        found = extract_numbers(raw)
        cards = extract_cards(raw)
        exp = int(expected_amount or 0)
        amount_ok = bool(exp) and (exp in found or any(abs(exp - f) <= 100 for f in found))
        
        card_ok = None
        if expected_card_last4:
            last4 = re.sub(r"[^\d]", "", expected_card_last4 or "")[-4:]
            card_ok = bool(last4) and any(c.endswith(last4) for c in cards)

        confidence = 0.9 if amount_ok else (0.5 if found else 0.1)
        if card_ok is True:
            confidence = min(1.0, confidence + 0.1)

        return {
            "ok": bool(amount_ok and (card_ok is not False)),
            "amount_ok": amount_ok,
            "card_ok": card_ok,
            "card_found": sorted(cards),
            "found": sorted(found)[-8:],
            "confidence": confidence,
            "raw": (raw or "")[:150],
        }
    except Exception:
        return None


def verdict_line(result, expected_amount: int) -> str:
    """Admin caption uchun qisqa matn (3 darajali)."""
    if not result:
        return ""
    exp = f"{int(expected_amount or 0):,}".replace(",", " ")
    amount_ok = result.get("amount_ok", result.get("ok"))
    card_ok = result.get("card_ok")
    if amount_ok and card_ok is not False:
        extra = " + karta mos ✅" if card_ok else ""
        return f"\n🔍 <b>Avtomatik tekshiruv:</b> ✅ summa mos ({exp} so'm{extra})"
    problems = []
    if not amount_ok:
        found = result.get("found") or []
        nums = ", ".join(f"{n:,}".replace(",", " ") for n in found[-4:]) or "topilmadi"
        problems.append(f"summa topilmadi (ko'rilgan: {nums})")
    if card_ok is False:
        problems.append("🚨 <b>karta raqami mos emas — soxta chek bo'lishi mumkin!</b>")
    return (
        f"\n🔍 <b>Avtomatik tekshiruv:</b> ⚠️ chekda {exp} so'm: "
        + "; ".join(problems) + ". Qo'lda tekshirib tasdiqlang."
    )
