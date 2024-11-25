from bot_file import bot
import logging
from aiogram import Dispatcher
from handlers.start_handler import start_router
from handlers.sabad_handler import sabad_router
from handlers.menu_handler import menu_router
from handlers.reply_handler import reply_router
from handlers.admin_folder.admin_accept import admin_accept
from handlers.admin_folder.admin_menu_handler import admin_menu_router
from handlers.admin_folder.admin_add_func import admin_add_func_router
from handlers.admin_folder.admin_product_handler import admin_product_router
from aiogram.fsm.storage.memory import MemoryStorage
from functions.all_func import set_commands
from database.db import init_db


# Танзими логгирӣ
logging.basicConfig(level=logging.INFO)


dp = Dispatcher(storage=MemoryStorage())


# Функсияи асосӣ барои оғоз кардани бот
async def main():
    await init_db()
    await set_commands()
    
    dp.include_router(start_router)
    dp.include_router(menu_router)
    dp.include_router(admin_accept)
    dp.include_router(reply_accept)
    
    dp.include_router(admin_menu_router)
    dp.include_router(admin_add_func_router)
    dp.include_router(admin_product_router)
    # dp.bot['session'] = async_session()

    # Register router
    dp.include_router(sabad_router)

    # Оғози боти Telegram
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())