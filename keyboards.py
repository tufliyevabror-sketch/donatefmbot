import json

from aiogram.types import (
    CopyTextButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

import config
from config import GAME_ICONS, PACKAGES_PATH


def load_games():
    with open(PACKAGES_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["games"]


def find_game(game_id):
    for game in load_games():
        if game["id"] == game_id:
            return game
    return None


def find_package(game_id, package_id):
    game = find_game(game_id)
    if not game:
        return None
    for p in game["packages"]:
        if p["id"] == package_id:
            return p
    return None


# ---------- Reply Keyboard (pastki menyu) ----------

def main_menu_kb():
    kb = [
        [KeyboardButton(text="🏠 Bosh sahifa")],
        [KeyboardButton(text="🛒 O'yinlar")],
        [KeyboardButton(text="💰 Balans")],
        [KeyboardButton(text="📜 Tarix")],
        [KeyboardButton(text="🤝 Taklif"), KeyboardButton(text="❓ Yordam")],
        [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="📧 Murojaat")],
        [KeyboardButton(text="⚙️ Sozlamalar")],
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def help_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="💳 To'lov qanday?", callback_data="faq:pay")
    builder.button(text="📦 Buyurtma qanday?", callback_data="faq:order")
    builder.button(text="💎 Keshbek", callback_data="faq:cashback")
    builder.button(text="🤝 Taklif (referral)", callback_data="faq:referral")
    builder.button(text="📧 Murojaat", callback_data="faq:support")
    builder.adjust(1)
    return builder.as_markup()


def support_admin_kb(user_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✉️ Javob berish", callback_data=f"admin_reply:{user_id}")],
            [InlineKeyboardButton(text="👁 Profil", callback_data=f"admin_user_view:{user_id}")],
        ]
    )


def help_back_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 Yordam ro'yxati", callback_data="faq:main")]]
    )


def cancel_kb():
    kb = [[KeyboardButton(text="❌ Bekor qilish")]]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


# ---------- Inline keyboards ----------

def games_menu_kb():
    builder = InlineKeyboardBuilder()
    games = load_games()
    for game in games:
        emoji = GAME_ICONS.get(game["id"], "🎮")
        builder.button(
            text=f"{emoji} {game['name']} — {game['desc']}",
            callback_data=f"game:{game['id']}",
        )
    builder.adjust(1)
    return builder.as_markup()


def packages_kb(game_id):
    builder = InlineKeyboardBuilder()
    game = find_game(game_id)
    if not game:
        return InlineKeyboardMarkup(inline_keyboard=[])
    for p in game["packages"]:
        btn = InlineKeyboardButton(
            text=f"{p['name']} — {p['price']:,} so'm".replace(",", " "),
            callback_data=f"pkg:{game_id}:{p['id']}",
        )
        builder.add(btn)
    builder.add(InlineKeyboardButton(text="🔙 Orqaga", callback_data="back:games"))
    builder.add(InlineKeyboardButton(text="🏠 Bosh sahifa", callback_data="back:home"))
    builder.adjust(1)
    return builder.as_markup()


def back_home_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Bosh sahifa", callback_data="back:home")]
        ]
    )


def pay_method_kb(game_id, package_id, price, balance):
    name = "💠 Balans bilan to'lash"
    if balance < price:
        name = f"💠 Balans bilan ({balance:,} so'm yetarli emas)".replace(",", " ")
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text=name, callback_data=f"buy_balance:{game_id}:{package_id}"))
    builder.add(
        InlineKeyboardButton(
            text="⭐️ Telegram Stars", callback_data=f"buy_stars:{game_id}:{package_id}"
        )
    )
    builder.add(InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"game:{game_id}"))
    builder.add(InlineKeyboardButton(text="🏠 Bosh sahifa", callback_data="back:home"))
    builder.adjust(1)
    return builder.as_markup()


def balance_kb():
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="🚀 Hisobni to'ldirish", callback_data="topup:menu"))
    builder.add(
        InlineKeyboardButton(text="⭐️ Telegram Stars bilan", callback_data="topup:stars")
    )
    builder.add(InlineKeyboardButton(text="💳 Karta orqali", callback_data="topup:card"))
    builder.adjust(1)
    return builder.as_markup()


def topup_amounts_kb():
    builder = InlineKeyboardBuilder()
    for amount in [10000, 25000, 50000, 100000, 200000, 500000]:
        builder.button(
            text=f"{amount:,} so'm".replace(",", " "),
            callback_data=f"topup_manual:{amount}",
        )
    builder.button(text="✏️ Boshqa summa", callback_data="topup:custom")
    builder.adjust(3)
    return builder.as_markup()


