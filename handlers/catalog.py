"""Katalog + balans/stars orqali sotib olish — bot.py dan ko'chirildi (faza 3a)."""
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

import config
import database as db
import keyboards as kb
import text as ls
from handlers.helpers import _ensure_not_banned, _lang, format_price, safe_edit
from states import BalanceBuyStates, StarsBuyStates

router = Router()


@router.callback_query(F.data == "back:games")
async def back_to_games(call: CallbackQuery):
    if not await _ensure_not_banned(call): return
    await safe_edit(call.message,
        "🎮 <b>O'yinlar katalogi</b>\n\nTanlang 👇",
        reply_markup=kb.games_menu_kb(),
    )
    await call.answer()


@router.callback_query(F.data == "back:home")
async def back_to_home(call: CallbackQuery):
    if not await _ensure_not_banned(call): return
    await safe_edit(call.message, ls.menu_text(_lang(call)), reply_markup=kb.back_home_kb())
    await call.answer()


@router.callback_query(F.data.startswith("game:"))
async def show_game(call: CallbackQuery):
    if not await _ensure_not_banned(call): return
    game_id = call.data.split(":")[1]
    game = kb.find_game(game_id)
    if not game:
        await call.answer("O'yin topilmadi", show_alert=True)
        return
    await safe_edit(call.message,
        ls.game_info_text(game, _lang(call)),
        reply_markup=kb.packages_kb(game_id),
    )
    await call.answer()


@router.callback_query(F.data.startswith("pkg:"))
async def show_package(call: CallbackQuery):
    if not await _ensure_not_banned(call): return
    parts = call.data.split(":")
    game_id, package_id = parts[1], parts[2]
    game = kb.find_game(game_id)
    pkg = kb.find_package(game_id, package_id)
    if not game or not pkg:
        await call.answer("Paket topilmadi", show_alert=True)
        return
    user = await db.get_user(call.from_user.id)
    balance = user["balance"] if user else 0
    await safe_edit(call.message,
        f"🛒 <b>{game['name']} — {pkg['name']}</b>\n\n"
        f"💰 Narx: <b>{format_price(pkg['price'])} so'm</b>\n"
        f"💠 Sizning balans: <b>{format_price(balance)} so'm</b>\n\n"
        f"To'lov usulini tanlang:",
        reply_markup=kb.pay_method_kb(game_id, package_id, pkg["price"], balance),
    )
    await call.answer()


@router.callback_query(F.data.startswith("buy_balance:"))
async def buy_with_balance(call: CallbackQuery, state: FSMContext):
    if not await _ensure_not_banned(call): return
    parts = call.data.split(":")
    game_id, package_id = parts[1], parts[2]
    game = kb.find_game(game_id)
    pkg = kb.find_package(game_id, package_id)
    user = await db.get_user(call.from_user.id)
    if not game or not pkg or not user:
        await call.answer("Xatolik", show_alert=True)
        return

    if user["balance"] < pkg["price"]:
        await safe_edit(call.message,
            ls.too_low_balance_text(_lang(call)),
            reply_markup=kb.back_home_kb(),
        )
        await call.answer()
        return

    await state.set_state(BalanceBuyStates.waiting_player_id)
    await state.update_data(
        pending_game_id=game_id,
        pending_package_id=package_id,
        pending_price=pkg["price"],
    )
    placeholder = game.get("game_id_placeholder", "O'yin ID ni kiriting")
    await safe_edit(call.message,
        f"🎮 <b>{game['name']}</b>\n\n🕹 {placeholder}:\n\n"
        f"<i>Masalan: 123456789</i>",
        reply_markup=kb.back_home_kb(),
    )
    await call.answer()


@router.callback_query(F.data.startswith("buy_stars:"))
async def buy_with_stars(call: CallbackQuery, state: FSMContext):
    if not await _ensure_not_banned(call): return
    parts = call.data.split(":")
    game_id, package_id = parts[1], parts[2]
    game = kb.find_game(game_id)
    pkg = kb.find_package(game_id, package_id)
    if not game or not pkg:
        await call.answer("Paket topilmadi", show_alert=True)
        return
    stars = config.stars_count_for_price(pkg["price"])
    await state.set_state(StarsBuyStates.waiting_player_id)
    await state.update_data(pending_stars_game_id=game_id, pending_stars_package_id=package_id)
    placeholder = game.get("game_id_placeholder", "O'yin ID ni kiriting")
    await safe_edit(call.message,
        f"🎮 <b>{game['name']}</b> — {pkg['name']}\n\n"
        f"🕹 {placeholder}:\n\n"
        f"<i>Summa: {format_price(pkg['price'])} so'm ≈ {stars} ⭐️</i>\n\n"
        f"<i>Bekor qilish uchun /cancel</i>",
        reply_markup=kb.back_home_kb(),
    )
    await call.answer()
