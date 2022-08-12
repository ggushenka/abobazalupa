import asyncio
import logging

import aiohttp
import sqlalchemy.orm
import tronpy.exceptions
import web3.exceptions
from aiogram.utils import executor
from tronpy import Tron
from web3 import Web3, HTTPProvider

import utils
from admin_handlers import *

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
logger.error("Starting bot")


@dp.message_handler(commands=['start', 'menu'], state='*')
@dp.callback_query_handler(lambda c: c.data == 'return_to_main_menu', state='*')
async def cmd_start(message: typing.Union[types.Message, types.CallbackQuery], state: FSMContext):
    await state.finish()
    with db_session.create_session() as session:
        with session.begin():
            user = session.query(User).where(User.user_id == message.from_user.id).first()
            if not user:
                raw_user_id = message.text.split()[-1]
                referer_first_level_id = 0
                referer_second_level_id = 0
                referer_third_level_id = 0
                if raw_user_id.isdigit():
                    referer_first_level = session.query(User).where(User.user_id == int(raw_user_id)).first()
                    if referer_first_level:
                        referer_first_level_id = referer_first_level.user_id
                        referer_second_level_id = referer_first_level.referer_first_level_id
                        referer_third_level_id = referer_first_level.referer_second_level_id
                session.add(User(user_id=message.from_user.id, referer_first_level_id=referer_first_level_id,
                                 referer_second_level_id=referer_second_level_id,
                                 referer_third_level_id=referer_third_level_id))
                session.commit()
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    with db_session.create_session() as session:
        with session.begin():
            user_id = message.from_user.id
            user = session.query(User).where(User.user_id == user_id).first()
            if user.user_id in ADMIN_IDS:
                kb.row(types.KeyboardButton('TARIFF ⚙️'), types.KeyboardButton('PROFILE 👤'))
            elif user.subscription:
                kb.row(types.KeyboardButton('PROFILE 👤'))
            else:
                kb.row(types.KeyboardButton('TARIFF ⚙️'))

            kb.row(types.KeyboardButton('AFFILATES 👥'), types.KeyboardButton('INFO ℹ️'))
            kb.row(types.KeyboardButton('ADD BALANCE 💵'))
    text = 'Select'
    if isinstance(message, types.CallbackQuery):
        await message.message.answer(text, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)


@dp.callback_query_handler(lambda c: c.data.startswith("replenish_balance"), state='*')
@dp.message_handler(lambda m: m.text == 'ADD BALANCE 💵', state='*')
async def replenish_balance(call: typing.Union[types.CallbackQuery, types.Message], state: FSMContext):
    await state.finish()
    kb = types.InlineKeyboardMarkup()
    kb.row(types.InlineKeyboardButton("BTC", callback_data='top_up&btc'),
           types.InlineKeyboardButton("LTC", callback_data='top_up&ltc'),
           types.InlineKeyboardButton("USDT", callback_data='top_up&usdt'))
    text = 'Choose how you want to recharge'
    if isinstance(call, types.CallbackQuery):
        await call.message.edit_text(text, reply_markup=kb)
    else:
        await call.answer(text, reply_markup=kb)


@dp.callback_query_handler(lambda c: c.data.startswith('top_up'), state='*')
async def top_up_btc_inline_handler(call: types.CallbackQuery):
    address = None
    coin = call.data.split('&')[1]
    if coin in ['btc', 'ltc']:
        if coin == 'btc':
            address = BTC_DEPOSIT_ADDRESS
            await Deposit.tx_btc.set()
        elif coin == 'ltc':
            address = LTC_DEPOSIT_ADDRESS
            await Deposit.tx_ltc.set()
        text = f"""
Address for replenishment:    
<code>{address}</code>
After sending the transaction, send the bot the hash of the transaction
"""

        kb = types.InlineKeyboardMarkup()
        kb.row(types.InlineKeyboardButton("Go back", callback_data='replenish_balance'))
        await call.message.edit_text(text, reply_markup=kb)

    elif coin == 'usdt':
        kb = types.InlineKeyboardMarkup()
        kb.row(types.InlineKeyboardButton("ERC20", callback_data='deposit_usdt&eth'),
               types.InlineKeyboardButton("BEP20", callback_data='deposit_usdt&bsc'),
               types.InlineKeyboardButton("TRC20", callback_data='deposit_usdt&tron'))
        kb.row(types.InlineKeyboardButton("Go back", callback_data='replenish_balance'))
        await call.message.edit_text('Select the network to transfer', reply_markup=kb)


