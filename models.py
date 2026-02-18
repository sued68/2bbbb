from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from database import Base
import datetime

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    balance = Column(Float, default=0)
    role = Column(String, default="player")

class GameRoom(Base):
    __tablename__ = "rooms"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    entry_fee = Column(Float)
    jackpot = Column(Float, default=0)
    status = Column(String, default="waiting")

class Card(Base):
    __tablename__ = "cards"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    room_id = Column(Integer, ForeignKey("rooms.id"))
    numbers = Column(String)
    is_winner = Column(Integer, default=0)

class CalledNumber(Base):
    __tablename__ = "called_numbers"
    id = Column(Integer, primary_key=True)
    room_id = Column(Integer)
    number = Column(Integer)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
