"""Bot xabarlari — 3 til (uz/ru/en). i18n.t() orqali ishlatiladi."""
import config
from i18n import t as _t


def money(v):
    return f"{v:,}".replace(",", " ")


def _lang(user):
    """User obyektidan til kodini oladi (uz/ru/en). Default: uz."""
    if not user:
        return "uz"
    return user.get("lang") or "uz"


# ==================== ASOSIY MENYU ====================

def start_text(lang="uz"):
    return _t(lang, "start")


def menu_text(lang="uz"):
    return _t(lang, "menu_text")


def games_title(lang="uz"):
    return _t(lang, "games_title")


# ==================== BALANS ====================

def balance_text(user):
    lang = _lang(user)
    return (
        f"{_t(lang, 'balance_title')}\n\n"
        f"💠 {_t(lang, 'balance_label')}: <b>{money(user.get('balance', 0))} so'm</b>\n"
        f"📈 {_t(lang, 'total_topup_label')}: <b>{money(user.get('total_topup', 0))} so'm</b>\n"
        f"🆔 ID: <code>{user.get('user_id', 0)}</code>\n\n"
        f"{_t(lang, 'topup_hint')}"
    )


def topup_menu_text(lang="uz"):
    return _t(lang, "topup_menu")


def card_topup_text(amount, lang="uz", card_key=None):
    s = config.get_settings()
    cards = config.all_cards()
    if card_key:
        only = [c for c in cards if c["key"] == card_key]
        if only:
            cards = only
    lines = [
        f"{_t(lang, 'pay_center')}\n",
        f"💰 {_t(lang, 'pay_amount')}: <b>{money(amount)} so'm</b>\n",
    ]
    for c in cards:
        holder = f" ({c['holder']})" if c["holder"] else ""
        lines.append(f"• <b>{c['label']}:</b> <code>{c['number']}</code>{holder}")
    phone = s.get("support_phone", "")
    email = s.get("support_email", "")
    admin = s.get("admin_username", "")
    lines += [
        "",
        _t(lang, "copy_hint"),
        "",
        _t(lang, "receipt_required"),
    ]
    if phone:
        lines.append(f"📞 Tel: <code>{phone}</code>")
    if email:
        lines.append(f"📧 Email: <code>{email}</code>")
    if admin:
        lines.append(f"👤 {_t(lang, 'contact_admin')}: @{admin}")
    lines += [
        "",
        _t(lang, "send_receipt"),
        _t(lang, "after_approval"),
    ]
    return "\n".join(lines)


def card_photo_received(payment_id, lang="uz"):
    return (
        f"✅ <b>{_t(lang, 'receipt_accepted')}</b>\n\n"
        f"{_t(lang, 'payment_id')}: <code>#{payment_id}</code>\n"
        f"{_t(lang, 'wait_admin')}"
    )


# ==================== O'YINLAR ====================

def game_info_text(game, lang="uz"):
    name = game.get("name") or "O'yin"
    return (
        f"{game.get('emoji', '🎮')} <b>{name}</b>\n"
        f"📝 {game.get('desc', '')}\n\n"
        f"{_t(lang, 'choose_package')}"
    )


def confirm_buy_text(game, pkg, user_id, lang="uz"):
    return (
        f"🛒 <b>{_t(lang, 'order_info')}</b>\n\n"
        f"🎮 {_t(lang, 'game_label')}: <b>{game.get('name', '')}</b>\n"
        f"📦 {_t(lang, 'package_label')}: <b>{pkg.get('name', '')}</b>\n"
        f"💰 {_t(lang, 'price_label')}: <b>{money(pkg.get('price', 0))} so'm</b>\n"
        f"🆔 {_t(lang, 'game_id_label')}: <code>{user_id}</code>\n\n"
        f"{_t(lang, 'choose_pay_method')}"
    )


def order_created_text(order_id, lang="uz"):
    return _t(lang, "order_created", order_id=order_id)


def too_low_balance_text(lang="uz"):
    return _t(lang, "too_low_balance")


def balance_after_topup_text(balance, lang="uz"):
    return _t(lang, "balance_added", balance=money(balance))


# ==================== TARIX ====================

def history_text(orders, payments, lang="uz"):
    lines = [f"📜 <b>{_t(lang, 'history_title')}</b>\n"]
    if orders:
        lines.append(f"📦 <b>{_t(lang, 'orders_label')}:</b>")
        for o in orders[:10]:
            st = o.get("status", "")
            lines.append(f"  #{o['id']} — {o['package_name']} — {money(o['price'])} so'm — {st}")
    if payments:
        lines.append(f"\n💳 <b>{_t(lang, 'payments_label')}:</b>")
        for p in payments[:10]:
            st = p.get("status", "")
            lines.append(f"  #{p['id']} — {money(p['amount'])} so'm ({p['method']}) — {st}")
    if not orders and not payments:
        lines.append(_t(lang, "empty"))
    return "\n".join(lines)