def topup_cards_kb(amount):
    builder = InlineKeyboardBuilder()
    for c in config.all_cards():
        builder.button(text=f"💳 {c['label']}", callback_data=f"topup_card_pick:{amount}:{c['key']}")
    builder.button(text="⬅️ Orqaga", callback_data="topup:card")
    builder.adjust(2)
    return builder.as_markup()


def topup_cards_kb_manual():
    builder = InlineKeyboardBuilder()
    for c in config.all_cards():
        builder.button(text=f"💳 {c['label']}", callback_data=f"topup_manual_card:{c['key']}")
    builder.adjust(2)
    return builder.as_markup()


def topup_stars_amounts_kb():
    builder = InlineKeyboardBuilder()
    for amount in [10, 25, 50, 100, 250, 500]:
        builder.button(text=f"⭐️ {amount} Stars", callback_data=f"topup_stars_amt:{amount}")
    builder.adjust(3)
    return builder.as_markup()


def confirm_topup_kb(payment_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Tasdiqlandi", callback_data=f"admin_pay_ok:{payment_id}")],
            [InlineKeyboardButton(text="❌ Rad etish", callback_data=f"admin_pay_no:{payment_id}")],
        ]
    )


def order_admin_kb(order_id, player_id=""):
    rows = []
    if player_id:
        rows.append([
            InlineKeyboardButton(
                text=f"📋 ID: {player_id}",
                copy_text=CopyTextButton(text=str(player_id)),
            )
        ])
    rows += [
        [InlineKeyboardButton(text="🚚 Avto-yuborish", callback_data=f"admin_send_delivery:{order_id}")],
        [InlineKeyboardButton(text="✅ Bajarildi", callback_data=f"admin_order_ok:{order_id}")],
        [InlineKeyboardButton(text="↩️ Qaytarish", callback_data=f"admin_order_refund:{order_id}")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_menu_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Statistika", callback_data="admin:stats")
    builder.button(text="📦 Buyurtmalar", callback_data="admin:orders")
    builder.button(text="💸 To'lovlar", callback_data="admin:payments")
    builder.button(text="👥 Foydalanuvchilar", callback_data="admin:users")
    builder.button(text="🔎 Qidiruv", callback_data="admin:search")
    builder.button(text="📢 Reklama", callback_data="admin:broadcast")
    builder.button(text="🎁 Promokodlar", callback_data="admin:promos")
    builder.button(text="🚚 Avto-delivery", callback_data="admin:delivery")
    builder.button(text="⚙️ Sozlamalar", callback_data="admin:settings")
    builder.button(text="📚 Katalog", callback_data="admin:catalog")
    builder.button(text="⭐ PRO", callback_data="admin:pro")
    builder.button(text="🖥 Holat", callback_data="admin:status")
    builder.button(text="➕ Balans qo'shish", callback_data="admin:add_balance")
    builder.button(text="🏠 Bosh sahifa", callback_data="back:home")
    builder.adjust(2)
    return builder.as_markup()


def _money(v):
    try:
        return f"{int(v or 0):,}".replace(",", " ")
    except (TypeError, ValueError):
        return str(v)


def catalog_kb():
    builder = InlineKeyboardBuilder()
    games = load_games()
    for g in games:
        n = len(g.get("packages") or [])
        builder.button(
            text=f"{g.get('emoji', '')} {g.get('name', g['id'])} · {n}",
            callback_data=f"admin:cat:{g['id']}"[:64],
        )
    builder.button(text="➕ O'yin qo'shish", callback_data="admin:cat_game_add")
    builder.button(text="🔙 Admin panel", callback_data="admin:menu")
    builder.adjust(1)
    return builder.as_markup()


def catalog_game_kb(game_id, packages):
    builder = InlineKeyboardBuilder()
    for p in packages:
        builder.button(
            text=f"{p.get('name', p['id'])} — {_money(p.get('price'))} so'm",
            callback_data=f"admin:catp:{game_id}:{p['id']}"[:64],
        )
    builder.button(text="➕ Paket qo'shish", callback_data=f"admin:catp_add:{game_id}"[:64])
    builder.button(text="✏️ O'yinni tahrirlash", callback_data=f"admin:catg_edit:{game_id}"[:64])
    builder.button(text="🗑 O'yinni o'chirish", callback_data=f"admin:catg_del:{game_id}"[:64])
    builder.button(text="🔙 Katalog", callback_data="admin:catalog")
    builder.adjust(1)
    return builder.as_markup()


def catalog_pkg_kb(game_id, pkg_id):
    builder = InlineKeyboardBuilder()
    builder.button(text="💰 Narxni o'zgartirish", callback_data=f"admin:catp_price:{game_id}:{pkg_id}"[:64])
    builder.button(text="✏️ Nomi", callback_data=f"admin:catp_name:{game_id}:{pkg_id}"[:64])
    builder.button(text="🗑 O'chirish", callback_data=f"admin:catp_del:{game_id}:{pkg_id}"[:64])
    builder.button(text="🔙 O'yin", callback_data=f"admin:cat:{game_id}"[:64])
    builder.adjust(1)
    return builder.as_markup()


def pro_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="💳 Balans bilan sotib olish", callback_data="pro:buy")
    builder.button(text="ℹ️ Afzalliklar", callback_data="pro:info")
    builder.button(text="🔙 Bosh menyu", callback_data="back:home")
    builder.adjust(1)
    return builder.as_markup()


def back_admin_menu_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Admin panel", callback_data="admin:menu")]
        ]
    )


