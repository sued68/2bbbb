from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import GameRoom, User
from auth import get_admin_user
from game_engine import call_unique_number, detect_winner

router = APIRouter()

@router.post("/rooms/{room_id}/start")
def start_game(room_id: int,
               db: Session = Depends(get_db),
               admin: User = Depends(get_admin_user)):
    room = db.query(GameRoom).get(room_id)
    room.status = "active"
    db.commit()
    return {"status": "Game started"}

@router.post("/rooms/{room_id}/call")
def call_number(room_id: int,
                db: Session = Depends(get_db),
                admin: User = Depends(get_admin_user)):
    number = call_unique_number(db, room_id)
    winner_id = detect_winner(db, room_id)
    return {"number_called": number, "winner": winner_id}
