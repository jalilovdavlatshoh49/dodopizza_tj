from aiogram import types, Router
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery 
from aiogram.filters import Command
from sqlalchemy.future import select
from database.tables import Cart, CartItem  # Импорт кардани моделҳо
from sqlalchemy.ext.asyncio import AsyncSession
from database.db import SessionLocal
sabad_router = Router()

# Create cart keyboard
async def create_cart_keyboard(cart):
    session = SessionLocal()
    keyboard = []

    for item in cart.items:
        product_model = globals()[item.product_type.capitalize()]
        product = await session.execute(select(product_model).filter_by(id=item.product_id))
        product = product.scalar_one_or_none()

        if product:
            total_price = product.price * item.quantity
            buttons = [
                InlineKeyboardButton(text="➕ Зам", callback_data=f"increase_{item.product_type}_{item.product_id}"),
                InlineKeyboardButton(text="➖ Кам", callback_data=f"decrease_{item.product_type}_{item.product_id}"),
                InlineKeyboardButton(text="❌ Нест", callback_data=f"remove_{item.product_type}_{item.product_id}")
            ]
            keyboard.append(buttons)
            keyboard.append([InlineKeyboardButton(
                text=f"{product.name}: {item.quantity} x {product.price} = {total_price} сомони", callback_data="no_action"
            )])

    keyboard.append([InlineKeyboardButton(text="🛒 Ҳисоби сабад", callback_data="checkout")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
    

# Функсияи ёрирасон барои гирифтани маҳсулотҳо аз сабад
async def get_cart_items(session: AsyncSession, user_id: int):
    query = await session.execute(
        select(CartItem, Cart)
        .join(Cart)
        .where(Cart.user_id == user_id)
    )
    items = query.scalars().all()

    result = []
    for item in items:
        product_model = globals()[item.product_type.capitalize()]  # Таблицаро муайян мекунем
        product = await session.get(product_model, item.product_id)
        if product:
            result.append({
                "id": item.id,
                "name": product.name,
                "price": product.price,
                "image_url": product.image_url,
                "quantity": item.quantity,
            })
    return result


async def show_cart(target, user_id: int):
    session = SessionLocal()
    """
    Сабадро барои истифодабаранда нишон медиҳад.

    Args:
        target: Паём ё объекти callback_query (Message ё CallbackQuery).
        session: Сессияи асинхронии SQLAlchemy.
        user_id: ID-и истифодабаранда.
    """
    cart_items = await get_cart_items(session, user_id)

    if not cart_items:
        # Агар сабад холӣ бошад
        if isinstance(target, CallbackQuery):
            await target.message.edit_text("Сабади шумо холӣ аст.")
        else:
            await target.answer("Сабади шумо холӣ аст.")
        return

    # Ҳар як маҳсулотро нишон медиҳем
    for item in cart_items:
        # Сохтани клавиатураи идоракунӣ
        keyboard = InlineKeyboardMarkup(row_width=3)
        keyboard.add(
            InlineKeyboardButton("➕", callback_data=f"sabad:add_{item['id']}"),
            InlineKeyboardButton("➖", callback_data=f"sabad:remove_{item['id']}"),
            InlineKeyboardButton("❌ Нест кардан", callback_data=f"sabad:delete_{item['id']}")
        )

        # Намуди нишон додани маълумоти маҳсулот
        caption = (
            f"📦 <b>{item['name']}</b>\n"
            f"💰 Нарх: {item['price']} сомонӣ\n"
            f"🔢 Миқдор: {item['quantity']}\n"
            f"💵 Ҷамъи умумӣ: {item['price'] * item['quantity']} сомонӣ"
        )

        if isinstance(target, CallbackQuery):
            # Агар даъват аз callback_query бошад
            await target.message.edit_caption(
                caption=caption,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        else:
            # Агар даъват аз message бошад
            await target.answer_photo(
                photo=item["image_url"],
                caption=caption,
                reply_markup=keyboard,
                parse_mode="HTML"
            )


# Helper function to get the user's cart
async def get_cart_for_user(user_id):
    session = SessionLocal()
    cart = await session.execute(select(Cart).filter(Cart.user_id == user_id, Cart.status == "pending"))
    cart = cart.scalar_one_or_none()
    if not cart:
        cart = Cart(user_id=user_id)
        session.add(cart)
        await session.commit()
    return cart

# Function to handle "buy product" callback
@sabad_router.callback_query(lambda c: c.data and c.data.startswith("buy_"))
async def buy_product_callback(query: CallbackQuery):
    await query.answer()

    callback_data = query.data
    product_id = int(callback_data.split("_")[2])
    product_type = callback_data.split("_")[1]

    user_id = query.from_user.id
    session: AsyncSession = query.bot['session']

    cart = await get_cart_for_user(user_id, session)

    product_model = globals()[product_type.capitalize()]
    product = await session.execute(select(product_model).filter_by(id=product_id))
    product = product.scalar_one_or_none()

    if product:
        cart.add_item(product_type, product_id, quantity=1)
        await session.commit()

        buttons = [
            InlineKeyboardButton(text="➕ Зам", callback_data=f"increase_{product_type}_{product_id}"),
            InlineKeyboardButton(text="➖ Кам", callback_data=f"decrease_{product_type}_{product_id}"),
            InlineKeyboardButton(text="❌ Нест", callback_data=f"remove_{product_type}_{product_id}")
        ]

        total_price = product.price
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            buttons,
            [InlineKeyboardButton(text=f"{product.name}: 1 x {product.price} = {total_price} сомони", callback_data="no_action")],
            [InlineKeyboardButton(text="🛒 Ҳисоби сабад", callback_data="checkout")]
        ])

        await query.edit_message_text(text=f"Маҳсулот илова шуд: {product.name}", reply_markup=keyboard)

# Function to update cart item
@sabad_router.callback_query(lambda c: c.data and c.data.startswith(("increase_", "decrease_", "remove_")))
async def update_cart_item(query: CallbackQuery):
    await query.answer()

    callback_data = query.data
    action, product_type, product_id = callback_data.split("_")

    user_id = query.from_user.id
    session: AsyncSession = query.bot['session']

    cart = await get_cart_for_user(user_id, session)
    cart_item = await session.execute(select(CartItem).filter(
        CartItem.cart == cart, 
        CartItem.product_type == product_type, 
        CartItem.product_id == int(product_id)
    ))
    cart_item = cart_item.scalar_one_or_none()

    if action == 'increase':
        cart_item.quantity += 1
    elif action == 'decrease' and cart_item.quantity > 1:
        cart_item.quantity -= 1
    elif action == 'remove':
        cart.remove_item(product_type, int(product_id))
        await session.commit()
        await query.edit_message_text(text="Маҳсулот аз сабад хориҷ шуд.", reply_markup=await create_cart_keyboard(cart))
        return

    await session.commit()
    await query.edit_message_text(text="Сабади шумо:", reply_markup=await create_cart_keyboard(cart))



# Ҳендлер барои командаи /cart
@sabad_router.message(Command("cart"))
async def show_cart(message: types.Message, session: AsyncSession):
    user_id = message.from_user.id
    cart_items = await get_cart_items(session, user_id)

    if not cart_items:
        await message.answer("Сабади шумо холӣ аст.")
        return

    for item in cart_items:
        keyboard = InlineKeyboardMarkup(row_width=3)
        keyboard.add(
            InlineKeyboardButton("➕", callback_data=f"sabad:add_{item['id']}"),
            InlineKeyboardButton("➖", callback_data=f"sabad:remove_{item['id']}"),
            InlineKeyboardButton("❌ Нест кардан", callback_data=f"sabad:delete_{item['id']}")
        )

        await message.answer_photo(
            photo=item["image_url"],
            caption=(
                f"📦 <b>{item['name']}</b>\n"
                f"💰 Нарх: {item['price']} сомонӣ\n"
                f"🔢 Миқдор: {item['quantity']}\n"
                f"💵 Ҷамъи умумӣ: {item['price'] * item['quantity']} сомонӣ"
            ),
            reply_markup=keyboard,
            parse_mode="HTML"
        )

# Callback ҳендлерҳо барои идоракунии миқдор
@sabad_router.callback_query(lambda c: c.data.startswith("sabad:add_"))
async def add_item(callback_query: CallbackQuery, session: AsyncSession):
    item_id = int(callback_query.data.split("_")[1])
    cart_item = await session.get(CartItem, item_id)
    if cart_item:
        cart_item.quantity += 1
        await session.commit()
        await callback_query.answer("Миқдор зиёд шуд!")
        await show_cart(callback_query.message, session)

@sabad_router.callback_query(lambda c: c.data.startswith("sabad:remove_"))
async def remove_item(callback_query: CallbackQuery, session: AsyncSession):
    item_id = int(callback_query.data.split("_")[1])
    cart_item = await session.get(CartItem, item_id)
    if cart_item and cart_item.quantity > 1:
        cart_item.quantity -= 1
        await session.commit()
        await callback_query.answer("Миқдор кам шуд!")
        await show_cart(callback_query.message, session)
    else:
        await callback_query.answer("Миқдорро кам кардан мумкин нест!")

@sabad_router.callback_query(lambda c: c.data.startswith("sabad:delete_"))
async def delete_item(callback_query: CallbackQuery, session: AsyncSession):
    item_id = int(callback_query.data.split("_")[1])
    cart_item = await session.get(CartItem, item_id)
    if cart_item:
        await session.delete(cart_item)
        await session.commit()
        await callback_query.answer("Маҳсулот аз сабад нест карда шуд!")
        await show_cart(callback_query.message, session)