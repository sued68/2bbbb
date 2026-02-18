import random
from models import CalledNumber, Card

def generate_card():
    numbers = random.sample(range(1, 101), 25)
    return ",".join(map(str, numbers))

def call_unique_number(db, room_id):
    used = db.query(CalledNumber).filter_by(room_id=room_id).all()
    used_numbers = [u.number for u in used]

    available = list(set(range(1, 101)) - set(used_numbers))
    if not available:
        return None

    number = random.choice(available)
    db.add(CalledNumber(room_id=room_id, number=number))
    db.commit()
    return number

def check_full_house(card_numbers, called_numbers):
    card_set = set(map(int, card_numbers.split(",")))
    return card_set.issubset(set(called_numbers))

def detect_winner(db, room_id):
    called = db.query(CalledNumber).filter_by(room_id=room_id).all()
    called_numbers = [c.number for c in called]

    cards = db.query(Card).filter_by(room_id=room_id).all()
    for card in cards:
        if check_full_house(card.numbers, called_numbers):
            card.is_winner = 1
            db.commit()
            return card.user_id
    return None
