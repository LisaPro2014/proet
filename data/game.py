import sqlalchemy
from sqlalchemy import orm
from data.db_session import SqlAlchemyBase


class Game(SqlAlchemyBase):
    __tablename__ = 'games'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    name = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    cover_url = sqlalchemy.Column(sqlalchemy.String, nullable=True)

    users_link = orm.relationship("UserGame", back_populates="game")