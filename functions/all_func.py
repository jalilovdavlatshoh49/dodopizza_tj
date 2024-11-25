from aiogram import types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from database.db import Pizza, Combo, Snacks, Sauces, Desserts, Drinks, Kids_Love, OtherGoods
from database.db import SessionLocal
from sqlalchemy.future import select
from database.tables import Order  # Ба модели худ истинод кунед
from sqlalchemy.sql import func
from aiogram.utils.keyboard import InlineKeyboardBuilder


# Функсияи барои гирифтани маводҳои сабад
async def get_cart_items(user_id: int):
    session = SessionLocal()
    # Йом кардани сабад барои истифодабаранда
    result = await session.execute(select(Cart).filter(Cart.order.has(user_id=user_id)))
    cart = result.scalars().first()

    if not cart:
        return []  # Агар сабад пайдо нашавад, рӯйхат холӣ бармегардад

    cart_items = []
    # Ба ҳар як ашёи сабад маълумотро гирем
    for cart_item in cart.items:
        # Модели маҳсулот мувофиқи product_type
        product_model = globals().get(cart_item.product_type.capitalize())
        if product_model:
            product = await session.execute(select(product_model).filter(product_model.id == cart_item.product_id))
            product = product.scalars().first()
            
            if product:
                cart_items.append({
                    'name': product.name,
                    'price': product.price,
                    'quantity': cart_item.quantity,
                    'image_url': product.image_url
                })
    
    return cart_items

# Категорияҳои меню бо иловакунӣ барои нишон додани шумораи маҳсулот
categories = {
    "pizza": "🍕 Pizza",
    "combo": "🥙 Combo",
    "snacks": "🍟 Snacks",
    "desserts": "🍰 Desserts",
    "drinks": "🥤 Drinks",
    "sauces": "🧂 Sauces",
    "kidslove": "👶 Kids Love",
    "othergoods": "🛒 Other Goods"
}


# The model mappings
model_map = {
    "pizza": Pizza,
    "combo": Combo,
    "snacks": Snacks,
    "desserts": Desserts,
    "drinks": Drinks,
    "sauces": Sauces,
    "kidslove": Kids_Love,
    "othergoods": OtherGoods
}


# Функсия барои эҷоди клавиатура бо категорияҳо
async def get_category_keyboard():
    session = SessionLocal()
    keyboard_builder = InlineKeyboardBuilder()

    for key, label in categories.items():
        model = model_map.get(key)
        if model:
            # Қисми ҳисоб кардани шумораи маҳсулот
            stmt = select(func.count()).select_from(model)
            result = await session.execute(stmt)
            count = result.scalar() or 0
            
            # Илова кардани тугмаҳо бо маълумоти мувофиқ
            button_text = f"{label} ({count})"
            callback_data = f"category_{key}"
            keyboard_builder.button(text=button_text, callback_data=callback_data)

    # Танзими тугмаҳо дар сатри пайдарпай
    keyboard_builder.adjust(2)  # 2 тугма дар як сатр
    return keyboard_builder.as_markup()

# Create reply keyboard with styled options (to display at the bottom of the keyboard)
def get_main_menu_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    # Row with a single button centered
    keyboard.add(KeyboardButton(text="📋 Меню"))
    
    # Row with two buttons side by side
    keyboard.row(
        KeyboardButton(text="📦 Фармоишот"), 
        KeyboardButton(text="🛒 Сабад")
    )
    
    # Row with a single button spanning the width
    keyboard.add(KeyboardButton(text="👤 Маълумотҳои шахсии ман"))
    
    return keyboard
    
    
    

# Функсия барои эҷоди менюи асосӣ
async def main_menu():
    builder = InlineKeyboardBuilder()

    categories = [
        ("Пицца 🍕", "pizza"),
        ("Комбо 🍱", "combo"),
        ("Закуски 🍟", "snacks"),
        ("Десерты 🍰", "desserts"),
        ("Напитки 🥤", "drinks"),
        ("Соусы 🥫", "sauces"),
        ("Любят дети 🧸", "kids_love"),
        ("Другие товары 📦", "other_goods")
    ]

    # Илова кардани тугмаҳо ба клавиатура
    for name, callback_data in categories:
        builder.button(text=name, callback_data=callback_data)

    # Танзими 2 тугма дар як сатр
    builder.adjust(2)

    # Бозгардони клавиатура
    return builder.as_markup()


# Командоҳои бот
async def set_commands():
    from bot_file import bot
    commands = [
        types.BotCommand(command="/menu", description="Меню асосӣ"),
        types.BotCommand(command="/cart", description="Сабади ман"),
        types.BotCommand(command="/orders", description="Фармоишоти ман"),
        types.BotCommand(command="/profile", description="Маълумотҳои шахсии ман"),
        types.BotCommand(command="/admin_menu", description="Панели админ"),
    ]
    await bot.set_my_commands(commands)
    
    
    
# Функсия барои гирифтани таърихи фармоишҳо
async def get_order_history(user_id):
    session = SessionLocal()
    # Ҷустуҷӯи фармоишҳои истифодабаранда аз базаи додаҳо
    orders = session.query(Order).filter(Order.user_id == user_id).all()
    
    order_history = []
    for order in orders:
        order_details = {
            "status": order.status.value,
            "items": []
        }
        
        for item in order.cart.items:
            product_model = globals()[item.product_type.capitalize()]  # Барои муайян кардани таблитса
            product = session.query(product_model).filter(product_model.id == item.product_id).first()
            if product:
                order_details["items"].append({
                    "name": product.name,
                    "quantity": item.quantity,
                    "price": product.price,
                    "total_price": product.price * item.quantity,
                    "image_url": product.image_url
                })
        
        order_details["total_order_price"] = sum(item["total_price"] for item in order_details["items"])
        order_history.append(order_details)
    
    return order_history
    
    
# Логика барои истихроҷи маълумоти шахсӣ аз базаи маълумот
async def get_user_info(user_id: int):
    session = SessionLocal()
    # Дар база ҷустуҷӯи маълумоти корбар бо user_id
    result = await session.execute(
        select(Order).where(Order.user_id == user_id).order_by(Order.id.desc())
    )
    last_order = result.scalars().first()  # Охирин закази истифодабаранда

    if last_order:
        return {
            "name": last_order.customer_name,
            "phone": last_order.phone_number,
            "address": "Маълумот нест"  # Агар адрес надошта бошад
        }
    else:
        return {
            "name": "Ном муайян нашудааст",
            "phone": "Рақами телефон вуҷуд надорад",
            "address": "Адрес вуҷуд надорад"
        }
        
        
        

