from aiogram.dispatcher.filters.state import StatesGroup, State


class AdminPanel(StatesGroup):
    requisites_wait = State()
    about_tariff = State()
    name_tariff = State()
    price_tariff = State()
    full_info_user_id = State()
    change_support_link = State()
    user_id_manual_replenishment = State()
    summa_manual_replenishment = State()
    mailing_wait = State()
    withdraw_wait = State()
    daily_percent = State()
    top_up_ask_amount = State()

class Deposit(StatesGroup):
    amount_money = State()
    tx_btc = State()
    tx_ltc = State()
    tx_tron_usdt = State()
    tx_eth_usdt = State()
    tx_bsc_usdt = State()