@dp.callback_query_handler(lambda c: c.data.startswith('deposit_usdt'), state='*')
async def deposit_usdt_inline_handler(call: types.CallbackQuery):
    network = call.data.split('&')[-1]
    address = None
    if network in ['eth', 'bsc']:
        address = USDT_ETH_DEPOSIT_ADDRESS
        if network == 'eth':
            await Deposit.tx_eth_usdt.set()
        else:
            await Deposit.tx_bsc_usdt.set()
    elif network == 'tron':
        await Deposit.tx_tron_usdt.set()
        address = USDT_TRON_DEPOSIT_ADDRESS
    text = f"""
Address for replenishment:    
<code>{address}</code>
After sending the transaction, send the bot the hash of the transaction
"""

    kb = types.InlineKeyboardMarkup()
    kb.row(types.InlineKeyboardButton("Go back", callback_data='replenish_balance'))
    await call.message.edit_text(text, reply_markup=kb)


@dp.message_handler(state=Deposit.tx_tron_usdt)
async def deposit_tx_tron_usdt_handler(message: types.Message, state: FSMContext):
    client = Tron()
    try:
        tx = client.get_transaction(message.text)
    except tronpy.exceptions.TransactionNotFound:
        await message.answer('Transaction not found')
        return
    except Exception as ex:
        print(ex)
        await message.answer('Buy any tariff first')
        return
    if tx['ret'][0]['contractRet'] == 'SUCCESS':
        contract_address = tx.get('raw_data')['contract'][0]['parameter']['value']['contract_address']
        if contract_address == 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t':
            raw_data = tx.get('raw_data')['contract'][0]['parameter']['value']['data']
            receiver_address = client.to_base58check_address(Web3.toChecksumAddress(raw_data[32:72]))
            if receiver_address == USDT_TRON_DEPOSIT_ADDRESS:
                value = int(raw_data[72:], 16) / 1000000
                utils.deposit_funds_on_balance(message.from_user.id, int(value))
                await state.finish()
                await message.answer(f'Your balance has been successfully credited to {value}$')
            else:
                await message.answer('Our service address was not found among the output addresses')
        else:
            await message.answer('The USDT contract does not participate in the transaction')
    else:
        await message.answer('Transaction status is not SUCCESS')


@dp.message_handler(state=[Deposit.tx_eth_usdt, Deposit.tx_bsc_usdt])
async def tx_eth_usdt_handler(message: types.Message, state: FSMContext):
    if await state.get_state() == 'Deposit:tx_eth_usdt':
        usdt_contract = '0xdAC17F958D2ee523a2206206994597C13D831ec7'
        w3 = Web3(HTTPProvider("https://rpc.ankr.com/eth"))
    else:
        usdt_contract = '0x55d398326f99059fF775485246999027B3197955'
        w3 = Web3(HTTPProvider("https://rpc.ankr.com/bsc"))
    try:
        tx = w3.eth.get_transaction(message.text)
    except web3.exceptions.TransactionNotFound:
        await message.answer('Transaction not found')
        return
    if tx.to == usdt_contract:
        hexdata = tx.input.lstrip('0x')
        if w3.toChecksumAddress(hexdata[32:72]) == USDT_ETH_DEPOSIT_ADDRESS:
            value = w3.fromWei(int(hexdata[72:].lstrip('0'), 16), 'ether')
            utils.deposit_funds_on_balance(message.from_user.id, value)
            await state.finish()
            await message.answer(f'Your balance has been successfully credited to {value}$')
        else:
            await message.answer('Our service address was not found among the output addresses')
    else:
        await message.answer('The USDT contract does not participate in the transaction')


