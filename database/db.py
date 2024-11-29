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


# Модели сабад
class Cart(Base):
    __tablename__ = 'cart'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, index=True)  # ID-и корбар
    items = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")  # Предметҳои сабад
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)  # Статуси сабад
    order = relationship("Order", back_populates="cart", uselist=False)

    async def add_item(self, product_type: str, product_id: int, quantity: int = 1):
        session = SessionLocal()
        result = await session.execute(
            select(CartItem).filter(
                CartItem.cart_id == self.id,
                CartItem.product_type == product_type,
                CartItem.product_id == product_id
            )
        )
        existing_item = result.scalars().first()

        if existing_item:
            existing_item.quantity += quantity
        else:
            new_item = CartItem(cart_id=self.id, product_type=product_type, product_id=product_id, quantity=quantity)
            session.add(new_item)

    async def remove_item(self, product_type: str, product_id: int):
        session = SessionLocal()
        result = await session.execute(
            select(CartItem).filter(
                CartItem.cart_id == self.id,
                CartItem.product_type == product_type,
                CartItem.product_id == product_id
            )
        )
        existing_item = result.scalars().first()

        if existing_item:
            await session.delete(existing_item)

    async def get_total_price(self) -> float:
        session = SessionLocal()
        """Ҳисоби нархи умумии сабад."""
        total_price = 0
        for item in self.items:
            product_model = globals().get(item.product_type.capitalize())
            if product_model:
                result = await session.execute(select(product_model).filter(product_model.id == item.product_id))
                product = result.scalars().first()
                if product:
                    total_price += product.price * item.quantity
        return total_price



# Модели маҳсулот дар сабад
class CartItem(Base):
    __tablename__ = 'cart_item'

    id = Column(Integer, primary_key=True, index=True)
    product_type = Column(String(255), index=True)  # Навъи маҳсулот
    product_id = Column(Integer, index=True)  # ID маҳсулот
    quantity = Column(Integer, default=1)  # Миқдори маҳсулот
    cart_id = Column(Integer, ForeignKey('cart.id'))  # ID сабад
    cart = relationship("Cart", back_populates="items")  # Системаи алоқаманд бо Cart

    async def get_price(self) -> float:
        session = SessionLocal()
        """Ҳисоби нархи маҳсулот."""
        product_model = globals().get(self.product_type.capitalize())
        if product_model:
            result = await session.execute(select(product_model).filter(product_model.id == self.product_id))
            product = result.scalars().first()
            if product:
                return product.price
        return 0

    async def get_total_price(self) -> float:
        session = SessionLocal()
        """Нархи умумии ин маҳсулот."""
        price = await self.get_price(session)
        return price * self.quantity

async def init_db():
    async with engine.begin() as conn:
        # Сохтани ҳамаи таблицаҳо дар база
        await conn.run_sync(Base.metadata.create_all)