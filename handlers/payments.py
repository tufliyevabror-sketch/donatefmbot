"""To'lov handlerlari: topup, chek qabul, Telegram Stars — bot.py dan ko'chirildi (faza 3b)."""
import base64
from datetime import datetime, timedelta

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
)

import config
import database as db
import keyboards as kb
import text as ls
import animations
from handlers.helpers import (
    _admin_ids_cache,
    _all_admin_ids,
    _client_line,
    _ensure_not_banned,
    _expected_card_last4,
    _lang,
    _ocr_verdict,
    _start_card_topup,
    format_price,
    is_admin,
    safe_edit,
    stars_to_som,
)
from states import AdminStates, SupportStates, TopUpStates

router = Router()


@router.callback_query(F.data == "topup:menu")
async def topup_menu(call: CallbackQuery):
    if not await _ensure_not_banned(call): return
    await safe_edit(call.message, ls.topup_menu_text(_lang(call)), reply_markup=kb.balance_kb())
    await call.answer()


@router.callback_query(F.data == "topup:card")
async def topup_card(call: CallbackQuery):
    if not await _ensure_not_banned(call): return
    # Loading animation
    await call.message.edit_text("💳 <b>Karta to'lovi</b>\n\n⏳ <b>Summalar yuklanmoqda...</b> ", reply_markup=None)
    await asyncio.sleep(0.3)
    await safe_edit(call.message,
        "💳 <b>Karta orqali to'lov</b>\n\n"
        "Summani tanlang yoki o'zingiz yozing:",
        reply_markup=kb.topup_amounts_kb(),
    )
    await call.answer()


@router.callback_query(F.data.startswith("topup_manual:"))
async def topup_manual_selected(call: CallbackQuery, state: FSMContext):
    if not await _ensure_not_banned(call): return
    amount = int(call.data.split(":")[1])
    await state.set_state(TopUpStates.waiting_card_choice)
    await state.update_data(card_amount=amount)
    await safe_edit(
        call.message,
        f"💳 <b>Qaysi kartaga to'lov qilasiz?</b>\n\n"
        f"💰 Summa: <b>{format_price(amount)} so'm</b>\n\n"
        "Kartani tanlang — so'ngra karta raqami ko'rsatiladi:",
        reply_markup=kb.topup_cards_kb(amount),
    )
    await call.answer()


@router.callback_query(F.data.startswith("topup_card_pick:"))
async def topup_card_pick(call: CallbackQuery, state: FSMContext):
    if not await _ensure_not_banned(call): return
    try:
        _, amount_s, card_key = call.data.split(":", 2)
        amount = int(amount_s)
    except Exception:
        await call.answer("Xatolik", show_alert=True)
        return
    cards = config.all_cards()
    card = next((c for c in cards if c["key"] == card_key), None)
    if not card:
        await call.answer("Karta topilmadi", show_alert=True)
        return
    data = await state.get_data()
    pending_photo = data.get("pending_photo")
    await state.set_state(TopUpStates.waiting_card_photo)
    await state.update_data(card_amount=amount, card_key=card["key"], pending_photo=None)
    await safe_edit(
        call.message,
        ls.card_topup_text(amount, _lang(call), card_key=card["key"]),
        reply_markup=None,
    )
    await call.answer()
    payment_id = await _start_card_topup(call.message, call.from_user.id, amount, _lang(call), card_label=card["label"])
    if pending_photo:
        try:
            await db.set_payment_chek(payment_id)
            client = await _client_line(call.from_user.id, "👤 Foydalanuvchi")
            for admin_id in await _all_admin_ids():
                try:
                    await call.message.bot.send_photo(
                        admin_id,
                        photo=pending_photo,
                        caption=f"💳 <b>Chek keldi!</b> (To'lov #{payment_id})\n\n"
                                f"💠 Usul: karta ({card['label']})\n"
                                f"{client}\n"
                                f"💰 Summa: <b>{format_price(amount or 0)} so'm</b>",
                        reply_markup=kb.confirm_topup_kb(payment_id),
                    )
                except Exception:
                    pass
            await call.message.answer(
                f"✅ <b>Chek qabul qilindi!</b>\n\n"
                f"To'lov raqami: <code>#{payment_id}</code>\n"
                f"Admin tekshirmoqda... ⏳"
            )
        except Exception:
            pass


