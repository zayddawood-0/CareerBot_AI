"""
Hackathon MVP auth: the frontend generates a random session ID and stores it
in the browser (see README "Development Shortcuts"). We look it up here and
create a User row on first sight — no passwords, no JWTs.
"""
from fastapi import Header, Depends
from sqlalchemy.orm import Session

from database import get_db
from models.user import User


def get_current_user(
    x_session_id: str = Header(..., alias="X-Session-Id"),
    db: Session = Depends(get_db),
) -> User:
    user = db.query(User).filter(User.session_id == x_session_id).first()
    if user is None:
        user = User(session_id=x_session_id)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user
