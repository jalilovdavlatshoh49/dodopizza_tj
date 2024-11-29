from sqlalchemy import Enum, ForeignKey, Column, Integer, String, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import enum
from sqlalchemy import Float 

Base = declarative_base()


class Pizza(Base):
    __tablename__ = 'pizza'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), index=True)
    description = Column(String(512))
    price = Column(Integer)
    image_url = Column(String(512))  # Илова кардани сурат

class Combo(Base):
    __tablename__ = 'combo'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), index=True)
    description = Column(String(512))
    price = Column(Integer)
    image_url = Column(String(512))

class Snacks(Base):
    __tablename__ = 'snacks'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), index=True)
    description = Column(String(512))
    price = Column(Integer)
    image_url = Column(String(512))

class Desserts(Base):
    __tablename__ = 'desserts'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), index=True)
    description = Column(String(512))
    price = Column(Integer)
    image_url = Column(String(512))

class Drinks(Base):
    __tablename__ = 'drinks'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), index=True)
    description = Column(String(512))
    price = Column(Integer)
    image_url = Column(String(512))

class Sauces(Base):
    __tablename__ = 'sauces'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), index=True)
    description = Column(String(512))
    price = Column(Integer)
    image_url = Column(String(512))

class Kidslove(Base):
    __tablename__ = 'kids_love'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), index=True)
    description = Column(String(512))
    price = Column(Integer)
    image_url = Column(String(512))

class OtherGoods(Base):
    __tablename__ = 'other_goods'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), index=True)
    description = Column(String(512))
    price = Column(Integer)
    image_url = Column(String(512))



# Энам барои ҳолати заказ
class OrderStatus(enum.Enum):
    PENDING = "pending"          # Интизорӣ
    ACCEPTED = "accepted"        # Қабулшуда
    IN_PROGRESS = "in_progress"  # Дар роҳ
    DELIVERED = "delivered"      # Расонида шудааст
    CANCELLED = "cancelled"      # Бекоршуда

# Модели маҳсулот
class Product(Base):
    __tablename__ = 'product'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)  # Номи маҳсулот
    price = Column(Float, nullable=False)  # Нархи маҳсулот
    description = Column(String(255), nullable=True)  # Тавсифи маҳсулот







class Order(Base):
    __tablename__ = 'order'

    id = Column(Integer, primary_key=True, index=True)
    cart_id = Column(Integer, ForeignKey('cart.id'))  # Равиш ба сабад
    cart = relationship("Cart", back_populates="order")
    
    # Ҳолати заказ
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    
    # Маъзарат ва маълумоти рақами телефон
    customer_name = Column(String(255), index=True)  # Номи мизоҷ
    phone_number = Column(String(15), index=True)    # Рақами телефон (String барои +)

    # Барои пайгирии id-и Telegram
    user_id = Column(BigInteger, index=True)  # Telegram User ID

    # Маълумоти суроға
    address = Column(String(512), nullable=True)  # Суроғаи дастӣ
    latitude = Column(Float, nullable=True)       # Координатаҳои GPS
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




        
        
