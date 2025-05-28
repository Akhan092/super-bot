from sqlalchemy import Table, Column, Integer, String, MetaData
from databases import Database

DATABASE_URL = "sqlite:///./users.db"
database = Database(DATABASE_URL)
metadata = MetaData()

users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("first_name", String),
    Column("last_name", String),
    Column("phone", String),
    Column("password", String),
)