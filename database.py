from sqlalchemy import Table, Column, Integer, String, DateTime, MetaData
from databases import Database
from datetime import datetime

DATABASE_URL = "postgresql://superbotdb_rclo_user:XcneYf7IkosTX2Rb2AbR14HvujBRyfKh@dpg-d0rh1bjuibrs73d82dpg-a:5432/superbotdb_rclo"

database = Database(DATABASE_URL)
metadata = MetaData()

users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("first_name", String(100)),
    Column("last_name", String(100)),
    Column("phone", String(20), unique=True),
    Column("password", String(255)),
    Column("created_at", DateTime, default=datetime.utcnow)
)

kaspi_shops = Table(
    "kaspi_shops",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer),
    Column("login", String(100), nullable=False),
    Column("password", String(255), nullable=False),
    Column("shop_name", String(255)),
    Column("created_at", DateTime, default=datetime.utcnow)
)
