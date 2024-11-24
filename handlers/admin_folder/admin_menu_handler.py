from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.types import KeyboardButton
from database.db import SessionLocal
from sqlalchemy.sql import func
from functions.all_func import get_category_keyboard
# Истифодаи Router
admin_menu_router = Router()

# Функсия барои сохтани клавиатура
def admin_menu_keyboard():
    # Сохтани клавиатура бо истифодаи ReplyKeyboardBuilder
    keyboard_builder = ReplyKeyboardBuilder()

    # Илова кардани тугмаҳо
    keyboard_builder.row(
        KeyboardButton(text="➕ Зам кардани продукт"),
        KeyboardButton(text="📋 Заказҳои интизорӣ (қабул нашуда)")
    )
    keyboard_builder.row(
        KeyboardButton(text="✅ Заказҳои қабулшуда"),
        KeyboardButton(text="🚚 Заказҳои дар роҳ")
    )
    keyboard_builder.row(
        KeyboardButton(text="🏠 Заказҳои расонидашуда"),
        KeyboardButton(text="📂 Админ Меню")
    )

    # Сохтани клавиатура
    return keyboard_builder.as_markup(resize_keyboard=True)

# Ҳендлер барои админ меню
@admin_menu_router.message(Command("admin_menu"))
async def admin_menu_handler(message: types.Message):
    keyboard = await get_category_keyboard()
    await message.answer("📂 Менюи админ:", reply_markup=keyboard)

    reply_keyboard = admin_menu_keyboard()
    await message.answer("a", reply_markup=reply_keyboard)


# Ҳендлер барои тугмаи "📂 Меню"
@admin_menu_router.message(F.text == "📂 Админ Меню")
async def category_menu_handler(message: types.Message):
    keyboard = await get_category_keyboard()
    await message.answer("📂 Интихоби категория:", reply_markup=keyboard)
    
