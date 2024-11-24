from aiogram import Router, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from aiogram.filters import CommandStart
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from functions.all_func import get_category_keyboard
from database.tables import Pizza, Combo, Snacks, Desserts, Drinks, Sauces, Kids_Love, OtherGoods
from database.db import SessionLocal

start_router = Router()


# Handle the start command
@start_router.message(CommandStart())
async def start_handler(message: types.Message):
    keyboard = await get_category_keyboard()
    await message.answer(
        "Хуш омадед ба бот!",
        reply_markup=keyboard
    )



# Callback handler to display products based on category
@start_router.callback_query(lambda c: c.data.startswith("category_"))
async def category_handler(callback_query: types.CallbackQuery):
    category = callback_query.data.split("_")[1]  # Extract category from callback data
    session = SessionLocal()
    # Query products from the database based on category
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
    
    model = model_map.get(category)
    if model:
        stmt = select(model)
        results = await session.execute(stmt)
        products = results.scalars().all()
        
        total_products = len(products)  # Ҳисоби теъдоди умумии маҳсулот
        displayed_products = 0  # Теъдоди маҳсулотҳои намоишшуда
        
        if products:
            for product in products:
                caption = (
                    f"🔸 **{product.name}**\n"
                    f"Описание: {product.description}\n"
                )
                
                # Тугмаи "Харид" бо нарх
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=f"Харид {product.price} сомонӣ", callback_data=f"buy_{product}_{product.id}")]
                ])
                
                if product.image_url:
                    await callback_query.message.answer_photo(
                        photo=product.image_url, 
                        caption=caption, 
                        reply_markup=keyboard, 
                        parse_mode="Markdown"
                    )
                else:
                    await callback_query.message.answer(caption, reply_markup=keyboard, parse_mode="Markdown")
                
                displayed_products += 1  # Теъдоди намоишшударо зиёд кун
                
           
                text = f"📋 Аз {total_products} намуди маҳсулот, {displayed_products} нишон дода шуд."
                
                exit_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=f"Назад", callback_data=f"exit_to_main_menu")]
                ])
                
                await callback_query.message.answer(text = text, reply_markub=exit_keyboard, parse_mode="Markdown")
        else:
            await callback_query.message.answer("Маҳсулот дар ин категория ёфт нашуд.")
        
    await callback_query.answer()



# Ҳангоми пахши тугмаи "Назад", ин функсия фаро гирифта мешавад
@start_router.callback_query(lambda c: c.data == "exit_to_main_menu")
async def exit_to_main_menu_handler(callback_query: CallbackQuery):
    bot = callback_query.bot
    keyboard = await get_category_keyboard()
    await bot.edit_message_reply_markup(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        reply_markup=keyboard
    )