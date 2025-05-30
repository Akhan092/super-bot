from sqlalchemy import Table, Column, Integer, String, DateTime, MetaData
from databases import Database
from datetime import datetime

DATABASE_URL = "postgresql://...ваш_url..."

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
    Column("user_id", Integer),  # Қай қолданушы қосқанын сақтау
    Column("login", String(100), nullable=False),
    Column("password", String(255), nullable=False),
    Column("shop_name", String(255)),
    Column("created_at", DateTime, default=datetime.utcnow)
)
