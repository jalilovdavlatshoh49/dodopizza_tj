from aiogram import Router, types, F
from sqlalchemy.ext.asyncio import AsyncSession
from functions.all_func import get_category_keyboard, get_cart_items, get_order_history, get_user_info
from aiogram.types import InputMediaPhoto
from database.db import SessionLocal
reply_router = Router()


# Handle "Меню" button to show category keyboard
@reply_router.message(F.text == "Категорияҳо")
async def menu_handler(message: types.Message):
    keyboard = await get_category_keyboard()
    await message.answer("Категорияҳоро интихоб кунед:", reply_markup=keyboard)






# Handle "Фармоишот" button to show past orders
@reply_router.message(F.text == "Фармоишот")
async def reply_orders_handler(message: types.Message):
    user_id = message.from_user.id

    # Гирифтани таърихи фармоишҳо
    orders = await get_order_history(user_id)
    
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



# Функсияи кор бо "ℹ️ Маълумотҳои шахсии ман"
@reply_router.message(F.text == "Маълумотҳои шахсии ман")
async def my_info_handler(message: types.Message):
    session = SessionLocal()
    # Дарёфти маълумоти корбар
    user_info = await get_user_info(user_id=message.from_user.id)

    if not user_info:
        # Агар маълумот вуҷуд надошта бошад
        await message.answer("Маълумоти шахсии шумо ёфт нашуд. Лутфан аввал фармоиш диҳед.")
        return

    # Ташкили матни ҷавоб бо маълумотҳо
    info_text = (
        f"Ном: {user_info['name']}\n"
        f"Рақами телефон: {user_info['phone']}\n"
        f"Адрес: {user_info['address']}\n"
        f"Координатаҳо: {user_info['latitude']}, {user_info['longitude']}\n\n"
        "Барои тағйир додани маълумотҳо, тугмаи зерро истифода баред."
    )

    # Эҷоди клавиатура бо тугма
    keyboard = InlineKeyboardMarkup(row_width=1)
    change_button = InlineKeyboardButton(
        text="Тағйир додани маълумотҳо", callback_data="change_user_info"
    )
    keyboard.add(change_button)

    # Фиристодани паём бо клавиатура
    await message.answer(info_text, reply_markup=keyboard)


@reply_router.callback_query(lambda c: c.data == "continue_shopping")
async def continue_shopping_handler(callback_query: types.CallbackQuery):
    keyboard = await get_category_keyboard()
    await callback_query.message.answer("Категорияҳоро интихоб кунед:", reply_markup=keyboard)