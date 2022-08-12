import sqlalchemy.orm

from db import db_session
from db.__all_models import User


def deposit_funds_on_balance(user_id: int, balance: float):
    with db_session.create_session() as session:
        session: sqlalchemy.orm.Session
        with session.begin():
            user = session.query(User).where(User.user_id == user_id).first()
            user.balance += balance