# ==================== SOZLAMALAR ====================

def settings_text(user):
    lang = _lang(user)
    return (
        f"{_t(lang, 'settings_title')}\n\n"
        f"🆔 ID: <code>{user.get('user_id', 0)}</code>\n"
        f"👤 {_t(lang, 'name_label')}: <b>{user.get('full_name') or '—'}</b>\n"
        f"📛 {_t(lang, 'username_label')}: @{user.get('username') or '—'}\n"
        f"🌐 {_t(lang, 'language_label')}: <b>{lang.upper()}</b>\n"
        f"💰 {_t(lang, 'balance_label')}: <b>{money(user.get('balance', 0))} so'm</b>\n"
        f"📆 {_t(lang, 'reg_date_label')}: {user.get('reg_date', '')}\n\n"
        f"{_t(lang, 'need_help')}"
    )


# ==================== ADMIN ====================

def admin_menu_text(lang="uz"):
    return _t(lang, "admin_menu")


def admin_stats_text(s, lang="uz"):
    return (
        f"📊 <b>{_t(lang, 'admin_stats')}</b>\n\n"
        f"👥 {_t(lang, 'users_label')}: <b>{s.get('users', 0)}</b>\n"
        f"📦 {_t(lang, 'orders_label')}: <b>{s.get('orders', 0)}</b>\n"
        f"💳 {_t(lang, 'payments_label')}: <b>{s.get('payments', 0)}</b>\n"
        f"💰 {_t(lang, 'revenue_label')}: <b>{money(s.get('revenue', 0))} so'm</b>\n"
        f"📥 {_t(lang, 'topups_label')}: <b>{money(s.get('topups', 0))} so'm</b>\n"
        f"📅 {_t(lang, 'today_orders')}: <b>{s.get('today_orders', 0)}</b>\n"
        f"📆 {_t(lang, 'month_users')}: <b>{s.get('month_users', 0)}</b>\n"
        f"🆕 {_t(lang, 'month_new_users')}: <b>{s.get('month_new_users', 0)}</b>\n"
        f"📈 {_t(lang, 'month_revenue')}: <b>{money(s.get('month_revenue', 0))} so'm</b>\n"
        f"💸 {_t(lang, 'month_topups')}: <b>{money(s.get('month_topups', 0))} so'm</b>"
    )


def admin_order_text(o, lang="uz"):
    return (
        f"📦 <b>{_t(lang, 'order_label')} #{o['id']}</b>\n\n"
        f"👤 User: <code>{o['user_id']}</code>\n"
        f"🎮 O'yin: {o.get('platform', '')}\n"
        f"📦 Paket: {o.get('package_name', '')}\n"
        f"💰 Narx: {money(o.get('price', 0))} so'm\n"
        f"🆔 ID: <code>{o.get('game_id', '')}</code>\n"
        f"📅 Sana: {o.get('created_at', '')}\n"
        f"📍 Holat: <b>{o.get('status', '')}</b>"
    )


def admin_payment_text(p, lang="uz"):
    return (
        f"💳 <b>{_t(lang, 'payment_label')} #{p['id']}</b>\n\n"
        f"👤 User: <code>{p['user_id']}</code>\n"
        f"💸 Summa: {money(p.get('amount', 0))} so'm\n"
        f"💳 Usul: {p.get('method', '')}\n"
        f"📍 Holat: <b>{p.get('status', '')}</b>\n"
        f"📅 Sana: {p.get('created_at', '')}"
    )


def admin_user_text(u, lang="uz"):
    banned = "Ha" if u.get("is_banned") else "Yo'q"
    return (
        f"👤 <b>{_t(lang, 'user_profile')}</b>\n\n"
        f"🆔 ID: <code>{u['user_id']}</code>\n"
        f"👤 Ism: <b>{u.get('full_name') or '—'}</b>\n"
        f"📛 Username: @{u.get('username') or '—'}\n"
        f"🌐 Til: <b>{u.get('lang', 'uz')}</b>\n"
        f"💰 Balans: <b>{money(u.get('balance', 0))} so'm</b>\n"
        f"📈 Jami to'ldirilgan: <b>{money(u.get('total_topup', 0))} so'm</b>\n"
        f"💎 Keshbek: <b>{money(u.get('keshbek', 0))} so'm</b>\n"
        f"🚫 Bloklangan: {banned}\n"
        f"📆 Ro'yxatdan: {u.get('reg_date', '')}"
    )


def admin_settings_text(s, lang="uz"):
    lines = [f"⚙️ <b>{_t(lang, 'admin_settings')}</b>\n"]
    for k, v in s.items():
        lines.append(f"• <b>{k}</b>: <code>{v}</code>")
    return "\n".join(lines)


# ==================== BOSHQA ====================

