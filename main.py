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

# PostgreSQL байланысын бастау
engine = sqlalchemy.create_engine(str(database.url))
metadata.create_all(engine)
templates = Jinja2Templates(directory="templates")

# SMS Aero параметрлері
SMS_API_KEY = "OOz_jt9g1TfWYsGwbMaMU-DTwBrBVeZq"  # Құпия кілтіңіз
SMS_SIGN = "SMS Aero"  # Жалпы sender аты

# Уақытша SMS кодтар
sms_codes = {}

# Телефонды тазалау
def clean_phone(phone: str) -> str:
    phone = phone.replace("+7", "7")
    return phone.replace("(", "").replace(")", "").replace(" ", "").replace("-", "")

# База қосу/ажырату
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

# SMS код жіберу
@app.post("/send_code")
async def send_code(phone: str = Form(...)):
    cleaned = clean_phone(phone)
    code = str(random.randint(100000, 999999))
    sms_codes[cleaned] = code

    print(f"[SMS] Код {code} жіберілді: {cleaned}")

    url = "https://gate.smsaero.kz/v2/sms/send"
    headers = {
        "Authorization": f"Bearer {SMS_API_KEY}"
    }
    payload = {
        "sign": SMS_SIGN,
        "channel": "DIRECT",
        "number": cleaned,
        "text": f"Код: {code} (super-bot.kz)",
        "type": "plain",
        "dateSend": ""
    }

    response = requests.post(url, json=payload, headers=headers)
    data = response.json()

    if response.status_code == 200 and data.get("success"):
        return JSONResponse({"ok": True, "msg": "Код жіберілді ✅"})
    else:
        return JSONResponse({"ok": False, "msg": f"Қате: код жіберілмеді ❌ ({data})"}, status_code=500)

# Кодты тексеру
@app.post("/verify_code")
async def verify_code(phone: str = Form(...), code: str = Form(...)):
    cleaned = clean_phone(phone)
    expected_code = sms_codes.get(cleaned)

    print(f"[VERIFY] Күтілген код: {expected_code}, келген код: {code}, номер: {cleaned}")

    if expected_code == code:
        return JSONResponse({"success": True})
    return JSONResponse({"success": False})

# Пайдаланушыны тіркеу
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

    print(f"[REGISTER] Күтілген код: {expected_code}, енгізілген код: {sms_code}, номер: {cleaned}")

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

# Барлық қолданушыларды көру (админге арналған сілтеме)
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

# created_at бағанын қосу (бір рет қолдануға арналған)
@app.get("/add-created-at")
async def add_created_at_column():
    try:
        await database.execute(text(
            "ALTER TABLE users ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
        ))
        return {"ok": True, "msg": "✅ created_at бағаны қосылды"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

# Debug — база ішіндегі қолданушыларды JSON түрінде көру
@app.get("/debug-users")
async def debug_users():
    query = users.select().order_by(users.c.created_at.desc())
    result = await database.fetch_all(query)
    return [dict(u) for u in result]
