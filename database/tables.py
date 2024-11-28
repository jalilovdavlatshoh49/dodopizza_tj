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



class CartItem(Base):
    __tablename__ = 'cart_item'
    
    id = Column(Integer, primary_key=True, index=True)
    product_type = Column(String(255), index=True)  # Навъи маҳсулот
    product_id = Column(Integer, index=True)  # Идентификатори маҳсулот аз таблитсаи асосӣ
    quantity = Column(Integer, default=1)  # Миқдор
    cart_id = Column(Integer, ForeignKey('cart.id'))  # ID сабад
    cart = relationship("Cart", back_populates="items")



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

class Cart(Base):
    __tablename__ = 'cart'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, index=True)  # Add this field to link the cart with a user
    items = relationship("CartItem", back_populates="cart")  # Items in the cart
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)  # Status of the order
    order = relationship("Order", back_populates="cart", uselist=False)

    def add_item(self, product_type, product_id, quantity=1):
        item = next((item for item in self.items if item.product_type == product_type and item.product_id == product_id), None)
        if item:
            item.quantity += quantity  # If the product already exists, increase the quantity
        else:
            new_item = CartItem(product_type=product_type, product_id=product_id, quantity=quantity)
            self.items.append(new_item)  # Add the new product to the cart

    def remove_item(self, product_type, product_id):
        self.items = [item for item in self.items if not (item.product_type == product_type and item.product_id == product_id)]

    def get_total_price(self, session):
        total_price = 0
        for item in self.items:
            product_model = globals()[item.product_type.capitalize()]  # Determine the table
            product = session.query(product_model).filter(product_model.id == item.product_id).first()
            if product:
                total_price += product.price * item.quantity
        return total_price
        
        
