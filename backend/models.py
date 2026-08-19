"""Four tables: User, Product, PriceHistory, Alert."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    name = Column(String, nullable=True)
    age = Column(Integer, nullable=True)
    profile_picture_url = Column(String, nullable=True)
    reset_code = Column(String, nullable=True)
    reset_code_expiry = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    products = relationship("Product", back_populates="owner", cascade="all, delete")


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String, nullable=False)
    url = Column(String, nullable=False)
    site = Column(String, nullable=False)
    target_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=True)
    last_checked = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    image_url = Column(String, nullable=True)
    category = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    matched_product_id = Column(Integer, ForeignKey("products.id"), nullable=True)

    owner = relationship("User", back_populates="products")
    price_history = relationship("PriceHistory", back_populates="product", cascade="all, delete")
    alerts = relationship("Alert", back_populates="product", cascade="all, delete")
    matched_product = relationship("Product", remote_side=[id])


class PriceHistory(Base):
    __tablename__ = "price_history"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    price = Column(Float, nullable=False)
    checked_at = Column(DateTime, default=datetime.utcnow)
    product = relationship("Product", back_populates="price_history")


class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    price_at_alert = Column(Float, nullable=False)
    channel = Column(String, nullable=False)
    sent_at = Column(DateTime, default=datetime.utcnow)
    product = relationship("Product", back_populates="alerts")