def promo_invalid_text(lang="uz"):
    return _t(lang, "promo_invalid")


def promo_expired_text(lang="uz"):
    return _t(lang, "promo_expired")


def promo_limit_text(lang="uz"):
    return _t(lang, "promo_limit")


def promo_used_text(lang="uz"):
    return _t(lang, "promo_used")


def promo_ok_text(lang="uz"):
    return _t(lang, "promo_ok")


def promo_result_text(ok, msg, lang="uz"):
    return msg if ok else _t(lang, "promo_invalid")


def referral_text(link, stats, percent, lang="uz"):
    return (
        f"🤝 <b>{_t(lang, 'referral_title')}</b>\n\n"
        f"{_t(lang, 'referral_hint', percent=percent)}\n\n"
        f"🔗 {_t(lang, 'your_link')}:\n<code>{link}</code>\n\n"
        f"📊 {_t(lang, 'stats')}: {stats.get('count', 0)} ta do'st, "
        f"{money(stats.get('total_reward', 0))} so'm bonus"
    )


def broadcast_start_text(lang="uz"):
    return _t(lang, "broadcast_start")


def broadcast_preview_text(count, lang="uz"):
    return _t(lang, "broadcast_preview", count=count)


def no_photo_text(lang="uz"):
    return _t(lang, "no_photo")


def no_admin_text(lang="uz"):
    return _t(lang, "no_admin")


def cancel_text(lang="uz"):
    return _t(lang, "cancel")


def back_text(lang="uz"):
    return _t(lang, "back")


def home_text(lang="uz"):
    return _t(lang, "home")


def done_text(lang="uz"):
    return _t(lang, "done")


def refused_text(lang="uz"):
    return _t(lang, "refused")


def phone_ok_text(lang="uz"):
    return _t(lang, "phone_ok")


def enter_promo_text(lang="uz"):
    return _t(lang, "enter_promo")


def send_photo_hint_text(lang="uz"):
    return _t(lang, "send_photo_hint")


def order_waiting_text(lang="uz"):
    return _t(lang, "order_waiting")

def admin_search_prompt(lang="uz"):
    return _t(lang, "admin_search_prompt")


def user_profile_text(u):
    lang = _lang(u)
    return (
        f"{_t(lang, 'user_profile')}\n\n"
        f"🆔 ID: <code>{u['user_id']}</code>\n"
        f"👤 {_t(lang, 'name_label')}: <b>{u.get('full_name') or '—'}</b>\n"
        f"📛 {_t(lang, 'username_label')}: @{u.get('username') or '—'}\n"
        f"📱 {_t(lang, 'phone')}: {u.get('phone', '') or '—'}\n"
        f"💰 {_t(lang, 'balance_label')}: <b>{money(u.get('balance', 0))} so'm</b>\n"
        f"📈 {_t(lang, 'total_topup_label')}: <b>{money(u.get('total_topup', 0))} so'm</b>\n"
        f"🤝 {_t(lang, 'keshbek_label')}: <b>{money(u.get('keshbek', 0))} so'm</b>\n"
        f"📆 {_t(lang, 'reg_date_label')}: {u.get('reg_date', '')}\n"
        f"⛔️ {_t(lang, 'status_label')}: {_t(lang, 'banned_label') if u.get('is_banned') else _t(lang, 'active')}"
    )


def banned_message(lang="uz"):
    s = config.get_settings()
    contact = s.get("admin_username") or s.get("support_username") or "donatefm_support"
    return _t(lang, "banned") + f": @{contact}"


def order_reason_admin(lang="uz"):
    return _t(lang, "order_reason_admin")


def order_reason_delivery(lang="uz"):
    return _t(lang, "order_reason_delivery")


def delivery_status_text(cfg, pending_count, lang="uz"):
    lbl = {
        "manual": {"uz": "Qo'lda (admin bajaradi)", "ru": "Вручную (админ)", "en": "Manual (admin)"},
        "custom": {"uz": "O'z HTTP API", "ru": "Свой HTTP API", "en": "Custom HTTP API"},
        "baulu": {"uz": "Baulu API", "ru": "Baulu API", "en": "Baulu API"},
        "liveop": {"uz": "LiveOP API", "ru": "LiveOP API", "en": "LiveOP API"},
    }
    provider = cfg.get("provider", "manual")
    p_label = lbl.get(provider, {}).get(lang, provider)
    return (
        f"🚚 <b>{_t(lang, 'delivery_title')}</b>\n\n"
        f"Provider: <b>{p_label}</b>\n"
        f"API URL: <code>{cfg.get('api_url') or '—'}</code>\n"
        f"Interval: {cfg.get('interval', 30)} sek\n\n"
        f"📦 {_t(lang, 'pending_orders')}: <b>{pending_count}</b>\n\n"
        f"{_t(lang, 'delivery_hint')}"
    )
