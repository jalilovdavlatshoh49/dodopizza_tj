from aiogram import Router, types
from sqlalchemy.future import select
from database.tables import Cart, OrderStatus  # Ба модели худ истинод кунед
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from database.db import SessionLocal
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


async def show_pending_orders(message: types.Message):
    # Ҳамаи заказҳои интизориро интихоб мекунем
    session = SessionLocal()
    query = select(Cart).where(Cart.status == OrderStatus.PENDING)
    result = await session.execute(query)
    pending_orders = result.scalars().all()

    if not pending_orders:
        await message.answer("Дар ҳоли ҳозир ягон закази интизорӣ вуҷуд надорад.")
        return

    for order in pending_orders:
        text = f"Заказ #{order.id}:\n"
        for item in order.items:
            text += f"- {item.quantity} x {item.product_type.capitalize()} (ID: {item.product_id})\n"
        text += f"\nҲолати заказ: {order.status.value}\n"

        # Тугмаи қабул ё бекор кардани заказ
        keyboard = InlineKeyboardMarkup(row_width=2)
        accept_button = InlineKeyboardButton(text="Қабул", callback_data=f"accept_order_{order.id}")
        decline_button = InlineKeyboardButton(text="Бекор кардан", callback_data=f"decline_order_{order.id}")
        keyboard.add(accept_button, decline_button)

        await message.answer(text, reply_markup=keyboard)


@admin_accept.message(lambda message: message.text == "Заказҳои интизорӣ")
async def handle_pending_orders(message: types.Message):
    async with SessionLocal() as session:
        await show_pending_orders(session, message)
        
@admin_accept.callback_query(lambda c: c.data.startswith("accept_order_"))
async def accept_order(callback_query: types.CallbackQuery):
    order_id = int(callback_query.data.split("_")[-1])

    async with SessionLocal() as session:
        query = select(Cart).where(Cart.id == order_id)
        result = await session.execute(query)
        order = result.scalar_one_or_none()

        if order:
            order.status = OrderStatus.ACCEPTED
            await session.commit()
            await callback_query.message.edit_text(f"Заказ #{order_id} қабул карда шуд.")
        else:
            await callback_query.message.edit_text("Заказ ёфт нашуд.")

@admin_accept.callback_query(lambda c: c.data.startswith("decline_order_"))
async def decline_order(callback_query: types.CallbackQuery):
    order_id = int(callback_query.data.split("_")[-1])

    async with SessionLocal() as session:
        query = select(Cart).where(Cart.id == order_id)
        result = await session.execute(query)
        order = result.scalar_one_or_none()

        if order:
            order.status = OrderStatus.PENDING  # Ё ҳолати дигаре, ки "бекоршуда"-ро ифода мекунад
            await session.commit()
            await callback_query.message.edit_text(f"Заказ #{order_id} бекор карда шуд.")
        else:
            await callback_query.message.edit_text("Заказ ёфт нашуд.")


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