def payment_view_kb(payment_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Tasdiqlash", callback_data=f"admin_pay_ok:{payment_id}"
                ),
                InlineKeyboardButton(text="❌ Rad", callback_data=f"admin_pay_no:{payment_id}"),
            ]
        ]
    )


def orders_list_kb(orders, prefix="o"):
    builder = InlineKeyboardBuilder()
    for o in orders[:15]:
        builder.button(
            text=f"#{o['id']} | {o['platform']} | {o['package_name']}",
            callback_data=f"admin_order_view:{o['id']}",
        )
    builder.button(text="🔙 Orqaga", callback_data="admin:menu")
    builder.adjust(1)
    return builder.as_markup()


def payments_list_kb(payments):
    builder = InlineKeyboardBuilder()
    MARK = {"kutilmoqda": "⏳", "rad_etildi": "❌", "tasdiqlandi": "✅", "qaytarildi": "↩️"}
    for p in payments[:15]:
        st = p.get("status", "")
        mark = MARK.get(st, "")
        builder.button(
            text=f"{mark} #{p['id']} | {p['method']} | {p['amount']:,} so'm".replace(",", " "),
            callback_data=f"admin_pay_view:{p['id']}",
        )
    builder.button(text="🔙 Orqaga", callback_data="admin:menu")
    builder.adjust(1)
    return builder.as_markup()


def users_list_kb(users):
    builder = InlineKeyboardBuilder()
    for u in users[:15]:
        builder.button(
            text=f"ID:{u['user_id']} | {u['balance']:,}".replace(",", " "),
            callback_data=f"admin_user_view:{u['user_id']}",
        )
    builder.button(text="🔙 Orqaga", callback_data="admin:menu")
    builder.adjust(1)
    return builder.as_markup()


def user_view_kb(user_id, is_banned=False, is_reseller=False):
    ban_text = "✅ Ban'ni o'chirish" if is_banned else "⛔️ Ban qo'yish"
    res_text = "🏪 Sotuvchilikni o'chirish" if is_reseller else "🏪 Sotuvchi qilish"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Balans qo'shish", callback_data=f"admin_ub_plus:{user_id}")],
            [InlineKeyboardButton(text="➖ Balans kamaytirish", callback_data=f"admin_ub_minus:{user_id}")],
            [InlineKeyboardButton(text=res_text, callback_data=f"admin_reseller:{user_id}:{0 if is_reseller else 1}")],
            [InlineKeyboardButton(text=ban_text, callback_data=f"admin_ban:{user_id}:{0 if is_banned else 1}")],
            [InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin:users")],
        ]
    )


def invite_kb(bot_username, user_id):
    link = f"https://t.me/{bot_username}?start=ref_{user_id}"
    import urllib.parse
    share = urllib.parse.quote(f"Game Shop do'koniga xush kelibsiz! O'yinlarni arzon narxda sotib oling.\n{link}")
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📩 Do'stlarga ulashish", url=f"https://t.me/share/url?text={share}")],
            [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back:home")],
        ]
    )


def promo_list_kb(promos):
    builder = InlineKeyboardBuilder()
    for p in promos[:15]:
        builder.button(
            text=f"{p['code']} | {p['reward_amount']} so'm | {p['used_count']}/{p['max_uses']}",
            callback_data=f"admin_promo_view:{p['code']}",
        )
    builder.button(text="➕ Yangi", callback_data="admin_promo_new")
    builder.button(text="🔙 Orqaga", callback_data="admin:menu")
    builder.adjust(1)
    return builder.as_markup()


