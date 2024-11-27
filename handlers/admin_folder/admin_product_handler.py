from aiogram import types, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters.state import State, StatesGroup
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from database.db import SessionLocal
from database.tables import *

# Router setup for admin product handling
admin_product_router = Router()

from aiogram.utils.keyboard import InlineKeyboardBuilder

# Callback query-ро коркард мекунем
@admin_product_router.callback_query(lambda c: c.data.startswith("admin_category_"))
async def handle_category(callback_query: CallbackQuery):
    category = callback_query.data.split("_")[-1]

    # Модели мувофиқро муайян мекунем
    product_model = globals()[category.capitalize()]
    async with SessionLocal() as session:
        query = select(product_model)
        result = await session.execute(query)
        products = result.scalars().all()

        if not products:
            await callback_query.message.answer("Дар ин категория маҳсулоте вуҷуд надорад.")
            return

        for product in products:
            product_text = (
                f"📦 {product.name}\n"
                f"📜 Тавсиф: {product.description}\n"
                f"💵 Нархи: {product.price} сомонӣ\n"
            )

            # Клавиатураро барои идоракунии маҳсулот месозем
            builder = InlineKeyboardBuilder()
            builder.add(
                InlineKeyboardButton(
                    text=f"✏️ Иваз",
                    callback_data=f"edit_{category}_{product.id}"
                )
            )
            builder.add(
                InlineKeyboardButton(
                    text=f"❌ Ҳазф",
                    callback_data=f"delete_{category}_{product.id}"
                )
            )

            # Ирсоли тасвир бо матн ва клавиатура
            await callback_query.message.answer_photo(
                photo=product.image_url,
                caption=product_text,
                reply_markup=builder.as_markup()
            )
            
 

# Callback query барои оғози тасдиқи ҳазф
@admin_product_router.callback_query(lambda c: c.data.startswith("delete_"))
async def confirm_delete_product(callback_query: CallbackQuery):
    _, category, product_id = callback_query.data.split("_")

    # Паёми тасдиқ бо клавиатураи "Ҳа" ва "Не"
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(
            text="✅ Ҳафз кардан",
            callback_data=f"confirm_delete_{category}_{product_id}"
        )
    )
    builder.add(
        InlineKeyboardButton(
            text="❌ Ҳафз накардан",
            callback_data="cancel_delete"
        )
    )
    await callback_query.message.edit_reply_markup(
    reply_markup=builder.as_markup()
)
    await callback_query.answer()


# Callback query барои тасдиқи ҳазф
@admin_product_router.callback_query(lambda c: c.data.startswith("confirm_delete_"))
async def delete_product(callback_query: CallbackQuery):
    _, category, product_id = callback_query.data.split("_")
    product_model = globals()[category.capitalize()]
    async with SessionLocal() as session:
        query = select(product_model).filter(product_model.id == int(product_id))
        result = await session.execute(query)
        product = result.scalar_one_or_none()

        if product:
            await session.delete(product)
            await session.commit()
            await callback_query.message.answer("Маҳсулот бо муваффақият ҳазф шуд.")
            await callback_query.message.delete()
            await callback_query.answer()
        else:
            await callback_query.answer("Маҳсулот ёфт нашуд!")


# Callback query барои бекор кардани ҳазф
@admin_product_router.callback_query(lambda c: c.data == "cancel_delete")
async def cancel_delete(callback_query: CallbackQuery):
    # Клавиатураро барои идоракунии маҳсулот месозем
            builder = InlineKeyboardBuilder()
            builder.add(
                InlineKeyboardButton(
                    text=f"✏️ Иваз",
                    callback_data=f"edit_{category}_{product.id}"
                )
            )
            builder.add(
                InlineKeyboardButton(
                    text=f"❌ Ҳазф",
                    callback_data=f"delete_{category}_{product.id}"
                )
            )
            await callback_query.message.edit_reply_markup(
    reply_markup=builder.as_markup()
)
            await callback_query.answer()
   

# Define the state machine
class ProductEdit(StatesGroup):
    waiting_for_attribute = State()  # State for attribute selection
    waiting_for_value = State()  # State for value input

# Example callback query handler to check for product editing
@admin_product_router.callback_query(lambda c: c.data.startswith("edit_"))
async def edit_product(callback_query: CallbackQuery):
    _, category, product_id = callback_query.data.split("_")

    # Ask the user which attribute they want to edit
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("Ном", callback_data=f"edit_{category}_{product_id}_name"),
        InlineKeyboardButton("Тавсиф", callback_data=f"edit_{category}_{product_id}_description"),
        InlineKeyboardButton("Нарх", callback_data=f"edit_{category}_{product_id}_price"),
        InlineKeyboardButton("Тасвир", callback_data=f"edit_{category}_{product_id}_image_url")
    )

    await callback_query.message.answer("Лутфан, интихоб кунед, ки кадом маълумотро мехоҳед иваз кунед:", reply_markup=keyboard)

# Handling the attribute selection
@admin_product_router.callback_query(lambda c: c.data.startswith("edit_") and len(c.data.split("_")) == 4)
async def choose_attribute(callback_query: CallbackQuery, state: FSMContext):
    _, category, product_id, attribute = callback_query.data.split("_")

    # Store product_id and category in FSM state
    await state.update_data(product_id=product_id, category=category, attribute=attribute)

    # Set state to ask for the value
    await ProductEdit.waiting_for_value.set()

    # Ask for the corresponding value based on the attribute selected
    messages = {
        "name": "Лутфан, номи маҳсулотро ворид кунед:",
        "description": "Лутфан, тавсифи маҳсулотро ворид кунед:",
        "price": "Лутфан, нархи маҳсулотро ворид кунед:",
        "image_url": "Лутфан, URL тасвирро ворид кунед:"
    }
    await callback_query.message.answer(messages.get(attribute, "Маълумоти нодуруст!"))

# Handling value input (name, description, price, image_url)
@admin_product_router.message(ProductEdit.waiting_for_value)
async def process_value(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    product_id = user_data['product_id']
    category = user_data['category']
    attribute = user_data['attribute']
    value = message.text

    async with SessionLocal() as session:
        product_model = globals()[category.capitalize()]
        query = select(product_model).filter(product_model.id == int(product_id))
        result = await session.execute(query)
        product = result.scalars().first()

        if product:
            try:
                if attribute == "name":
                    product.name = value
                elif attribute == "description":
                    product.description = value
                elif attribute == "price":
                    product.price = int(value)
                elif attribute == "image_url":
                    product.image_url = value
                await session.commit()
                await message.answer(f"Маълумоти {attribute} иваз шуд.")
            except Exception as e:
                await message.answer(f"Хатогӣ: {e}")
        else:
            await message.answer("Маҳсулот ёфт нашуд!")

    # Finish the FSM process
    await state.finish()