@router.callback_query(F.data.startswith("topup_manual_card:"))
async def topup_manual_card_pick(call: CallbackQuery, state: FSMContext):
    if not await _ensure_not_banned(call): return
    card_key = call.data.split(":", 1)[1]
    cards = config.all_cards()
    card = next((c for c in cards if c["key"] == card_key), None)
    if not card:
        await call.answer("Karta topilmadi", show_alert=True)
        return
    data = await state.get_data()
    photo_id = data.get("manual_photo")
    await state.clear()
    
    # Loading animation
    msg = await call.message.edit_text("⏳ <b>To'lov yaratilmoqda...</b> ", reply_markup=None)
    await asyncio.sleep(0.3)
    
    payment_id = await db.create_payment(call.from_user.id, "karta", 0, "", chek=1)
    client = await _client_line(call.from_user.id, "👤 Foydalanuvchi")
    verdict = await _ocr_verdict(call.message.bot, photo_id, 0) if photo_id else ""
    
    # Animate success
    await animations.animate_success(msg, f"✅ To'lov yaratildi! <code>#{payment_id}</code>")
    await asyncio.sleep(0.5)
    
    verdict = await _ocr_verdict(call.message.bot, photo_id, 0) if photo_id else ""
    for admin_id in await _all_admin_ids():
        try:
            if photo_id:
                await call.message.bot.send_photo(
                    admin_id,
                    photo=photo_id,
                    caption=f"💰 <b>Yangi karta to'lovi!</b>\n\n"
                            f"To'lov: <code>#{payment_id}</code>\n"
                            f"💳 Karta: <b>{card['label']}</b>\n"
                            f"{client}\n"
                            f"💰 Summa: noma'lum (foydalanuvchi chek yubordi)"
                            f"{verdict}",
                        reply_markup=kb.confirm_topup_kb(payment_id),
                    )
            else:
                await call.message.bot.send_message(
                    admin_id,
                    f"💰 <b>Yangi karta to'lovi!</b>\n\n"
                    f"To'lov: <code>#{payment_id}</code>\n"
                    f"💳 Karta: <b>{card['label']}</b>\n"
                    f"{client}\n"
                    f"💰 Summa: noma'lum",
                )
        except Exception:
            pass
    await call.message.answer(
        ls.card_photo_received(payment_id, _lang(call)) + f"\n💳 Karta: <b>{card['label']}</b>"
    )
    await call.answer()


@router.callback_query(F.data == "topup:custom")
async def topup_custom(call: CallbackQuery, state: FSMContext):
    if not await _ensure_not_banned(call): return
    await state.set_state(TopUpStates.waiting_custom_amount)
    await safe_edit(call.message,
        "💳 <b>Boshqa summa</b>\n\n"
        "Summani so'mda kiriting (masalan: 75 000):\n\n"
        "<i>Bekor qilish uchun /cancel</i>",
        reply_markup=None,
    )
    await call.answer()


@router.callback_query(F.data == "topup:stars")
async def topup_stars(call: CallbackQuery):
    if not await _ensure_not_banned(call): return
    await safe_edit(call.message,
        "⭐️ <b>Telegram Stars orqali to'ldirish</b>\n\n"
        f"1 ⭐️ = {config.stars_rate_per_1000() // 1000} so'm\n\n"
        "Stars sonini tanlang:",
        reply_markup=kb.topup_stars_amounts_kb(),
    )
    await call.answer()


