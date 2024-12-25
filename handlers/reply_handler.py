from aiogram import Router, types, F
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from functions.all_func import get_category_keyboard, get_cart_items, get_order_history, get_user_info
from aiogram.types import InputMediaPhoto
from database.db import SessionLocal, Order, Cart
from handlers.menu_handler import get_custom_menu_keyboard
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)

reply_router = Router()



# FSM States
class UserDataStates(StatesGroup):
    input_name = State()
    input_phone = State()
    choose_address_method = State()
    input_address_manual = State()
    input_address_location = State()
    after_pressing_which_key = State()



class EditUserDataStates(StatesGroup):
    edit_data = State()
    input_name = State()
    input_phone = State()
    choose_address_method = State()
    input_address_manual = State()
    input_address_map = State()


async def save_address_and_finish(message: types.Message, state: FSMContext, session: AsyncSession, address: str):
    user_id = message.from_user.id
    user_data = await state.get_data()

    # Сабт кардани маълумот ба база
    new_order = Order(
        cart=None,  # Агар cart лозим бошад, муайян кунед
        customer_name=user_data.get("customer_name"),
        phone_number=user_data.get("phone_number"),
        user_id=user_id,
        address=address
    )
    session.add(new_order)
    
    # Ҳамзамон commit() истифода мебарем
    await session.commit()

    # Ҳолати истифодабарандаро тоза мекунем
    await state.clear()
    await message.answer("Маълумот бо муваффақият сабт шуд.", reply_markup=main_keyboard)




# Клавиатураи интихоб барои иваз кардан
edit_options_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Иваз кардани ном")],
        [KeyboardButton(text="Иваз кардани рақами телефон")],
        [KeyboardButton(text="Иваз кардани суроға")],
        [KeyboardButton(text="Бозгашт")],
    ],
    resize_keyboard=True
)

address_method_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Ворид кардани суроға (дастӣ)")],
        [KeyboardButton(text="Интихоби ҷойгиршавӣ (харита)", request_location=True)],
    ],
    resize_keyboard=True
)

# Клавиатураи асосӣ
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Маълумотҳои шахсии ман")],
    ],
    resize_keyboard=True
)

# Клавиатура барои таҳрир/нест кардан
edit_delete_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Иваз кардан"), KeyboardButton(text="Нест кардан")],
        [KeyboardButton(text="Бозгашт")]
    ],
    resize_keyboard=True
)


# Handle "Меню" button to show category keyboard
@reply_router.message(F.text == "Категорияҳо")
async def menu_handler(message: types.Message):
    keyboard = await get_category_keyboard()
    await message.answer("Категорияҳоро интихоб кунед:", reply_markup=keyboard)



# Функсия барои ирсоли фармоиш ба администратор
async def send_order_to_admin(order, admin_id: int, message):
    """Ирсоли фармоиш ба администратор."""
    products_info = [
        f"Маҳсулот: {item.product_type}\n"
        f"ID: {item.product_id}\n"
        f"Миқдор: {item.quantity}"
        for item in order.cart.items
    ]

    order_message = (
        f"Фармоиши нав аз {order.customer_name} ({order.phone_number}):\n"
        f"Нишонӣ: {order.address if order.address else 'Нишонӣ дастрас нест'}\n\n" +
        "\n\n".join(products_info)
    )
    
    # Ирсоли паём ва координатаҳо ё нишонӣ
    if order.latitude and order.longitude:
        await message.bot.send_message(admin_id, order_message)
        await message.bot.send_location(admin_id, latitude=order.latitude, longitude=order.longitude)
    else:
        await message.bot.send_message(admin_id, order_message)