@dp.message_handler(state=[Deposit.tx_btc, Deposit.tx_ltc])
async def tx_btc_handler(message: types.Message, state: FSMContext):
    kb = types.InlineKeyboardMarkup()
    kb.row(types.InlineKeyboardButton("Go back", callback_data='replenish_balance'))
    blockhain = None
    address = None
    if await state.get_state() == "Deposit:tx_btc":
        blockhain = 'bitcoin'
        address = BTC_DEPOSIT_ADDRESS
    elif await state.get_state() == "Deposit:tx_ltc":
        address = LTC_DEPOSIT_ADDRESS
        blockhain = 'litecoin'
    async with aiohttp.ClientSession() as session:
        r = await session.get(f"https://api.blockchair.com/{blockhain}/dashboards/transaction/{message.text}")
        json_data = await r.json()
        if json_data['data']:
            deposit_value = 0
            for output in json_data['data'][message.text]['outputs']:
                if output['recipient'] == address:
                    value = output['value'] / 100000000
                    price_btc = json_data['context']['market_price_usd']
                    deposit_value = int(value * price_btc)
                    utils.deposit_funds_on_balance(message.from_user.id, deposit_value)
                    break
            if deposit_value > 0:
                await state.finish()
                await message.answer(f'Your balance has been successfully credited to {deposit_value}$')
            else:
                await message.answer('Our service address was not found among the output addresses', reply_markup=kb)
        else:
            await message.answer('Incorrect transaction hash', reply_markup=kb)


@dp.callback_query_handler(lambda c: c.data.startswith("cabinet"), state='*')
@dp.message_handler(lambda m: m.text == 'PROFILE 👤', state='*')
async def cabinet(call: typing.Union[types.CallbackQuery, types.Message], state: FSMContext):
    await state.finish()
    kb = types.InlineKeyboardMarkup()
    with db_session.create_session() as session:
        with session.begin():
            user_id = call.from_user.id
            user = session.query(User).where(User.user_id == user_id).first()
            if user.subscription:
                kb.row(types.InlineKeyboardButton('Profile', callback_data='profile'),
                       types.InlineKeyboardButton('Help', url='https://t.me/USBITsupport'))
                kb.row(types.InlineKeyboardButton('Withdraw', callback_data='withdraw'),
                       types.InlineKeyboardButton('Deposit', callback_data='deposit'))
                text = 'Select'
                if isinstance(call, types.CallbackQuery):
                    await call.message.edit_text(text, reply_markup=kb)
                else:
                    await call.answer(text, reply_markup=kb)
            else:
                if isinstance(call, types.CallbackQuery):
                    await call.message.edit_text('Unknown error', reply_markup=return_to_main_menu_kb)
                else:
                    await call.answer('Unknown error', reply_markup=return_to_main_menu_kb)


@dp.callback_query_handler(lambda c: c.data == 'AFFILATES 👥', state='*')
@dp.message_handler(lambda m: m.text == 'AFFILATES 👥', state='*')
async def referals_inline_handler(call: typing.Union[types.CallbackQuery, types.Message]):
    with db_session.create_session() as session:
        session: sqlalchemy.orm.Session
        with session.begin():
            user = session.query(User).where(User.user_id == call.from_user.id).first()
            amount_primary_referals = session.query(User).where(
                User.referer_first_level_id == call.from_user.id).count()
            amount_secondary_referals = session.query(User).where(
                User.referer_second_level_id == call.from_user.id).count()
            amount_ternary_referals = session.query(User).where(
                User.referer_third_level_id == call.from_user.id).count()
            text = f"""
Your referral link: https://t.me/{BOT_USERNAME}?start={call.from_user.id}
1st level referals: {amount_primary_referals}
2nd level referals: {amount_secondary_referals}
3rd level referals: {amount_ternary_referals}
Your balance: <b>{int(user.balance)}</b>$


Income from referrals:
- 10% from the 1st level referal
- 7.5% from the 2nd level referal
- 5% from the 3rd level referal        
"""
            if isinstance(call, types.CallbackQuery):
                await call.message.edit_text(text)
            else:
                await call.answer(text)