@router.callback_query(F.data.startswith("topup_stars_amt:"))
async def topup_stars_amount(call: CallbackQuery):
    if not await _ensure_not_banned(call): return
    stars = int(call.data.split(":")[1])
    som = stars_to_som(stars)
    
    # Loading animation
    msg = await call.message.edit_text(f"⭐️ <b>Stars to'lovi</b>\n\n⏳ <b>Invoice yaratilmoqda...</b> ", reply_markup=None)
    await asyncio.sleep(0.3)
    
    await call.message.answer_invoice(
        title="Hisobni to'ldirish (Stars)",
        description=(
            f"{stars} ⭐️ = <b>{format_price(som)} so'm</b>\n\n"
            f"To'lovdan keyin balansingizga avtomatik qo'shiladi."
        ),
        payload=f"topup_stars:{stars}",
        currency="XTR",
        prices=[LabeledPrice(label="XTR", amount=stars)],
        provider_token="",
    )
    await animations.animate_success(call.message, f"✅ Invoice yuborildi! {stars} ⭐️ Stars")
    await call.answer()


# ================== CARD CHECK RECEIVE ==================

@router.message(F.photo)
async def receive_card_photo(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    if user and "is_banned" in user and user["is_banned"]:
        return
    st = await state.get_state()

    # Admin broadcast state: photo + caption alohida ishlatiladi
    if st == AdminStates.broadcast_text and is_admin(user_id):
        text = message.caption or ""
        if not text.strip():
            await message.answer("⚠️ Rasmga izoh (caption) yozing yoki /cancel.")
            return
        users = await db.get_all_user_ids()
        await state.update_data(broadcast_msg=text, broadcast_photo=message.photo[-1].file_id)
        await state.set_state(AdminStates.entering_notice)
        preview_kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✅ Yuborish", callback_data="broadcast_go")],
                [InlineKeyboardButton(text="❌ Bekor", callback_data="broadcast_cancel")],
            ]
        )
        await message.answer(
            f"{ls.broadcast_preview_text(len(users), _lang(message))}\n\n📷 Rasm bilan:\n<i>{text[:200]}</i>",
            reply_markup=preview_kb,
        )
        return

    if st and st not in (
        TopUpStates.waiting_card_photo,
        TopUpStates.waiting_card_choice,
        TopUpStates.waiting_manual_card,
    ):
        if st == TopUpStates.waiting_custom_amount:
            await message.answer("❌ Avval summani <b>raqam</b> ko'rinishida kiriting.")
            return
        if st == SupportStates.awaiting_message:
            await message.answer(
                "📧 Iltimos, murojaatingizni <b>matn</b> ko'rinishida yozing.\n\n"
                "<i>(/cancel — bekor qilish)</i>"
            )
            return
        if st == AdminStates.replying_user and is_admin(user_id):
            data = await state.get_data()
            target = data.get("reply_target")
            await state.clear()
            if not target:
                await message.answer("❌ Xatolik yuz berdi.")
                return
            try:
                await message.bot.send_photo(
                    int(target),
                    photo=message.photo[-1].file_id,
                    caption="📬 <b>Admin javobi:</b>",
                )
                await message.answer("✅ Rasm foydalanuvchiga yuborildi.")
            except Exception:
                await message.answer("❌ Yuborilmadi (foydalanuvchi botni bloklagan bo'lishi mumkin).")
            return
        if st == AdminStates.entering_notice and is_admin(user_id):
            await message.answer("⚠️ E'lonni tasdiqlash tugmalarini bosing yoki /cancel.")
            return
        await state.clear()
        await message.answer(ls.menu_text(_lang(message)), reply_markup=kb.main_menu_kb())
        return

    payments = await db.get_user_payments(user_id, 10)
    pending = [p for p in payments if p["status"] == "kutilmoqda"]

    # Kartani tanlamasdan chek yuborildi: chekni saqlab, birinchi kartani tanlatamiz
    if st == TopUpStates.waiting_card_choice:
        data = await state.get_data()
        amount = data.get("card_amount")
        if amount:
            await state.update_data(pending_photo=message.photo[-1].file_id)
            await message.answer(
                f"💳 <b>Qaysi kartaga to'lov qildingiz?</b>\n\n"
                f"💰 Summa: <b>{format_price(amount)} so'm</b>",
                reply_markup=kb.topup_cards_kb(amount),
            )
        else:
            await state.set_state(TopUpStates.waiting_manual_card)
            await state.update_data(manual_photo=message.photo[-1].file_id)
            await message.answer(
                "💳 <b>Qaysi kartaga to'lov qildingiz?</b>",
                reply_markup=kb.topup_cards_kb_manual(),
            )
        return

    if st == TopUpStates.waiting_manual_card:
        # Oldingi chek hali "qo'lda" rejimida edi; yana chek kelsa — ikkedan oling
        await message.answer("⏳ Avval yuqoridagi kartalardan birini tanlang.")
        return

    in_topup = st == TopUpStates.waiting_card_photo
    if in_topup:
        data = await state.get_data()
        amount = data.get("card_amount")
        await state.clear()
    else:
        # Webapp orqali yaratilgan to'lov: FSM holati bo'lmasa ham,
        # yaqin vaqtdagi kutilayotgan to'lov bo'lsa — chek sifatida qabul qilinadi.
        amount = None
        fresh = []
        for p in pending:
            try:
                created = datetime.strptime(p["created_at"], "%Y-%m-%d %H:%M")
                if datetime.now() - created <= timedelta(hours=6):
                    fresh.append(p)
            except Exception:
                pass
        pending = fresh
        if not pending:
            return

    if pending:
        payment_id = pending[0]["id"]
        method = pending[0]["method"]
        if not amount:
            amount = pending[0]["amount"]
        file_uid = ""
        try:
            file_uid = message.photo[-1].file_unique_id
        except Exception:
            pass
        dup = await db.find_payment_by_file(file_uid)
        dup_warn = ""
        if dup and int(dup["id"]) != int(payment_id):
            dup_warn = (
                f"\n🚨 <b>Dublikat ogohlantirish:</b> bu chek avval "
                f"#{dup['id']} to'lovda ishlatilgan!"
            )
        await db.set_payment_chek(payment_id)
        await db.set_payment_file(payment_id, file_uid)
        await message.answer(
            f"✅ <b>Chek qabul qilindi!</b>\n\n"
            f"To'lov raqami: <code>#{payment_id}</code>\n"
            f"Admin tekshirmoqda... ⏳"
        )
        client = await _client_line(user_id, "👤 Foydalanuvchi")
        verdict = await _ocr_verdict(
            message.bot, message.photo[-1].file_id, amount,
            _expected_card_last4(method),
        )
        for admin_id in _admin_ids_cache:
            try:
                await message.bot.send_photo(
                    admin_id,
                    photo=message.photo[-1].file_id,
                    caption=f"💳 <b>Chek keldi!</b> (To'lov #{payment_id})\n\n"
                            f"💠 Usul: {method}\n"
                            f"{client}\n"
                            f"💰 Summa: <b>{format_price(amount or 0)} so'm</b>\n"
                            f"⏰ Kutilmoqda: {len(pending)} ta to'lov"
                            f"{verdict}"
                            f"{dup_warn}",
                    reply_markup=kb.confirm_topup_kb(payment_id),
                )
            except Exception:
                pass
        return

    # Oddiy qo'lda top-up: chek yuborildi — avval kartani tanlatamiz
    if not amount:
        await state.set_state(TopUpStates.waiting_manual_card)
        await state.update_data(manual_photo=message.photo[-1].file_id)
        await message.answer(
            "💳 <b>Qaysi kartaga to'lov qildingiz?</b>\n\n"
            "Chekni qabul qilish uchun kartani tanlang, so'ng summani yozing.",
            reply_markup=kb.topup_cards_kb_manual(),
        )
        return

    payment_id = await db.create_payment(user_id, "karta", amount, "", chek=1)
    try:
        await db.set_payment_file(payment_id, message.photo[-1].file_unique_id)
    except Exception:
        pass
    await message.answer(ls.card_photo_received(payment_id, _lang(message)))
    client = await _client_line(user_id, "👤 Foydalanuvchi")
    verdict = await _ocr_verdict(
        message.bot, message.photo[-1].file_id, amount, _expected_card_last4("karta")
    )
    for admin_id in _admin_ids_cache:
        try:
            await message.bot.send_photo(
                admin_id,
                photo=message.photo[-1].file_id,
                caption=f"💰 <b>Yangi karta to'lovi!</b>\n\n"
                        f"To'lov: <code>#{payment_id}</code>\n"
                        f"{client}\n"
                        f"💰 Summa: <b>{format_price(amount)} so'm</b>"
                        f"{verdict}",
                reply_markup=kb.confirm_topup_kb(payment_id),
            )
        except Exception:
            pass