@reply_router.callback_query(lambda c: c.data == "checkout")
async def handle_checkout(callback_query, state):
    user_id = callback_query.from_user.id

    async with SessionLocal() as session:
        # Ҷустуҷӯи сабади истифодабаранда
        result = await session.execute(
            select(Cart)
            .filter(Cart.user_id == user_id)
            .filter(Cart.order == None)
            .options(joinedload(Cart.items))
        )
        cart = result.scalars().first()

        if not cart:
            await callback_query.message.reply("Сабади шумо холӣ аст!")
            return

        # Ҷустуҷӯи фармоиши пешина
        result = await session.execute(
            select(Order).filter(Order.user_id == user_id)
        )
        existing_order = result.scalars().first()

        # Агар маълумоти зарурӣ вуҷуд надошта бошад
        if not existing_order or not all(
            [existing_order.customer_name, existing_order.phone_number]
        ):
            await state.update_data(after_pressing_which_key="offer_order")
            await state.set_state(UserDataStates.input_name)
            await callback_query.message.answer("Лутфан номи худро ворид кунед:")
            return

        # Ҳисоб кардани нархи умумӣ
        total_price = await cart.get_total_price(session)

        # Ташкили фармоиш
        new_order = Order(
            user_id=user_id,
            cart=cart,
            total_price=total_price,
        )
        session.add(new_order)
        await session.commit()
        await session.refresh(new_order)

        # Санҷиши фармоиши нав
        result_new_order = await session.execute(
            select(Order)
            .filter(Order.user_id == user_id)
            .order_by(Order.id.desc())
        )
        existing_new_order = result_new_order.scalars().first()

        if not existing_new_order:
            await callback_query.message.reply("Хатогӣ: Фармоиш аз пойгоҳи додаҳо ёфт нашуд!")
            return

        # Ирсоли фармоиш ба администратор
        admin_id = user_id  # ID-и администраторро дар инҷо таъин кунед
        await send_order_to_admin(existing_new_order, admin_id, callback_query.message)

        # Ҷавоб ба истифодабаранда
        await callback_query.message.reply(
            f"Фармоиш ба маблағи {total_price} ба админ ирсол карда шуд. Ҷавоби админро интизор шавед."
        )



@reply_router.message(F.text == "Маълумотҳои шахсии ман")
async def show_user_data(message: types.Message, state: FSMContext):
    user_id = message.from_user.id

    # Сессияи дастӣ
    async with SessionLocal() as session:
        result = await session.execute(select(Order).filter(Order.user_id == user_id))
        user_data = result.scalars().first()

        if user_data:
            # Агар ҷойгиршавӣ тавассути харита бошад
            if user_data.latitude and user_data.longitude:
                # Фиристодани харитаи ҷойгиршавӣ
                await message.answer("Суроғаи шумо:")
                await message.bot.send_location(
                    chat_id=message.chat.id,
                    latitude=user_data.latitude,
                    longitude=user_data.longitude,
                )
            else:
                # Агар ҷойгиршавӣ бо дасти ворид шуда бошад
                address_text = f"Суроғаи бо дасти воридшуда: {user_data.address or 'Номаълум'}"
                await message.answer(address_text)

            # Фиристодани маълумоти шахсӣ
            text = (
                f"Ном: {user_data.customer_name}\n"
                f"Рақами телефон: {user_data.phone_number}\n"
            )
            await message.answer(text, reply_markup=edit_delete_keyboard)

        else:
            await state.set_state(UserDataStates.after_presing_which_key)
            await state.update_data(after_pressing_which_key="registration_key")
            # Агар маълумот вуҷуд надошта бошад
            await state.set_state(UserDataStates.input_name)
            await message.answer("Лутфан номи худро ворид кунед:")


@reply_router.message(UserDataStates.input_name)
async def input_name_handler(message: types.Message, state: FSMContext):
    await state.update_data(customer_name=message.text)
    await state.set_state(UserDataStates.input_phone)
    await message.answer("Лутфан рақами телефони худро ворид кунед:")

@reply_router.message(UserDataStates.input_phone)
async def input_phone_handler(message: types.Message, state: FSMContext):
    await state.update_data(phone_number=message.text)
    await state.set_state(UserDataStates.choose_address_method)
    await message.answer(
        "Лутфан тарзи ворид кардани суроғаи худро интихоб кунед:", 
        reply_markup=address_method_keyboard
    )

@reply_router.message(UserDataStates.choose_address_method, F.text == "Ворид кардани суроға (дастӣ)")
async def choose_manual_address(message: types.Message, state: FSMContext):
    await state.set_state(UserDataStates.input_address_manual)
    await message.answer(
        "Лутфан суроғаи худро ворид кунед:",
        reply_markup=ReplyKeyboardRemove()
    )