@dp.callback_query_handler(lambda c: c.data == 'deposit', state='*')
async def deposit_inline_handler(call: types.CallbackQuery):
    await Deposit.amount_money.set()
    kb = types.InlineKeyboardMarkup()
    kb.row(types.InlineKeyboardButton("Go back", callback_data='cabinet'))
    await call.message.edit_text('Enter the amount of money to be transferred to the deposit account', reply_markup=kb)


@dp.message_handler(state=Deposit.amount_money)
async def amount_money_deposit_handler(message: types.Message, state: FSMContext):
    if message.text.isdigit():
        with db_session.create_session() as session:
            session: sqlalchemy.orm.Session
            with session.begin():
                user = session.query(User).where(User.user_id == message.from_user.id).first()
                if user.balance >= int(message.text):
                    user.deposit += int(message.text)
                    user.balance -= int(message.text)
                    await state.finish()
                    await message.answer(f'Your deposit account has been successfully funded by {message.text}$',
                                         reply_markup=return_to_main_menu_kb)
                else:
                    await message.answer('You have entered a value that exceeds your balance. Try again',
                                         reply_markup=return_to_main_menu_kb)
    else:
        await message.answer('You entered an invalid value. Try again',
                             reply_markup=return_to_main_menu_kb)


@dp.callback_query_handler(lambda c: c.data.startswith("withdraw"), state='*')
async def withdraw(call: types.CallbackQuery):
    user_id = call.from_user.id
    await AdminPanel.withdraw_wait.set()
    kb = types.InlineKeyboardMarkup()
    kb.row(types.InlineKeyboardButton("Go back", callback_data='cabinet'))
    await bot.edit_message_text('Enter the amount to withdraw', user_id, call.message.message_id,
                                reply_markup=kb)


