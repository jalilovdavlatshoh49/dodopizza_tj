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












        
        