# Handler for manual address input
@reply_router.message(UserDataStates.input_address_manual)
async def input_manual_address_handler(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_data = await state.get_data()
    after_pressing_which_key = user_data.get("after_pressing_which_key")

    async with SessionLocal() as session:
        # Сабти маълумот ба база
        await save_address_and_finish(
            message=message, 
            state=state, 
            session=session, 
            address=message.text
        )

        # Ҷустуҷӯи маълумотҳои корбар
        result = await session.execute(select(Order).filter(Order.user_id == user_id))
        user_data = result.scalars().first()

        if user_data:
            text = (
                f"Ном: {user_data.customer_name}\n"
                f"Рақами телефон: {user_data.phone_number}\n"
                f"Суроға: {user_data.address or 'Номаълум'}"
            )
            await message.answer(text, reply_markup=edit_delete_keyboard)
        else:
            await message.answer("Хатогӣ рух дод. Лутфан бори дигар кӯшиш кунед.")
    if after_pressing_which_key == "offer_order":
        # Гирифтани фармоиши сабтшуда аз пойгоҳи додаҳо
        result_new_order = await session.execute(select(Order).filter(Order.user_id == user_id).order_by(Order.id.desc())
)
        existing_new_order = result.scalars().first()

        if not existing_new_order:
            await message.reply("Хатогӣ: Фармоиш аз пойгоҳи додаҳо ёфт нашуд!")
            return

        
        # Ирсоли фармоиш ба администратор
        admin_id = user_id  # ID-и администратор
        await send_order_to_admin(existing_new_order, admin_id, message)

        # Ҷавоб ба истифодабаранда
        await message.reply(f"Фармоиш ба маблағи {total_price} ба админ ирсол карда шуд. Ҷавоби админро интизор шавед.")


# Клавиатураи интихоб барои иваз кардани суроға
address_edit_method_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Иваз кардани суроға (дастӣ)")],
        [KeyboardButton(text="Иваз кардани суроға (бо харита)", request_location=True)],
        [KeyboardButton(text="Бозгашт")]
    ],
    resize_keyboard=True
)

async def save_location_data(message: types.Message, state: FSMContext, session: AsyncSession, user_id, latitude, longitude):
    user_id = message.from_user.id
    user_data = await state.get_data()
    
        # Агар Order мавҷуд набошад, Order-и нав месозем
    order = Order(
        cart=None, 
        user_id=user_id,
        latitude=latitude,
        longitude=longitude,
        address=f"Latitude: {latitude}, Longitude: {longitude}",
        customer_name=user_data.get("customer_name"),
        phone_number=user_data.get("phone_number")
        )
    session.add(order)

    # Сабти тағйирот 
    await session.commit()
    
    # Ҳолати истифодабарандаро тоза мекунем
    await state.clear()
    await message.answer("Маълумот бо муваффақият сабт шуд.", reply_markup=main_keyboard)
    