# ================== INVOICE / PAYMENTS ==================

@router.pre_checkout_query()
async def pre_checkout(pre_checkout_query: PreCheckoutQuery):
    payload = pre_checkout_query.invoice_payload
    user = await db.get_user(pre_checkout_query.from_user.id)
    if user and "is_banned" in user and user["is_banned"]:
        await pre_checkout_query.answer(ok=False, error_message="Siz bloklangansiz.")
        return
    if payload.startswith("buy:"):
        parts = payload.split(":")
        if len(parts) < 3:
            await pre_checkout_query.answer(ok=False, error_message="Noto'g'ri so'rov.")
            return
        game = kb.find_game(parts[1])
        pkg = kb.find_package(parts[1], parts[2])
        if not game or not pkg:
            await pre_checkout_query.answer(ok=False, error_message="Mahsulot topilmadi.")
            return
        expected = config.stars_count_for_price(pkg["price"])
        if pre_checkout_query.total_amount != expected:
            await pre_checkout_query.answer(ok=False, error_message="Summa noto'g'ri.")
            return
    elif payload.startswith("topup:"):
        try:
            amount = int(payload.split(":")[1])
        except (IndexError, ValueError):
            await pre_checkout_query.answer(ok=False, error_message="Noto'g'ri summa.")
            return
        if amount <= 0 or amount > 100_000_000:
            await pre_checkout_query.answer(ok=False, error_message="Noto'g'ri summa.")
            return
        expected = config.stars_count_for_price(amount)
        if pre_checkout_query.total_amount != expected:
            await pre_checkout_query.answer(ok=False, error_message="Summa noto'g'ri.")
            return
    elif payload.startswith("topup_stars:"):
        try:
            s = int(payload.split(":")[1])
            if s < 1:
                raise ValueError
        except (IndexError, ValueError):
            await pre_checkout_query.answer(ok=False, error_message="Noto'g'ri miqdor.")
            return
        if pre_checkout_query.total_amount != s:
            await pre_checkout_query.answer(ok=False, error_message="Miqdor noto'g'ri.")
            return
    await pre_checkout_query.answer(ok=True)


