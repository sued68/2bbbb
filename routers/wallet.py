from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import User
from auth import get_current_user

router = APIRouter()

@router.post("/deposit")
def deposit(amount: float,
            db: Session = Depends(get_db),
            user: User = Depends(get_current_user)):
    user.balance += amount
    db.commit()
    return {"balance": user.balance}
