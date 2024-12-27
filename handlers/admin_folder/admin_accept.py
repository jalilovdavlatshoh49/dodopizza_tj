from aiogram import Router, types
from sqlalchemy.future import select
from database.tables import OrderStatus  # Ба модели худ истинод кунед
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from database.db import Cart, Order, SessionLocal
from sqlalchemy.orm import joinedload

admin_accept = Router()


# Ҳодиса барои "🏠 Заказҳои расонидашуда"
@admin_accept.message(lambda message: message.text == "🏠 Заказҳои расонидашуда")
async def show_delivered_orders(message: types.Message):
    """
    Ҳамаи заказҳое, ки дар ҳолати "Расонида шудааст" (DELIVERED) қарор доранд, нишон медиҳад.
    """
    session = SessionLocal()
    query = select(Cart).where(Cart.status == OrderStatus.DELIVERED)
    result = await session.execute(query)
    delivered_orders = result.scalars().all()

    if not delivered_orders:
        await message.answer("🏠 Ҳоло ягон заказ расонида нашудааст.")
        return

    response = "📋 Заказҳои расонидашуда:\n\n"
    for order in delivered_orders:
        order_details = f"🆔 ID: {order.id}\n"
        for item in order.items:
            order_details += f"• {item.product_type.capitalize()} (ID: {item.product_id}), Миқдор: {item.quantity}\n"
        order_details += "\n"
        response += order_details

    await message.answer(response)





@admin_accept.message(lambda message: message.text == "🚚 Заказҳои дар роҳ")
async def show_on_road_orders(message: types.Message):
    """
    Ҳамаи заказҳое, ки дар ҳолати "Дар роҳ" (IN_PROGRESS) қарор доранд, нишон медиҳад.
    """
    session = SessionLocal()
    query = select(Cart).where(Cart.status == OrderStatus.IN_PROGRESS)
    result = await session.execute(query)
    in_progress_orders = result.scalars().all()

    if not in_progress_orders:
        await message.answer("📦 Ҳоло ягон заказ дар роҳ нест.")
        return

    response = "📋 Заказҳои дар роҳ:\n\n"
    for order in in_progress_orders:
        order_details = f"🆔 ID: {order.id}\n"
        for item in order.items:
            order_details += f"• {item.product_type.capitalize()} (ID: {item.product_id}), Миқдор: {item.quantity}\n"
        order_details += "\n"
        response += order_details

    await message.answer(response)




ORDERS_PER_PAGE = 5


# Функсияи пахши тугмаи "📋 Заказҳои интизорӣ"
@admin_accept.message(lambda message: message.text == "📋 Заказҳои интизорӣ (қабул нашуда)")
async def show_pending_orders(message: types.Message):
    page = 1  # Саҳифаи аввал
    user_id = message.from_user.id
    await send_orders_page(message, user_id, page)



