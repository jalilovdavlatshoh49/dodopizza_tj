from aiogram import types, Router
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery 
from aiogram.filters import Command
from sqlalchemy.future import select
from database.db import SessionLocal, Cart, CartItem
from aiogram.utils.keyboard import InlineKeyboardBuilder 
from sqlalchemy.orm import joinedload
from database.tables import *
sabad_router = Router()







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

        # Поиск модели продукта
        product_model = globals().get(category.capitalize())
        if not product_model:
            await call.answer("Категория ёфт нашуд!", show_alert=True)
            return

        # Поиск продукта
        result = await session.execute(select(product_model).filter(product_model.id == product_id))
        product = result.scalars().first()
        if not product:
            await call.answer("Маҳсулот ёфт нашуд!", show_alert=True)
            return

        # Иловаи маҳсулот ба сабад
        await cart.add_item(session, category, product_id)

        # Эҷоди клавиатураи нав
        result = await session.execute(
            select(CartItem).where(
                CartItem.cart_id == cart.id,
                CartItem.product_type == category,
                CartItem.product_id == product_id
            )
        )
        cart_item = result.scalars().first()
        if cart_item:
            keyboard = await get_keyboard(cart_item)
    
            # Тағир додани reply_markup
            await call.message.edit_reply_markup(reply_markup=keyboard)
        else:
            await call.answer("Иловаи маҳсулот ба сабад номуваффақ буд.", show_alert=True)


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

        await cart.add_item(session, category, product_id, quantity=1)
        await session.commit()

        # Ҷустуҷӯи cart_item бо истифодаи асинхронӣ
        async with session.begin():
            result = await session.execute(
            select(CartItem).where(CartItem.product_type == category, CartItem.product_id == product_id)
        )
            cart_item = result.scalars().first()  # Истифодаи first ба ҷои next

        if cart_item:
            keyboard = await get_keyboard(cart_item)
            await call.message.edit_reply_markup(reply_markup=keyboard)
        else:
            await call.answer("Маҳсулоти дархостшуда ёфт нашуд!", show_alert=True)


@sabad_router.callback_query(lambda call: call.data.startswith("decrease_"))
async def decrease_quantity(call: types.CallbackQuery):
    """Уменьшение количества продукта."""
    data = call.data.split("_")
    category, product_id = data[1], int(data[2])

    async with SessionLocal() as session:
        user_id = call.from_user.id

        # Поиск корзины пользователя
        result = await session.execute(select(Cart).filter(Cart.user_id == user_id))
        cart = result.scalars().first()
        if not cart:
            await call.answer("Корзина холӣ аст!", show_alert=True)
            return

        # Поиск товара в корзине
        result = await session.execute(
            select(CartItem).filter(
                CartItem.cart_id == cart.id,
                CartItem.product_type == category,
                CartItem.product_id == product_id
            )
        )
        cart_item = result.scalars().first()
        if not cart_item:
            await call.answer("Маҳсулот дар сабад нест!", show_alert=True)
            return

        # Уменьшение количества или удаление товара
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            await session.commit()

            # Обновление клавиатуры для измененного товара
            await call.message.edit_reply_markup(reply_markup=await get_keyboard(cart_item))
        else:
            # Удаление товара
            session.delete(cart_item)
            await session.commit()

            # Если товара нет, показать кнопку "Харид"
            await call.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="Харид", callback_data=f"buy_{category}_{product_id}")
                ]
            ]))

 
# Функсия барои гирифтани маълумоти сабад
async def get_cart_items(user_id: int):
    async with SessionLocal() as session:
        result = await session.execute(
            select(Cart)
            .filter(Cart.user_id == user_id, Cart.status == OrderStatus.PENDING)
            .options(joinedload(Cart.items))  # Пешакӣ бор кардани муносибатҳо
        )
        cart = result.scalars().first()
        return cart

