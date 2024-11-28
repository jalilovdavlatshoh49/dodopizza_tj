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
    user_id = Column(BigInteger, index=True)
    items = relationship("CartItem", back_populates="cart")
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    order = relationship("Order", back_populates="cart", uselist=False)

    async def add_item(self, session, product_type, product_id, quantity=1):
        result = await session.execute(select(CartItem).filter(
            CartItem.cart_id == self.id,
            CartItem.product_type == product_type,
            CartItem.product_id == product_id
        ))
        existing_item = result.scalars().first()

        if existing_item:
            existing_item.quantity += quantity
        else:
            new_item = CartItem(cart_id=self.id, product_type=product_type, product_id=product_id, quantity=quantity)
            session.add(new_item)

    async def remove_item(self, session, product_type, product_id):
        result = await session.execute(select(CartItem).filter(
            CartItem.cart_id == self.id,
            CartItem.product_type == product_type,
            CartItem.product_id == product_id
        ))
        existing_item = result.scalars().first()

        if existing_item:
            await session.delete(existing_item)

    async def get_total_price(self, session):
        total_price = 0
        for item in self.items:
            product_model = globals().get(item.product_type.capitalize())
            if product_model:
                result = await session.execute(select(product_model).filter(product_model.id == item.product_id))
                product = result.scalars().first()
                if product:
                    total_price += product.price * item.quantity
        return total_price


async def init_db():
    async with engine.begin() as conn:
        # Сохтани ҳамаи таблицаҳо дар база
        await conn.run_sync(Base.metadata.create_all)