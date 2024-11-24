from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from database.tables import *
import os
from dotenv import load_dotenv
import asyncmy

load_dotenv()
db_url=os.getenv("DATABASE_URL")


# Асинкронӣ пайвастшавӣ ба MySQL
engine = create_async_engine(db_url, echo=True)
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        # Сохтани ҳамаи таблицаҳо дар база
        await conn.run_sync(Base.metadata.create_all)