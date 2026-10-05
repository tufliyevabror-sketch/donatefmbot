from aiogram.fsm.state import State, StatesGroup


class TopUpStates(StatesGroup):
    waiting_card_photo = State()
    waiting_custom_amount = State()
    waiting_card_choice = State()
    waiting_manual_card = State()


class StarsBuyStates(StatesGroup):
    waiting_player_id = State()


class BalanceBuyStates(StatesGroup):
    waiting_player_id = State()


class SupportStates(StatesGroup):
    awaiting_message = State()


class AdminStates(StatesGroup):
    choosing_user = State()
    entering_balance = State()
    entering_notice = State()
    promo_code = State()
    promo_reward = State()
    promo_max = State()
    promo_expiry = State()
    search_query = State()
    broadcast_text = State()
    settings_key = State()
    settings_value = State()
    replying_user = State()
    provider_url = State()
    provider_key = State()
    catalog_game = State()
    catalog_game_edit = State()
    catalog_pkg = State()
    catalog_pkg_price = State()
    catalog_pkg_name = State()
    pro_target = State()
