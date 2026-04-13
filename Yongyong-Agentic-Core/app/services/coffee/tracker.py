# app/services/coffee/tracker.py
from sqlalchemy.orm import Session
from app.database import CoffeeLog

def record_coffee(db: Session, caffeine_mg: int, drink_type: str, body_reaction: str):
    new_log = CoffeeLog(
        caffeine_mg=caffeine_mg,
        drink_type=drink_type,
        body_reaction=body_reaction
    )
    db.add(new_log)
    db.commit()
    db.refresh(new_log)
    return new_log