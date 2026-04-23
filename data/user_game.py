import sqlalchemy
from sqlalchemy import orm
from data.db_session import SqlAlchemyBase

class UserGame(SqlAlchemyBase):
    __tablename__ = 'user_game_links'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'))
    game_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('games.id'))
    playtime_forever = sqlalchemy.Column(sqlalchemy.Integer, default=0)
    last_played = sqlalchemy.Column(sqlalchemy.DateTime, nullable=True)

    user = orm.relationship("User", back_populates="games_link")
    game = orm.relationship("Game", back_populates="users_link")