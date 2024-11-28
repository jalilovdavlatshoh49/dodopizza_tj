from aiogram import types, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.state import State, StatesGroup
from aiogram.types import ContentType
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from database.db import SessionLocal
from database.tables import *



# Router setup for admin product handling
admin_product_router = Router()



# Callback query-ро коркард мекунем
@admin_product_router.callback_query(lambda c: c.data.startswith("admin_category_"))
async def handle_category(callback_query: CallbackQuery):
    category = callback_query.data.split("_")[-1]
    product_model = globals().get(category.capitalize())
    if not product_model:
        await callback_query.answer("Категорияи нодуруст.", show_alert=True)
        return

    async with SessionLocal() as session:
        query = select(product_model)
        result = await session.execute(query)
        products = result.scalars().all()

        if not products:
            await callback_query.message.answer("Дар ин категория маҳсулоте вуҷуд надорад.")
            return
        await callback_query.message.delete()

        for product in products:
            product_text = (
                f"📦 {product.name}\n"
                f"📜 Тавсиф: {product.description}\n"
                f"💵 Нархи: {product.price} сомонӣ\n"
            )

            builder = InlineKeyboardBuilder()
            builder.add(
                InlineKeyboardButton(
                    text="✏️ Иваз",
                    callback_data=f"edit_{category}_{product.id}"
                )
            )
            builder.add(
                InlineKeyboardButton(
                    text="❌ Ҳазф",
                    callback_data=f"delete_{category}_{product.id}"
                )
            )


            await callback_query.message.answer_photo(
                photo=product.image_url,
                caption=product_text,
                reply_markup=builder.as_markup()
            )

        

        total_products = len(products)
        page_text = f"Аз {total_products} маҳсулот, {total_products} дона нишон дода шуд"
        # Матни шумораи маҳсулот ва тугмаи ба қафо
        exit_builder = InlineKeyboardBuilder()
        exit_builder.add(
            InlineKeyboardButton(
                text="🔙 Ба қафо",
                callback_data="exit_to_admin_menu"
            )
        )
        await callback_query.message.answer(
            page_text,
            reply_markup=exit_builder.as_markup()
        )


# Callback query барои оғози тасдиқи ҳазф
@admin_product_router.callback_query(lambda c: c.data.startswith("delete_"))
async def confirm_delete_product(callback_query: CallbackQuery):
    _, category, product_id = callback_query.data.split("_")

    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(
            text="✅ Ҳазф кардан",
            callback_data=f"confirmdelete_{category}_{product_id}"
        )
    )
    builder.add(
        InlineKeyboardButton(
            text="❌ Ҳазф накардан",
            callback_data=f"canceldelete_{category}_{product_id}"
        )
    )
    await callback_query.message.edit_reply_markup(
        reply_markup=builder.as_markup()
    )
    await callback_query.answer()


# Callback query барои тасдиқи ҳазф
@admin_product_router.callback_query(lambda c: c.data.startswith("confirmdelete_"))
async def delete_product(callback_query: CallbackQuery):
    _, category, product_id = callback_query.data.split("_")
    product_model = globals().get(category.capitalize())
    if not product_model:
        await callback_query.answer("Категорияи нодуруст.", show_alert=True)
        return

    async with SessionLocal() as session:
        query = select(product_model).filter(product_model.id == int(product_id))
        result = await session.execute(query)
        product = result.scalar_one_or_none()

        if product:
            await session.delete(product)
            await session.commit()
            await callback_query.answer("Маҳсулот бо муваффақият ҳазф шуд.")
            await callback_query.message.delete()
        else:
            await callback_query.answer("Маҳсулот ёфт нашуд!", show_alert=True)


# Callback query барои рад кардани ҳазф
@admin_product_router.callback_query(lambda c: c.data.startswith("canceldelete_"))
async def cancel_delete(callback_query: CallbackQuery):
    _, category, product_id = callback_query.data.split("_")

    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(
            text="✏️ Иваз",
            callback_data=f"edit_{category}_{product_id}"
        )
    )
    builder.add(
        InlineKeyboardButton(
            text="❌ Ҳазф",
            callback_data=f"delete_{category}_{product_id}"
        )
    )

    if callback_query.message:
        await callback_query.message.edit_reply_markup(
            reply_markup=builder.as_markup()
        )
    await callback_query.answer("Ҳазф бекор карда шуд.")
   


# Define the state machine
class ProductEdit(StatesGroup):
    waiting_for_attribute = State()  # State for attribute selection
    waiting_for_value = State()  # State for value input

# Handler for editing a product
@admin_product_router.callback_query(lambda c: c.data.startswith("edit_") and len(c.data.split("_")) == 3)
async def edit_product(callback_query: CallbackQuery):
    _, category, productid = callback_query.data.split("_")

    # Creating keyboard
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Ном", callback_data=f"edit_{category}_{productid}_name"),
        InlineKeyboardButton(text="Тавсиф", callback_data=f"edit_{category}_{productid}_description")
    )
    builder.row(
        InlineKeyboardButton(text="Нарх", callback_data=f"edit_{category}_{productid}_price"),
        InlineKeyboardButton(text="Тасвир", callback_data=f"edit_{category}_{productid}_image_url")
    )

    await callback_query.message.answer(
        "Лутфан, интихоб кунед, ки кадом маълумотро мехоҳед иваз кунед:",
        reply_markup=builder.as_markup()
    )

# Handling the attribute selection
@admin_product_router.callback_query(lambda c: c.data.startswith("edit_") and len(c.data.split("_")) == 4)
async def choose_attribute(callback_query: CallbackQuery, state: FSMContext):
    _, category, product_id, attribute = callback_query.data.split("_")

    # Store product_id and category in FSM state
    await state.update_data(product_id=product_id, category=category, attribute=attribute)

    # Set state to ask for the value
    await state.set_state(ProductEdit.waiting_for_value)

    # Ask for the corresponding value based on the attribute selected
    messages = {
        "name": "Лутфан, номи маҳсулотро ворид кунед:",
        "description": "Лутфан, тавсифи маҳсулотро ворид кунед:",
        "price": "Лутфан, нархи маҳсулотро ворид кунед:",
        "image_url": "Лутфан, тасвирро ирсол кунед:"
    }
    await callback_query.message.answer(messages.get(attribute, "Маълумоти нодуруст!"))



admin_product_router = Router()

# Handling value input (name, description, price, image_url)
@admin_product_router.message(ProductEdit.waiting_for_value)
async def process_value(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    product_id = user_data['product_id']
    category = user_data['category']
    attribute = user_data['attribute']

    async with SessionLocal() as session:
        product_model = globals()[category.capitalize()]
        query = select(product_model).filter(product_model.id == int(product_id))
        result = await session.execute(query)
        product = result.scalars().first()

        if product:
            try:
                if attribute == "name":
                    product.name = message.text
                elif attribute == "description":
                    product.description = message.text
                elif attribute == "price":
                    product.price = int(message.text)
                elif attribute == "image_url" and message.photo:
                    # Downloading the photo
                    photo = message.photo[-1]
                    product.image_url = photo.file_id

                await session.commit()
                await message.answer(f"Маълумоти {attribute} иваз шуд.")
            except Exception as e:
                await message.answer(f"Хатогӣ: {e}")
        else:
            await message.answer("Маҳсулот ёфт нашуд!")

    # Finish the FSM process
    await state.clear()