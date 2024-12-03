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

 
# Функсияҳо барои кор бо сабад
async def get_user_cart(user_id: int):
    """Сабади корбарро бо маводҳояш мегирад."""
    async with SessionLocal() as session:
        result = await session.execute(
            select(Cart)
            .filter(Cart.user_id == user_id, Cart.status == OrderStatus.PENDING)
            .options(joinedload(Cart.items))
        )
        return result.scalars().first()


async def get_product_by_id(product_model, product_id):
    """Маҳсулотро бо ID аз базаи додаҳо мегирад."""
    async with SessionLocal() as session:
        result = await session.execute(
            select(product_model).filter(product_model.id == product_id)
        )
        return result.scalars().first()


def create_cart_keyboard(cart, current_index, item, total_price):
    """Клавиатура барои маҳсулоти сабад месозад."""
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(
            text="❌", callback_data=f"sabad:remove_{item.product_type}_{item.product_id}"
        ),
        InlineKeyboardButton(
            text="➖", callback_data=f"sabad:decrease_{item.product_type}_{item.product_id}"
        ),
        InlineKeyboardButton(text=f"{item.quantity}", callback_data="noop"),
        InlineKeyboardButton(
            text="➕", callback_data=f"sabad:increase_{item.product_type}_{item.product_id}"
        ),
    )
    keyboard.row(
        InlineKeyboardButton(
            text="⬅️", callback_data=f"sabad:prev_{current_index}"
        ),
        InlineKeyboardButton(
            text=f"{current_index + 1}/{len(cart.items)}", callback_data="noop"
        ),
        InlineKeyboardButton(
            text="➡️", callback_data=f"sabad:next_{current_index}"
        ),
    )
    keyboard.row(
        InlineKeyboardButton(
            text=f"🛒 Аформит заказ на {total_price} сомонӣ", callback_data="checkout"
        ),
    )
    keyboard.row(
        InlineKeyboardButton(text="🔄 Продолжить покупки", callback_data="continue_shopping"),
    )
    return keyboard


async def send_cart_item_details(message, product, item, current_index, cart):
    """Маълумоти маҳсулотро ба корбар мефиристад."""
    name = product.name
    description = product.description
    price = product.price
    quantity = item.quantity
    total_price = price * quantity

    keyboard = create_cart_keyboard(cart, current_index, item, total_price)

    text = (
        f"{name}\n\n"
        f"{description}\n\n"
        f"Нарх: {price} x {quantity} = {total_price} сомонӣ"
    )
    await message.answer_photo(
        photo=product.image_url, caption=text, reply_markup=keyboard.as_markup()
    )


# Хандлерҳо
@sabad_router.message(Command("cart"))
async def show_cart(message: types.Message):
    """Намоиши сабад ба корбар."""
    user_id = message.from_user.id
    cart = await get_user_cart(user_id)

    if not cart or not cart.items:
        await message.answer("Сабади шумо холӣ аст.")
        return

    current_index = 0
    item = cart.items[current_index]
    product_model = globals().get(item.product_type.capitalize())

    if not product_model:
        await message.answer("Модели маҳсулот ёфт нашуд.")
        return

    product = await get_product_by_id(product_model, item.product_id)
    if not product:
        await message.answer("Маҳсулот ёфт нашуд.")
        return

    await send_cart_item_details(message, product, item, current_index, cart)



@sabad_router.callback_query(lambda c: c.data.startswith('sabad:increase_'))
async def increase_quantity(callback_query: CallbackQuery):
    """Миқдори маҳсулотро зиёд мекунад."""
    _, product_type, product_id = callback_query.data.split("_")
    product_id = int(product_id)
    user_id = callback_query.from_user.id

    async with SessionLocal() as session:
        # Retrieve the cart
        cart_result = await session.execute(select(Cart).where(Cart.user_id == user_id))
        cart = cart_result.scalars().first()

        if not cart:
            await callback_query.answer("Сабади шумо холӣ аст!", show_alert=True)
            return

        # Retrieve the cart item
        item_result = await session.execute(
            select(CartItem).where(
                CartItem.cart_id == cart.id,
                CartItem.product_type == product_type,
                CartItem.product_id == product_id
            )
        )
        item = item_result.scalars().first()

        if not item:
            await callback_query.answer("Маҳсулот дар сабад нест!", show_alert=True)
            return

        # Increase quantity
        item.quantity += 1
        await session.commit()

        # Fetch updated cart
        updated_cart_result = await session.execute(select(Cart).where(Cart.user_id == user_id))
        updated_cart = updated_cart_result.scalars().first()

        if updated_cart and updated_cart.items:
            total_price = await updated_cart.get_total_price(session)
            current_index = next(
                (i for i, itm in enumerate(updated_cart.items) if itm.product_id == product_id), 0
            )
            keyboard = create_cart_keyboard(updated_cart, current_index, updated_cart.items[current_index], total_price)
            await callback_query.message.edit_reply_markup(reply_markup=keyboard.as_markup())
        else:
            # If cart is empty, show a default message
            await callback_query.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Сабад холӣ аст!", callback_data="empty_cart")]
            ]))
    await callback_query.answer("Миқдор зиёд карда шуд!")




@sabad_router.callback_query(lambda c: c.data.startswith('sabad:decrease_'))
async def decrease_quantity(callback_query: CallbackQuery):
    _, product_type, product_id = callback_query.data.split("_")
    product_id = int(product_id)
    user_id = callback_query.from_user.id

    async with SessionLocal() as session:
        # Retrieve the user's cart
        cart_result = await session.execute(select(Cart).where(Cart.user_id == user_id))
        cart = cart_result.scalars().first()

        if not cart:
            await callback_query.answer("Сабади шумо холӣ аст!", show_alert=True)
            return

        # Retrieve the specific cart item
        item_result = await session.execute(
            select(CartItem).where(
                CartItem.cart_id == cart.id,
                CartItem.product_type == product_type,
                CartItem.product_id == product_id
            )
        )
        item = item_result.scalars().first()

        if not item:
            await callback_query.answer("Маҳсулот дар сабад нест!", show_alert=True)
            return

        # Decrease the quantity or remove the item
        try:
            if item.quantity > 1:
                item.quantity -= 1
                await session.commit()
                message = "Миқдори маҳсулот кам карда шуд!"
            else:
                await session.delete(item)
                await session.commit()
                message = "Маҳсулот аз сабад хориҷ карда шуд!"
        except Exception as e:
            await callback_query.answer("Хатогӣ ҳангоми таҷдид: {}".format(str(e)), show_alert=True)
            return

        # Fetch updated cart and refresh the UI
        updated_cart_result = await session.execute(select(Cart).where(Cart.user_id == user_id))
        updated_cart = updated_cart_result.scalars().first()

        if updated_cart and updated_cart.items:
            total_price = await updated_cart.get_total_price(session)
            current_index = next(
                (i for i, itm in enumerate(updated_cart.items) if itm.product_id == product_id), 0
            )
            keyboard = create_cart_keyboard(updated_cart, current_index, updated_cart.items[current_index], total_price)
            await callback_query.message.edit_reply_markup(reply_markup=keyboard.as_markup())
        else:
            # If cart is empty, show a "cart is empty" message
            await callback_query.message.edit_text(
                text="Сабади шумо холӣ аст!",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Ба мағоза баргардед", callback_data="return_to_shop")]
                ])
            )

    # Respond to the callback
    await callback_query.answer(message)

        