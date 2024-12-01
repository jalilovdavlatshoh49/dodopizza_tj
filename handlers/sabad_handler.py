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

        # Проверка элемента в корзине
        result = await session.execute(
            select(CartItem).where(
                CartItem.cart_id == cart.id, 
                CartItem.product_type == category, 
                CartItem.product_id == product_id
            )
        )
        cart_item = result.scalars().first()

        if cart_item:
            # Элемент уже в корзине, просто обновляем клавиатуру
            keyboard = await get_keyboard(cart_item)
            await call.message.edit_reply_markup(reply_markup=keyboard)
        else:
            # Если элемента в корзине нет, выводим предупреждение
            await call.answer("Ин маҳсулот дар сабад нест. Лутфан онро илова кунед.", show_alert=True)


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
    session = SessionLocal()
    user_id = message.from_user.id
    cart = await get_cart_items(user_id)
    if not cart or not cart.items:
        await message.answer("Сабади шумо холӣ аст.")
        return

    # Пешсаҳифа барои маҳсулоти сабад
    current_index = 0
    item = cart.items[current_index]
    product_model = globals().get(item.product_type.capitalize())
    result = await session.execute(select(product_model).filter(product_model.id == item.product_id))
    product = result.scalars().first()

    # Маълумоти маҳсулот
    name = product.name
    description = product.description
    price = product.price
    quantity = item.quantity
    total_price = price * quantity

    # Сохтани клавиатура
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(text="❌", callback_data=f"sabad:remove_{item.id}"),
        InlineKeyboardButton(text="➖", callback_data=f"sabad:decrease_{item.id}"),
        InlineKeyboardButton(text=f"{quantity}", callback_data="noop"),
        InlineKeyboardButton(text="➕", callback_data=f"sabad:increase_{item.id}"),
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
    photo = product.image_url  # URL расми маҳсулот
    text = (
        f"{name}\n\n"
        f"{description}\n\n"
        f"Нарх: {price} x {quantity} = {total_price} сомонӣ"
    )
    await message.answer_photo(photo=photo, caption=text, reply_markup=keyboard.as_markup())

# Хандлер барои callback-и клавиатура
@sabad_router.callback_query()
async def handle_callback(call: types.CallbackQuery):
    session = SessionLocal()
    data = call.data
    if data.startswith("sabad:remove_"):
        item_id = int(data.split("_")[1])
        # Нест кардани маҳсулот
        await remove_item_from_cart(item_id)
        await call.answer("Маҳсулот нест карда шуд.")
        await show_cart(call.message)
    elif data.startswith("sabad:decrease_"):
        item_id = int(data.split("_")[1])
        # Кам кардани миқдор
        await decrease_item_quantity(item_id)
        
        await show_cart(call.message)
    elif data.startswith("sabad:increase_"):
        item_id = int(data.split("_")[1])
        # Афзудани миқдор
        await increase_item_quantity(item_id)
        
        await show_cart(call.message)
    elif data.startswith("sabad:prev_") or data.startswith("next_"):
        # Паймоиш байни маҳсулотҳо
        current_index = int(data.split("_")[1])
        new_index = (current_index - 1) if data.startswith("prev_") else (current_index + 1)
        await show_cart(call.message, new_index)
    elif data == "checkout":
        await call.answer("Шумо фармоиши худро аформит кардед!")
    elif data == "continue_shopping":
        await call.answer("Шумо метавонед хариди худро идома диҳед!")

# Функсияҳо барои тағйир додани сабад
async def remove_item_from_cart(item_id: int):
    session = SessionLocal()
    result = await session.execute(select(CartItem).filter(CartItem.id == item_id))
    item = result.scalars().first()
    if item:
        await session.delete(item)
        await session.commit()

async def decrease_item_quantity(item_id: int):
    session = SessionLocal()
    result = await session.execute(select(CartItem).filter(CartItem.id == item_id))
    item = result.scalars().first()
    if item and item.quantity > 1:
        item.quantity -= 1
        await session.commit()

async def increase_item_quantity(item_id: int):
    session = SessionLocal()
    result = await session.execute(select(CartItem).filter(CartItem.id == item_id))
    item = result.scalars().first()
    if item:
        item.quantity += 1
        await session.commit()