@dp.message_handler(state=AdminPanel.withdraw_wait)
async def withdraw(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        with db_session.create_session() as session:
            with session.begin():
                user_id = message.from_user.id
                user = session.query(User).where(User.user_id == user_id).first()
                text = message.text
                if int(text) <= user.balance:
                    data['hold'] = text
                    data['money'] = text
                    data['username'] = message.from_user.username
                    kb = types.InlineKeyboardMarkup()
                    kb.row(types.InlineKeyboardButton("Go back", callback_data='cabinet'))
                    await bot.send_message(message.from_user.id, 'Enter requisites', reply_markup=kb)
                    await AdminPanel.requisites_wait.set()
                else:
                    await bot.send_message(message.from_user.id, 'Insufficient funds',
                                           reply_markup=return_to_main_menu_kb)


@dp.message_handler(state=AdminPanel.requisites_wait)
async def withdraw(message: types.message, state: FSMContext):
    async with state.proxy() as data:
        with db_session.create_session() as session:
            with session.begin():
                text = message.text
                user_id = message.from_user.id
                user = session.query(User).where(User.user_id == user_id).first()
                data['requisites'] = text
                user.hold += int(data['hold'])
                await bot.send_message(message.from_user.id,
                                       'The application has been sent and will be reviewed within a day',
                                       reply_markup=return_to_main_menu_kb)
                for admin in ADMIN_IDS:
                    try:
                        await bot.send_message(admin, 'Новая заявка на вывод')
                    except:
                        ...
                withdrawal = Transaction(amount_money=data['money'], ordered_the_withdrawal=message.from_user.id,
                                         user_name=data['username'],
                                         requisites=text)
                session.add(withdrawal)
                user.balance -= int(data['money'])
                await state.finish()
                session.commit()


@dp.callback_query_handler(lambda c: c.data.startswith("profile"), state='*')
async def profile(call: types.CallbackQuery):
    with db_session.create_session() as session:
        with session.begin():
            user_id = call.from_user.id
            user = session.query(User).where(User.user_id == user_id).first()
            kb = types.InlineKeyboardMarkup()
            kb.row(types.InlineKeyboardButton("Go back", callback_data='cabinet'))
            await bot.edit_message_text(f'''
Your balance: {int(user.balance)}$
Balance of deposit: {int(user.deposit)}$
Funds on withdrawal: {int(user.hold)}$
Your tariff: {user.user_tariff_id}
Your daily percentage: {user.percent}%''', user_id, call.message.message_id, reply_markup=kb)


@dp.callback_query_handler(lambda c: c.data.startswith("info"), state='*')
@dp.message_handler(lambda m: m.text == 'INFO ℹ️', state='*')
async def user_info(call: typing.Union[types.CallbackQuery, types.Message]):
    text = 'To work with our service you need to buy a tariff 📈 Tariff is the interest rate, your daily profit, which directly depends on the selected offer 💰 Deposit balance - the money that you invest in the development of the project and get a constant daily profit. The maximum payback period of the deposit is 100 days. The minimum - 50 days. Your funds are invested in equipment and project promotion, and cannot be withdrawn 💸 You can withdraw the earned money every day, immediately after the accrual. And also, to spend them to buy another tariff or making a deposit account, which will increase your daily profit'
    if isinstance(call, types.CallbackQuery):
        await bot.edit_message_text(text, call.from_user.id,
                                    call.message.message_id)
    else:
        await call.answer(text)


@dp.callback_query_handler(lambda c: c.data.startswith('TARIFF ⚙️'), state='*')
@dp.message_handler(lambda m: m.text == 'TARIFF ⚙️', state='*')
async def subscription(call: typing.Union[types.CallbackQuery, types.Message]):
    kb = types.InlineKeyboardMarkup()
    with db_session.create_session() as session:
        with session.begin():
            tariffs = session.query(Tariff).all()
            for tariff in tariffs:
                if tariff.active:
                    kb.row(
                        types.InlineKeyboardButton(tariff.name,
                                                   callback_data=f'tariff_detail_view&{tariff.tariff_id}'))
        if isinstance(call, types.CallbackQuery):
            await bot.edit_message_text('Choose your tariff', call.from_user.id,
                                        call.message.message_id, reply_markup=kb)
        else:
            await call.answer('Choose your tariff', reply_markup=kb)


async def distribution_dividends():
    while True:
        await asyncio.sleep(86400)
        with db_session.create_session() as session:
            session: sqlalchemy.orm.Session
            with session.begin():
                users = session.query(User).where(User.subscription == True).all()
                for user in users:
                    try:
                        profit = user.percent / 100 * user.deposit
                        if profit > 0:
                            user.balance += profit
                            await dp.bot.send_message(user.user_id, f"Your income {profit}$")
                        if user.referer_first_level_id:
                            referer_first_level = session.query(User).where(
                                User.user_id == user.referer_first_level_id).first()
                            referer_first_level.balance += int(0.1 * profit)
                            if user.referer_second_level_id:
                                referer_second_level = session.query(User).where(
                                    User.user_id == user.referer_second_level_id).first()
                                referer_second_level.balance += int(0.075 * profit)
                                if user.referer_third_level_id:
                                    referer_third_level = session.query(User).where(
                                        User.user_id == user.referer_third_level_id).first()
                                    referer_third_level.balance += int(0.05 * profit)
                    except Exception as ex:
                        print(ex)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(distribution_dividends())
    db_session.global_init("db/database.db")
    executor.start_polling(dp, skip_updates=True)
