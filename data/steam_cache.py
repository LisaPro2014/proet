import sqlalchemy
import datetime
from data.db_session import SqlAlchemyBase

class SteamCache(SqlAlchemyBase):
    __tablename__ = 'steam_cache'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    key_name = sqlalchemy.Column(sqlalchemy.String(50), unique=True, nullable=False) 
    data_json = sqlalchemy.Column(sqlalchemy.Text, nullable=False) 
    updated_at = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.now) 