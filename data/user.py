from data.db_session import SqlAlchemyBase 
import sqlalchemy
from sqlalchemy import orm

class User(SqlAlchemyBase): 
    __tablename__ = 'users'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    email = sqlalchemy.Column(sqlalchemy.String(120), unique=True, nullable=True)
    password_hash = sqlalchemy.Column(sqlalchemy.String(256), nullable=True)
    steam_id = sqlalchemy.Column(sqlalchemy.String(50), unique=True, nullable=True)
    nickname = sqlalchemy.Column(sqlalchemy.Text, default="Новый игрок")
    avatar_url = sqlalchemy.Column(sqlalchemy.Text, default="https://avatars.steamstatic.com/fef49e7fa7e1997310d705b2a6158ff8dc1cdfeb_full.jpg")
    profile_json = sqlalchemy.Column(sqlalchemy.Text)

    games_link = orm.relationship("UserGame", back_populates="user", cascade="all, delete-orphan")