# Функсия барои фиристодани заказҳои саҳифаи интихобшуда бо маълумотҳои маҳсулот
async def send_orders_page(message, chat_id: int, page: int):
    async with SessionLocal() as session:  # Сессияи пойгоҳи додаҳо
        offset = (page - 1) * ORDERS_PER_PAGE
        result = await session.execute(
            select(Order)
            .where(Order.status == OrderStatus.PENDING)
            .options(joinedload(Order.cart).joinedload(Cart.items))
            .offset(offset)
            .limit(ORDERS_PER_PAGE)
        )
        orders = result.scalars().all()

        if not orders:
            await message.bot.send_message(chat_id, "Ҳеҷ закази интизорӣ нест.")
            return

        # Сохтани клавиатура
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        text = "📋 Заказҳои интизорӣ:\n\n"
        for order in orders:
            text += (
                f"🆔 ID: {order.id}\n"
                f"👤 Муштарӣ: {order.customer_name}\n"
                f"📞 Телефон: {order.phone_number}\n"
                f"📍 Нишонӣ: {order.address if order.address else 'Дастрас нест'}\n"
                f"📦 Маҳсулотҳо:\n"
            )

            # Намоиши маълумотҳои маҳсулот
            if order.cart and order.cart.items:
                for item in order.cart.items:
                    product = await session.get(Product, item.product_id)  # Гирифтани маълумоти маҳсулот
                    product_name = product.name if product else "Номи номаълум"
                    product_type = item.product_type if item.product_type else "Номаълум"
                    text += (
                        f"  - Ном: {product_name}\n"
                        f"    Тип: {product_type}\n"
                        f"    ID: {item.product_id}\n"
                        f"    Миқдор: {item.quantity}\n"
                        f"    Нархи ягона: {item.price} сомонӣ\n"
                        f"    Нархи умумӣ: {item.quantity * item.price} сомонӣ\n\n"
                    )
            else:
                text += "  Маҳсулот вуҷуд надорад.\n\n"

            # Илова кардани тугмаҳо барои ҳар як заказ
            keyboard.inline_keyboard.append([
                InlineKeyboardButton(text="✅ Қабул кардан", callback_data=f"accept_{order.id}"),
                InlineKeyboardButton(text="❌ Рад кардан", callback_data=f"reject_{order.id}")
            ])

        # Тугмаҳои саҳифабандӣ
        navigation_buttons = []
        if page > 1:
            navigation_buttons.append(InlineKeyboardButton(text="⬅️ Пешина", callback_data=f"page_{page-1}"))
        if len(orders) == ORDERS_PER_PAGE:
            navigation_buttons.append(InlineKeyboardButton(text="➡️ Баъдӣ", callback_data=f"page_{page+1}"))

        if navigation_buttons:
            keyboard.inline_keyboard.append(navigation_buttons)

        # Фиристодани паём
        await message.bot.send_message(chat_id, text, reply_markup=keyboard)


# Callback барои қабул ва рад кардани заказ
@admin_accept.callback_query(lambda call: call.data.startswith("accept_") or call.data.startswith("reject_"))
async def handle_order_action(callback_query: types.CallbackQuery):
    action, order_id = callback_query.data.split("_")
    order_id = int(order_id)

    async with SessionLocal() as session:  # Сессияи пойгоҳи додаҳо
        order = await session.get(Order, order_id)

        if not order:
            await callback_query.message.edit_text("Заказ ёфт нашуд.")
            return

        if action == "accept":
            order.status = OrderStatus.ACCEPTED
            await callback_query.message.edit_text(f"Заказ бо ID {order_id} қабул шуд.")
        elif action == "reject":
            order.status = OrderStatus.REJECTED
            await callback_query.message.edit_text(f"Заказ бо ID {order_id} рад шуд.")

        await session.commit()


# Callback барои паймоиш байни саҳифаҳо
@admin_accept.callback_query(lambda call: call.data.startswith("page_"))
async def handle_pagination(callback_query: types.CallbackQuery):
    page = int(callback_query.data.split("_")[1])
    await send_orders_page(callback_query.message.chat.id, page)

@admin_accept.message(lambda message: message.text == "Заказҳои қабулшуда")
async def handle_accepted_orders(message: types.Message):
    async with SessionLocal() as session:
        # Баходир фаҳмидани заказҳое, ки ACCEPTED шудаанд
        query = select(Cart).where(Cart.status == OrderStatus.ACCEPTED)
        result = await session.execute(query)
        accepted_orders = result.scalars().all()

        # Агар ягон заказ набошад
        if not accepted_orders:
            await message.answer("Ҳоло ягон заказ қабул нашудааст.")
            return

        # Генерация кардани рӯйхати заказҳо
        response = "Заказҳои қабулшуда:\n\n"
        for order in accepted_orders:
            order_details = f"ID: {order.id}\n"
            for item in order.items:
                order_details += f"- {item.product_type} (ID: {item.product_id}), Миқдор: {item.quantity}\n"
            order_details += f"Ҳолати умумӣ: ACCEPTED\n\n"
            response += order_details

        await message.answer(response)