# Handler for location-based address input
@reply_router.message(UserDataStates.choose_address_method)
async def input_location_address_handler(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_data = await state.get_data()
    after_pressing_which_key = user_data.get("after_pressing_which_key")

    # Санҷиши оё корбар ҷойгиршавӣ фиристодааст
    if message.location:
        location = message.location
        address = f"Latitude: {location.latitude}, Longitude: {location.longitude}"

        # Сабт кардани маълумот
        async with SessionLocal() as session:
            success = await save_location_data(
                message=message, 
                state=state, 
                session=session,
                user_id=user_id,
                latitude=location.latitude,
                longitude=location.longitude
            )

            # Ҷустуҷӯи маълумотҳои корбар
            result = await session.execute(select(Order).filter(Order.user_id == user_id))
            user_data = result.scalars().first()

            if user_data:
                await message.answer("Суроғаи шумо:")
                await message.bot.send_location(
                    chat_id=message.chat.id,
                    latitude=user_data.latitude,
                    longitude=user_data.longitude,
                )
                # Фиристодани маълумоти шахсӣ
                text = (
                f"Ном: {user_data.customer_name}\n"
                f"Рақами телефон: {user_data.phone_number}\n"
            )
                await message.answer(text, reply_markup=edit_delete_keyboard)
            else:
                await message.answer("Хатогӣ рух дод. Лутфан бори дигар кӯшиш кунед.")
        
    else:
        # Агар ҷойгиршавӣ фиристода нашавад
        await message.answer("Лутфан ҷойгиршавии худро фиристед.")
        # Ҳолати FSM-и корбарро тоза намекунем, то ӯ боз кӯшиш кунад
    if after_pressing_which_key == "offer_order":
        # Гирифтани фармоиши сабтшуда аз пойгоҳи додаҳо
        result_new_order = await session.execute(
    select(Order).filter(Order.user_id == user_id).order_by(Order.id.desc())
)
        existing_new_order = result.scalars().first()

        if not existing_new_order:
            await message.reply("Хатогӣ: Фармоиш аз пойгоҳи додаҳо ёфт нашуд!")
            return

        # Ирсоли фармоиш ба администратор
        admin_id = user_id  # ID-и администратор
        await send_order_to_admin(existing_new_order, admin_id, message)

        # Ҷавоб ба истифодабаранда
        await message.reply(f"Фармоиш ба маблағи {total_price} ба админ ирсол карда шуд. Ҷавоби админро интизор шавед.")





@reply_router.message(F.text == "Иваз кардан")
async def start_edit_user_data(message: types.Message, state: FSMContext):
    await state.set_state(EditUserDataStates.edit_data)
    await message.answer(
        "Лутфан интихоб кунед, кадом маълумотро иваз кардан мехоҳед:",
        reply_markup=edit_options_keyboard,
    )


@reply_router.message(EditUserDataStates.edit_data, F.text == "Иваз кардани ном")
async def edit_name_start(message: types.Message, state: FSMContext):
    await state.set_state(EditUserDataStates.input_name)
    await message.answer("Лутфан номи нави худро ворид кунед:")


@reply_router.message(EditUserDataStates.input_name)
async def edit_name(message: types.Message, state: FSMContext):
    new_name = message.text
    user_id = message.from_user.id

    async with SessionLocal() as session:
        async with session.begin():  # Транзаксия оғоз мешавад
            result = await session.execute(select(Order).filter(Order.user_id == user_id))
            user_order = result.scalars().first()

            if user_order:
                user_order.customer_name = new_name
                # Бе зарурат session.commit() набояд такрор шавад
                await state.clear()
                await message.answer("Ном бо муваффақият иваз шуд.", reply_markup=main_keyboard)
            else:
                await message.answer("Хатогӣ: маълумот пайдо нашуд.")

@reply_router.message(EditUserDataStates.edit_data, F.text == "Иваз кардани рақами телефон")
async def edit_phone_start(message: types.Message, state: FSMContext):
    await state.set_state(EditUserDataStates.input_phone)
    await message.answer("Лутфан рақами телефони нави худро ворид кунед:")


@reply_router.message(EditUserDataStates.input_phone)
async def edit_phone(message: types.Message, state: FSMContext):
    new_phone = message.text
    user_id = message.from_user.id

    async with SessionLocal() as session:
        async with session.begin():  # Транзаксия дар ин ҷо оғоз мешавад
            result = await session.execute(select(Order).filter(Order.user_id == user_id))
            user_order = result.scalars().first()

            if user_order:
                user_order.phone_number = new_phone
                await session.commit()  # Тағйиротро сабт мекунем
                await state.clear()
                await message.answer("Рақами телефон бо муваффақият иваз шуд.", reply_markup=main_keyboard)
            else:
                await message.answer("Хатогӣ: маълумот пайдо нашуд.")


@reply_router.message(EditUserDataStates.edit_data, F.text == "Иваз кардани суроға")
async def edit_address_start(message: types.Message, state: FSMContext):
    await state.set_state(EditUserDataStates.choose_address_method)
    await message.answer(
        "Лутфан тарзи иваз кардани суроғаи худро интихоб кунед:",
        reply_markup=address_edit_method_keyboard,
    )


@reply_router.message(EditUserDataStates.choose_address_method, F.text == "Иваз кардани суроға (дастӣ)")
async def edit_address_manual_start(message: types.Message, state: FSMContext):
    await state.set_state(EditUserDataStates.input_address_manual)
    await message.answer("Лутфан суроғаи нави худро ворид кунед:")


@reply_router.message(EditUserDataStates.input_address_manual)
async def edit_address_manual(message: types.Message, state: FSMContext):
    new_address = message.text
    user_id = message.from_user.id

    async with SessionLocal() as session:
        async with session.begin():  # Транзаксия оғоз мешавад
            result = await session.execute(select(Order).filter(Order.user_id == user_id))
            user_order = result.scalars().first()

            if user_order:
                user_order.address = new_address

                # Агар latitude ва longitude мавҷуд бошанд, нест кунем
                if hasattr(user_order, 'latitude') and hasattr(user_order, 'longitude'):
                    user_order.latitude = None
                    user_order.longitude = None

                await session.commit()  # Тағйиротро сабт мекунем
                await state.clear()
                await message.answer("Суроға бо муваффақият иваз шуд.", reply_markup=main_keyboard)
            else:
                await message.answer("Хатогӣ: маълумот пайдо нашуд.")





@reply_router.message(EditUserDataStates.choose_address_method)
async def edit_address_map_start(message: types.Message, state: FSMContext):
    await state.set_state(EditUserDataStates.input_address_map)
    
    
    user_id = message.from_user.id

    if message.location:
        location = message.location
        address = f"Latitude: {location.latitude}, Longitude: {location.longitude}"

        async with SessionLocal() as session:
            async with session.begin():
                # Сабти суроға
                result = await session.execute(select(Order).filter(Order.user_id == user_id))
                user_order = result.scalars().first()

                if user_order:
                    user_order.latitude = location.latitude
                    user_order.longitude = location.longitude
                    user_order.address = address
                    await session.commit()

                    await message.answer("Суроға бо муваффақият иваз шуд.", reply_markup=main_keyboard)
                    await state.clear()
                else:
                    await message.answer("Хатогӣ рух дод. Лутфан бори дигар кӯшиш кунед.")
    else:
        await message.answer("Лутфан ҷойгиршавии худро тавассути харита фиристед.")




@reply_router.message(F.text == "Нест кардан")
async def delete_user_data(message: types.Message, state: FSMContext):
    user_id = message.from_user.id

    try:
        async with SessionLocal() as session:
            # Fetch the user's order from the database
            result = await session.execute(select(Order).filter(Order.user_id == user_id))
            user_order = result.scalars().first()

            if user_order:
                # Delete the user's order from the database
                await session.delete(user_order)
                await session.commit()  # Commit the transaction

                # Clear the state and send confirmation message
                await state.clear()
                await message.answer("Маълумот бо муваффақият нест карда шуд.", reply_markup=main_keyboard)
            else:
                await message.answer("Маълумот пайдо нашуд.")
    except Exception as e:
        # Log the error and notify the user
        print(f"Error deleting user data: {e}")
        await message.answer("Хатогӣ рух дод. Лутфан дубора кӯшиш кунед.")

@reply_router.message(F.text == "Бозгашт")
async def go_back(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Бозгашт ба менюи асосӣ.", reply_markup=get_custom_menu_keyboard())




# Handle "Фармоишот" button to show past orders
@reply_router.message(F.text == "Фармоишот")
async def reply_orders_handler(message: types.Message):
    user_id = message.from_user.id

    # Гирифтани таърихи фармоишҳо
    orders = await get_order_history(user_id)
    
    if not orders:
        await message.answer("Шумо ҳоло фармоиш надоред.")
        return

    for order in orders:
        order_text = f"**Ҳолати фармоиш:** {order['status']}\n\n"
        for item in order['items']:
            order_text += (
                f"📦 **Ном:** {item['name']}\n"
                f"🔢 **Миқдор:** {item['quantity']}\n"
                f"💵 **Нарх:** {item['price']} сомонӣ\n"
                f"💰 **Нархи умумӣ:** {item['total_price']} сомонӣ\n\n"
            )
            if item['image_url']:
                await message.answer_photo(photo=item['image_url'], caption=order_text)
            else:
                await message.answer(order_text)
        
        order_text = f"💳 **Нархи умумии фармоиш:** {order['total_order_price']} сомонӣ\n"
    await message.answer(info_text)



# Функсияи кор бо "ℹ️ Маълумотҳои шахсии ман"
@reply_router.message(F.text == "Маълумотҳои шахсии ман")
async def my_info_handler(message: types.Message):
    session = SessionLocal()
    # Дарёфти маълумоти корбар
    user_info = await get_user_info(user_id=message.from_user.id)

    if not user_info:
        # Агар маълумот вуҷуд надошта бошад
        await message.answer("Маълумоти шахсии шумо ёфт нашуд. Лутфан аввал фармоиш диҳед.")
        return

    # Ташкили матни ҷавоб бо маълумотҳо
    info_text = (
        f"Ном: {user_info['name']}\n"
        f"Рақами телефон: {user_info['phone']}\n"
        f"Адрес: {user_info['address']}\n"
        f"Координатаҳо: {user_info['latitude']}, {user_info['longitude']}\n\n"
        "Барои тағйир додани маълумотҳо, тугмаи зерро истифода баред."
    )

    # Эҷоди клавиатура бо тугма
    keyboard = InlineKeyboardMarkup(row_width=1)
    change_button = InlineKeyboardButton(
        text="Тағйир додани маълумотҳо", callback_data="change_user_info"
    )
    keyboard.add(change_button)

    # Фиристодани паём бо клавиатура
    await message.answer(info_text, reply_markup=keyboard)


@reply_router.callback_query(lambda c: c.data == "continue_shopping")
async def continue_shopping_handler(callback_query: types.CallbackQuery):
    keyboard = await get_category_keyboard()
    await callback_query.message.answer("Категорияҳоро интихоб кунед:", reply_markup=keyboard)