from aiogram import Router, types, F
from sqlalchemy.ext.asyncio import AsyncSession
from functions.all_func import get_category_keyboard, get_cart_items, get_order_history, get_user_info
from aiogram.types import InputMediaPhoto
from database.db import SessionLocal
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from sqlalchemy.future import select
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


async def save_address_and_finish(message: types.Message, state: FSMContext, session: AsyncSession, address: str):
    user_id = message.from_user.id
    user_data = await state.get_data()
    
    # Сабт кардани маълумот ба база
    new_order = Order(
        cart=None,  # Агар cart лозим бошад, муаян кунед
        customer_name=user_data.get("customer_name"),
        phone_number=user_data.get("phone_number"),
        user_id=user_id,
        address=address
    )
    session.add(new_order)
    async with session.begin():
        await session.commit()

    await state.clear()
    await message.answer("Маълумот бо муваффақият сабт шуд.", reply_markup=main_keyboard)

# Клавиатураи интихоб барои иваз кардани суроға
address_edit_method_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Иваз кардани суроға (дастӣ)")],
        [KeyboardButton(text="Иваз кардани суроға (бо харита)", request_location=True)],
        [KeyboardButton(text="Бозгашт")]
    ],
    resize_keyboard=True
)

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






@reply_router.message(F.text == "Маълумотҳои шахсии ман")
async def show_user_data(message: types.Message, state: FSMContext, session: AsyncSession):
    user_id = message.from_user.id

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
        # Агар маълумот набошад, аз корбар хоҳиш кардани маълумот
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

@reply_router.message(UserDataStates.input_address_manual)
async def input_manual_address_handler(message: types.Message, state: FSMContext, session: AsyncSession):
    await save_address_and_finish(
        message=message, 
        state=state, 
        session=session, 
        address=message.text
    )

@reply_router.message(UserDataStates.choose_address_method, content_types=types.ContentType.LOCATION)
async def input_location_address_handler(message: types.Message, state: FSMContext, session: AsyncSession):
    location = message.location
    address = f"Latitude: {location.latitude}, Longitude: {location.longitude}"
    await save_address_and_finish(
        message=message, 
        state=state, 
        session=session, 
        address=address
    )



@reply_router.message(F.text == "Иваз кардан")
async def start_edit_user_data(message: types.Message, state: FSMContext):
    await state.set_state(UserDataStates.edit_data)
    await message.answer(
        "Лутфан интихоб кунед, кадом маълумотро иваз кардан мехоҳед:", 
        reply_markup=edit_options_keyboard
    )

@reply_router.message(UserDataStates.edit_data, F.text == "Иваз кардани ном")
async def edit_name_start(message: types.Message, state: FSMContext):
    await state.set_state(UserDataStates.input_name)
    await message.answer("Лутфан номи нави худро ворид кунед:")

@reply_router.message(UserDataStates.input_name)
async def edit_name(message: types.Message, state: FSMContext, session: AsyncSession):
    new_name = message.text
    user_id = message.from_user.id

    # Маълумотро дар база навсозӣ кардан
    result = await session.execute(select(Order).filter(Order.user_id == user_id))
    user_order = result.scalars().first()

    if user_order:
        user_order.customer_name = new_name
        async with session.begin():
            await session.commit()

        await state.clear()
        await message.answer("Ном бо муваффақият иваз шуд.", reply_markup=main_keyboard)
    else:
        await message.answer("Хатогӣ: маълумот пайдо нашуд.")

@reply_router.message(UserDataStates.edit_data, F.text == "Иваз кардани рақами телефон")
async def edit_phone_start(message: types.Message, state: FSMContext):
    await state.set_state(UserDataStates.input_phone)
    await message.answer("Лутфан рақами телефони нави худро ворид кунед:")

@reply_router.message(UserDataStates.input_phone)
async def edit_phone(message: types.Message, state: FSMContext, session: AsyncSession):
    new_phone = message.text
    user_id = message.from_user.id

    # Маълумотро дар база навсозӣ кардан
    result = await session.execute(select(Order).filter(Order.user_id == user_id))
    user_order = result.scalars().first()

    if user_order:
        user_order.phone_number = new_phone
        async with session.begin():
            await session.commit()

        await state.clear()
        await message.answer("Рақами телефон бо муваффақият иваз шуд.", reply_markup=main_keyboard)
    else:
        await message.answer("Хатогӣ: маълумот пайдо нашуд.")

@reply_router.message(UserDataStates.edit_data, F.text == "Иваз кардани суроға")
async def edit_address_start(message: types.Message, state: FSMContext):
    await state.set_state(UserDataStates.choose_address_method)
    await message.answer(
        "Лутфан тарзи иваз кардани суроғаи худро интихоб кунед:", 
        reply_markup=address_edit_method_keyboard
    )

@reply_router.message(UserDataStates.choose_address_method, F.text == "Иваз кардани суроға (дастӣ)")
async def edit_address_manual_start(message: types.Message, state: FSMContext):
    await state.set_state(UserDataStates.input_address_manual)
    await message.answer("Лутфан суроғаи нави худро ворид кунед:")

@reply_router.message(UserDataStates.input_address_manual)
async def edit_address_manual(message: types.Message, state: FSMContext, session: AsyncSession):
    new_address = message.text
    user_id = message.from_user.id

    # Маълумотро дар база навсозӣ кардан
    result = await session.execute(select(Order).filter(Order.user_id == user_id))
    user_order = result.scalars().first()

    if user_order:
        user_order.address = new_address
        async with session.begin():
            await session.commit()

        await state.clear()
        await message.answer("Суроға бо муваффақият иваз шуд.", reply_markup=main_keyboard)
    else:
        await message.answer("Хатогӣ: маълумот пайдо нашуд.")

@reply_router.message(UserDataStates.choose_address_method, content_types=types.ContentType.LOCATION)
async def edit_address_location(message: types.Message, state: FSMContext, session: AsyncSession):
    location = message.location
    new_address = f"Latitude: {location.latitude}, Longitude: {location.longitude}"
    user_id = message.from_user.id

    # Маълумотро дар база навсозӣ кардан
    result = await session.execute(select(Order).filter(Order.user_id == user_id))
    user_order = result.scalars().first()

    if user_order:
        user_order.address = new_address
        async with session.begin():
            await session.commit()

        await state.clear()
        await message.answer("Суроға бо муваффақият иваз шуд.", reply_markup=main_keyboard)
    else:
        await message.answer("Хатогӣ: маълумот пайдо нашуд.")



@reply_router.message(F.text == "Нест кардан")
async def delete_user_data(message: types.Message, state: FSMContext, session: AsyncSession):
    user_id = message.from_user.id

    # Маълумотро нест кардан
    result = await session.execute(select(Order).filter(Order.user_id == user_id))
    user_order = result.scalars().first()

    if user_order:
        async with session.begin():
            await session.delete(user_order)
            await session.commit()

        await state.clear()
        await message.answer("Маълумот бо муваффақият нест карда шуд.", reply_markup=main_keyboard)
    else:
        await message.answer("Маълумот пайдо нашуд.")

@reply_router.message(F.text == "Бозгашт")
async def go_back(message: types.Message, state: FSMContext):
    await state.clear()
    keyboard = await get_category_keyboard()
    await message.answer("Бозгашт ба менюи асосӣ.", reply_markup=keyboard)




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