from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, JSON, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    photo_url = Column(String, nullable=True)
    
    balance_ton = Column(Integer, default=0)  # баланс в звёздах
    balance_ton = Column(Float, default=0.0)    # баланс в TON
    
    total_deposited = Column(Integer, default=0)
    total_withdrawn = Column(Integer, default=0)
    
    is_banned = Column(Boolean, default=False)
    last_free_case = Column(DateTime, nullable=True)  # когда последний раз открывал фри кейс
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)
    
    inventory = relationship("InventoryItem", back_populates="user")
    transactions = relationship("Transaction", back_populates="user")


class InventoryItem(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    gift_id = Column(String, nullable=False)      # id подарка
    gift_name = Column(String, nullable=False)
    gift_type = Column(String, nullable=False)    # ordinary / nft / rare
    gift_image = Column(String, nullable=True)
    gift_value_ton = Column(Integer, default=0) # оценочная стоимость
    is_nft = Column(Boolean, default=False)
    
    obtained_from = Column(String, nullable=True) # case_free / case_cheap / case_selected / roulette / upgrade / crash
    obtained_at = Column(DateTime, default=datetime.utcnow)
    is_withdrawn = Column(Boolean, default=False)
    
    user = relationship("User", back_populates="inventory")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    type = Column(String, nullable=False)  # deposit / withdraw / open_case / game_bet / game_win
    amount_ton = Column(Integer, default=0)
    amount_ton = Column(Float, default=0.0)
    description = Column(String, nullable=True)
    status = Column(String, default="completed")  # pending / completed / failed
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="transactions")


class CaseOpen(Base):
    __tablename__ = "case_opens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    case_type = Column(String, nullable=False)  # free / cheap / selected
    cost_ton = Column(Integer, default=0)
    prize_gift_id = Column(String, nullable=True)
    prize_name = Column(String, nullable=True)
    prize_value = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class GameHistory(Base):
    __tablename__ = "game_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    game_type = Column(String, nullable=False)  # roulette / upgrade / crash
    bet_amount = Column(Integer, nullable=False)
    result = Column(String, nullable=True)
    win_amount = Column(Integer, default=0)
    multiplier = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
