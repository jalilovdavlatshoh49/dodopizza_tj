from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Enum, BigInteger, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import joinedload
from database.tables import *
import os
from dotenv import load_dotenv
import asyncmy

load_dotenv()
db_url = os.getenv("DATABASE_URL")

# Асинкронӣ пайвастшавӣ ба MySQL
engine = create_async_engine(db_url, echo=True)

SessionLocal = async_sessionmaker(
    engine, 
    expire_on_commit=False, 
    class_=AsyncSession
)

# Асинкронӣ табдили коди таблицаҳо
Base = declarative_base()

class Order(Base):
    __tablename__ = 'order'

    id = Column(Integer, primary_key=True, index=True)
    cart_id = Column(Integer, ForeignKey('cart.id'))  # Равиш ба сабад
    cart = relationship("Cart", back_populates="order")

    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)

    customer_name = Column(String(255), index=True)  
    phone_number = Column(String(15), index=True)  

    user_id = Column(BigInteger, index=True)  

    address = Column(String(512), nullable=True)  
    latitude = Column(Float, nullable=True)       
    longitude = Column(Float, nullable=True)

    def __init__(self, cart, customer_name, phone_number, user_id, address=None, latitude=None, longitude=None):
        self.cart = cart
        self.customer_name = customer_name
        self.phone_number = phone_number
        self.user_id = user_id
        self.status = OrderStatus.PENDING
        self.address = address
        self.latitude = latitude
        self.longitude = longitude


class Cart(Base):
    __tablename__ = 'cart'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, index=True)  
    items = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")  
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)  
    order = relationship("Order", back_populates="cart", uselist=False)

    async def add_item(self, session, product_type: str, product_id: int, quantity: int = 1):
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

    async def remove_item(self, session, product_type: str, product_id: int):
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

    async def get_total_price(self, session) -> float:
        total_price = 0
        for item in self.items:
            product_model = globals().get(item.product_type.capitalize())
            if product_model:
                result = await session.execute(select(product_model).filter(product_model.id == item.product_id))
                product = result.scalars().first()
                if product:
                    total_price += product.price * item.quantity
        return total_price


class CartItem(Base):
    __tablename__ = 'cart_item'

    id = Column(Integer, primary_key=True, index=True)
    product_type = Column(String(255), index=True)
    product_id = Column(Integer, index=True)
    quantity = Column(Integer, default=1)
    cart_id = Column(Integer, ForeignKey('cart.id'))
    cart = relationship("Cart", back_populates="items")

    async def get_price(self, session) -> float:
        """Ҳисоби нархи маҳсулот."""
        product_model = globals().get(self.product_type.capitalize())
        if product_model:
            result = await session.execute(select(product_model).filter(product_model.id == self.product_id))
            product = result.scalars().first()
            if product:
                return product.price
        return 0

    async def get_total_price(self, session) -> float:
        price = await self.get_price(session)
        return price * self.quantity


    async def increase_quantity(self, session, amount: int = 1):
        """Зиёд кардани миқдори маҳсулот."""
        self.quantity += amount
        async with session.begin():
            await session.commit()

    async def decrease_quantity(self, session, amount: int = 1):
        """Кам кардани миқдори маҳсулот."""
        if self.quantity > amount:
            self.quantity -= amount
        else:
            async with session.begin():
                await session.delete(self)  # Агар миқдор ба 0 расад, маҳсулот нест мешавад
            await session.commit()



async def calculate_total_user_spending(user_id: int) -> float:
    """
    Ҳисоб кардани нархи умумии хариди як клиент.
    
    :param session: Сессияи асинхронии SQLAlchemy.
    :param user_id: ID-и корбар.
    :return: Нархи умумии хариди корбар.
    """

    async with SessionLocal() as session:
        total_spending = 0.0

        # Ҳамаи фармоишҳои корбарро гирд овардан
        result = await session.execute(
        select(Order).filter(Order.user_id == user_id)
    )
        orders = result.scalars().all()

        # Ҳисоб кардани нархи умумии ҳар як сабад
        for order in orders:
            total_spending += await order.cart.get_total_price(session)

        return total_spending




async def calculate_total_price_pending_cart(user_id: int) -> float:
    """
    Ҳисоб кардани нархи умумии ҳамаи сабадҳое, ки то ҳол фармоиш нашудаанд.

    :param user_id: ID-и корбар.
    :return: Нархи умумии сабадҳои то ҳол фармоишнашуда.
    """
    async with SessionLocal() as session:
        total_price = 0.0

        # Сабадҳои то ҳол фармоишнашудаи корбарро ёфтан
        result = await session.execute(
            select(Cart)
            .filter(Cart.user_id == user_id)
            .filter(Cart.order == None)  # Сабадҳое, ки фармоиш надоранд
            .options(joinedload(Cart.items))  # Пешакӣ бор кардани ашёҳои сабад
        )
        carts = result.unique().scalars().all()  # Ба натиҷаҳо .unique() татбиқ кардан

        # Ҳисоб кардани нархи умумии ҳамаи ашёҳои сабадҳои ёфтшуда
        for cart in carts:
            total_price += await cart.get_total_price(session)

        return total_price


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)