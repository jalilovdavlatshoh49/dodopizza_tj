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


class Cart(Base):
    __tablename__ = 'cart'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, index=True)  # Привязка корзины к пользователю
    items = relationship("CartItem", back_populates="cart")  # Товары в корзине
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)  # Статус заказа
    order = relationship("Order", back_populates="cart", uselist=False)

    async def add_item(self, product_type, product_id, quantity=1):
        session = SessionLocal()
        # Поиск существующего товара
        existing_item = next(
            (item for item in self.items if item.product_type == product_type and item.product_id == product_id),
            None
        )
        if existing_item:
            existing_item.quantity += quantity  # Увеличиваем количество
        else:
            new_item = CartItem(product_type=product_type, product_id=product_id, quantity=quantity)
            self.items.append(new_item)  # Добавляем новый товар
        await session.flush()  # Сохраняем изменения в сессии

    async def remove_item(self, product_type, product_id):
        session = SessionLocal()
        self.items = [item for item in self.items if not (item.product_type == product_type and item.product_id == product_id)]
        await session.flush()  # Сохраняем изменения в сессии

    async def get_total_price(self):
        session = SessionLocal()
        total_price = 0
        for item in self.items:
            # Поиск продукта через асинхронный запрос
            product_model = globals()[item.product_type.capitalize()]  # Определение таблицы
            result = await session.execute(select(product_model).filter(product_model.id == item.product_id))
            product = result.scalars().first()
            if product:
                total_price += product.price * item.quantity
        return total_price


async def init_db():
    async with engine.begin() as conn:
        # Сохтани ҳамаи таблицаҳо дар база
        await conn.run_sync(Base.metadata.create_all)