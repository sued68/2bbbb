from pydantic import BaseModel

class UserCreate(BaseModel):
    username: str
    password: str

class RoomCreate(BaseModel):
    name: str
    entry_fee: float