# Хандлер барои фармони /cart
@sabad_router.message(Command("cart"))
async def show_cart(message: types.Message):
    user_id = message.from_user.id
    cart = await get_cart_items(user_id)

    if not cart or not cart.items:
        await message.answer("Сабади шумо холӣ аст.")
        return

    # Пешсаҳифа барои маҳсулоти сабад
    current_index = 0
    item = cart.items[current_index]
    product_model = globals().get(item.product_type.capitalize())

    if not product_model:
        await message.answer("Модели маҳсулот ёфт нашуд.")
        return

    async with SessionLocal() as session:
        result = await session.execute(select(product_model).filter(product_model.id == item.product_id))
        product = result.scalars().first()

        if not product:
            await message.answer("Маҳсулот ёфт нашуд.")
            return

        # Маълумоти маҳсулот
        name = product.name
        description = product.description
        price = product.price
        quantity = item.quantity
        total_price = price * quantity

        # Сохтани клавиатура
        keyboard = InlineKeyboardBuilder()
        keyboard.row(
            InlineKeyboardButton(text="❌", callback_data=f"sabad:remove_{item.product_type}_{item.product_id}"),
            InlineKeyboardButton(text="➖", callback_data=f"sabad:decrease_{item.product_type}_{item.product_id}"),
            InlineKeyboardButton(text=f"{quantity}", callback_data="noop"),
            InlineKeyboardButton(text="➕", callback_data=f"sabad:increase_{item.product_type}_{item.product_id}"),
        )
        keyboard.row(
            InlineKeyboardButton(text="⬅️", callback_data=f"sabad:prev_{current_index}"),
            InlineKeyboardButton(
                text=f"{current_index + 1}/{len(cart.items)}", callback_data="noop"
            ),
            InlineKeyboardButton(text="➡️", callback_data=f"sabad:next_{current_index}"),
        )
        keyboard.row(
            InlineKeyboardButton(text=f"🛒 Аформит заказ на {await cart.get_total_price(session)} сомонӣ", callback_data="checkout"),
        )
        keyboard.row(
            InlineKeyboardButton(text="🔄 Продолжить покупки", callback_data="continue_shopping"),
        )

        # Ирсоли паём
        photo = product.image_url
        text = (
            f"{name}\n\n"
            f"{description}\n\n"
            f"Нарх: {price} x {quantity} = {total_price} сомонӣ"
        )
        await message.answer_photo(photo=photo, caption=text, reply_markup=keyboard.as_markup())

@sabad_router.callback_query(lambda c: c.data.startswith("sabad:"))
async def handle_cart_callbacks(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    cart = await get_cart_items(user_id)

    if not cart or not cart.items:
        await callback_query.answer("Сабади шумо холӣ аст.", show_alert=True)
        return

    data = callback_query.data.split(":")[1]
    parts = data.split("_")
    action = parts[0]

    if action in ["prev", "next"]:
        current_index = int(parts[1])
    else:
        product_type = parts[1]
        product_id = int(parts[2])

        # Ҷустуҷӯи маҳсулот
        item = None
        for i in cart.items:
            if i.product_type == product_type and i.product_id == product_id:
                item = i
                break
        if not item:
            await callback_query.answer("Маҳсулот ёфт нашуд.", show_alert=True)
            return
        current_index = cart.items.index(item)

    # Амалиёт дар асоси `action`
    if action == "increase":
        cart.items[current_index].quantity += 1
    elif action == "decrease" and cart.items[current_index].quantity > 1:
        cart.items[current_index].quantity -= 1
    elif action == "remove":
        async with SessionLocal() as session:
            await cart.remove_item(session, product_type, product_id)
        await callback_query.message.delete()
        await callback_query.answer("Маҳсулот аз сабад хориҷ шуд.", show_alert=True)
        return
    elif action == "prev":
        current_index = (current_index - 1) % len(cart.items)
    elif action == "next":
        current_index = (current_index + 1) % len(cart.items)

    # Маҳсулоти ҷорӣ
    item = cart.items[current_index]
    product_model = globals().get(item.product_type.capitalize())
    if not product_model:
        await callback_query.answer("Модели маҳсулот ёфт нашуд.", show_alert=True)
        return

    async with SessionLocal() as session:
        result = await session.execute(select(product_model).filter(product_model.id == item.product_id))
        product = result.scalars().first()
        if not product:
            await callback_query.answer("Маҳсулот ёфт нашуд.", show_alert=True)
            return

    # Навсозии маълумоти маҳсулот
    quantity = item.quantity
    total_price = product.price * quantity
    name = product.name
    description = product.description

    # Сохтани клавиатураи нав
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(text="❌", callback_data=f"sabad:remove_{item.product_type}_{item.product_id}"),
        InlineKeyboardButton(text="➖", callback_data=f"sabad:decrease_{item.product_type}_{item.product_id}"),
        InlineKeyboardButton(text=f"{quantity}", callback_data="noop"),
        InlineKeyboardButton(text="➕", callback_data=f"sabad:increase_{item.product_type}_{item.product_id}"),
    )
    keyboard.row(
        InlineKeyboardButton(text="⬅️", callback_data=f"sabad:prev_{current_index}"),
        InlineKeyboardButton(
            text=f"{current_index + 1}/{len(cart.items)}", callback_data="noop"
        ),
        InlineKeyboardButton(text="➡️", callback_data=f"sabad:next_{current_index}"),
    )
    keyboard.row(
        InlineKeyboardButton(text=f"🛒 Аформит заказ на {await cart.get_total_price(session)} сомонӣ", callback_data="checkout"),
    )
    keyboard.row(
        InlineKeyboardButton(text="🔄 Продолжить покупки", callback_data="continue_shopping"),
    )

    # Навсозии паём
    new_caption = (
        f"{name}\n\n"
        f"{description}\n\n"
        f"Нарх: {product.price} x {quantity} = {total_price} сомонӣ"
    )

    if callback_query.message.caption != new_caption:
        await callback_query.message.edit_caption(caption=new_caption, reply_markup=keyboard.as_markup())

    # Коммит кардани тағирот
    async with SessionLocal() as session:
        await session.commit()