def promo_admin_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Yangi promokod", callback_data="admin_promo_new")
    builder.button(text="📋 Ro'yxat", callback_data="admin:promos")
    builder.button(text="🔙 Admin panel", callback_data="admin:menu")
    builder.adjust(1)
    return builder.as_markup()


def delivery_kb(pending_count, provider):
    builder = InlineKeyboardBuilder()
    builder.button(text=f"🚚 Avto-yuborish (kutilmoqda: {pending_count})", callback_data="admin_delivery_retry")
    builder.button(text=f"ℹ️ Provider: {provider}", callback_data="noop")
    builder.button(text="🔧 Provider o'zgartirish", callback_data="admin_set_provider")
    builder.button(text="🔙 Admin panel", callback_data="admin:menu")
    builder.adjust(1)
    return builder.as_markup()


def features_kb():
    """Funksiyalarni yoqish/o'chirish (bitta tugma bosish bilan)."""
    on = lambda k: "✅" if config.bool_setting(k, True) else "❌"
    builder = InlineKeyboardBuilder()
    builder.button(
        text=f"{on('auto_delivery_enabled')} Avtomatik yetkazish",
        callback_data="admin:toggle:auto_delivery_enabled",
    )
    builder.button(
        text=f"{on('ocr_enabled')} Chek OCR tekshiruv",
        callback_data="admin:toggle:ocr_enabled",
    )
    builder.button(
        text=f"{on('nickname_check_enabled')} O'yinchi nomini ko'rsatish",
        callback_data="admin:toggle:nickname_check_enabled",
    )
    builder.button(
        text=f"{on('id_validation_enabled')} ID format tekshiruv",
        callback_data="admin:toggle:id_validation_enabled",
    )
    builder.button(
        text=f"{on('chek_reminder_enabled')} Chek eslatmasi",
        callback_data="admin:toggle:chek_reminder_enabled",
    )
    builder.button(
        text=f"{on('maintenance')} Texnik ishlar rejimi",
        callback_data="admin:toggle:maintenance",
    )
    builder.button(text="🔙 Admin panel", callback_data="admin:menu")
    builder.adjust(1)
    return builder.as_markup()


def settings_kb():
    s = config.get_settings()
    builder = InlineKeyboardBuilder()
    builder.button(text="⚙️ Funksiyalarni yoqish/o'chirish", callback_data="admin:features")
    builder.button(text=f"💳 Karta (hozir: {s.get('card_active','uzcard')})", callback_data="admin:set:card_active")
    builder.button(text=f"⭐️ Kurs: {s.get('star_rate_1000',270000)}", callback_data="admin:set:star_rate_1000")
    builder.button(text=f"💰 Keshbek: {s.get('keshbek_percent',10)}%", callback_data="admin:set:keshbek_percent")
    builder.button(text=f"🤝 Referral: {s.get('referral_reward_topup_percent',5)}%", callback_data="admin:set:referral_reward_topup_percent")
    builder.button(text=f"🏪 Sotuvchi %: {s.get('reseller_percent',10)}", callback_data="admin:set:reseller_percent")
    builder.button(text="📢 E'lon matni", callback_data="admin:set:announcement")
    builder.button(text=f"🚚 Provider: {s.get('delivery_provider','manual')}", callback_data="admin:set:delivery_provider")
    builder.button(text="🔌 Provider ulash (URL+kalit)", callback_data="admin:provider_link")
    builder.button(text="🧪 Provider test", callback_data="admin:provider_test")
    builder.button(text="🌐 Webapp URL", callback_data="admin:set:webapp_url")
    builder.button(text="✏️ Boshqa kalit", callback_data="admin:set_other")
    builder.button(text="🔙 Admin panel", callback_data="admin:menu")
    builder.adjust(1)
    return builder.as_markup()


LANG_LABELS = {"uz": "🇺🇿 O'zbekcha", "ru": "🇷🇺 Русский", "en": "🇬🇧 English"}


def lang_kb(current="uz"):
    builder = InlineKeyboardBuilder()
    for code, label in LANG_LABELS.items():
        mark = " ✅" if code == current else ""
        builder.button(text=f"{label}{mark}", callback_data=f"lang:{code}")
    builder.adjust(1)
    return builder.as_markup()


def user_settings_kb(lang="uz"):
    builder = InlineKeyboardBuilder()
    builder.button(text=f"🌐 Til: {LANG_LABELS.get(lang, lang)}", callback_data="lang:menu")
    builder.button(text="🔙 Bosh sahifa", callback_data="back:home")
    builder.adjust(1)
    return builder.as_markup()