from aiogram import types

admin_keyboard = types.InlineKeyboardMarkup()
admin_keyboard.row(types.InlineKeyboardButton('Информация о пользователе', callback_data='full_info_about_user'),
                   types.InlineKeyboardButton('Добавить тариф', callback_data='add_tariff'))
admin_keyboard.row(types.InlineKeyboardButton('Начислить баланс', callback_data='manual_replenishment'))
admin_keyboard.row(types.InlineKeyboardButton('Сделать рассылку', callback_data='mailing'))
admin_keyboard.row(types.InlineKeyboardButton('Заявки на вывод', callback_data='withdraw_app'))
admin_keyboard.row(types.InlineKeyboardButton('В главное меню', callback_data='return_to_main_menu'))

return_to_main_admin_menu_kb = types.InlineKeyboardMarkup()
return_to_main_admin_menu_button = types.InlineKeyboardButton('Вернуться в главное меню', callback_data='admin_panel')
return_to_main_admin_menu_kb.row(return_to_main_admin_menu_button)

return_to_main_menu_kb = types.InlineKeyboardMarkup()
return_to_main_menu_button = types.InlineKeyboardButton('Back to main menu', callback_data='return_to_main_menu')
return_to_main_menu_kb.row(return_to_main_menu_button)
