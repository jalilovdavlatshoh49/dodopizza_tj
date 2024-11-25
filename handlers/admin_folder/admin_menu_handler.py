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

    # Илова кардани тугмаҳо бо тартиби нав
    keyboard_builder.row(
        KeyboardButton(text="📂 Админ Меню"),  # Тугмаи аввал
        KeyboardButton(text="➕ Зам кардани продукт")  # Тугмаи дуюм
    )
    keyboard_builder.row(
        KeyboardButton(text="📋 Заказҳои интизорӣ (қабул нашуда)"),
        KeyboardButton(text="✅ Заказҳои қабулшуда")
    )
    keyboard_builder.row(
        KeyboardButton(text="🚚 Заказҳои дар роҳ"),
        KeyboardButton(text="🏠 Заказҳои расонидашуда")
    )

    # Сохтани клавиатура
    return keyboard_builder.as_markup(resize_keyboard=True)

# Ҳендлер барои админ меню
@admin_menu_router.message(Command("admin_menu"))
async def admin_menu_handler(message: types.Message):
    
    reply_keyboard = admin_menu_keyboard()
    await message.answer("Хуш омадед ба саҳифаи админ", reply_markup=reply_keyboard)


# Ҳендлер барои тугмаи "📂 Меню"
@admin_menu_router.message(F.text == "📂 Админ Меню")
async def category_menu_handler(message: types.Message):
    keyboard = await get_category_keyboard()
    await message.answer("📂 Интихоби категория:", reply_markup=keyboard)
    
