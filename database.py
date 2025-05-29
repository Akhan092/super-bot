from sqlalchemy import Table, Column, Integer, String, MetaData
from databases import Database

# 🔐 PostgreSQL URL (егер GitHub-қа салсаңыз .env ішінде сақтаңыз)
DATABASE_URL = "postgresql://superbotdb_rclo_user:XcneYf7IkosTX2Rb2AbR14HvujBRyfKh@dpg-d0rh1bjuibrs73d82dpg-a:5432/superbotdb_rclo"

# 🔌 Асинхронды Database объект
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
    Column("password", String(255)),  # хэштелген пароль болуы мүмкін
)
