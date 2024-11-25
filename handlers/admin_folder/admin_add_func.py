from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.enums import ParseMode
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database.tables import Pizza, Combo, Snacks, Desserts, Drinks, Sauces, Kids_Love, OtherGoods
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from database.db import SessionLocal
# Модели FSM барои илова кардани маҳсулот
class AddProductFSM(StatesGroup):
    category = State()
    name = State()
    description = State()
    price = State()
    image_url = State()

# Router
admin_add_func_router = Router()



# Категорияҳо
categories = [
    ("Пицца 🍕", "pizza"),
    ("Комбо 🍱", "combo"),
    ("Закуски 🍟", "snacks"),
    ("Десерты 🍰", "desserts"),
    ("Напитки 🥤", "drinks"),
    ("Соусы 🥫", "sauces"),
    ("Любят дети 🧸", "kids_love"),
    ("Другие товары 📦", "other_goods")
]

# Тугмаҳо барои категорияҳо
async def categories_keyboard():
    keyboard_builder = InlineKeyboardBuilder()
    for name, callback_data in categories:
        keyboard_builder.add(
            InlineKeyboardButton(text=name, callback_data=callback_data)
        )
    keyboard_builder.adjust(2)  # Танзими тугмаҳо дар 2 сутун
    return keyboard_builder.as_markup()

# Илова кардани тугмаи "Зам кардани продукт"
@admin_add_func_router.message(lambda message: message.text == "➕ Зам кардани продукт")
async def add_product_start(message: types.Message, state: FSMContext):
    keyboard = await categories_keyboard()
    await message.answer("Лутфан категорияро интихоб кунед:", reply_markup=keyboard)
    await state.set_state(AddProductFSM.category)

# Callback барои интихоби категория
@admin_add_func_router.callback_query(lambda call: call.data in [category[1] for category in categories])
async def choose_category(callback: CallbackQuery, state: FSMContext):
    category = callback.data
    await state.update_data(category=category)
    await callback.message.answer("Шумо категорияро интихоб кардед. Номи маҳсулотро ворид кунед:")
    await state.set_state(AddProductFSM.name)

# Гирифтани номи маҳсулот
@admin_add_func_router.message(AddProductFSM.name)
async def get_name(message: types.Message, state: FSMContext):
    name = message.text
    await state.update_data(name=name)
    await message.answer("Тавсифи маҳсулотро ворид кунед:")
    await state.set_state(AddProductFSM.description)

# Гирифтани тавсифи маҳсулот
@admin_add_func_router.message(AddProductFSM.description)
async def get_description(message: types.Message, state: FSMContext):
    description = message.text
    await state.update_data(description=description)
    await message.answer("Нархи маҳсулотро ворид кунед (танҳо рақам):")
    await state.set_state(AddProductFSM.price)

# Гирифтани нархи маҳсулот
@admin_add_func_router.message(AddProductFSM.price)
async def get_price(message: types.Message, state: FSMContext):
    try:
        price = float(message.text)
        await state.update_data(price=price)
        await message.answer("Сурати маҳсулотро ворид кунед:")
        await state.set_state(AddProductFSM.image_url)
    except ValueError:
        await message.answer("Лутфан рақами дурустро ворид кунед!")



@admin_add_func_router.message(AddProductFSM.image_url)
async def get_image_url(message: types.Message, state: FSMContext):
     
    if message.photo:
        # Агар корбар URL фиристад
        image_url = message.text
    else:
        await message.answer("Лутфан сурат ё URL-и дурусти тасвирро ирсол кунед.")
        await state.set_state(AddProductFSM.image_url)
        return

    # Истифодаи URL барои илова ба база
    await state.update_data(image_url=image_url)
    session = SessionLocal()

    data = await state.get_data()
    category = data['category']
    name = data['name']
    description = data['description']
    price = data['price']

    table_mapping = {
        "pizza": Pizza,
        "combo": Combo,
        "snacks": Snacks,
        "desserts": Desserts,
        "drinks": Drinks,
        "sauces": Sauces,
        "kids_love": Kids_Love,
        "other_goods": OtherGoods
    }

    if category not in table_mapping:
        await message.answer(f"Категорияи '{category}' нодуруст аст. Лутфан категорияи дурустро интихоб кунед.")
        return

    product_model = table_mapping[category]
    new_product = product_model(
        name=name,
        description=description,
        price=price,
        image_url=image_url
    )
    session.add(new_product)
    session.commit()

    # Гирифтани маҳсулот бо филтр
    filtered_product = session.query(product_model).filter_by(
    name=name,
    description=description,
    price=price
).first()

    # Ҷавоб додан бо маълумоти гирифташуда
    if filtered_product:
        await message.answer_photo(
            photo=filtered_product.image_url,
            caption=(
                f"<b>Маҳсулот ба категорияи '{category}' илова шуд!</b>\n\n"
            f"<b>Ном:</b> {filtered_product.name}\n"
            f"<b>Тавсиф:</b> {filtered_product.description}\n"
            f"<b>Нарх:</b> {filtered_product.price} сомонӣ"
        ),
        parse_mode=ParseMode.HTML
    )
    else:
        await message.answer("Маҳсулот ёфт нашуд. Лутфан бори дигар санҷед.")

# Пок кардани ҳолати FSM
    await state.clear()

