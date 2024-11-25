from aiogram import Router, types
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from functions.all_func import get_category_keyboard, get_order_history, get_user_info
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.types import KeyboardButton

# Эҷоди router
menu_router = Router()



def get_custom_menu_keyboard():
    keyboard_builder = ReplyKeyboardBuilder()
    keyboard_builder.row(
        KeyboardButton(text="🍔 Категорияҳо"),
        KeyboardButton(text="🛒 Сабад"),
    )
    keyboard_builder.row(
        KeyboardButton(text="📜 Фармоишот"),
        KeyboardButton(text="ℹ️ Маълумотҳои шахсии ман"),
    )
    return keyboard_builder.as_markup(resize_keyboard=True, one_time_keyboard=True)

# Функсияи "Меню" барои нишон додани клавиатураи категорияҳо
@menu_router.message(Command(commands=["menu"]))
async def menu_handler(message: types.Message):
    keyboard = await get_category_keyboard()
    await message.answer(
        text="\u200b",  # Матни ноаён
        reply_markup=keyboard
    )


    await message.answer(
        text="\u200b",  # Матни ноаён
        reply_markup=get_custom_menu_keyboard()
    )

    



# Функсияи "Фармоишот" барои нишон додани таърихи фармоишҳо
@menu_router.message(Command(commands=["orders"]))
async def orders_handler(message: types.Message):
    session = SessionLocal()
    user_id = message.from_user.id

    # Гирифтани таърихи фармоишҳо
    orders = await get_order_history(user_id, session)
    
    if not orders:
        await message.answer("Шумо ҳоло фармоиш надоред.")
        return

    for order in orders:
        order_text = f"**Ҳолати фармоиш:** {order['status']}\n\n"
        for item in order['items']:
            order_text += (
                f"📦 **Ном:** {item['name']}\n"
                f"🔢 **Миқдор:** {item['quantity']}\n"
                f"💵 **Нарх:** {item['price']} сомонӣ\n"
                f"💰 **Нархи умумӣ:** {item['total_price']} сомонӣ\n\n"
            )
            if item['image_url']:
                await message.answer_photo(photo=item['image_url'], caption=order_text)
            else:
                await message.answer(order_text)
        
        order_text = f"💳 **Нархи умумии фармоиш:** {order['total_order_price']} сомонӣ\n"
    await message.answer(info_text)

