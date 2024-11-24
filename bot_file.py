import os
from dotenv import load_dotenv
from aiogram import Bot

load_dotenv()

# Токени боти Telegram-и худро ворид кунед
API_TOKEN = os.getenv("API_BOT_TOKEN")

# Танзими бот ва диспетчер
bot = Bot(token=API_TOKEN)