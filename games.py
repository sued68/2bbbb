from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import GameRoom, Card, User
from schemas import RoomCreate
from auth import get_current_user
from game_engine import generate_card

router = APIRouter()

@router.post("/rooms")
def create_room(room: RoomCreate,
                db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    new_room = GameRoom(name=room.name, entry_fee=room.entry_fee)
    db.add(new_room)
    db.commit()
    return {"message": "Room created"}

@router.post("/rooms/{room_id}/join")
def join_room(room_id: int,
              db: Session = Depends(get_db),
              user: User = Depends(get_current_user)):
    room = db.query(GameRoom).get(room_id)

    if user.balance < room.entry_fee:
        raise HTTPException(status_code=400, detail="Insufficient balance")

    user.balance -= room.entry_fee
    room.jackpot += room.entry_fee

    card_numbers = generate_card()
    card = Card(user_id=user.id, room_id=room_id, numbers=card_numbers)

    db.add(card)
    db.commit()

    return {"card": card_numbers}
