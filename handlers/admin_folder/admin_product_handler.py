from aiogram import types, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters.state import State, StatesGroup
from sqlalchemy.future import select
from database.db import SessionLocal

# Router setup for admin product handling
admin_product_router = Router()


# Callback query-ро коркард мекунем
@admin_product_router.callback_query(lambda c: c.data.startswith("admin_category_"))
async def handle_category(callback_query: CallbackQuery):
    session = SessionLocal()
    category = callback_query.data.split("_")[-1]

    # Модели мувофиқро муайян мекунем
    product_model = globals()[category.capitalize()]
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
        keyboard = InlineKeyboardMarkup(row_width=1)
        keyboard.add(
            InlineKeyboardButton(
                text=f"✏️ Иваз {product.name}",
                callback_data=f"edit_{category}_{product.id}"
            ),
            InlineKeyboardButton(
                text=f"❌ Ҳазф {product.name}",
                callback_data=f"delete_{category}_{product.id}"
            )
        )

        # Ирсоли тасвир бо матн ва клавиатура
        await callback_query.message.answer_photo(
            photo=product.image_url,
            caption=product_text,
            reply_markup=keyboard
        )
        


@admin_product_router.callback_query(lambda c: c.data.startswith("delete_"))
async def delete_product(callback_query: CallbackQuery, session: AsyncSession):
    _, category, product_id = callback_query.data.split("_")
    product_model = globals()[category.capitalize()]
    query = select(product_model).filter(product_model.id == int(product_id))
    result = await session.execute(query)
    product = result.scalar_one_or_none()
    
    if product:
        await session.delete(product)
        await session.commit()
        await callback_query.answer("Маҳсулот ҳазф шуд!")
    else:
        await callback_query.answer("Маҳсулот ёфт нашуд!")
        


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
    
    await callback_query.answer("Лутфан, интихоб кунед, ки кадом маълумотро мехоҳед иваз кунед:", reply_markup=keyboard)

# Handling the attribute selection
@admin_product_router.callback_query(lambda c: c.data.startswith("edit_") and len(c.data.split("_")) == 4)
async def choose_attribute(callback_query: CallbackQuery, state: FSMContext):
    _, category, product_id, attribute = callback_query.data.split("_")
    
    # Store product_id and category in FSM state
    await state.update_data(product_id=product_id, category=category)
    
    # Set state to ask for the value
    await ProductEdit.waiting_for_value.set()
    
    # Ask for the corresponding value based on the attribute selected
    if attribute == "name":
        await callback_query.message(callback_query.from_user.id, "Лутфан, номи маҳсулотро ворид кунед:")
    elif attribute == "description":
        await callback_query.message(callback_query.from_user.id, "Лутфан, тавсифи маҳсулотро ворид кунед:")
    elif attribute == "price":
        await callback_query.message(callback_query.from_user.id, "Лутфан, нархи маҳсулотро ворид кунед:")
    elif attribute == "image_url":
        await callback_query.message(callback_query.from_user.id, "Лутфан, URL тасвирро ворид кунед:")

# Handling value input (name, description, price, image_url)
@admin_product_router.message(ProductEdit.waiting_for_value)
async def process_value(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    product_id = user_data['product_id']
    category = user_data['category']
    value = message.text
    session = SessionLocal()
    
    # Retrieve the selected attribute from FSM state
    attribute = user_data.get("attribute")

    # Update the product information based on the attribute selected
    product_model = globals()[category.capitalize()]
    async with session.begin():
        product = await session.execute(select(product_model).filter(product_model.id == product_id))
        product = product.scalars().first()
        
        if product:
            if attribute == "name":
                product.name = value
            elif attribute == "description":
                product.description = value
            elif attribute == "price":
                try:
                    product.price = int(value)
                except ValueError:
                    await message.answer("Нарх дуруст нест, лутфан як рақам ворид кунед:")
                    return
            elif attribute == "image_url":
                if not value.startswith("http") or not value.endswith(("jpg", "png", "jpeg")):
                    await message.answer("Лутфан, як URL дуруст барои тасвир ворид кунед (ҷавоб бояд бо 'http' оғоз ёбад ва бо 'jpg', 'png' ё 'jpeg' тамом шавад):")
                    return
                product.image_url = value

            # Commit the changes to the database
            await session.commit()
            await message.answer(f"Маълумоти {category} муваффақона иваз карда шуд.")
        else:
            await message.answer("Маҳсулот ё маълумот пайдо нашуд.")

    # Finish the FSM process
    await state.finish()