import datetime

import sqlalchemy

from db.db_session import SqlAlchemyBase


class User(SqlAlchemyBase):
    __tablename__ = 'users'

    user_id = sqlalchemy.Column(sqlalchemy.BIGINT, unique=True, primary_key=True)
    referer_first_level_id = sqlalchemy.Column(sqlalchemy.BIGINT, default=0)
    referer_second_level_id = sqlalchemy.Column(sqlalchemy.BIGINT, default=0)
    referer_third_level_id = sqlalchemy.Column(sqlalchemy.BIGINT, default=0)
    balance = sqlalchemy.Column(sqlalchemy.FLOAT, default=0)
    deposit = sqlalchemy.Column(sqlalchemy.Integer, default=0)
    subscription = sqlalchemy.Column(sqlalchemy.Boolean, default=False)
    user_tariff_id = sqlalchemy.Column(sqlalchemy.Integer, default=0)
    percent = sqlalchemy.Column(sqlalchemy.Integer, default=0)
    hold = sqlalchemy.Column(sqlalchemy.Integer, default=0)


class Tariff(SqlAlchemyBase):
    __tablename__ = 'tariffs'

    tariff_id = sqlalchemy.Column(sqlalchemy.Integer, autoincrement=True, primary_key=True)
    description = sqlalchemy.Column(sqlalchemy.VARCHAR(1000), default='')
    price = sqlalchemy.Column(sqlalchemy.Integer, nullable=False)
    name = sqlalchemy.Column(sqlalchemy.VARCHAR(1000), default='')
    active = sqlalchemy.Column(sqlalchemy.Boolean, default=True)
    daily_percent = sqlalchemy.Column(sqlalchemy.Integer, nullable=False)


class Transaction(SqlAlchemyBase):
    __tablename__ = 'transactions'

    transaction_id = sqlalchemy.Column(sqlalchemy.Integer, autoincrement=True, primary_key=True)
    amount_money = sqlalchemy.Column(sqlalchemy.FLOAT, default=0)
    amount = sqlalchemy.Column(sqlalchemy.FLOAT, default=0)
    ordered_the_withdrawal = sqlalchemy.Column(sqlalchemy.Integer, nullable=False)
    active = sqlalchemy.Column(sqlalchemy.Integer, default=True)
    user_id = sqlalchemy.Column(sqlalchemy.Integer, unique=True)
    requisites = sqlalchemy.Column(sqlalchemy.String, default='')
    user_name = sqlalchemy.Column(sqlalchemy.String, default='')