async def _notify_stars_topup(bot, user_id, amount_som, payment_id, stars=None):
    """Stars orqali to'lov: adminga xabar (Telegram username + ID bilan)."""
    client = await _client_line(user_id)
    if stars is None:
        stars = config.stars_count_for_price(int(amount_som or 0))
    for admin_id in _admin_ids_cache:
        try:
            await bot.send_message(
                admin_id,
                f"⭐️ <b>Stars orqali to'lov</b>\n\n"
                f"{client}\n"
                f"💰 Summa: <b>{format_price(int(amount_som or 0))} so'm</b>\n"
                f"⭐️ To'lov: <b>{stars} ⭐️</b>\n"
                f"💠 Usul: Telegram Stars\n"
                f"💳 To'lov raqami: <code>#{payment_id}</code>\n"
                f"✅ Balans avtomatik to'ldirildi",
            )
        except Exception:
            pass


@router.message(F.successful_payment)
async def successful_payment(message: Message):
    payload = message.successful_payment.invoice_payload
    charge_id = message.successful_payment.telegram_payment_charge_id

    # Loading animation
    msg = await message.answer("⏳ <b>To'lov tasdiqlanmoqda...</b> ")
    await asyncio.sleep(0.5)
    
    payload = message.successful_payment.invoice_payload
    charge_id = message.successful_payment.telegram_payment_charge_id

    # topup:{amount_som}
    if payload.startswith("topup:"):
        amount = int(payload.split(":")[1])
        existing = await db.get_payment_by_ref(charge_id)
        if not existing:
            await db.add_balance(
                message.from_user.id, amount, method="stars", ref=charge_id
            )
            # add_balance(ref=...) payment qatorini o'zi yaratadi
            row = await db.get_payment_by_ref(charge_id)
            payment_id = row["id"] if row else 0
            await _notify_stars_topup(message.bot, message.from_user.id, amount, payment_id)
        await animations.animate_success(msg, f"✅ To'lov qabul qilindi! Balansingiz: <b>{format_price((await db.get_user(message.from_user.id))['balance'])} so'm</b>. 🎉")
        return

    # legacy topup_stars:{stars}
    if payload.startswith("topup_stars:"):
        stars = int(payload.split(":")[1])
        som = stars_to_som(stars)
        existing = await db.get_payment_by_ref(charge_id)
        if not existing:
            await db.add_balance(message.from_user.id, som, method="stars", ref=charge_id)
            row = await db.get_payment_by_ref(charge_id)
            payment_id = row["id"] if row else 0
            await _notify_stars_topup(message.bot, message.from_user.id, som, payment_id, stars)
        await animations.animate_success(msg, ls.balance_after_topup_text(
            (await db.get_user(message.from_user.id))["balance"],
            _lang(message)
        ))
        return

    # buy:{game_id}:{package_id}:{b64_player_id}
    if payload.startswith("buy:"):

        parts = payload.split(":")
        game_id, package_id = parts[1], parts[2]
        player_b64 = parts[3] if len(parts) > 3 else ""
        try:
            player_id = base64.urlsafe_b64decode(player_b64.encode()).decode()
        except Exception:
            player_id = ""
        game = kb.find_game(game_id)
        pkg = kb.find_package(game_id, package_id)
        if not game or not pkg:
            await message.answer("❌ Xatolik: mahsulot topilmadi. Admin bilan bog'laning.")
            return
        # Idempotent: bu charge_id allaqachon ishlangan bo'lsa (retry) qayta yaratmaymiz
        existing = await db.get_payment_by_ref(charge_id)
        if existing:
            return
        order_id = await db.create_order(
            message.from_user.id,
            game["id"],
            pkg["name"],
            str(pkg["amount"]),
            pkg["price"],
            player_id,
        )
        payment_id = await db.create_payment(
            message.from_user.id, "stars", pkg["price"], ref=charge_id
        )
        if payment_id:
            await db.set_payment_status(payment_id, "tasdiqlandi")
        await message.answer(
            f"✅ <b>To'lov qabul qilindi!</b>\n\n"
            f"🎮 {game['name']} — {pkg['name']}\n"
            f"🆔 O'yin ID: <code>{player_id}</code>\n"
            f"📦 Buyurtma: <code>#{order_id}</code>\n\n"
            f"Iltimos admin bajarishini kuting. 📜 Tarix bo'limidan kuzatish mumkin.",
        )
        client = await _client_line(message.from_user.id)
        for admin_id in _admin_ids_cache:
            try:
                await message.bot.send_message(
                    admin_id,
                    f"📦 <b>Yangi buyurtma!</b>\n\n"
                    f"🎮 {game['name']}\n📦 {pkg['name']}\n"
                    f"🆔 O'yin ID: <code>{player_id}</code>\n"
                    f"{client}\n"
                    f"💰 {format_price(pkg['price'])} so'm\n"
                    f"⭐️ To'lov: Telegram Stars",
                    reply_markup=kb.order_admin_kb(order_id),
                )
            except Exception:
                pass
        return

