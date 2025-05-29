from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from database import database, users, metadata
import sqlalchemy
import random
import requests
from datetime import datetime
from sqlalchemy import text

app = FastAPI()

# PostgreSQL engine және Jinja шаблондар
engine = sqlalchemy.create_engine(str(database.url))
metadata.create_all(engine)
templates = Jinja2Templates(directory="templates")

# Textbelt API
SMS_API_KEY = "58ed0414c9e959d68d66c2b55e0a4c576e2a4c52BgRzbptGWysU5P2wvItnvUbHD"

# СМС кодтарды уақытша сақтау
sms_codes = {}

# Телефон форматтау
def clean_phone(phone: str) -> str:
    return phone.replace("+7", "7").replace("(", "").replace(")", "").replace(" ", "").replace("-", "")

# Базамен байланыс
@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

# Басты бет
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Тіркелу беті
@app.get("/register", response_class=HTMLResponse)
async def register_form(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

# ✅ СМС код жіберу және нөмірді тексеру
@app.post("/send_code")
async def send_code(phone: str = Form(...)):
    cleaned = clean_phone(phone)

    # Егер нөмір бұрын тіркелген болса
    query = users.select().where(users.c.phone == phone)
    user_exists = await database.fetch_one(query)
    if user_exists:
        return JSONResponse({
            "ok": False,
            "msg": "Бұл нөмір тіркелген",
            "exists": True
        })

    # Код генерациялау және сақтау
    code = str(random.randint(100000, 999999))
    sms_codes[cleaned] = code
    print(f"[SMS] Код {code} жіберілді: {cleaned}")

    payload = {
        "phone": cleaned,
        "message": f"Кіру коды: {code}",
        "key": SMS_API_KEY
    }

    response = requests.post("https://textbelt.com/text", data=payload)

    try:
        data = response.json()
    except Exception as e:
        return JSONResponse({"ok": False, "msg": f"JSON қатесі: {str(e)}", "raw": response.text}, status_code=500)

    if data.get("success"):
        return JSONResponse({"ok": True, "msg": "Код жіберілді ✅"})
    else:
        return JSONResponse({"ok": False, "msg": "Қате: код жіберілмеді ❌", "data": data}, status_code=500)

# ✅ СМС кодты тексеру
@app.post("/verify_code")
async def verify_code(phone: str = Form(...), code: str = Form(...)):
    cleaned = clean_phone(phone)
    expected_code = sms_codes.get(cleaned)

    if expected_code == code:
        return JSONResponse({"success": True})
    return JSONResponse({"success": False})

# ✅ Қолданушыны тіркеу
@app.post("/register_user")
async def register_user(
    first_name: str = Form(...),
    last_name: str = Form(...),
    phone: str = Form(...),
    password: str = Form(...),
    sms_code: str = Form(...)
):
    cleaned = clean_phone(phone)
    expected_code = sms_codes.get(cleaned)

    if not expected_code or sms_code != expected_code:
        return JSONResponse({"ok": False, "msg": "❌ Код дұрыс емес"}, status_code=400)

    query = users.insert().values(
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        password=password,
        created_at=datetime.utcnow()
    )
    await database.execute(query)
    print("✅ Пайдаланушы тіркелді:", phone)
    return JSONResponse({"ok": True, "msg": "✅ Пайдаланушы тіркелді!"})

# 🔐 Барлық қолданушылар (тек админге)
@app.get("/users{admin_code}", response_class=HTMLResponse)
async def view_all_users(request: Request, admin_code: str):
    if admin_code != "190340006343":
        return templates.TemplateResponse("user_not_found.html", {
            "request": request,
            "phone": admin_code
        })

    query = users.select().order_by(users.c.created_at.desc())
    user_list = await database.fetch_all(query)

    return templates.TemplateResponse("user_list.html", {
        "request": request,
        "users": user_list
    })

# ✅ created_at бағанын қосу (бір рет қолданылады)
@app.get("/add-created-at")
async def add_created_at_column():
    try:
        await database.execute(text(
            "ALTER TABLE users ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
        ))
        return {"ok": True, "msg": "✅ created_at бағаны қосылды"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

# ✅ Барлық қолданушыларды JSON арқылы көру (debug)
@app.get("/debug-users")
async def debug_users():
    query = users.select().order_by(users.c.created_at.desc())
    result = await database.fetch_all(query)
    return [dict(u) for u in result]
