from aiogram import types, Router
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery 
from aiogram.filters import Command
from sqlalchemy.future import select
from database.db import SessionLocal, Cart, CartItem
from database.tables import *
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
async def get_cart_items(user_id: int):
    session = SessionLocal()
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





async def get_keyboard(cart_item: CartItem):
    """Сохтани клавиатураи динамикӣ барои маҳсулот."""
    quantity = cart_item.quantity
    price = await cart_item.get_price()  # Get the price using the async method
    total_price = price * quantity  # Calculate total price
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="-", callback_data=f"decrease_{cart_item.product_type}_{cart_item.product_id}"),
            InlineKeyboardButton(text=f"{quantity} дона", callback_data="noop"),
            InlineKeyboardButton(text="+", callback_data=f"increase_{cart_item.product_type}_{cart_item.product_id}")
        ],
        [
            InlineKeyboardButton(
                text=f"Карзина ({total_price} сомонӣ)",
                callback_data="view_cart"
            )
        ]
    ])
    return keyboard


@sabad_router.callback_query(lambda call: call.data.startswith("buy_"))
async def buy_product(call: types.CallbackQuery):
    async with SessionLocal() as session:
        data = call.data.split("_")
        category, product_id = data[1], int(data[2])
        user_id = call.from_user.id

        # Поиск или создание корзины
        result = await session.execute(select(Cart).filter(Cart.user_id == user_id))
        cart = result.scalars().first()
        if not cart:
            cart = Cart(user_id=user_id)
            session.add(cart)
            await session.flush()

        # Поиск продукта
        product_model = globals().get(category.capitalize())
        if not product_model:
            await call.answer("Категория ёфт нашуд!", show_alert=True)
            return

        result = await session.execute(select(product_model).filter(product_model.id == product_id))
        product = result.scalars().first()
        if not product:
            await call.answer("Маҳсулот ёфт нашуд!", show_alert=True)
            return

        # Добавление продукта в корзину
        await cart.add_item(session, category, product_id, quantity=1)
        await session.commit()

        # Получение элемента корзины из базы данных
        result = await session.execute(
        select(CartItem).where(CartItem.product_type == category, CartItem.product_id == product_id)
    )
        cart_item = result.scalars().first()

        if cart_item:
            # Отправка клавиатуры
            await call.message.edit_reply_markup(reply_markup=get_keyboard(cart_item))
        else:
            await call.answer("Элемент не найден", show_alert=True)


@sabad_router.callback_query(lambda call: call.data.startswith("increase_"))
async def increase_quantity(call: types.CallbackQuery):
    async with SessionLocal() as session:
        """Увеличение количества продукта."""
        data = call.data.split("_")
        category, product_id = data[1], int(data[2])

        # Поиск корзины и товара
        user_id = call.from_user.id
        result = await session.execute(select(Cart).filter(Cart.user_id == user_id))
        cart = result.scalars().first()
        if not cart:
            await call.answer("Корзина холӣ аст!", show_alert=True)
            return

        await cart.add_item(category, product_id, quantity=1)
        await session.commit()

        # Ҷустуҷӯи cart_item бо истифодаи асинхронӣ
        async with session.begin():
            result = await session.execute(
            select(CartItem).where(CartItem.product_type == category, CartItem.product_id == product_id)
        )
            cart_item = result.scalars().first()  # Истифодаи first ба ҷои next

        if cart_item:
            await call.message.edit_reply_markup(reply_markup=get_keyboard(cart_item))
        else:
            await call.answer("Маҳсулоти дархостшуда ёфт нашуд!", show_alert=True)


@sabad_router.callback_query(lambda call: call.data.startswith("decrease_"))
async def decrease_quantity(call: types.CallbackQuery):
    async with SessionLocal() as session:
        """Уменьшение количества продукта."""
        data = call.data.split("_")
        category, product_id = data[1], int(data[2])

        # Поиск корзины и товара
        user_id = call.from_user.id
        result = await session.execute(select(Cart).filter(Cart.user_id == user_id))
        cart = result.scalars().first()
        if not cart:
            await call.answer("Корзина холӣ аст!", show_alert=True)
            return

        cart_item = next(item for item in cart.items if item.product_type == category and item.product_id == product_id)
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
        else:
            await cart.remove_item(category, product_id)

        await session.commit()

        async with session.begin():
            result = await session.execute(
            select(CartItem).where(CartItem.product_type == category, CartItem.product_id == product_id)
        )
            cart_items = result.scalars().all()

        if cart_items:
        # Барои гирифтани аввалин мувофиқ, агар чизи мувофиқ ёфта шавад
            cart_item = cart_items[0]
            await call.message.edit_reply_markup(reply_markup=get_keyboard(cart_item))
        else:
            await call.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text=f"Харид {product.price} сомонӣ",
                                         callback_data=f"buy_{category}_{product_id}")
                ]
            ]))



# Ҳендлер барои командаи /cart
@sabad_router.message(Command("cart"))
async def show_cart(message: types.Message):
    session = SessionLocal()
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
async def add_item(callback_query: CallbackQuery):
    session = SessionLocal()
    item_id = int(callback_query.data.split("_")[1])
    cart_item = await session.get(CartItem, item_id)
    if cart_item:
        cart_item.quantity += 1
        await session.commit()
        await callback_query.answer("Миқдор зиёд шуд!")
        await show_cart(callback_query.message, session)

@sabad_router.callback_query(lambda c: c.data.startswith("sabad:remove_"))
async def remove_item(callback_query: CallbackQuery):
    session = SessionLocal()
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
async def delete_item(callback_query: CallbackQuery):
    session = SessionLocal()
    item_id = int(callback_query.data.split("_")[1])
    cart_item = await session.get(CartItem, item_id)
    if cart_item:
        await session.delete(cart_item)
        await session.commit()
        await callback_query.answer("Маҳсулот аз сабад нест карда шуд!")
        await show_cart(callback_query.message, session)