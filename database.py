from sqlalchemy import Table, Column, Integer, String, DateTime, MetaData
from databases import Database
from datetime import datetime

# 🔐 PostgreSQL URL
DATABASE_URL = "postgresql://superbotdb_rclo_user:XcneYf7IkosTX2Rb2AbR14HvujBRyfKh@dpg-d0rh1bjuibrs73d82dpg-a:5432/superbotdb_rclo"

# 🔌 Асинхронды Database объектісі
database = Database(DATABASE_URL)
metadata = MetaData()

# 📦 Users кестесі
users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("first_name", String(100)),
    Column("last_name", String(100)),
    Column("phone", String(20), unique=True),
    Column("password", String(255)),
    Column("created_at", DateTime, default=datetime.utcnow)  # ✅ Тіркелу уақыты
)
