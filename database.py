from sqlalchemy import Table, Column, Integer, String, MetaData
from databases import Database

DATABASE_URL = "postgresql://superbotdb_rclo_user:XcneYfZI...@dpg-d0rhlbjui...a:5432/superbotdb_rclo"

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
